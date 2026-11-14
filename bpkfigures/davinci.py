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
import contextlib
import filecmp
import json
import os
import shutil
import sys
import time

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
    # Resolve's fusionscript library resets this process's locale to plain "C" when
    # it connects, which turns Python's default text encoding into ASCII: every
    # later open() without an encoding then dies on the first non-ASCII byte (it
    # broke `render NN all --stills` after subscene a, reading the next scene file).
    # So the locale is put back however the connection goes.
    import locale
    saved = locale.setlocale(locale.LC_ALL)
    try:
        import DaVinciResolveScript as dvr
        return dvr.scriptapp("Resolve")  # None if Resolve isn't running
    except Exception:
        return None
    finally:
        locale.setlocale(locale.LC_ALL, saved)


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


def _pool_item_current(item, name, src):
    """True if pool `item` is listed as `name` and its file has the same bytes as the
    staged `src` (its file is a `.swap/` copy, so compared by content)."""
    if item.GetName() != name:
        return False
    path = _clip_path(item)
    try:
        return bool(path) and filecmp.cmp(path, src, shallow=False)
    except OSError:
        return False


def _video_items(timeline):
    items = []
    for i in range(1, timeline.GetTrackCount("video") + 1):
        items.extend(timeline.GetItemListInTrack("video", i) or [])
    return items


def _audio_items(timeline):
    items = []
    for i in range(1, timeline.GetTrackCount("audio") + 1):
        items.extend(timeline.GetItemListInTrack("audio", i) or [])
    return items


def _timeline_sources(timeline):
    """Absolute media paths every timeline item references — VIDEO **and AUDIO**.

    The audio half matters once subscene clips carry sound effects: a clip dragged in
    puts its linked audio on an audio track, and `_prune_swaps` deletes any `.swap`
    copy this set does not name. Walking video alone would therefore delete a swap
    that only the audio side still points at, taking the timeline media OFFLINE.
    Cheap and harmless while every render is silent — the audio tracks are then empty
    or hold only VO and music, whose paths are not swap copies.
    """
    out = set()
    for ti in _video_items(timeline) + _audio_items(timeline):
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


def _pool_sources(mp):
    """Absolute media paths every media-pool item references."""
    out = set()
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if p:
                out.add(os.path.abspath(p))
    return out


def _walk_folders(folder):
    """Yield `folder` and every subfolder, recursively."""
    yield folder
    for sub in folder.GetSubFolderList() or []:
        yield from _walk_folders(sub)


def _staging_name(path):
    """The name of the staging dir a clip path lives in (`edit_clips`,
    `edit_clips_bonus`, ...), looking through a `.swap/` subdir."""
    d = os.path.dirname(os.path.abspath(path))
    if os.path.basename(d) == ".swap":
        d = os.path.dirname(d)
    return os.path.basename(d)


def _find_pool_item(mp, identity, scope=None):
    """The MediaPoolItem ANYWHERE in the pool matching this (scene, method, ext)
    identity, or None. Letter-agnostic, so a re-lettered clip is still found.
    `scope` (a staging-dir name) restricts the match to clips staged from that dir,
    so the main video's 01a and a bonus 01a are never mistaken for each other."""
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if p and _identity(p) == identity and \
                    (scope is None or _staging_name(p) == scope):
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
REPLACE_ATTEMPTS = 3      # ReplaceClip tries before a refresh counts as failed
REPLACE_WAIT = 1.0        # seconds between tries (Resolve may still be reading the file)


