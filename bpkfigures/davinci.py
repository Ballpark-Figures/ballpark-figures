"""DaVinci Resolve scripting helpers (shared).

Connect to a running Resolve (macOS) and swap a re-rendered clip into the open
timeline IN PLACE. Everything degrades gracefully to a no-op when Resolve isn't
reachable (not installed — e.g. the WSL desktop — or not running), so callers
never have to guard the connection themselves.

NB the module is named `davinci` (not `resolve`) to avoid clashing with
`bpkfigures.resolve`, which is the scene-target address resolver.

## Why the `.swap/` dance
Within a single Resolve session, `ReplaceClip` on the SAME path does NOT re-read a
file whose bytes changed on disk (verified: media stays cached). Only pointing a
clip at a DIFFERENT path forces a fresh read. So:

  * `edit_clips/<name>` — the clean, always-latest import copy (stable name, good
    for alphabetical import ordering). Overwritten every render.
  * `edit_clips/.swap/<stem>.<n><ext>` — hidden, per-swap versioned copies. When a
    clip is already on the timeline, we write a NEW `.swap` file and `ReplaceClip`
    the timeline item onto it (different path -> real re-read), then prune older
    `.swap` files that nothing references. The hidden dir keeps versions out of the
    import view.
"""
import os
import shutil
import sys

_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
_LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"


# ── connection ────────────────────────────────────────────────────────────────
def get_resolve():
    """Return a connected Resolve app object, or None if unreachable."""
    if not os.path.exists(_LIB):
        return None  # Resolve not installed on this machine (e.g. WSL desktop)
    mods = os.path.join(_API, "Modules")
    if mods not in sys.path:
        sys.path.insert(0, mods)
    os.environ.setdefault("RESOLVE_SCRIPT_API", _API)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", _LIB)
    try:
        import DaVinciResolveScript as dvr
        return dvr.scriptapp("Resolve")  # None if Resolve isn't running
    except Exception:
        return None


def current_timeline(resolve=None):
    """Return (project, timeline) of what's open, or (None, None)."""
    r = resolve or get_resolve()
    if r is None:
        return None, None
    p = r.GetProjectManager().GetCurrentProject()
    if p is None:
        return None, None
    return p, p.GetCurrentTimeline()


# ── clip lookup ───────────────────────────────────────────────────────────────
def _clip_path(mpi):
    try:
        return mpi.GetClipProperty("File Path")
    except Exception:
        return None


def _video_items(timeline):
    items = []
    for i in range(1, timeline.GetTrackCount("video") + 1):
        items.extend(timeline.GetItemListInTrack("video", i) or [])
    return items


def _timeline_sources(timeline):
    """Set of absolute media paths every video item on the timeline references."""
    out = set()
    for ti in _video_items(timeline):
        mpi = ti.GetMediaPoolItem()
        p = _clip_path(mpi) if mpi else None
        if p:
            out.add(os.path.abspath(p))
    return out


def _identity(name):
    """(scene_prefix, method, ext) from a clip filename — the LETTER-AGNOSTIC
    identity. `01c_play_win.mp4` and `01b_play_win.mp4` both map to ('01',
    'play_win', '.mp4'), so a subscene keeps its identity across re-lettering:
    split/merge/remove shifts the positional LETTER but never the @subscene
    METHOD NAME. Returns None if the basename isn't a subscene clip.

    (The trailing `_still` rides along in `method` — `play_win_still` — so a still
    matches its own re-lettered self and never the anim.)"""
    stem, ext = os.path.splitext(os.path.basename(name))
    if len(stem) < 3 or "_" not in stem[2:]:
        return None
    prefix, rest = stem[:2], stem[2:]           # "01", "c_play_win" | "_board_still"
    _label, method = rest.split("_", 1)         # "c","play_win" | "","board_still"
    # a .swap copy is `<prefix>_<method>.<n><ext>` — strip the trailing ".<n>" version
    # so `.swap/04_board.1.mp4` resolves to the same (04, board) as `04c_board.mp4`
    # (method names are Python identifiers, so a numeric ".<n>" tail is always the version)
    if "." in method:
        head, tail = method.rsplit(".", 1)
        if tail.isdigit():
            method = head
    return (prefix, method, ext)


