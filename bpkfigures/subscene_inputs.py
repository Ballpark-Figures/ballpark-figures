"""What each subscene READS: the non-code files it opens while it runs.

A subscene's clip depends on the files it opens while it runs (an image, a cache loaded
inside a beat). Files opened when the scene's modules are IMPORTED (`DATA = load()` at
module level) are not counted: what they hold reaches a beat only through a module
constant, and the snapshot digest already hashes the VALUE of every constant a beat reads
(scene `_reach_parts`), beat by beat. So a regenerated cache re-keys only the beats that
read what changed.

Until 2026-11-09 the render skip key hashed EVERY file under assets/ for every clip, so
regenerating one cache re-rendered the whole video; and the snapshot key hashed none, so
a changed image left stale snapshots behind.

HOW: `render` starts manim as `python -m bpkfigures.subscene_inputs <manim args>`. This
module watches (sys.monitoring, Python 3.12+) the scene's setup_scene and subscene
methods start and return, and an audit hook notes each file opened for READING while
one runs: under the scene's project tree (animations/) or bpkfigures/, not code, not
under cache/ or media/. Each record, {subscene: {path: md5}}, goes to
cache/snapshots/<Scene>_inputs.json when the subscene returns. NOTHING HERE IS IMPORTED
BY A SCENE: the snapshot and skip keys hash the code a scene reaches, so code in
scene.py would re-key every clip of every video whenever it changed.

render.py reads the records (`inputs_hash`, `stale_from`). A subscene with no record yet
(not run since) keeps the old whole-assets/ hash. Blind spot: a file read at import into
something whose repr is not stable (a module-level Mobject built from an image).
"""
import hashlib
import json
import os
import sys

SNAPSHOT_DIR = os.path.join("cache", "snapshots")      # as bpkfigures.scene's
SKIP_DIRS = {"cache", "media", "__pycache__"}
_BPK_DIR = os.path.dirname(os.path.realpath(__file__))


# ── the records (read by render.py) ───────────────────────────────────────────

def records_path(class_name):
    return os.path.join(SNAPSHOT_DIR, f"{class_name}_inputs.json")


def load_records(class_name):
    try:
        with open(records_path(class_name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def file_md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return "missing"


def inputs_hash(class_name, names, records=None):
    """Hash of the CURRENT contents of the files `names` (subscene names, with
    "setup_scene") were recorded reading, or None if any of them has no record."""
    rec = load_records(class_name) if records is None else records
    if any(n not in rec for n in names):
        return None
    files = sorted(set().union(*(rec[n] for n in names)))
    return hashlib.md5("".join(f + file_md5(f) for f in files).encode()).hexdigest()


def stale_from(class_name, names, records=None):
    """The index of the first subscene whose snapshot is stale because a file it (or
    setup_scene, or a subscene before it) read has changed since it last ran, or None.
    setup_scene counts as index 0."""
    rec = load_records(class_name) if records is None else records
    for i, name in enumerate(["setup_scene"] + list(names)):
        if any(file_md5(f) != md5 for f, md5 in rec.get(name, {}).items()):
            return max(i - 1, 0)
    return None


# ── the recorder (in the manim child) ─────────────────────────────────────────

class _Recorder:
    def __init__(self):
        self.roots = (os.path.realpath(os.path.join(os.getcwd(), "..")) + os.sep,
                      _BPK_DIR + os.sep)
        self.stack = []                 # [(name, set of files)] of running subscenes
        self.watched = {}               # code object -> subscene name
        self.class_name = None
        self.busy = False

    def audit(self, event, args):
        if event != "open" or not self.stack or self.busy:
            return
        self.busy = True
        try:
            path, mode, flags = (tuple(args) + (None, None, None))[:3]
            if isinstance(path, int):
                return
            if mode is not None:
                if any(c in str(mode) for c in "wax+"):
                    return
            elif flags and flags & (os.O_WRONLY | os.O_RDWR):
                return
            f = os.path.realpath(os.fsdecode(path))
            if f.endswith((".py", ".pyc")) or not f.startswith(self.roots):
                return
            if SKIP_DIRS & set(f.split(os.sep)):
                return
            self.stack[-1][1].add(f)
        except Exception:
            pass
        finally:
            self.busy = False

    def watch(self, scene_cls):
        """Start watching `scene_cls`'s setup_scene and subscenes (once)."""
        from bpkfigures.scene import _ordered_subscenes
        mon = sys.monitoring
        self.class_name = scene_cls.__name__
        for name in ["setup_scene"] + _ordered_subscenes(scene_cls):
            code = getattr(getattr(scene_cls, name, None), "__code__", None)
            if code is not None and code not in self.watched:
                self.watched[code] = name
                mon.set_local_events(self.tool, code,
                                     mon.events.PY_START | mon.events.PY_RETURN)

    def start(self, code, _offset):
        if code is self.construct:
            scene = sys._getframe(1).f_locals.get("self")
            if scene is not None:
                self.watch(type(scene))
        elif code in self.watched:
            self.stack.append((self.watched[code], set()))

    def finish(self, code, _offset, _retval):
        if code not in self.watched or not self.stack:
            return
        name, files = self.stack.pop()
        rec = load_records(self.class_name)
        rec[name] = {f: file_md5(f) for f in sorted(files)}
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        tmp = records_path(self.class_name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=0, sort_keys=True)
        os.replace(tmp, records_path(self.class_name))

    def install(self):
        from bpkfigures.scene import BpkScene
        mon = sys.monitoring
        self.tool = next(i for i in range(6) if mon.get_tool(i) is None)
        mon.use_tool_id(self.tool, "bpkfigures.subscene_inputs")
        mon.register_callback(self.tool, mon.events.PY_START, self.start)
        mon.register_callback(self.tool, mon.events.PY_RETURN, self.finish)
        self.construct = BpkScene.construct.__code__
        mon.set_local_events(self.tool, self.construct, mon.events.PY_START)
        sys.addaudithook(self.audit)


def main():
    """`python -m bpkfigures.subscene_inputs <manim args>`: manim, recording."""
    _Recorder().install()
    from manim.__main__ import main as manim_main
    sys.argv[0] = "manim"
    return manim_main()


if __name__ == "__main__":
    sys.exit(main())
