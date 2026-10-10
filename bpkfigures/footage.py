"""Import a tree's FOOTAGE (non-manim clips) into its own DaVinci project.

    python -m bpkfigures.footage <tree-dir> [--timeline] [--switch] [--dry-run]

`<tree-dir>` is an animations tree: a video's `animations/` or its `bonus/`. Its
footage folder is `<repo>/footage/` for `animations/` (the long-standing place for
talking heads) and `<tree>/footage/` for any other tree, so the bonus video's clips
live in `bonus/footage/` beside its graphics. Files are taken in NAME order, which is
why recordings are named `A_intro.mov`, `B_wordle.mov`, ...: the letter IS the order.

  * Every clip not already in the Media Pool is imported into a `Footage` bin.
    A clip already there (matched by its file path) is left alone, so re-running
    after adding a clip imports just the new one.
  * `--timeline` also APPENDS, in name order, every clip not yet on the open timeline
    to its end (creating a timeline if the project has none). Placed clips are never
    moved or re-trimmed. A new clip whose letter sorts BEFORE one already placed is
    still appended at the end, and reported, since the API cannot insert mid-timeline.
  * The project is the tree's own (davinci.project_for_tree: `Wordle Bonus` for
    wordle's `bonus/`). With any other project open nothing is touched, unless
    `--switch`: then the open project is SAVED, the right one opened, the work done,
    it is saved, and the original reopened (davinci.in_project; whether undo history
    survives the round trip is untested).
  * `--dry-run` lists what it would import and append, and opens no connection.

One connection, one pass: everything is read, done and reported in a single run
(see CLAUDE.md § Scripting the user's open DaVinci project).
"""
import argparse
import os
import sys

from bpkfigures import davinci

VIDEO_EXTS = (".mov", ".mp4", ".m4v", ".mxf")
BIN = "Footage"


def repo_root(path):
    d = os.path.abspath(path)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    raise SystemExit(f"no git repo above {path}")


def footage_dir(tree):
    tree = os.path.abspath(tree)
    if os.path.basename(tree) == "animations":
        return os.path.join(repo_root(tree), "footage")
    return os.path.join(tree, "footage")


def clips(fdir):
    if not os.path.isdir(fdir):
        raise SystemExit(f"no footage folder: {fdir}")
    out = [os.path.join(fdir, f) for f in sorted(os.listdir(fdir))
           if not f.startswith(".") and os.path.splitext(f)[1].lower() in VIDEO_EXTS]
    if not out:
        raise SystemExit(f"no clips in {fdir}")
    return out


def _work(r, files, timeline):
    proj = r.GetProjectManager().GetCurrentProject()
    mp = proj.GetMediaPool()

    pooled = {}
    for folder in davinci._walk_folders(mp.GetRootFolder()):
        for c in folder.GetClipList() or []:
            p = davinci._clip_path(c)
            if p:
                pooled[os.path.abspath(p)] = c

    new = [f for f in files if f not in pooled]
    if new:
        prev = mp.GetCurrentFolder()
        mp.SetCurrentFolder(davinci._get_or_make_bin(mp, BIN))
        for item in mp.ImportMedia(new) or []:
            pooled[os.path.abspath(davinci._clip_path(item))] = item
        if prev:
            mp.SetCurrentFolder(prev)
    for f in files:
        tag = "imported" if f in new else "already in pool"
        if f not in pooled:
            tag = "IMPORT FAILED"
        print(f"  {os.path.basename(f):32s} {tag}")
    if not timeline:
        return 0 if all(f in pooled for f in files) else 1

    tl = proj.GetCurrentTimeline()
    if tl is None:
        tl = mp.CreateEmptyTimeline("Timeline 1")
        if tl is None:
            print("[footage] could not create a timeline")
            return 1
        print(f"[footage] created timeline {tl.GetName()!r}")
    placed = davinci._timeline_sources(tl)
    todo = [f for f in files if f in pooled and f not in placed]
    if not todo:
        print(f"[footage] every clip is already on {tl.GetName()!r}")
        return 0
    last_placed = max((f for f in files if f in placed), default=None)
    for f in todo:
        if last_placed and f < last_placed:
            print(f"  NOTE {os.path.basename(f)} sorts before {os.path.basename(last_placed)}, "
                  f"which is already placed; it goes at the END, move it by hand")
    got = mp.AppendToTimeline([pooled[f] for f in todo]) or []
    print(f"[footage] appended {len(got)} of {len(todo)} clip(s) to {tl.GetName()!r}:")
    for ti in got:
        mpi = ti.GetMediaPoolItem()
        kind, idx = ti.GetTrackTypeAndIndex() if hasattr(ti, "GetTrackTypeAndIndex") else ("?", "?")
        print(f"  {mpi.GetName() if mpi else ti.GetName():32s} {kind} {idx}")
    return 0 if len(got) >= len(todo) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tree", help="the animations tree: <video>/animations or <video>/bonus")
    ap.add_argument("--timeline", action="store_true",
                    help="also append unplaced clips, in name order, to the open timeline")
    ap.add_argument("--switch", action="store_true",
                    help="open the tree's project if another is open, then reopen it")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    tree = os.path.abspath(a.tree)
    project = davinci.project_for_tree(tree, repo_root(tree))
    files = [os.path.abspath(f) for f in clips(footage_dir(tree))]
    print(f"[footage] {len(files)} clip(s) in {footage_dir(tree)} -> project {project!r}, bin {BIN!r}")
    if a.dry_run:
        for f in files:
            print(f"  {os.path.basename(f)}")
        return 0

    r = davinci.get_resolve()
    if r is None:
        print("[footage] DaVinci Resolve is not reachable; nothing imported")
        return 1
    open_name = davinci.open_project_name(r)
    if open_name == project:
        return _work(r, files, a.timeline)
    if not a.switch:
        print(f"[footage] {open_name!r} is open, not {project!r}; open it (or pass --switch)")
        return 1
    with davinci.in_project(project, r) as ok:
        if not ok:
            return 1
        return _work(r, files, a.timeline)


if __name__ == "__main__":
    sys.exit(main())