def _swap_refresh(item, src, edit_dir, ident, referenced):
    """Point `item` (a MediaPoolItem) at a fresh `.swap/<key>.<n><ext>` copy of `src`
    so Resolve actually re-reads the changed bytes (a same-path overwrite is cached).
    Updates the item EVERYWHERE it's used — the pool list AND any timeline instances —
    then prunes older `.swap` versions nothing references.

    Returns `(ok, new_path)`. On failure the `.swap` copy is LEFT on disk for the
    caller, which either imports it as a replacement item or removes it."""
    prefix, method, ext = ident
    key = f"{prefix}_{method}"                        # letter-free swap lineage
    swap_dir = os.path.join(edit_dir, ".swap")
    os.makedirs(swap_dir, exist_ok=True)
    n = _next_counter(swap_dir, key, ext)
    new_path = os.path.join(swap_dir, f"{key}.{n}{ext}")
    shutil.copy2(src, new_path)
    # ReplaceClip can report success WITHOUT re-pointing the item (seen 2026-10-06:
    # 64 clips across eight scenes stayed on the old copy, which the prune below then
    # deleted, taking them OFFLINE). So read the path back and retry, with a pause:
    # 2026-11-12 one clip (wheel-of-fortune 01d, the scene's largest, with sound)
    # failed both of two back-to-back tries, while Resolve may still have been reading
    # it from its import 11 minutes earlier. A failed try can still RENAME the item to
    # the .swap file's name, which the caller undoes.
    for attempt in range(REPLACE_ATTEMPTS):
        if attempt:
            time.sleep(REPLACE_WAIT)
        if item.ReplaceClip(new_path) and \
                os.path.abspath(_clip_path(item) or "") == os.path.abspath(new_path):
            _prune_swaps(swap_dir, key, ext, keep=new_path, referenced=referenced)
            return True, new_path
    return False, new_path


def _folder_of(mp, item):
    """The Media Pool folder holding `item`, or None."""
    want = item.GetMediaId()
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            if c.GetMediaId() == want:
                return folder
    return None


RENAME_ATTEMPTS = 3


def _set_name(item, name):
    """Give `item` the list name `name`, and return whether it now HAS it.

    Judged by reading the name back, never by SetClipProperty's return value, which
    is unreliable both ways: 2026-11-13 it returned False on a rename that worked.
    The read-back is the point. Before, a failed rename was swallowed, and
    wheel-of-fortune 11o sat in its bin as `11_round_4.1.mp4` (a .swap name a
    refresh gave it), sorted above 11a, with nothing reporting it."""
    for attempt in range(RENAME_ATTEMPTS):
        if attempt:
            time.sleep(REPLACE_WAIT)
        try:
            if item.GetClipProperty("Clip Name") == name:
                return True
            item.SetClipProperty("Clip Name", name)
            if item.GetClipProperty("Clip Name") == name:
                return True
        except Exception:
            pass
    return False


def _rename_warning(item, name):
    """'' when `item` is named `name`, else a loud note for the status line."""
    try:
        have = item.GetClipProperty("Clip Name")
    except Exception:
        have = "?"
    return ("" if have == name else
            f"; NAME NOT RESTORED: the pool shows it as {have!r}, not {name!r} "
            f"(rename it by hand, or re-run the render)")


def _replace_by_import(mp, item, new_path, import_name):
    """A refresh failed on an item NO timeline uses: import the fresh `.swap` copy
    (a new path, so Resolve reads the new bytes) into the same folder, give it the
    clean name, and delete the old item. Returns the new item on success (its name
    is the caller's to check); on failure None, and the old item is left as it was."""
    folder = _folder_of(mp, item) or mp.GetRootFolder()
    prev = mp.GetCurrentFolder()
    mp.SetCurrentFolder(folder)
    new_items = mp.ImportMedia([new_path]) or []
    if prev:
        mp.SetCurrentFolder(prev)
    if not new_items:
        return None
    _set_name(new_items[0], import_name)
    mp.DeleteClips([item])
    return new_items[0]


