import hashlib
import inspect
import os
import pickle
import sys
import types

from manim import Scene
from bpkfigures.style import *
from bpkfigures.highlight import *
from bpkfigures.resolve import index_to_label, label_to_index

# ── Render-hang workaround (manim + Python 3.14) ──────────────────────────────
# manim's SceneFileWriter spawns a NON-daemon thread per partial movie
# (`listen_and_write`). Our snapshot skip-replay (fast-forwarding earlier
# subscenes) can leave some of those threads orphaned, blocked forever on an
# empty queue. Under Python 3.14 the interpreter won't exit until every
# non-daemon thread joins, so the process deadlocks AFTER rendering finishes
# (0% CPU, no mp4 written) and `render` appears to hang.
# Force those writer threads to be daemons so a stray one can't wedge shutdown.
# Safe: normal use still joins the thread explicitly (close_partial_movie_stream)
# before closing each file, so no frame is lost; daemon only affects orphans.
import manim.scene.scene_file_writer as _sfw  # noqa: E402

_OrigThread = _sfw.Thread


def _DaemonThread(*args, **kwargs):
    kwargs.setdefault("daemon", True)
    return _OrigThread(*args, **kwargs)


_sfw.Thread = _DaemonThread

SNAPSHOT_DIR = os.path.join("cache", "snapshots")

# Bump this to manually invalidate every cached snapshot (e.g. after changing
# the snapshot machinery itself or any dependency the source hash can't see).
SNAPSHOT_VERSION = 4

# Every subscene is framed by a static hold: the framework plays one leading
# self.wait(SUBSCENE_HOLD) at the very start of a render, then one trailing hold
# after each subscene. So a single-subscene render is HOLD·sub·HOLD (a standalone
# clip with a pause each side), while a full-scene render reads
# HOLD·a·HOLD·b·HOLD·…·N·HOLD — a SINGLE shared pause between adjacent subscenes,
# not two. Subscene bodies therefore must NOT add their own start/end wait (the
# framework owns those); internal mid-subscene waits are fine.
SUBSCENE_HOLD = 1.0

_BPK_DIR = os.path.dirname(os.path.realpath(__file__))


def _iter_py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        # don't descend into caches / virtualenvs / build dirs
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", ".venv", "venv", "media",
                                    "cache", ".git")]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def _source_hash(roots, exclude=()):
    """Deterministic md5 over the source of every .py file under `roots`,
    skipping any realpath in `exclude`.

    Walking fixed directories (not sys.modules) makes the hash stable across
    invocations — sys.modules varies with what manim happens to import, which
    would spuriously invalidate snapshots between a full render and a single-
    subscene render. Editing any project source under these roots changes the
    key and invalidates stale snapshots.

    `exclude` is used to drop the scene's own module file: the scene source is
    captured at finer (per-subscene) granularity by _scene_source_digest, so
    hashing the whole file here too would make any edit to ANY subscene
    invalidate ALL snapshots."""
    skip = {os.path.realpath(p) for p in exclude}
    files = set()
    for root in roots:
        if root and os.path.isdir(root):
            files.update(os.path.realpath(p) for p in _iter_py_files(root))
    files -= skip
    h = hashlib.md5()
    for f in sorted(files):
        try:
            with open(f, "rb") as fh:
                h.update(f.encode())
                h.update(fh.read())
        except OSError:
            pass
    return h.hexdigest()


def _referenced_names(fn):
    """All global/attribute names a function references, including those inside
    nested code objects (comprehensions, lambdas)."""
    names = set()
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        names.update(code.co_names)
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                stack.append(const)
    return names


