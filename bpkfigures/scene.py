import ast
import dis
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
from bpkfigures.sfx import sfx_path, wav_info, spec_complaints

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
SNAPSHOT_VERSION = 7

# Every subscene is framed by a static hold: the framework plays one leading
# self.wait(SUBSCENE_HOLD) at the very start of a render, then one trailing hold
# after each subscene. So a single-subscene render is HOLD·sub·HOLD (a standalone
# clip with a pause each side), while a full-scene render reads
# HOLD·a·HOLD·b·HOLD·…·N·HOLD — a SINGLE shared pause between adjacent subscenes,
# not two. Subscene bodies therefore must NOT add their own start/end wait (the
# framework owns those); internal mid-subscene waits are fine.
SUBSCENE_HOLD = 1.0

# Per-render AUDIO bookkeeping (see BpkScene.sfx). These are seeded BEFORE
# _baseline_keys is captured, so they are baseline keys and never reach a snapshot;
# this set is belt-and-braces so a future attribute added in the wrong place cannot
# leak either. A restored _audio_t0 from whichever run happened to write the
# snapshot would silently shift every cue in the clip.
_NEVER_PICKLE = {"_audio_t0", "_sfx_live", "_sfx_still", "_sfx_cues",
                 "_in_setup_scene", "_dep_files"}

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


def _module_files(name, dirs):
    """The files importing dotted module `name` would EXECUTE, found under `dirs`
    (tried in order, like sys.path): each parent package's __init__.py, then the
    module itself (`x.py` or `x/__init__.py`). The first dir holding the top-level
    name wins; [] if none does (a third-party module)."""
    parts = name.split(".")
    for d in dirs:
        top = os.path.join(d, parts[0])
        if not (os.path.isfile(top + ".py") or os.path.isdir(top)):
            continue
        out, path = [], d
        for i, p in enumerate(parts):
            path = os.path.join(path, p)
            if os.path.isfile(os.path.join(path, "__init__.py")):
                out.append(os.path.join(path, "__init__.py"))
            elif i == len(parts) - 1 and os.path.isfile(path + ".py"):
                out.append(path + ".py")
                break
            else:
                break
        return out
    return []


def _import_closure(entry, roots, search):
    """Every project .py file (under `roots`) that `entry` can import, followed
    RECURSIVELY and STATICALLY: every import statement anywhere in a file's AST
    counts, including ones inside functions, so a module imported lazily by a
    later subscene is in the closure from the start. That is the point of doing it
    statically — sys.modules depends on what has RUN, so it would differ between a
    full render and a single-subscene render and flip the key between them.

    Resolution tries the importing file's own directory first (a data module that
    puts its own folder on sys.path), then `search` (the scene's sys.path roots).
    Relative imports resolve against the importing package. Anything that resolves
    outside `roots` (manim, numpy, math/ pipeline code) is not followed.

    Returns the set of realpaths, `entry` itself excluded."""
    roots = [os.path.realpath(r) for r in roots if r]
    under = lambda p: any(p == r or p.startswith(r + os.sep) for r in roots)
    entry = os.path.realpath(entry)
    seen, stack = {entry}, [entry]
    while stack:
        f = stack.pop()
        try:
            with open(f, "rb") as fh:
                tree = ast.parse(fh.read(), filename=f)
        except (OSError, SyntaxError, ValueError):
            continue
        here = os.path.dirname(f)
        for node in ast.walk(tree):
            names, dirs = [], [here, *search]
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:                       # relative: from the package
                    base = here
                    for _ in range(node.level - 1):
                        base = os.path.dirname(base)
                    dirs = [os.path.dirname(base)]
                    pkg = os.path.basename(base)
                    mod = pkg + ("." + node.module if node.module else "")
                else:
                    mod = node.module
                names = [mod] + [f"{mod}.{a.name}" for a in node.names if a.name != "*"]
            for name in names:
                for p in _module_files(name, dirs):
                    p = os.path.realpath(p)
                    if p not in seen and under(p):
                        seen.add(p)
                        stack.append(p)
    seen.discard(entry)
    return seen


# A project file with this name holds SOUND SETTINGS ONLY (which effect, how loud, where
# it peaks). A sound cannot change what is on screen, so the SNAPSHOT key leaves the file,
# and the names it defines, out: retuning a sound used to throw away every snapshot of
# every scene that imports the video's config (wheel-of-fortune, 2026-11-05: 03a and 03b,
# minutes each, rebuilt after a bubble's timing changed). The per-clip SKIP key
# (render.py `_video_key`) still covers both, so a changed sound re-renders its clips.
# Anything that affects a frame must NOT go in such a file.
AUDIO_ONLY_FILE = "sounds.py"