def ingest(edit_dir, import_name, bin_name=None, resolve=None, project=None,
           refresh=True):
    """Ensure `edit_dir/import_name` is in the DaVinci **Media Pool** so it shows up in
    the left-side master list, ready to drag:
      * NEW      -> ImportMedia into the per-scene bin `bin_name` (created if needed).
      * EXISTING -> refresh in place (the .swap trick), which also updates any timeline
                    instances, then restore the clean list name.
    Matched by letter-agnostic identity, so re-lettering is handled. Returns a short
    status; 'NOT IMPORTED: ...' (and the file QUEUED) when Resolve is installed but does
    not answer, 'skipped: ...' on a machine without it.

    `project`: the DaVinci project this file belongs in. If a different project is
    open, nothing is imported or refreshed — the file stays staged and the status
    names both projects, so a clip can never land in another video's edit.

    `refresh=False`: an EXISTING item is left alone ("already in pool") — for a clip
    whose bytes did not change (render skipped it as up to date), where a refresh
    would only churn `.swap/` copies. A missing one is still imported, and an existing
    one is still refreshed when its list name or its file is not the staged one: a
    skipped subscene can have been RE-LETTERED (a beat inserted before it), and the
    pool item must take the new name, or an earlier refresh may have missed it
    (2026-11-12: wheel-of-fortune 03's pie_12 kept the name 03w_pie_12, beside the
    real 03w, and a file two renders old)."""
    r = resolve or get_resolve()
    proj = r.GetProjectManager().GetCurrentProject() if r is not None else None
    if proj is None:
        if not os.path.exists(_LIB):
            return "skipped: no DaVinci Resolve on this machine"
        # Resolve is installed but did not answer (not running, no project open, or its
        # scripting down, as after a forced restart, 2026-11-14): QUEUE the file, so it
        # is imported the next time Resolve answers, rather than staged and forgotten
        if project:
            queue_pending(edit_dir, import_name, bin_name, project)
        why = "not running or its scripting is down" if r is None else "no project open"
        return (f"NOT IMPORTED: DaVinci did not answer ({why}); "
                + (f"QUEUED for {project!r}, imported on the next --stills render or "
                   f"`render --pending` once it answers" if project else "not queued"))
    if project and proj.GetName() != project:
        queue_pending(edit_dir, import_name, bin_name, project)
        return (f"QUEUED for {project!r} (open project is {proj.GetName()!r}); it is "
                f"imported the next time {project!r} is open and you render or run "
                f"`render --pending`")
    forget_pending(edit_dir, import_name)
    mp = proj.GetMediaPool()
    ident = _identity(import_name)
    if ident is None:
        return "skipped: unrecognized name"
    src = os.path.join(edit_dir, import_name)

    item = _find_pool_item(mp, ident, scope=os.path.basename(os.path.abspath(edit_dir)))
    if item is None:                                 # NEW -> import into the scene bin
        prev = mp.GetCurrentFolder()
        mp.SetCurrentFolder(_get_or_make_bin(mp, bin_name))
        ok = bool(mp.ImportMedia([src]))
        if prev:
            mp.SetCurrentFolder(prev)
        return "imported to pool" if ok else "import failed"
    if not refresh and _pool_item_current(item, import_name, src):
        return "already in pool"

    # EXISTING -> refresh in place (updates the pool item + any timeline instances).
    # A .swap copy survives the prune while ANYTHING points at it: any timeline's
    # items, AND any media-pool item — not just the open timeline's.
    on_timelines = set()
    for i in range(1, proj.GetTimelineCount() + 1):
        on_timelines |= _timeline_sources(proj.GetTimelineByIndex(i))
    referenced = _pool_sources(mp) | on_timelines
    old_path = os.path.abspath(_clip_path(item) or "")
    ok, new_path = _swap_refresh(item, src, edit_dir, ident, referenced)
    # ReplaceClip may adopt the .swap basename in the list (even when it FAILS to
    # re-point the item) — restore the clean name either way, and SAY so if it
    # does not take: a .swap name sorts the clip out of place in its bin
    _set_name(item, import_name)
    if ok:
        return "refreshed in pool" + _rename_warning(item, import_name)
    # Never leave a half-refreshed item behind. Not in the edit: swap the whole item.
    new_item = None if old_path in on_timelines else \
        _replace_by_import(mp, item, new_path, import_name)
    if new_item is not None:
        return ("refresh failed, so RE-IMPORTED as a new item "
                "(it was not on any timeline)" + _rename_warning(new_item, import_name))
    try:
        os.remove(new_path)
    except OSError:
        pass
    where = "is on a timeline and still shows" if old_path in on_timelines else \
        "could not be re-imported; it still shows"
    return f"REFRESH FAILED: {where} the PREVIOUS render" + \
        _rename_warning(item, import_name)