def _find_item_by_identity(timeline, identity):
    """Return the MediaPoolItem of the timeline clip with this (scene, method, ext)
    identity, or None. Letter-agnostic, so a re-lettered clip is still found and
    re-pointed rather than left offline."""
    for ti in _video_items(timeline):
        mpi = ti.GetMediaPoolItem()
        p = _clip_path(mpi) if mpi else None
        if p and _identity(p) == identity:
            return mpi
    return None


def _next_counter(swap_dir, stem, ext):
    n = 0
    if os.path.isdir(swap_dir):
        for f in os.listdir(swap_dir):
            s, e = os.path.splitext(f)
            if e == ext and s.startswith(stem + "."):
                tail = s[len(stem) + 1:]
                if tail.isdigit():
                    n = max(n, int(tail))
    return n + 1


def _prune_swaps(swap_dir, stem, ext, keep, referenced):
    """Delete `.swap/<stem>.<n><ext>` files except `keep` and any still referenced."""
    keep = os.path.abspath(keep)
    for f in os.listdir(swap_dir):
        s, e = os.path.splitext(f)
        if e != ext or not s.startswith(stem + "."):
            continue
        full = os.path.abspath(os.path.join(swap_dir, f))
        if full != keep and full not in referenced:
            try:
                os.remove(full)
            except OSError:
                pass


# ── the one call render.py makes ──────────────────────────────────────────────
def swap_if_live(edit_dir, import_name, resolve=None):
    """If the clip `edit_dir/import_name` is already on the open timeline, swap in
    its freshly-written bytes (via a new `.swap` copy so Resolve actually re-reads).

    Returns a short status string:
      'skipped: resolve not reachable' | 'skipped: no timeline' |
      'not on timeline (import it once)' | 'replaced' | 'replace failed'
    """
    r = resolve or get_resolve()
    if r is None:
        return "skipped: resolve not reachable"
    proj, tl = current_timeline(r)
    if tl is None:
        return "skipped: no timeline"

    ident = _identity(import_name)
    if ident is None:
        return "skipped: unrecognized name"
    mpi = _find_item_by_identity(tl, ident)          # matches across re-lettering
    if mpi is None:
        return "not on timeline (import it once)"

    prefix, method, ext = ident
    key = f"{prefix}_{method}"                        # letter-free swap lineage
    swap_dir = os.path.join(edit_dir, ".swap")
    os.makedirs(swap_dir, exist_ok=True)
    n = _next_counter(swap_dir, key, ext)
    new_path = os.path.join(swap_dir, f"{key}.{n}{ext}")
    shutil.copy2(os.path.join(edit_dir, import_name), new_path)

    if not mpi.ReplaceClip(new_path):
        try:
            os.remove(new_path)
        except OSError:
            pass
        return "replace failed"

    _prune_swaps(swap_dir, key, ext, keep=new_path, referenced=_timeline_sources(tl))
    return "replaced"


def orphan_clips(prefix, current_methods, resolve=None):
    """Media paths of video clips ON the open timeline for scene `prefix` whose
    @subscene METHOD no longer exists (the merge/remove case). Read-only — deleting
    a placed clip is the user's call, so this only REPORTS. `current_methods` is the
    scene's live @subscene method-name list (bpkfigures.resolve.subscene_methods)."""
    r = resolve or get_resolve()
    if r is None:
        return []
    _p, tl = current_timeline(r)
    if tl is None:
        return []
    keep = set(current_methods)
    orphans = []
    for ti in _video_items(tl):
        mpi = ti.GetMediaPoolItem()
        p = _clip_path(mpi) if mpi else None
        ident = _identity(p) if p else None
        if not ident or ident[0] != prefix:
            continue
        method = ident[1]
        base = method[:-6] if method.endswith("_still") else method   # strip trailing still
        if base == "lead" or base in keep:      # 'lead_still' -> 'lead' = the scene lead still
            continue
        orphans.append(p)
    return orphans