def _audio_only(files):
    """(the sound-settings files among `files`, the names they define at top level)."""
    found = {f for f in files if os.path.basename(f) == AUDIO_ONLY_FILE}
    names = set()
    for f in found:
        try:
            with open(f, "rb") as fh:
                tree = ast.parse(fh.read(), filename=f)
        except (OSError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            for tgt in targets:
                for n in ast.walk(tgt):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
    return found, names


def _files_hash(files):
    """md5 over the path and source of each of `files`, in sorted order."""
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


def _scene_source_digest(cls, method_names, skip=()):
    """Deterministic md5 over the source of `method_names` (methods on `cls`)
    plus the transitive closure of everything they reference that is defined in
    the SAME module/class — other methods, module-level helper functions, and
    module-level constants.

    This captures exactly the scene-side code that shapes the snapshot's state
    at per-subscene granularity: editing a LATER subscene (or code only it uses)
    doesn't change the digest for an earlier subscene, while editing a helper or
    constant that an in-scope method reaches does. Third-party / asset / config
    code is deliberately NOT followed here — it's covered wholesale by
    _source_hash.

    `skip`: module-level constant names left out (the snapshot key passes the sound
    settings' names, see AUDIO_ONLY_FILE); methods and functions are never skipped."""
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

    # INHERITED methods (a shared asset's base class, e.g. StacksView._move_view)
    # are walked for NAMES ONLY: their own source is covered wholesale by
    # _source_hash, but they call back into HOOKS the scene overrides (08's
    # _callout_spec, which reads CALLOUTS). Not following them made a scene
    # constant reached only through such a hook invisible to the digest — moving
    # SALET in 08's CALLOUTS left every snapshot and skip key "unchanged"
    # (2026-10-07).
    inherited_seen = set()

    def _walk_inherited(fn):
        stack = [fn]
        while stack:
            f = stack.pop()
            for ref in _referenced_names(f):
                obj = cls_ns.get(ref)
                if isinstance(obj, types.FunctionType):
                    _add_function(f"{cls.__name__}.{ref}", obj)
                    continue
                inh = getattr(cls, ref, None)
                inh = getattr(inh, "__func__", inh)
                if isinstance(inh, types.FunctionType) and not _same_module(inh) \
                        and ref not in inherited_seen:
                    inherited_seen.add(ref)
                    stack.append(inh)

    while queue:
        fn = queue.pop()
        for ref in _referenced_names(fn):
            # a sibling method on the class?
            obj = cls_ns.get(ref)
            if isinstance(obj, types.FunctionType):
                _add_function(f"{cls.__name__}.{ref}", obj)
                continue
            # an INHERITED method: follow it for calls back into this class
            inh = getattr(cls, ref, None)
            inh = getattr(inh, "__func__", inh)
            if isinstance(inh, types.FunctionType) and not _same_module(inh) \
                    and ref not in mod_ns:
                if ref not in inherited_seen:
                    inherited_seen.add(ref)
                    _walk_inherited(inh)
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
                elif ref in skip:
                    continue
                else:
                    # a module-level constant the code depends on. Capture its
                    # VALUE via repr so tuning it (a size, a position vector, a
                    # colour) invalidates the digest — NOT just the scalar types:
                    # numpy/manim position vectors (np.ndarray), enums, and
                    # dataclasses all have stable reprs and were silently skipped
                    # by an isinstance whitelist, so editing e.g. LEFT_SC left the
                    # snapshot stale. The ONE thing that poisons the cache is a
                    # repr carrying a memory address (`<Foo at 0x…>`) — it changes
                    # every process (see _add_function's fallback note) — so for
                    # those, fall back to the deterministic name key instead.
                    try:
                        r = repr(val)
                    except Exception:
                        r = f"const:{ref}"
                    # Fall back to the deterministic NAME key for a value whose repr is
                    # not stable across processes: a memory address (`<Foo at 0x…>`), OR
                    # manim's global `config` object — its repr embeds RENDER-SPECIFIC
                    # fields (output_file/scene_names differ per subscene target), so a
                    # scene that reads `config.frame_x_radius` (as CLAUDE.md recommends)
                    # would otherwise get a DIFFERENT digest for every render target and
                    # never reuse a snapshot. Its snapshot-relevant fields (frame size)
                    # live in manim.cfg, not a .py, so they're out of scope here anyway.
                    unstable = " at 0x" in r or type(val).__name__ == "ManimConfig"
                    parts[f"const:{ref}"] = f"const:{ref}" if unstable else r

    h = hashlib.md5()
    for qual in sorted(parts):
        h.update(qual.encode())
        h.update(parts[qual].encode())
    return h.hexdigest()


def subscene(fn):
    fn._is_subscene = True
    return fn


def still(fn):
    """An INDEPENDENT static-frame subscene — for a scene that's just a SERIES OF
    IMAGES with no animation BETWEEN them.

    A still IS a subscene (same `NNa`/`NNb` addressing, render, and resolve), but the
    framework renders it from a CLEAN, EMPTY frame: no snapshot carry-over from the
    previous subscene (which would ghost the prior frame behind this one) and no
    snapshot save/replay (each frame is self-contained, so the whole prefix-replay
    machinery is unnecessary). The body builds its composition on a clean slate —
    static `self.add`. Use `@still` instead of `@subscene` on each frame; the scene
    can keep any base class (the behaviour rides on this marker).

    `render` renders each @still target as a STILL IMAGE — a PNG (manim `-s`) under
    `media/images/<scene>/<res>/`, NOT a video — so a `@still`-only scene is a set of
    independent images (`render NN all` emits one PNG per subscene, no combined
    render). `@thumbnail` EXTENDS this for the reserved 99 slot: same still image, but
    4K (`-qk`) by default as an upload asset, plus change-detection on `render 99 all`."""
    fn._is_subscene = True
    fn._is_still = True
    return fn


def thumbnail(fn):
    """A `@still` specialized for the reserved `99` thumbnail slot: the clean-frame,
    no-snapshot behaviour comes from `@still` (which this extends), and the `99`
    prefix makes `render` emit a 4K still PNG (see render.py) — orthogonal to this
    marker. Use `@thumbnail` in `99thumbnails.py`; `@still` for any other
    image-series scene. The scene can keep any base (e.g. YahtzeeScene)."""
    still(fn)
    fn._is_thumbnail = True
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


# ── what a subscene REACHES (the key since SNAPSHOT_VERSION 7) ────────────────
# Until 2026-11-05 the key hashed EVERY project file a scene imports, so editing
# assets/tiles.py or bpkfigures/pie_chart.py threw away every snapshot of the scene,
# its first beats included, though they never touch either (wheel-of-fortune 03a/03b,
# minutes each). `_reach_parts` starts instead from the subscenes' own code and follows
# what it uses, across modules: the source of every project function and class reached,
# the VALUE of every constant read (default arguments and class attributes included),
# and two conservative catch-alls -- a module whose constant has no stable repr, or that
# is used as a module object (`mod.x`), is hashed WHOLE, and every reached module's
# top-level code that is not a definition, an import or a plain name assignment (a
# registration call, an `if` block) always counts. Framework methods run without being
# named (construct, setup...) are seeded from the scene's project base classes.
_IMPLICIT = ("construct", "setup", "tear_down", "__init__", "setup_scene")


def _project_file(obj, roots, tooling):
    """The project file `obj` is defined in (under `roots`, not the CLI tooling), or None."""
    try:
        f = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except (TypeError, OSError):
        return None
    if not f:
        return None
    f = os.path.realpath(f)
    if f in tooling:
        return None
    return f if any(f == r or f.startswith(r + os.sep) for r in roots) else None


def _canon(val):
    """repr(val) with every set's items in sorted order, nested sets included: a set's
    repr order follows string hashing, which Python randomises per process."""
    if isinstance(val, (set, frozenset)):
        return f"{type(val).__name__}({sorted(_canon(v) for v in val)})"
    if isinstance(val, dict) and type(val) is dict:
        return "{" + ", ".join(f"{_canon(k)}: {_canon(v)}" for k, v in val.items()) + "}"
    if type(val) in (list, tuple):
        inner = ", ".join(_canon(v) for v in val)
        return f"[{inner}]" if type(val) is list else f"({inner})"
    return repr(val)


def _stable_repr(val):
    """repr(val), or None when it is not stable across processes (a memory address, or
    manim's render-specific `config`; see _scene_source_digest)."""
    try:
        r = _canon(val)
    except Exception:
        return None
    if " at 0x" in r or type(val).__name__ == "ManimConfig":
        return None
    return r


def _side_effects(path):
    """A module's top-level code other than definitions, imports, docstrings and plain
    name assignments (those are reached by name instead): what can change state
    without being referenced."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
    except (OSError, SyntaxError, ValueError):
        return path
    out = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.Assign) and all(isinstance(x, ast.Name) for x in node.targets):
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            continue
        out.append(ast.get_source_segment(src, node) or ast.dump(node))
    return "\n".join(out)


def _code_names(fn):
    """(globals, attributes, imports) a function's bytecode names, nested code included:
    a global read resolves through the function's module, an attribute only to the
    scene's own methods (`self.x`). Keeping them apart matters: `board.tiles` must not
    pull in a module-level function that happens to be called `tiles`."""
    glob, attrs, imps = set(), set(), set()
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        for ins in dis.get_instructions(code):
            if not isinstance(ins.argval, str):
                continue
            if ins.opname in ("LOAD_GLOBAL", "LOAD_NAME", "LOAD_FROM_DICT_OR_GLOBALS"):
                glob.add(ins.argval)
            elif ins.opname in ("LOAD_ATTR", "LOAD_METHOD", "LOAD_SUPER_ATTR"):
                attrs.add(ins.argval)
            elif ins.opname == "IMPORT_NAME":
                imps.add(ins.argval)
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    return glob, attrs, imps


def _reach_parts(cls, method_names, skip=(), skip_files=(), texts=None, classes=None,
                 attr_classes=()):
    """(module_hash, digest) for subscenes `method_names` of scene class `cls`: what
    they reach (see the note above). `skip`: constant names left out, `skip_files`:
    files whose top-level code is left out (the snapshot key passes the sound settings,
    see AUDIO_ONLY_FILE). `texts`: a list to receive every hashed source and value, so
    render.py can find the sound effects a subscene names. `classes`: a list to receive
    every project class reached. `attr_classes`: classes whose methods an attribute
    call may also resolve to, from any reached code -- for a subscene looked at alone
    that calls methods on objects an EARLIER subscene built (`self.pie.fan_all`)."""
    scene_file = os.path.realpath(inspect.getfile(cls))
    project_root = os.path.dirname(os.path.dirname(scene_file))
    roots = [os.path.realpath(_BPK_DIR), os.path.realpath(project_root)]
    tooling = {os.path.realpath(os.path.join(_BPK_DIR, f)) for f in ("render.py", "resolve.py")}
    scene_classes = {c.__name__ for c in cls.__mro__
                     if c is cls or _project_file(c, roots, tooling)}
    skip_files = {os.path.realpath(f) for f in skip_files}
    parts, seen, queue = {}, set(), []
    modules, whole = set(), set()

    def value(key, v, owner):
        r = _stable_repr(v)
        if r is None:
            parts[key] = key
            if owner and owner != scene_file:
                whole.add(owner)
        else:
            parts[key] = r

    def code(qual, obj):
        if qual in seen:
            return
        seen.add(qual)
        try:
            parts[qual] = inspect.getsource(obj)
        except Exception:
            parts[qual] = qual              # deterministic (see _add_function)
        owner = _project_file(obj, roots, tooling)
        if owner and owner != scene_file:
            modules.add(owner)
        if isinstance(obj, types.FunctionType):
            for attr in ("__defaults__", "__kwdefaults__"):
                d = getattr(obj, attr, None)
                if d:
                    value(f"{qual}.{attr}", d, owner)
            queue.append(obj)
        elif isinstance(obj, type):
            if classes is not None:
                classes.append(obj)
            for k, v in vars(obj).items():
                fn = v.fget if isinstance(v, property) else getattr(v, "__func__", v)
                if isinstance(fn, types.FunctionType):
                    for attr in ("__defaults__", "__kwdefaults__"):
                        d = getattr(fn, attr, None)
                        if d:
                            value(f"{qual}.{k}.{attr}", d, owner)
                    queue.append(fn)
                elif not k.startswith("__"):
                    value(f"{qual}.{k}", v, owner)
            for base in obj.__mro__[1:]:
                if _project_file(base, roots, tooling):
                    code(f"{base.__module__}.{base.__qualname__}", base)

    def name(ref, glb, owner):
        v = glb[ref]
        if isinstance(v, types.ModuleType):
            f = _project_file(v, roots, tooling)
            if f:
                whole.add(f)
            return
        if isinstance(v, (types.FunctionType, type)):
            if _project_file(v, roots, tooling):
                code(f"{v.__module__}.{v.__qualname__}", v)
            return
        if ref in skip:
            return
        value(f"const:{owner or cls.__module__}:{ref}", v, owner)

    for n in method_names:                       # the subscenes themselves
        fn = getattr(cls, n, None)
        fn = getattr(fn, "__func__", fn)
        if isinstance(fn, types.FunctionType):
            code(f"{cls.__name__}.{n}", fn)
    for base in cls.__mro__[1:]:                 # framework methods run unnamed
        if _project_file(base, roots, tooling):
            for n in _IMPLICIT:
                fn = vars(base).get(n)
                fn = getattr(fn, "__func__", fn)
                if isinstance(fn, types.FunctionType):
                    code(f"{base.__module__}.{base.__qualname__}.{n}", fn)

    while queue:
        fn = queue.pop()
        glb = fn.__globals__
        owner = _project_file(fn, roots, tooling)
        on_scene = fn.__qualname__.split(".")[0] in scene_classes
        glob, attrs, imps = _code_names(fn)
        if on_scene:                             # self.<method> on the scene's classes
            for ref in attrs:
                a = getattr(cls, ref, None)
                a = getattr(a, "__func__", a)
                if isinstance(a, types.FunctionType) and _project_file(a, roots, tooling):
                    code(f"{cls.__name__}.{ref}" if ref in vars(cls)
                         else f"{a.__module__}.{a.__qualname__}", a)
        for ref in attrs:                        # methods of objects built earlier
            for C in attr_classes:
                a = getattr(C, ref, None)
                a = a.fget if isinstance(a, property) else getattr(a, "__func__", a)
                if isinstance(a, types.FunctionType) and _project_file(a, roots, tooling):
                    code(f"{a.__module__}.{a.__qualname__}", a)
        for ref in glob:
            if ref in glb:
                name(ref, glb, owner)
        for mod in imps:                         # an import inside a function: whole
            f = _project_file(sys.modules[mod], roots, tooling) if mod in sys.modules else None
            if f:
                whole.add(f)

    mh = hashlib.md5()
    for f in sorted(whole - skip_files):
        try:
            with open(f, "rb") as fh:
                mh.update(f.encode())
                mh.update(fh.read())
        except OSError:
            pass
    for f in sorted(modules - whole - skip_files):
        mh.update(f.encode())
        mh.update(_side_effects(f).encode())
    dh = hashlib.md5()
    for qual in sorted(parts):
        dh.update(qual.encode())
        dh.update(parts[qual].encode())
    if texts is not None:
        texts.extend(parts.values())
        texts.extend(_side_effects(f) for f in sorted(modules - skip_files))
    return mh.hexdigest(), dh.hexdigest()


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
        #   2. hash of the project code this scene IMPORTS (_dependency_files) EXCEPT the
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
        sh, dg = self._prefix_key_parts(idx, names)
        return hashlib.md5(f"v{SNAPSHOT_VERSION}{sh}{dg}".encode()).hexdigest()

    def _prefix_key_parts(self, idx, names):
        """(module_hash, digest) — the two non-version key terms, exposed so a snapshot MISS
        can report WHICH one changed: what setup_scene + subscenes 0..idx REACH
        (`_reach_parts`), less the sound settings (AUDIO_ONLY_FILE). module_hash = modules
        hashed whole and reached modules' top-level side effects; digest = the source of
        reached code and the values of reached constants."""
        audio_files, audio_names = _audio_only(self._dependency_files())
        return _reach_parts(type(self), ["setup_scene"] + list(names[: idx + 1]),
                            skip=audio_names, skip_files=audio_files)

    def _dependency_files(self):
        """The project .py files this scene can import (`_import_closure`), cached
        per run. ONLY THESE feed the source hash: until 2026-09-30 it was every .py
        under bpkfigures/ and animations/, so another tab saving an asset or a
        shared module this scene never imports (bpkfigures/number_line.py, for
        scene 13) threw away every snapshot of every scene mid-render."""
        if getattr(self, "_dep_files", None) is None:
            scene_file = os.path.realpath(inspect.getfile(type(self)))
            roots = self._project_roots()
            search = [roots[1], os.path.dirname(_BPK_DIR)]   # animations/, the umbrella
            self._dep_files = _import_closure(scene_file, roots, search)
        return self._dep_files

    def _snapshot_path(self, idx):
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        return os.path.join(SNAPSHOT_DIR, f"{type(self).__name__}_{_letter(idx)}.pkl")

    def _save_snapshot(self, idx, names):
        user_keys = set(self.__dict__) - self._baseline_keys - _NEVER_PICKLE
        sh, dg = self._prefix_key_parts(idx, names)   # stored too, so a later miss says which changed
        bundle = {
            "key": hashlib.md5(f"v{SNAPSHOT_VERSION}{sh}{dg}".encode()).hexdigest(),
            "srchash": sh, "digest": dg,
            "attrs": {k: self.__dict__[k] for k in user_keys},
            "mobjects": list(self.mobjects),  # same dump -> identity preserved
            # camera state lives on self.camera (a baseline key, so NOT in attrs); save
            # it explicitly so the leading hold on the next subscene shows the correct
            # incoming bg + frame pose instead of the class default (else it starts wrong
            # and jumps when the body re-establishes them). frame only on MovingCamera.
            "cam_bg": self.camera.background_color,
        }
        if hasattr(self.camera, "frame"):
            f = self.camera.frame
            bundle["cam_frame"] = (f.get_center(), f.get_width(), f.get_height())
        if hasattr(self.camera, "phi_tracker"):
            # A ThreeDScene's camera: its angles, focal distance and zoom (in
            # get_value_trackers' order), its centre, and the mobjects pinned to the
            # screen or turned to face it. In this same dump, so the pinned sets keep
            # identity with the mobjects above.
            cam = self.camera
            bundle["cam3d"] = {
                "trackers": [t.get_value() for t in cam.get_value_trackers()],
                "center": cam.frame_center.copy(),
                "fixed_in_frame": list(cam.fixed_in_frame_mobjects),
                "fixed_orientation": dict(cam.fixed_orientation_mobjects),
            }
        path = self._snapshot_path(idx)
        try:
            with open(path, "wb") as f:
                pickle.dump(bundle, f)
        except Exception as e:
            if os.path.exists(path):
                os.remove(path)
            print(f"[bpk] snapshot skipped at {_letter(idx)}: {type(e).__name__}: {e}")

    def _load_snapshot(self, idx, names):
        if os.environ.get("RECOMPUTE", "0") == "1":
            return False
        let = _letter(idx)
        path = self._snapshot_path(idx)
        if not os.path.exists(path):
            print(f"[bpk] snapshot miss at {let}: no file")
            return False
        try:
            with open(path, "rb") as f:
                bundle = pickle.load(f)
        except Exception as e:
            print(f"[bpk] snapshot miss at {let}: load {type(e).__name__}")
            return False
        sh, dg = self._prefix_key_parts(idx, names)
        cur = hashlib.md5(f"v{SNAPSHOT_VERSION}{sh}{dg}".encode()).hexdigest()
        if bundle.get("key") != cur:
            which = []
            if bundle.get("srchash") != sh:
                which.append(f"srchash {str(bundle.get('srchash'))[:6]}->{sh[:6]}")
            if bundle.get("digest") != dg:
                which.append(f"digest {str(bundle.get('digest'))[:6]}->{dg[:6]}")
            print(f"[bpk] snapshot miss at {let}: key mismatch [{', '.join(which) or 'version'}]")
            return False
        for k, v in bundle["attrs"].items():
            setattr(self, k, v)
        for m in bundle["mobjects"]:
            self.add(m)
        # restore camera bg + frame pose (see _save_snapshot) so the leading hold
        # renders the correct incoming state. .get() keeps pre-v6 snapshots loadable.
        if "cam_bg" in bundle:
            self.camera.background_color = bundle["cam_bg"]
        cf = bundle.get("cam_frame")
        if cf is not None and hasattr(self.camera, "frame"):
            center, w, h = cf
            self.camera.frame.move_to(center) \
                .stretch_to_fit_width(w).stretch_to_fit_height(h)
        c3 = bundle.get("cam3d")
        if c3 is not None and hasattr(self.camera, "phi_tracker"):
            cam = self.camera
            for t, v in zip(cam.get_value_trackers(), c3["trackers"]):
                t.set_value(v)
            cam.frame_center = c3["center"]
            cam.fixed_in_frame_mobjects = set(c3["fixed_in_frame"])
            cam.fixed_orientation_mobjects = dict(c3["fixed_orientation"])
        return True

    def _is_still(self, name):
        """True if subscene `name` is an INDEPENDENT static frame (@still, and its
        specialization @thumbnail): a clean slate with no snapshot."""
        return getattr(getattr(type(self), name), "_is_still", False)

    def _clear_frame(self):
        """Remove every top-level mobject — reset to an empty frame (used to give
        each @still/@thumbnail a clean slate with no carry-over from the previous)."""
        for m in list(self.mobjects):
            self.remove(m)

    def construct(self):
        # Seed the audio bookkeeping BEFORE _baseline_keys is captured, so these are
        # baseline keys and never land in a snapshot (see _NEVER_PICKLE). _sfx_live
        # starts False so a cue in setup_scene() is refused rather than behaving
        # differently between a full render and a subscene render.
        self._audio_t0 = 0.0
        self._sfx_live = False
        self._sfx_still = False
        self._in_setup_scene = False
        self._sfx_cues = []
        self._baseline_keys = set(self.__dict__.keys())
        names = _ordered_subscenes(type(self))
        target = os.environ.get("SUBSCENE", "")

        if not target:
            self._run_setup_scene()
            self._sfx_live = True                # t0 is 0 here: the clip IS the scene
            self.wait(SUBSCENE_HOLD)             # leading hold (once, at scene start)
            for i, name in enumerate(names):
                # A @still's cue is refused HERE too, not just on the single-subscene
                # path. Rendered alone a still is a PNG and carries no audio; in this
                # combined pass it happens to be a video segment, so without this the
                # same line would sound in `render NN` and be silent in `render NNf` --
                # the asymmetry the setup_scene guard exists to prevent.
                self._sfx_still = self._is_still(name)
                if self._is_still(name):
                    kept = list(self.mobjects)
                    self._clear_frame()          # independent frame: no carry-over
                getattr(self, name)()
                self._sfx_still = False
                self.wait(SUBSCENE_HOLD)         # single shared pause between subscenes
                if self._is_still(name):
                    # ...and none carried OUT either: the next subscene resumes from
                    # the state before the still, as it does when rendered alone.
                    self._clear_frame()
                    self.add(*kept)
                else:                            # still frames need no snapshot
                    self._save_snapshot(i, names)
            return

        idx = label_to_index(target)
        if not (0 <= idx < len(names)):
            raise IndexError(f"Subscene '{target}' out of range (have {len(names)})")

        # A @still/@thumbnail frame is self-contained: render it from an EMPTY frame
        # with no prior-snapshot load / prefix replay (that carry-over is what would
        # ghost the previous frame behind this one).
        if self._is_still(names[idx]):
            self._run_setup_scene()
            self._clear_frame()
            self._sfx_still = True               # _sfx_live stays False: a `-s` render
            self.wait(SUBSCENE_HOLD)             # writes no movie to carry audio
            getattr(self, names[idx])()
            self.wait(SUBSCENE_HOLD)             # trailing hold
            return

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
            self._run_setup_scene()
        if loaded_j < idx - 1:                  # replay the gap (or full prefix)
            self.renderer.skip_animations = True
            for i in range(loaded_j + 1, idx):
                if self._is_still(names[i]):     # a still changes no state: skip it,
                    continue                     # or its frame would leak into this one
                getattr(self, names[i])()
                self._save_snapshot(i, names)
            self.renderer.skip_animations = False

        # Discard any partial-movie frames produced while fast-forwarding the
        # prefix subscenes. Even under skip_animations, manim still appends each
        # replayed play()'s (cached) partial-movie file to the concat list, so
        # without this the earlier subscenes get stitched into this one's video.
        self._discard_replay_frames()
        self._reset_audio()                      # ...and its audio twin: drop any
        self._sfx_live = True                    # replay audio, rebase the clock

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

    # ── sound effects ─────────────────────────────────────────────────────────
    # The audio twin of _discard_replay_frames, and deliberately its neighbour: in
    # manim's SceneFileWriter.__init__ the two things they reset (init_audio() and
    # partial_movie_files) are set on adjacent lines, and they need discarding for
    # the same reason at the same moment. Rendering ONE subscene replays the prefix
    # to rebuild state; those frames are thrown away, and so must any audio.
    #
    # The other half is the CLOCK. renderer.time keeps advancing through the replay
    # (it does `self.time += scene.duration` even when skipping), so self.time at
    # the top of the target subscene is a FULL-SCENE timestamp -- for subscene h,
    # perhaps 120s into an 8s clip. file_writer.add_sound files at an absolute
    # position in the segment, so without rebasing, every cue in every staged clip
    # would land past the end of its own video.
    def _run_setup_scene(self):
        """setup_scene(), flagged so sfx() can refuse a cue placed there."""
        self._in_setup_scene = True
        try:
            self.setup_scene()
        finally:
            self._in_setup_scene = False

    def _reset_audio(self):
        """Discard replay audio and rebase the clock on the start of this clip."""
        self._audio_t0 = self.time
        self._sfx_cues = []
        fw = getattr(self.renderer, "file_writer", None)
        if fw is not None:
            fw.init_audio()      # manim's own reset: includes_sound = False, and
                                 # add_audio_segment recreates the segment lazily

    def sfx(self, name, at=0.0, gain=None):
        """Play sound effect `name` at this point in the subscene.

        `at` offsets in seconds from here (negative clamps to the clip start); `gain`
        is dB, for the exception -- the library is normalised at author time, so the
        usual call is just `self.sfx("click")`.

        Called for its side effect on the rendered clip's audio track, immediately
        before the animation it belongs to:

            self.sfx("click")
            self.play(FadeIn(tile), run_time=0.4)

        Cues belong on an ANIMATION BEAT. A cue in the TRAILING hold is dropped from
        the stitched full scene (`_stitch_full` trims exactly that second off every
        clip but the last) and is silent under the stretched still in the edit, so
        _finalize_audio warns about it. The leading hold is fine -- it survives.
        """
        if self._sfx_still:
            print(f"[bpk] sfx {name!r} ignored: a @still/@thumbnail renders a PNG, "
                  f"which carries no audio")
            return
        if not self._sfx_live:
            # Either replaying the prefix, or setup_scene(). The replay case is the
            # ordinary one and returning here also keeps it cheap -- otherwise every
            # prefix cue would decode its wav and overlay onto a growing segment.
            #
            # setup_scene() is a HARD ERROR instead, because it is the one place the
            # two render paths genuinely disagree: in a full-scene render it runs
            # with audio live, in a subscene render it runs inside the replay. A cue
            # there would play in `render 01` and vanish in `render 01d` -- exactly
            # the asymmetry this whole design exists to prevent.
            if self._in_setup_scene:
                raise RuntimeError(
                    f"sfx({name!r}) called from setup_scene(). Sound effects belong "
                    f"in a @subscene body: setup_scene runs inside the skipped prefix "
                    f"replay when a single subscene is rendered, so the cue would be "
                    f"heard in `render NN` and silently missing from `render NN<x>`.")
            return
        if os.environ.get("BPK_NO_SFX") == "1":
            return

        path = sfx_path(name)                    # raises, loudly, if unknown
        t = self.time - self._audio_t0 + at
        if t < 0:
            print(f"[bpk] sfx {name!r}: at={at} lands {-t:.3f}s before the clip "
                  f"start — clamped to 0")
            t = 0.0
        self.renderer.file_writer.add_sound(path, t, gain)

        try:
            dur = wav_info(path)[0]
        except Exception:
            dur = 0.0
        self._sfx_cues.append((name, path, t, dur))

    def _finalize_audio(self):
        """Match the audio segment to the video length, then audit the cues.

        THE TRIM IS LOAD-BEARING, not tidiness. manim asks PyAV to mux with
        `{"shortest": "1"}`, but `shortest` is an ffmpeg CLI flag and NOT an mp4
        muxer option, so it is ignored -- meaning the container duration would be
        whichever of audio/video is LONGER. Audio longer than video therefore
        produces an mp4 that REPORTS the wrong length, and everything downstream
        measures clips: render.py's `_duration` drives the stitch seam trim, the
        staged trailing still is grabbed with `-sseof`, and DaVinci shows the
        container length. Trimming here keeps container == video, always.
        """
        fw = getattr(self.renderer, "file_writer", None)
        if fw is None or not getattr(fw, "includes_sound", False):
            return
        clip_len = self.time - self._audio_t0

        seg = fw.audio_segment
        want_ms = int(round(clip_len * 1000))
        if len(seg) > want_ms:
            fw.audio_segment = seg[:want_ms]
        elif len(seg) < want_ms:
            from pydub import AudioSegment
            fw.audio_segment = seg + AudioSegment.silent(want_ms - len(seg),
                                                         frame_rate=seg.frame_rate)

        for name, path, t, dur in self._sfx_cues:
            if t + dur > clip_len + 1e-6:
                print(f"[bpk] sfx {name!r} at {t:.2f}s runs {t + dur - clip_len:.2f}s "
                      f"past the end of this clip ({clip_len:.2f}s) — it will be cut")
            elif t >= clip_len - SUBSCENE_HOLD - 1e-6:
                print(f"[bpk] sfx {name!r} at {t:.2f}s is inside the TRAILING hold — "
                      f"`--stills` trims that second off the staged clip and a "
                      f"full-scene stitch trims it off every clip but the last, so it "
                      f"is silent in the edit. Move it onto an animation beat.")
            elif t < SUBSCENE_HOLD - 1e-6:
                print(f"[bpk] sfx {name!r} at {t:.2f}s is inside the LEADING hold — "
                      f"`--stills` trims that second off the staged clip, so it is "
                      f"silent in the edit. Move it onto an animation beat.")
            for complaint in spec_complaints(path):
                print(f"[bpk] sfx {name!r}: {complaint}")

    def tear_down(self):
        # manim calls this after construct() and BEFORE scene_finished() ->
        # file_writer.finish() -> combine_to_movie(), so it is exactly the window in
        # which every cue is filed and the mux has not run yet.
        self._finalize_audio()
        super().tear_down()