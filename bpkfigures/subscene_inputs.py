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


# ── EARLY CUTOFF: the state each subscene ENDS in (2026-11-14) ────────────────
# A clip's skip key used to hash the code of setup + EVERY subscene up to it, so a
# change to b that left b's end exactly as it was (a wait added) still re-rendered c, d,
# ... The state records let a clip's key be its OWN code, its own files and the STATE it
# starts from instead: when b re-renders and ends in the same state, c's key is unchanged.
#
# Each record, {subscene: {"after": <state hash>, "chain": <chain key>}}, is written in the
# manim child when the subscene returns (rendered or replayed). `chain` is the key the
# state was produced under; render.py trusts a recorded `after` only if its `chain` equals
# the chain it computes now from the current code, files and the trusted state before it,
# from the first subscene on (`trusted_chain`), so a stale record can never skip a clip.

def states_path(class_name):
    return os.path.join(SNAPSHOT_DIR, f"{class_name}_states.json")


def load_states(class_name):
    try:
        with open(states_path(class_name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def chain_key(own, files, before):
    """The key a subscene's end state is produced under: its own code (`own_code`), the
    files it read (`inputs_hash`), and the state it started from ("setup" for the first
    subscene, whose `own` and `files` cover setup_scene too)."""
    return hashlib.md5(f"chain1|{own}|{files}|{before}".encode()).hexdigest()


_OWN = {}


def own_codes():
    """{subscene: {"first": .., "rest": ..}} as render.py passed them (`own_code`)."""
    try:
        return json.loads(os.environ.get("BPK_OWN_CODES") or "{}")
    except ValueError:
        return {}


def own_code(cls, name, first):
    """The code subscene `name` alone reaches (scene `_reach_parts`), with setup_scene's
    for the first subscene. Memoized: code does not change within a process."""
    k = (cls, name, first)
    if k not in _OWN:
        from bpkfigures.scene import _reach_parts
        _OWN[k] = "".join(_reach_parts(cls, (["setup_scene"] if first else []) + [name]))
    return _OWN[k]


def is_still(cls, name):
    return getattr(getattr(cls, name, None), "_is_still", False)


def trusted_chain(cls, class_name, names, states=None, records=None):
    """{subscene: chain key} for each subscene, in order, whose STARTING state is known to
    be the product of the current code: the first subscene, then each one after a
    subscene whose recorded state chain matches the current one. Stops at the first
    subscene with no file record, or whose record does not match (its state is unknown,
    so nothing after it can be keyed on state). Stills are passed over: they change no
    state."""
    st = load_states(class_name) if states is None else states
    rec = load_records(class_name) if records is None else records
    out, before, first = {}, "setup", True
    for name in names:
        if is_still(cls, name):
            continue
        files = inputs_hash(class_name, (["setup_scene"] if first else []) + [name], rec)
        if files is None:
            break
        k = chain_key(own_code(cls, name, first), files, before)
        out[name] = k
        if (st.get(name) or {}).get("chain") != k:
            break
        before, first = st[name]["after"], False
    return out


def _canon(obj, h, seen, depth=0):
    """Feed `obj`'s VALUE into hash `h`, the same whatever the process: numbers, strings
    and arrays by content, sequences in order, dicts and sets SORTED (by each element's
    own hash), any other object as its class and its attributes. An object met again is
    hashed by where it was first met, so shared references and cycles hash the same every
    run. NOT pickle: a pickle keeps a set's order, which follows memory addresses and
    changes every run (measured 2026-11-14: two identical replays of scene 17 gave a
    different pickle hash for every subscene)."""
    import numpy as np
    k = id(obj)
    if isinstance(obj, (type(None), bool, int, float, complex, str, bytes)):
        h.update(f"{type(obj).__name__}:{obj!r};".encode())
        return
    if k in seen:
        h.update(f"ref:{seen[k]};".encode())
        return
    seen[k] = len(seen)
    if isinstance(obj, np.ndarray):
        h.update(f"nd:{obj.dtype}:{obj.shape};".encode())
        h.update(np.ascontiguousarray(obj).tobytes() if obj.dtype != object
                 else repr(obj.tolist()).encode())
        return
    if isinstance(obj, np.generic):
        h.update(f"np:{obj!r};".encode())
        return
    if isinstance(obj, (list, tuple)):
        h.update(f"{type(obj).__name__}[{len(obj)}];".encode())
        for x in obj:
            _canon(x, h, seen, depth + 1)
        return
    if isinstance(obj, (set, frozenset, dict)):
        items = obj.items() if isinstance(obj, dict) else ((x, None) for x in obj)
        parts = []
        for a, b in items:
            sub = hashlib.md5()
            _canon(a, sub, {}, depth + 1)          # each element on its own: order-free
            _canon(b, sub, {}, depth + 1)
            parts.append(sub.hexdigest())
        h.update(f"{type(obj).__name__}{{{','.join(sorted(parts))}}};".encode())
        return
    if callable(obj) and not hasattr(obj, "__dict__") or isinstance(obj, type) or \
            type(obj).__name__ in ("function", "method", "builtin_function_or_method",
                                   "module", "cell"):
        h.update(f"fn:{getattr(obj, '__qualname__', type(obj).__name__)};".encode())
        return
    cls = type(obj)
    h.update(f"obj:{cls.__module__}.{cls.__qualname__}".encode())
    state = getattr(obj, "__dict__", None)
    if state is None:
        slots = [s for c in cls.__mro__ for s in getattr(c, "__slots__", ())]
        state = {s: getattr(obj, s) for s in slots if hasattr(obj, s)}
    if depth > 400:
        h.update(b"deep;")
        return
    for name in sorted(state):
        if name in _NOT_STATE:
            continue
        h.update(f".{name}=".encode())
        _canon(state[name], h, seen, depth + 1)


# attributes that hold a memory address, not a value: manim's `original_id`, stamped on a
# copy as str(id(the original)), differs every run (found 2026-11-14, scene 17)
_NOT_STATE = {"original_id", "file_name"}   # file_name: a Text's cached-SVG path, not its look


def state_hash(scene):
    """A fingerprint of everything a snapshot keeps (scene `_save_snapshot`): the scene's
    own attributes, its mobjects and the camera's pose, by VALUE (`_canon`), so two runs
    ending in the same state give the same hash."""
    from bpkfigures.scene import _NEVER_PICKLE
    keys = sorted(set(scene.__dict__) - scene._baseline_keys - _NEVER_PICKLE)
    cam = scene.camera
    pose = [str(cam.background_color)]
    if hasattr(cam, "frame"):
        f = cam.frame
        pose += [f.get_center().tolist(), f.get_width(), f.get_height()]
    if hasattr(cam, "phi_tracker"):
        pose += [[t.get_value() for t in cam.get_value_trackers()], cam.frame_center.tolist()]
    h = hashlib.md5()
    _canon(([(k, scene.__dict__[k]) for k in keys], list(scene.mobjects), pose), h, {})
    if os.environ.get("BPK_STATE_DEBUG"):
        parts = {}
        for k in keys:
            sub = hashlib.md5(); _canon(scene.__dict__[k], sub, {}); parts["attr:" + k] = sub.hexdigest()
        for i, m in enumerate(scene.mobjects):
            sub = hashlib.md5(); _canon(m, sub, {}); parts[f"mob{i}:{type(m).__name__}"] = sub.hexdigest()
            for name in sorted(vars(m)):
                sub = hashlib.md5(); _canon(vars(m)[name], sub, {})
                parts[f"mob{i}.{name}"] = sub.hexdigest()
        with open(os.environ["BPK_STATE_DEBUG"], "a") as fh:
            fh.write(json.dumps(parts) + "\n")
    return h.hexdigest()


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
        self.scene_cls = None
        self.after = {}                 # subscene -> its end-state hash, this process
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
        self.scene_cls = scene_cls
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
        if name != "setup_scene":
            try:
                self.record_state(name, sys._getframe(1).f_locals.get("self"), rec)
            except Exception as e:          # never let the record break a render
                print(f"[bpk] state record skipped at {name}: {type(e).__name__}: {e}")

    def record_state(self, name, scene, rec):
        """`name`'s end-state hash, and the chain key it was produced under."""
        cls = self.scene_cls
        if scene is None or cls is None or is_still(cls, name):
            return
        from bpkfigures.scene import _ordered_subscenes
        names = _ordered_subscenes(cls)
        i = names.index(name)
        prev = next((n for n in reversed(names[:i]) if not is_still(cls, n)), None)
        states = load_states(self.class_name)
        if prev is None:
            before, first = "setup", True
        else:
            # the state this subscene started from: the previous one's end, from this
            # process, or as recorded when a snapshot of it was loaded instead
            before, first = self.after.get(prev) or (states.get(prev) or {}).get("after"), False
        after = state_hash(scene)
        self.after[name] = after
        files = inputs_hash(self.class_name, (["setup_scene"] if first else []) + [name], rec)
        # the subscene's code fingerprint as RENDER computed it (BPK_OWN_CODES): computed
        # here it can differ for the same code (found 2026-11-14, scene 17f), and then no
        # chain would ever match
        own = own_codes().get(name, {}).get("first" if first else "rest")
        chain = (chain_key(own, files, before)
                 if own and before and files is not None else None)
        states[name] = {"after": after, "chain": chain}
        tmp = states_path(self.class_name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(states, fh, indent=0, sort_keys=True)
        os.replace(tmp, states_path(self.class_name))

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