def _scene_source_digest(cls, method_names):
    """Deterministic md5 over the source of `method_names` (methods on `cls`)
    plus the transitive closure of everything they reference that is defined in
    the SAME module/class — other methods, module-level helper functions, and
    module-level constants.

    This captures exactly the scene-side code that shapes the snapshot's state
    at per-subscene granularity: editing a LATER subscene (or code only it uses)
    doesn't change the digest for an earlier subscene, while editing a helper or
    constant that an in-scope method reaches does. Third-party / asset / config
    code is deliberately NOT followed here — it's covered wholesale by
    _source_hash."""
    module = sys.modules.get(cls.__module__)
    mod_ns = getattr(module, "__dict__", {})
    cls_ns = dict(vars(cls))

    def _same_module(obj):
        return getattr(obj, "__module__", None) == cls.__module__

    # collected (qualname -> source-or-repr); funcs/methods queued for walking
    parts = {}
    seen = set()
    queue = []

    def _add_function(qual, fn):
        if qual in seen:
            return
        seen.add(qual)
        try:
            parts[qual] = inspect.getsource(fn)
        except Exception:
            # getsource is best-effort: OSError (no source), TypeError (builtin),
            # or — if the file on disk was rewritten under a live render by a
            # concurrent session — a TokenError/SyntaxError from a stale line
            # range. None of these should abort the render, so fall back to a
            # DETERMINISTIC key (the qualname). NEVER repr(fn): its 0x… address
            # changes every process and would poison the snapshot cache.
            parts[qual] = qual
        queue.append(fn)

    # seed with the requested methods
    for name in method_names:
        fn = cls_ns.get(name) or getattr(cls, name, None)
        if isinstance(fn, types.FunctionType):
            _add_function(f"{cls.__name__}.{name}", fn)

    while queue:
        fn = queue.pop()
        for ref in _referenced_names(fn):
            # a sibling method on the class?
            obj = cls_ns.get(ref)
            if isinstance(obj, types.FunctionType):
                _add_function(f"{cls.__name__}.{ref}", obj)
                continue
            # a module-level name in the scene's module?
            if ref in mod_ns:
                val = mod_ns[ref]
                if isinstance(val, types.FunctionType) and _same_module(val):
                    _add_function(f"{cls.__module__}.{ref}", val)
                elif isinstance(val, type) and _same_module(val):
                    key = f"{cls.__module__}.{ref}"
                    if key not in seen:
                        seen.add(key)
                        try:
                            parts[key] = inspect.getsource(val)
                        except Exception:
                            parts[key] = key  # deterministic fallback (see above)
                elif isinstance(val, (int, float, str, bytes, bool, tuple,
                                      frozenset, type(None), dict, list, set)):
                    # module-level constant the code depends on
                    parts[f"const:{ref}"] = repr(val)

    h = hashlib.md5()
    for qual in sorted(parts):
        h.update(qual.encode())
        h.update(parts[qual].encode())
    return h.hexdigest()


def subscene(fn):
    fn._is_subscene = True
    return fn


def _ordered_subscenes(cls):
    found = []
    for name, fn in inspect.getmembers(cls, predicate=inspect.isfunction):
        if getattr(fn, "_is_subscene", False):
            found.append((fn.__code__.co_firstlineno, name))
    found.sort()
    return [name for _, name in found]


def _letter(i):
    return index_to_label(i)


