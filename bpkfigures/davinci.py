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


def _walk_folders(folder):
    """Yield `folder` and every subfolder, recursively."""
    yield folder
    for sub in folder.GetSubFolderList() or []:
        yield from _walk_folders(sub)


def _find_pool_item(mp, identity):
    """The MediaPoolItem ANYWHERE in the pool matching this (scene, method, ext)
    identity, or None. Letter-agnostic, so a re-lettered clip is still found."""
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if p and _identity(p) == identity:
                return c
    return None


def _get_or_make_bin(mp, name):
    """Find (or create) a top-level Media Pool bin `name`; the root folder if no name."""
    root = mp.GetRootFolder()
    if not name:
        return root
    for sub in root.GetSubFolderList() or []:
        if sub.GetName() == name:
            return sub
    return mp.AddSubFolder(root, name) or root


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


# ── media-pool ingest (the one call render.py makes) ──────────────────────────
def _swap_refresh(item, src, edit_dir, ident, referenced):
    """Point `item` (a MediaPoolItem) at a fresh `.swap/<key>.<n><ext>` copy of `src`
    so Resolve actually re-reads the changed bytes (a same-path overwrite is cached).
    Updates the item EVERYWHERE it's used — the pool list AND any timeline instances —
    then prunes older `.swap` versions nothing references. Returns True on success."""
    prefix, method, ext = ident
    key = f"{prefix}_{method}"                        # letter-free swap lineage
    swap_dir = os.path.join(edit_dir, ".swap")
    os.makedirs(swap_dir, exist_ok=True)
    n = _next_counter(swap_dir, key, ext)
    new_path = os.path.join(swap_dir, f"{key}.{n}{ext}")
    shutil.copy2(src, new_path)
    if not item.ReplaceClip(new_path):
        try:
            os.remove(new_path)
        except OSError:
            pass
        return False
    _prune_swaps(swap_dir, key, ext, keep=new_path, referenced=referenced)
    return True


def ingest(edit_dir, import_name, bin_name=None, resolve=None):
    """Ensure `edit_dir/import_name` is in the DaVinci **Media Pool** so it shows up in
    the left-side master list, ready to drag:
      * NEW      -> ImportMedia into the per-scene bin `bin_name` (created if needed).
      * EXISTING -> refresh in place (the .swap trick), which also updates any timeline
                    instances, then restore the clean list name.
    Matched by letter-agnostic identity, so re-lettering is handled. Returns a short
    status; a 'skipped: …' when Resolve is unreachable (caller degrades to files-only)."""
    r = resolve or get_resolve()
    if r is None:
        return "skipped: resolve not reachable"
    proj = r.GetProjectManager().GetCurrentProject()
    if proj is None:
        return "skipped: no project"
    mp = proj.GetMediaPool()
    ident = _identity(import_name)
    if ident is None:
        return "skipped: unrecognized name"
    src = os.path.join(edit_dir, import_name)

    item = _find_pool_item(mp, ident)
    if item is None:                                 # NEW -> import into the scene bin
        prev = mp.GetCurrentFolder()
        mp.SetCurrentFolder(_get_or_make_bin(mp, bin_name))
        ok = bool(mp.ImportMedia([src]))
        if prev:
            mp.SetCurrentFolder(prev)
        return "imported to pool" if ok else "import failed"

    # EXISTING -> refresh in place (updates the pool item + any timeline instances)
    tl = proj.GetCurrentTimeline()
    referenced = _timeline_sources(tl) if tl else set()
    if not _swap_refresh(item, src, edit_dir, ident, referenced):
        return "refresh failed"
    # ReplaceClip may adopt the .swap basename in the list — restore the clean name
    try:
        if item.GetClipProperty("Clip Name") != import_name:
            item.SetClipProperty("Clip Name", import_name)
    except Exception:
        pass
    return "refreshed in pool"


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