def missing_sfx_track(resolve=None):
    """The open timeline's name if it has NO audio track named `SFX`, else None (also
    None when Resolve or a timeline is not there to ask). Without that track a manim
    clip's sound effects drop onto a Music track, whose fader sits at -20 dB: a project
    made before the template gained the track (2026-10-04) has this, and it played
    wheel-of-fortune's effects ~20 dB quiet until 2026-11-12."""
    _p, tl = current_timeline(resolve)
    if tl is None:
        return None
    names = [tl.GetTrackName("audio", i) for i in range(1, tl.GetTrackCount("audio") + 1)]
    return None if "SFX" in names else tl.GetName()


# ── pending imports (clips staged while another project was open) ─────────────
# `<edit_dir>/.pending.json` maps a staged file name to {"bin", "project"}. ingest()
# adds an entry instead of importing into the wrong project, and flush_pending()
# imports the entries belonging to whichever project is open now. The file on disk is
# always the latest render, so an entry only remembers WHERE the file goes.
def _pending_path(edit_dir):
    return os.path.join(edit_dir, ".pending.json")


def _read_pending(edit_dir):
    try:
        with open(_pending_path(edit_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_pending(edit_dir, data):
    path = _pending_path(edit_dir)
    if not data:
        if os.path.exists(path):
            os.remove(path)
        return
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def queue_pending(edit_dir, import_name, bin_name, project):
    data = _read_pending(edit_dir)
    data[import_name] = {"bin": bin_name, "project": project}
    _write_pending(edit_dir, data)


def forget_pending(edit_dir, import_name):
    data = _read_pending(edit_dir)
    if data.pop(import_name, None) is not None:
        _write_pending(edit_dir, data)


def pending(edit_dir):
    """{name: {"bin", "project"}} still waiting to be imported from `edit_dir`."""
    return _read_pending(edit_dir)


def flush_pending(edit_dir, resolve=None):
    """Import every pending file from `edit_dir` that belongs in the OPEN project.
    Entries for other projects stay queued; entries whose file has been removed (the
    subscene was renamed or deleted) are dropped. Returns [(name, status)]."""
    r = resolve or get_resolve()
    data = _read_pending(edit_dir)
    if r is None or not data:
        return []
    proj = r.GetProjectManager().GetCurrentProject()
    open_name = proj.GetName() if proj else None
    out = []
    for name, entry in sorted(data.items()):
        if not os.path.exists(os.path.join(edit_dir, name)):
            forget_pending(edit_dir, name)
            out.append((name, "dropped: file no longer staged"))
        elif entry.get("project") == open_name:
            out.append((name, ingest(edit_dir, name, bin_name=entry.get("bin"),
                                     resolve=r, project=entry.get("project"))))
    return out


def project_for_tree(tree_dir, repo_root):
    """The DaVinci project a TREE's media belongs in (`animations/`, `bonus/`, ...).
    An explicit name in `<tree>/davinci_project` wins; otherwise the repo name in
    PascalCase (`wheel-of-fortune` -> `WheelOfFortune`), the way new-video names the
    project, plus ` Bonus` (the tree name, capitalised) for any tree other than
    `animations/`. The ONE statement of the rule: render.py's --stills and
    bpkfigures.footage both ask it, so a clip and a footage file of the same tree can
    never be routed to different projects."""
    override = os.path.join(tree_dir, "davinci_project")
    if os.path.isfile(override):
        with open(override, encoding="utf-8") as f:
            name = f.read().strip()
        if name:
            return name
    repo = os.path.basename(os.path.abspath(repo_root))
    name = "".join(w[:1].upper() + w[1:] for w in repo.split("-"))
    tree = os.path.basename(os.path.abspath(tree_dir))
    return name if tree == "animations" else f"{name} {tree.capitalize()}"


def open_project_name(resolve=None):
    """Name of the open DaVinci project, or None (Resolve unreachable / none open)."""
    r = resolve or get_resolve()
    if r is None:
        return None
    p = r.GetProjectManager().GetCurrentProject()
    return p.GetName() if p else None


@contextlib.contextmanager
def in_project(name, resolve=None):
    """Temporarily open project `name`, then put back whatever was open.

    Yields True when `name` is the open project inside the block, else False (Resolve
    unreachable, no such project, or a save/load failed — then nothing was switched
    and the caller should fall back to queueing). The ORIGINAL project is SAVED before
    switching away, `name` is saved before switching back, and the original is
    reopened even if the block raises. A no-op when `name` is already open."""
    r = resolve or get_resolve()
    if r is None:
        yield False
        return
    pm = r.GetProjectManager()
    cur = pm.GetCurrentProject()
    original = cur.GetName() if cur else None
    if original == name:
        yield True
        return
    if name not in (pm.GetProjectListInCurrentFolder() or []):
        print(f"[davinci] no project named {name!r} — not switching", file=sys.stderr)
        yield False
        return
    if cur is not None and not pm.SaveProject():
        print(f"[davinci] could not save {original!r} — not switching", file=sys.stderr)
        yield False
        return
    if not pm.LoadProject(name):
        print(f"[davinci] could not open {name!r} — not switching", file=sys.stderr)
        if original:
            pm.LoadProject(original)
        yield False
        return
    print(f"[davinci] switched {original!r} -> {name!r}", file=sys.stderr)
    try:
        yield True
    finally:
        pm.SaveProject()
        if original:
            if pm.LoadProject(original):
                print(f"[davinci] switched back to {original!r}", file=sys.stderr)
            else:
                print(f"[davinci] could NOT reopen {original!r} — open it by hand",
                      file=sys.stderr)


def _orphan_method(ident, prefix, keep):
    """True if a clip identity belongs to scene `prefix` but to NO current subscene."""
    if not ident or ident[0] != prefix:
        return False
    method = ident[1]
    base = method[:-6] if method.endswith("_still") else method   # strip trailing still
    # 'scene_end' = the scene's closing still; 'lead' = the pre-2026-10-06 lead still
    return not (base in ("scene_end", "lead") or base in keep)


def adopt_orphan_stills(prefix, current_methods, edit_dir, resolve=None, project=None):
    """A STILL of scene `prefix` whose subscene no longer exists (split, merged, renamed)
    but which a timeline still uses is re-pointed at the still now staged at its LETTER,
    and takes that still's name; the separately imported item for the new still is then
    deleted if no timeline uses it. So the edit shows the new frame (the user,
    2026-11-14: 17b_call_d_still stayed in the cut after 17b and c merged into calls).
    Safe for a still and not for a clip: a still is the frame before its beat starts,
    the same moment for the old beat and the new one at that letter, and refreshing a
    still keeps the duration it was stretched to; a clip's length changes, and swapping
    media under a placed clip resets its trims, so clips are only reported. Only runs
    with `project` open. Returns [(old name, new name)]."""
    r = resolve or get_resolve()
    if r is None:
        return []
    proj = r.GetProjectManager().GetCurrentProject()
    if proj is None or (project and proj.GetName() != project):
        return []
    used = set()
    for i in range(1, proj.GetTimelineCount() + 1):
        used |= _timeline_sources(proj.GetTimelineByIndex(i))
    mp = proj.GetMediaPool()
    scope = os.path.basename(os.path.abspath(edit_dir))
    keep = set(current_methods)
    staged = {}                                  # letter -> the still staged at it
    for f in os.listdir(edit_dir):
        ident = _identity(f)
        if ident and ident[0] == prefix and ident[1].endswith("_still") and \
                ident[2] == ".png" and not ident[1].startswith("scene_end"):
            staged[f[2:].split("_", 1)[0]] = f
    referenced = _pool_sources(mp) | used
    out = []
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if not p or _staging_name(p) != scope or os.path.abspath(p) not in used:
                continue
            ident = _identity(p)
            if not ident or ident[2] != ".png" or not _orphan_method(ident, prefix, keep):
                continue
            old = c.GetName()
            new = staged.get(old[2:].split("_", 1)[0])
            if new is None:
                continue
            new_ident = _identity(new)
            dup = _find_pool_item(mp, new_ident, scope=scope)
            ok, _path = _swap_refresh(c, os.path.join(edit_dir, new), edit_dir, new_ident,
                                      referenced)
            if not ok:
                continue
            _set_name(c, new)
            if dup is not None and dup.GetMediaId() != c.GetMediaId() and \
                    os.path.abspath(_clip_path(dup) or "") not in used:
                mp.DeleteClips([dup])
            out.append((old, new))
    return out


def prune_pool_orphans(prefix, current_methods, resolve=None, scope="edit_clips",
                       project=None):
    """DELETE from the media pool every clip of scene `prefix`, staged from `scope`,
    whose @subscene method no longer exists (a subscene renamed, merged or removed)
    — so a re-lettered scene does not leave two 07t's side by side. A clip still
    placed on ANY timeline is NOT deleted (that would pull it out of the edit); it is
    returned for the caller to report. Only runs with `project` open. Returns
    (deleted names, names kept because a timeline uses them)."""
    r = resolve or get_resolve()
    if r is None:
        return [], []
    proj = r.GetProjectManager().GetCurrentProject()
    if proj is None or (project and proj.GetName() != project):
        return [], []
    used = set()
    for i in range(1, proj.GetTimelineCount() + 1):
        used |= _timeline_sources(proj.GetTimelineByIndex(i))
    keep = set(current_methods)
    mp = proj.GetMediaPool()
    doomed, kept = [], []
    for folder in _walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if not p or _staging_name(p) != scope or not _orphan_method(_identity(p), prefix, keep):
                continue
            (kept if os.path.abspath(p) in used else doomed).append(c)
    names = [c.GetName() for c in doomed]
    if doomed and not mp.DeleteClips(doomed):
        names = []
    return names, [c.GetName() for c in kept]


def repair_pool_names(prefix, edit_dir, resolve=None, project=None):
    """Give every media-pool clip of scene `prefix` staged from `edit_dir` the name of
    the staged file it belongs to (`NN<letter>_<method>[_still].<ext>`), matched by
    letter-agnostic identity. Catches a clip left with ANY other name, whatever left
    it: a .swap name from a refresh (wheel-of-fortune 11o, 2026-11-13, listed as
    `11_round_4.1.mp4` above 11a) or a stale letter. Only runs with `project` open.
    Returns (renamed [(old, new)], failed [(old, wanted)])."""
    r = resolve or get_resolve()
    if r is None:
        return [], []
    proj = r.GetProjectManager().GetCurrentProject()
    if proj is None or (project and proj.GetName() != project):
        return [], []
    scope = os.path.basename(os.path.abspath(edit_dir))
    staged = {}
    for f in os.listdir(edit_dir):
        ident = _identity(f)
        if ident and ident[0] == prefix and f[2:3].isalpha():
            # a re-lettered beat can leave its old-letter file staged too: newest wins
            old = staged.get(ident)
            if old is None or os.path.getmtime(os.path.join(edit_dir, f)) > \
                    os.path.getmtime(os.path.join(edit_dir, old)):
                staged[ident] = f
    renamed, failed = [], []
    for folder in _walk_folders(proj.GetMediaPool().GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = _clip_path(c)
            if not p or _staging_name(p) != scope:
                continue
            want = staged.get(_identity(p))
            have = c.GetName()
            if want is None or have == want:
                continue
            (renamed if _set_name(c, want) else failed).append((have, want))
    return renamed, failed


def orphan_clips(prefix, current_methods, resolve=None, scope="edit_clips",
                 project=None):
    """Media paths of video clips ON the open timeline for scene `prefix` whose
    @subscene METHOD no longer exists (the merge/remove case). Read-only — deleting
    a placed clip is the user's call, so this only REPORTS. `current_methods` is the
    scene's live @subscene method-name list (bpkfigures.resolve.subscene_methods)."""
    r = resolve or get_resolve()
    if r is None:
        return []
    _p, tl = current_timeline(r)
    if tl is None or (project and _p.GetName() != project):
        return []
    keep = set(current_methods)
    orphans = []
    for ti in _video_items(tl):
        mpi = ti.GetMediaPoolItem()
        p = _clip_path(mpi) if mpi else None
        ident = _identity(p) if p else None
        if not ident or ident[0] != prefix or _staging_name(p) != scope:
            continue
        method = ident[1]
        base = method[:-6] if method.endswith("_still") else method   # strip trailing still
        # 'scene_end' = the scene's closing still; 'lead' = the pre-2026-10-06 lead still
        if base in ("scene_end", "lead") or base in keep:
            continue
        orphans.append(p)
    return orphans