class BpkScene(Scene):
    def setup_scene(self):
        pass

    def _project_roots(self):
        # The bpkfigures package, plus the scene's project tree (assets/,
        # config.py live in the parent of the scenes/ dir). Walking these fixed
        # dirs gives a stable hash regardless of how the scene was invoked.
        cls = type(self)
        scene_file = os.path.realpath(inspect.getfile(cls))
        project_root = os.path.dirname(os.path.dirname(scene_file))  # animations/
        return [_BPK_DIR, project_root]

    def _prefix_key(self, idx, names):
        # A snapshot at idx is valid iff the code that PRODUCES its end-state is
        # unchanged. The key hashes three things:
        #   1. a manual version stamp
        #   2. _source_hash of project code (assets/config/bpkfigures) EXCEPT the
        #      scene's own file — so an asset appearance change still invalidates
        #      (correctness), but editing a subscene body doesn't flip this term.
        #   3. the scene-side dependency closure of setup_scene + subscenes
        #      0..idx (per-subscene granularity), so editing a LATER subscene, or
        #      code only it uses, leaves earlier snapshots valid.
        cls = type(self)
        scene_file = os.path.realpath(inspect.getfile(cls))
        # render.py / resolve.py are the CLI wrapper — never imported during a
        # scene render, so their source can't change output. Exclude them too, so
        # editing the render script doesn't needlessly invalidate every snapshot.
        tooling = {os.path.realpath(os.path.join(_BPK_DIR, f))
                   for f in ("render.py", "resolve.py")}
        srcs = [
            f"v{SNAPSHOT_VERSION}",
            _source_hash(self._project_roots(), exclude={scene_file} | tooling),
            _scene_source_digest(cls, ["setup_scene"] + list(names[: idx + 1])),
        ]
        return hashlib.md5("".join(srcs).encode()).hexdigest()

    def _snapshot_path(self, idx):
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        return os.path.join(SNAPSHOT_DIR, f"{type(self).__name__}_{_letter(idx)}.pkl")

    def _save_snapshot(self, idx, names):
        user_keys = set(self.__dict__) - self._baseline_keys
        bundle = {
            "key": self._prefix_key(idx, names),
            "attrs": {k: self.__dict__[k] for k in user_keys},
            "mobjects": list(self.mobjects),  # same dump -> identity preserved
        }
        path = self._snapshot_path(idx)
        try:
            with open(path, "wb") as f:
                pickle.dump(bundle, f)
        except Exception as e:
            if os.path.exists(path):
                os.remove(path)
            print(f"[bpk] snapshot skipped at {_letter(idx)}: {type(e).__name__}")

    def _load_snapshot(self, idx, names):
        if os.environ.get("RECOMPUTE", "0") == "1":
            return False
        path = self._snapshot_path(idx)
        if not os.path.exists(path):
            return False
        try:
            with open(path, "rb") as f:
                bundle = pickle.load(f)
        except Exception:
            return False
        if bundle.get("key") != self._prefix_key(idx, names):
            return False
        for k, v in bundle["attrs"].items():
            setattr(self, k, v)
        for m in bundle["mobjects"]:
            self.add(m)
        return True

    def construct(self):
        self._baseline_keys = set(self.__dict__.keys())
        names = _ordered_subscenes(type(self))
        target = os.environ.get("SUBSCENE", "")

        if not target:
            self.setup_scene()
            self.wait(SUBSCENE_HOLD)             # leading hold (once, at scene start)
            for i, name in enumerate(names):
                getattr(self, name)()
                self.wait(SUBSCENE_HOLD)         # single shared pause between subscenes
                self._save_snapshot(i, names)
            return

        idx = label_to_index(target)
        if not (0 <= idx < len(names)):
            raise IndexError(f"Subscene '{target}' out of range (have {len(names)})")

        # Load the LATEST valid snapshot at or before idx-1, then replay only the
        # subscenes between it and idx (frames skipped). So editing subscene h
        # doesn't force a full a..g replay when rendering i: a..g's snapshots are
        # still valid, so we load g and replay just h. If nothing is valid we fall
        # back to setup + full-prefix replay.
        loaded_j = -1
        for j in range(idx - 1, -1, -1):
            if self._load_snapshot(j, names):
                loaded_j = j
                break

        if loaded_j == -1:
            self.setup_scene()
        if loaded_j < idx - 1:                  # replay the gap (or full prefix)
            self.renderer.skip_animations = True
            for i in range(loaded_j + 1, idx):
                getattr(self, names[i])()
                self._save_snapshot(i, names)
            self.renderer.skip_animations = False

        # Discard any partial-movie frames produced while fast-forwarding the
        # prefix subscenes. Even under skip_animations, manim still appends each
        # replayed play()'s (cached) partial-movie file to the concat list, so
        # without this the earlier subscenes get stitched into this one's video.
        self._discard_replay_frames()

        self.wait(SUBSCENE_HOLD)                 # leading hold on the incoming state
        getattr(self, names[idx])()
        self.wait(SUBSCENE_HOLD)                 # trailing hold
        self._save_snapshot(idx, names)

    def _discard_replay_frames(self):
        """Blank out the partial-movie files accumulated so far so the rendered
        output contains only the target subscene's animations.

        The entries are replaced with None (not removed): manim indexes
        partial_movie_files by num_plays, so the list length must be preserved,
        and the final concat step skips None entries."""
        fw = getattr(self.renderer, "file_writer", None)
        if fw is None:
            return
        if hasattr(fw, "partial_movie_files"):
            fw.partial_movie_files[:] = [None] * len(fw.partial_movie_files)
        for section in getattr(fw, "sections", []):
            if hasattr(section, "partial_movie_files"):
                section.partial_movie_files[:] = (
                    [None] * len(section.partial_movie_files))