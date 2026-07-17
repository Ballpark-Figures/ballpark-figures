"""One render path for both the user and the agent.

Wraps `bpkfigures.resolve` (subscene resolution + stale-output cleanup) and the
SUBSCENE/RECOMPUTE env the snapshot cache uses, and adds: auto-locating the venv,
multiple targets, one-shot frame extraction, and a no-render `--state` peek at a
subscene's start state. Quality defaults to HIGH (-qh); use --fast for -ql.

Usage (run from the dir holding the NN*.py scene files, e.g. animations/scenes/):
    render 01g                       # subscene g (high quality)
    render 01g --fast                # quick low-res check (-ql)
    render 01g --very-fast           # 3 fps @ 256x144 — fastest possible check
    render 01g 01h 01i               # several in sequence
    render 01                        # full scene
    render 01 sub                    # all subscenes, in order
    render 01 all                    # all subscenes, then the full scene
    render 01b-f                     # subscenes b through f (ranges are DASH-delimited)
    render 01b-                      # subscene b through the end
    render 01-f                      # the beginning through subscene f
    render 06za                      # a multi-char subscene label (a..z, then za..zz, ...)
    render 01g --recompute           # ignore the snapshot cache
    render 01g --frames "1.0,2.0,-0.3"   # render then extract those frames
    render 01g --frames 5            # 5 evenly-spaced frames
    render 01g --frames "1.0,-0.3" --extract  # extract from the EXISTING mp4
                                              # (no re-render); then Read the PNGs
    render 01 sub --padded           # render each subscene + a first/last-frame-
                                     # padded copy (10s/side) under padded_videos/
    render 01g --padded 3            # render, then pad with 3s each side
    render 01g --padded --extract    # pad the EXISTING mp4 (no re-render)
    render 99a                       # scene 99 = thumbnails: auto-renders a STATIC 4K PNG
                                     # (manim -s -qk) into media/images/<scene>/2160p/;
                                     # prints its path
    render 99a --fast                # same, but a quick low-res PNG (→ …/480p/)
    render 99 all                    # every thumbnail — but ONLY the ones whose inputs
                                     # changed re-render (unchanged ones are skipped)
    render 07a --thumb               # force a still PNG for ANY scene (99 is automatic)

Thumbnails are independent images, so `render 99 all` skips any whose code (or a
shared helper/asset it uses) is unchanged since its PNG — keyed the same way the
snapshot cache keys subscenes, with a quality tag. `--recompute` forces a rebuild.
Each PNG lands in a per-RESOLUTION subfolder (`media/images/<scene>/2160p|480p/…`)
so a low-res --fast test can't be mistaken for the 4K upload asset, and a slot
keeps a single image per quality (a renamed subscene's old PNG is swept).
    render 01h --state               # print mobjects at h's start (no render)
    render 01 --check                # AST-parse the scene + assets only (no manim)

Negative frame times are seconds-from-end (like ffmpeg -sseof). If `render`
isn't on PATH, use `<repo>/.venv/bin/python -m bpkfigures.render ...`.
"""
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

from bpkfigures import resolve


# ── locating tools ────────────────────────────────────────────────────────────
def _find_venv_manim(start=None):
    """Walk up from `start` looking for a `.venv/bin/manim` (or `manim.exe`)."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        for cand in (os.path.join(d, ".venv", "bin", "manim"),
                     os.path.join(d, "venv", "bin", "manim")):
            if os.path.exists(cand):
                return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # fall back to whatever manim is on PATH
    return shutil.which("manim") or "manim"


def _ffmpeg():
    return shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def _ffprobe():
    return shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"


# ── frame extraction ──────────────────────────────────────────────────────────
def _duration(mp4):
    out = subprocess.run([_ffprobe(), "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", mp4],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def _parse_frames(spec, dur):
    """spec is "t1,t2,..." (negative = from end) or an int N for N even frames."""
    if spec is None:
        return []
    spec = spec.strip()
    if "," not in spec and spec.lstrip("-").isdigit() and float(spec) > 0 \
            and "." not in spec:
        n = int(spec)
        if not dur:
            return []
        # N frames evenly spread, avoiding the very edges
        return [round(dur * (i + 1) / (n + 1), 3) for i in range(n)]
    times = []
    for part in spec.split(","):
        part = part.strip()
        if part:
            times.append(float(part))
    return times


def _extract_frames(mp4, times):
    """Write a PNG per time into a frames/ dir beside the mp4; return paths."""
    frames_dir = os.path.join(os.path.dirname(mp4), "frames")
    os.makedirs(frames_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(mp4))[0]
    paths = []
    for t in times:
        tag = f"end{abs(t):g}" if t < 0 else f"{t:g}"
        out = os.path.join(frames_dir, f"{stem}_{tag}.png")
        seek = ["-sseof", str(t)] if t < 0 else ["-ss", str(t)]
        r = subprocess.run([_ffmpeg(), "-y", *seek, "-i", mp4,
                            "-frames:v", "1", out],
                           capture_output=True)
        if r.returncode == 0:
            paths.append(out)
    return paths


def _pad_video(mp4, seconds):
    """Write a copy of `mp4` with `seconds` of its FIRST frame frozen at the head
    and its LAST frame frozen at the tail, into a `padded_videos/` tree mirroring
    `videos/` (same substructure). ffmpeg's tpad clones the end frames; renders are
    SILENT so only the video stream needs padding. Returns the output path (or None
    on failure). Re-encodes (tpad can't stream-copy) at near-lossless crf 18."""
    parts = os.path.normpath(mp4).split(os.sep)
    try:                                    # media/videos/<scene>/<q>/x.mp4 -> padded_videos
        vi = len(parts) - 1 - parts[::-1].index("videos")
    except ValueError:
        print(f"[render] {mp4} is not under a videos/ dir — can't pad", file=sys.stderr)
        return None
    parts[vi] = "padded_videos"
    out = os.sep.join(parts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    vf = (f"tpad=start_duration={seconds}:start_mode=clone:"
          f"stop_duration={seconds}:stop_mode=clone")
    r = subprocess.run([_ffmpeg(), "-y", "-i", mp4, "-vf", vf,
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out],
                       capture_output=True)
    if r.returncode != 0:
        print(f"[render] ffmpeg pad failed for {mp4}:\n"
              f"{r.stderr.decode(errors='replace')[-600:]}", file=sys.stderr)
        return None
    return out


def _output_mp4(output):
    """Find the rendered mp4 for `output` under media/videos/**/."""
    hits = glob.glob(os.path.join("media", "videos", "**", f"{output}.mp4"),
                     recursive=True)
    # newest wins if multiple qualities
    return max(hits, key=os.path.getmtime) if hits else None


def _output_png(output):
    """Find the saved-last-frame PNG for `output` under media/images/**/ (what
    manim's `-s` writes for a --thumb render). Prefers an exact `<output>.png`;
    falls back to the newest PNG in the images tree if manim named it otherwise."""
    hits = glob.glob(os.path.join("media", "images", "**", f"{output}.png"),
                     recursive=True)
    if not hits:
        hits = glob.glob(os.path.join("media", "images", "**", "*.png"),
                         recursive=True)
    return max(hits, key=os.path.getmtime) if hits else None


# ── thumbnail change-detection (skip re-rendering unchanged 99 images) ─────────
# Thumbnails (scene 99) are INDEPENDENT static frames, so a `render 99 all` need
# only re-render the ones whose inputs changed. We key each thumbnail's PNG by the
# SAME per-subscene digest the snapshot cache uses (bpkfigures.scene), so a change
# to one thumbnail's code (or a shared helper/asset it reaches) re-renders exactly
# the affected thumbnails and skips the rest. Keys live in a committed-free JSON
# manifest beside the PNGs under media/images/ (gitignored, machine-local).
def _thumb_scene_module_name(scene_path):
    return os.path.splitext(os.path.basename(scene_path))[0]


# Thumbnail PNGs go in a per-RESOLUTION subfolder (parallel to videos, but no fps —
# meaningless for a still) so a low-res --fast test can't be mistaken for the 4K
# upload asset: the real one is always 2160p/.
_QTAG_DIR = {"hq": "2160p", "fast": "480p", "very_fast": "144p"}


def _qtag(fast, very_fast):
    return "very_fast" if very_fast else ("fast" if fast else "hq")


def _load_scene_class(scene_path, classname):
    """Import the scene module (for its class + module namespace) so we can compute
    the per-subscene digest. Sets sys.modules[modname] so scene._scene_source_digest
    can resolve module-level references."""
    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..")))
    modname = _thumb_scene_module_name(scene_path)
    mod = sys.modules.get(modname)
    if mod is None:
        spec = importlib.util.spec_from_file_location(modname, scene_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
    return getattr(mod, classname)


def _thumb_key(cls, scene_path, name, qtag):
    """The change-key for one thumbnail subscene: the SAME three terms as the
    snapshot prefix-key (bpkfigures.scene), but for this ONE independent subscene —
    version + project-source hash (excluding the scene file + CLI tooling) + the
    subscene's dependency-closure digest — plus the render QUALITY tag (so a quick
    --fast PNG never satisfies a later full-res render)."""
    from bpkfigures import scene as S
    bpk = S._BPK_DIR
    project_root = os.path.dirname(os.path.dirname(os.path.realpath(scene_path)))
    tooling = {os.path.realpath(os.path.join(bpk, f)) for f in ("render.py", "resolve.py")}
    srcs = [
        f"v{S.SNAPSHOT_VERSION}",
        f"q:{qtag}",
        S._source_hash([bpk, project_root],
                       exclude={os.path.realpath(scene_path)} | tooling),
        S._scene_source_digest(cls, ["setup_scene", name]),
    ]
    return hashlib.md5("".join(srcs).encode()).hexdigest()


def _thumb_png_path(scene_path, output, qdir):
    return os.path.join("media", "images", _thumb_scene_module_name(scene_path),
                        qdir, f"{output}.png")


def _thumb_manifest_path(scene_path):
    return os.path.join("media", "images", _thumb_scene_module_name(scene_path),
                        ".render_keys.json")


def _clean_stale_thumb(scene_path, prefix, letter, keep_output):
    """Remove PNGs for this thumbnail SLOT (`<prefix><letter>_*`) whose subscene was
    renamed — a different name than the current `keep_output` — across every
    resolution subfolder AND the top level, so a slot keeps a single image per
    quality. Mirrors resolve.clean_stale for videos. Returns the files removed."""
    module_dir = os.path.join("media", "images", _thumb_scene_module_name(scene_path))
    removed = []
    for png in glob.glob(os.path.join(module_dir, "**", f"{prefix}{letter}_*.png"),
                         recursive=True):
        if os.path.splitext(os.path.basename(png))[0] != keep_output:
            try:
                os.remove(png)
                removed.append(png)
            except OSError:
                pass
    return removed


def _load_manifest(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_manifest(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=0, sort_keys=True)


def _thumb_change_plan(targets, qtag):
    """For the 99 (thumbnail) targets, compute each one's change-key and decide
    which are UP TO DATE (existing PNG in this quality's folder + matching manifest
    key → skip). Returns (skip:set, keys:{target:key}, mkeys:{target:manifest_key},
    manifest_path, manifest). The manifest key is scoped by quality subfolder so a
    --fast entry never satisfies a full-res render. Any failure → empty plan (render
    everything); never blocks."""
    tt = [t for t in targets if _is_thumb_prefix(t[:2])]
    empty = (set(), {}, {}, None, {})
    if not tt:
        return empty
    try:
        qdir = _QTAG_DIR[qtag]
        path0, classname0, _o, _l = resolve.resolve(tt[0])
        cls = _load_scene_class(path0, classname0)
        _cn, subs = resolve._parse(path0)
        manifest_path = _thumb_manifest_path(path0)
        manifest = _load_manifest(manifest_path)
        skip, keys, mkeys = set(), {}, {}
        for t in tt:
            letter = t[2:]
            name = subs[resolve.label_to_index(letter)]
            output = f"{t[:2]}{letter}_{name}"
            key = _thumb_key(cls, path0, name, qtag)
            mkey = f"{qdir}/{output}"
            keys[t], mkeys[t] = key, mkey
            if manifest.get(mkey) == key and \
                    os.path.exists(_thumb_png_path(path0, output, qdir)):
                skip.add(t)
        return skip, keys, mkeys, manifest_path, manifest
    except Exception as e:
        print(f"[render] thumbnail change-check skipped "
              f"({type(e).__name__}: {e})", file=sys.stderr)
        return empty


# ── --state: peek at a subscene's starting mobjects (no render) ────────────────
def _print_state(path, classname, letter):
    """Load the PRIOR subscene's snapshot and list the mobjects on screen at the
    start of subscene `letter` (idx-1). Reuses the snapshot the cache wrote."""
    if not letter:
        print("--state needs a subscene letter (e.g. 01h --state)")
        return 1
    idx = resolve.label_to_index(letter)
    if idx == 0:
        print(f"subscene '{letter}' is the first — starts from an empty scene.")
        return 0
    import pickle
    prev = resolve.index_to_label(idx - 1)
    pkl = os.path.join("cache", "snapshots", f"{classname}_{prev}.pkl")
    if not os.path.exists(pkl):
        print(f"no snapshot for subscene '{prev}' at {pkl} — render up to "
              f"'{prev}' first (e.g. render {path[:2]}{prev}).")
        return 1
    # the scene module must be importable so pickle can resolve mobject classes
    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..")))
    try:
        with open(pkl, "rb") as f:
            bundle = pickle.load(f)
    except Exception as e:
        print(f"could not load snapshot: {type(e).__name__}: {e}")
        return 1
    mobs = bundle.get("mobjects", [])
    attrs = list(bundle.get("attrs", {}).keys())
    print(f"At the START of subscene '{letter}' (end of '{prev}'):")
    print(f"  {len(mobs)} mobject(s) on screen:")
    for m in mobs:
        kind = type(m).__name__
        n = len(getattr(m, "submobjects", []))
        try:
            c = m.get_center()
            pos = f"({c[0]:.2f}, {c[1]:.2f})"
        except Exception:
            pos = "?"
        print(f"    - {kind}  submobs={n}  center={pos}")
    print(f"  setup attrs available: {', '.join(attrs)}")
    return 0


# ── target expansion (ranges + all/sub) ───────────────────────────────────────
def _expand_one(prefix, spec, letters):
    """Expand a single NN token's `spec` (the part after the 2-digit prefix) into
    concrete targets. "" → full scene; "za" → that subscene. Ranges are
    DASH-delimited (labels can be multi-char now, so `06za` must mean the single
    subscene za): "a-c" → a..c; "a-" → a..last; "-c" → first..c."""
    if spec == "":
        return [prefix]                                  # full scene
    if "-" not in spec:
        return [prefix + spec]                           # single subscene
    lo_s, hi_s = spec.split("-", 1)
    lo = lo_s if lo_s else letters[0]                    # "-c" → first..c
    hi = hi_s if hi_s else letters[-1]                   # "a-" → a..last
    if lo not in letters or hi not in letters:
        raise IndexError(f"range {prefix}{spec} out of {prefix}'s subscenes "
                         f"({letters[0]}..{letters[-1]})")
    i0, i1 = letters.index(lo), letters.index(hi)
    step = 1 if i0 <= i1 else -1
    return [prefix + L for L in letters[i0:i1 + step:step]]


def _is_thumb_prefix(prefix):
    """Scene `99` is the reserved thumbnails slot — every target is an individual
    still image, and there is NO meaningful whole-scene render."""
    return prefix == "99"


def _expand_targets(rest):
    """Turn `rest` into (targets, passthrough). Handles the `all`/`sub` keywords
    (all subscenes, plus the full scene for `all`) and the range forms above.

    Thumbnails (scene `99`) have no whole-scene image, so a bare `99` expands to
    each thumbnail and `all` does NOT append the full-scene target (that produced a
    meaningless combined `99_thumbnails.png`)."""
    mode = "all" if "all" in rest else ("sub" if "sub" in rest else None)
    toks = [a for a in rest if a not in ("all", "sub")]
    digit_toks = [a for a in toks if len(a) >= 2 and a[:2].isdigit()]
    passthrough = [a for a in toks if a not in digit_toks]

    targets = []
    for tok in digit_toks:
        prefix, spec = tok[:2], tok[2:]
        thumb = _is_thumb_prefix(prefix)
        if mode and spec == "":
            letters = resolve.subscene_letters(prefix)
            targets += [prefix + L for L in letters]
            if mode == "all" and not thumb:
                targets.append(prefix)                   # full scene last
        elif spec == "" and thumb:                       # bare `99`: each thumbnail
            targets += [prefix + L for L in resolve.subscene_letters(prefix)]
        elif "-" in spec:                                # dash-delimited range
            targets += _expand_one(prefix, spec, resolve.subscene_letters(prefix))
        else:
            targets.append(tok)                          # NN (full) or NN<label> — as-is
    return targets, passthrough


# ── --check: fast syntax check (no manim) ─────────────────────────────────────
def _check_syntax(targets):
    """AST-parse the target scene file(s) plus every assets/*.py they sit next to,
    with NO manim import — an instant catch for syntax errors before paying for a
    render — then WARN-ONLY style-lint the scene file(s) (see bpkfigures/lint.py).
    Returns 0 if all parse (lint warnings never fail the check), 1 on a syntax error."""
    import ast
    scene_paths = []
    for target in targets:
        try:
            scene_path = resolve.resolve(target)[0]
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 1
        scene_paths.append(os.path.abspath(scene_path))
    # the shared assets the scenes import live in ../assets/ (run from scenes/)
    asset_paths = [os.path.abspath(p) for p in glob.glob(os.path.join("..", "assets", "*.py"))]

    for p in dict.fromkeys(scene_paths + asset_paths):   # dedup, keep order
        try:
            with open(p) as f:
                ast.parse(f.read(), filename=p)
        except SyntaxError as e:
            print(f"{p}:{e.lineno}: {e.msg}", file=sys.stderr)
            return 1

    # WARN-ONLY style lint of the SCENE file(s) only (assets/ legitimately define
    # colours + use the text helpers). Never blocks a render — and a linter bug must
    # never take down the syntax check, so it's wrapped defensively.
    n = 0
    try:
        from bpkfigures import lint
        for p in dict.fromkeys(scene_paths):
            for lineno, msg in lint.lint_file(p):
                print(f"[lint] {os.path.basename(p)}:{lineno}: {msg}")
                n += 1
    except Exception as e:                    # pragma: no cover — lint must not fail --check
        print(f"[lint] skipped (linter error: {e})", file=sys.stderr)
    print("syntax OK" + (f" — {n} lint warning{'s' * (n != 1)} (style, warn-only)"
                         if n else ""))
    return 0


# ── per-scene render lock (avoid concurrent renders corrupting the cache) ──────
_LOCK_DIR = os.path.join("cache", "locks")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # exists, just not ours
    except OSError:
        return False
    return True


def _acquire_locks(prefixes):
    """One lock per scene prefix so a second render of the SAME scene can't run
    concurrently (concurrent manim runs corrupt partial movies / the snapshot
    cache). Stale locks (dead PID) are taken over. Returns the acquired paths, or
    None if any scene is already being rendered by a live process."""
    os.makedirs(_LOCK_DIR, exist_ok=True)
    acquired = []
    for prefix in prefixes:
        path = os.path.join(_LOCK_DIR, f"render-{prefix}.lock")
        if os.path.exists(path):
            try:
                pid = int(open(path).read().split()[0])
            except (ValueError, OSError, IndexError):
                pid = None
            if pid and _pid_alive(pid):
                print(f"[render] scene {prefix} is already being rendered "
                      f"(pid {pid}) — refusing a concurrent render of the same "
                      f"scene; wait for it or kill it. (lock: {path})",
                      file=sys.stderr)
                _release_locks(acquired)
                return None
        with open(path, "w") as f:
            f.write(f"{os.getpid()} {prefix}")
        acquired.append(path)
    return acquired


def _release_locks(paths):
    for p in paths or []:
        try:
            os.remove(p)
        except OSError:
            pass


# ── main ──────────────────────────────────────────────────────────────────────
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    # flags. Quality defaults to HIGH (-qh, matching the old alias / manim.cfg);
    # use --fast (or -ql) for a quick low-res check.
    recompute = "--recompute" in argv
    fast = ("--fast" in argv) or ("-ql" in argv)
    very_fast = "--very-fast" in argv   # 3 fps @ 256x144 — fastest possible
    hq = "--hq" in argv          # accepted but redundant (hq is the default)
    state = "--state" in argv
    check = "--check" in argv    # AST-parse the scene + assets (no manim, instant)
    extract = "--extract" in argv  # extract --frames from the EXISTING mp4 (no render)
    thumb = ("--thumb" in argv) or ("--thumbnail" in argv)  # static -s PNG (4K by default)
    quiet = "--quiet" in argv    # pass -v WARNING to manim (drops per-animation INFO spam)
    frames_spec = None
    padded = None                # --padded [N]: also write a first/last-frame-padded copy
    tail = None                  # --tail N: capture manim output, emit only its last N lines
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--recompute", "--hq", "--state", "--fast", "--very-fast", "-ql",
                 "--quiet", "--check", "--extract", "--thumb", "--thumbnail"):
            pass
        elif a == "--frames":
            i += 1
            frames_spec = argv[i] if i < len(argv) else None
        elif a == "--padded":
            # optional numeric arg = seconds per side (default 10); a non-number next
            # token (e.g. a target) is left alone
            padded = 10.0
            if i + 1 < len(argv):
                try:
                    padded = float(argv[i + 1])
                    i += 1
                except ValueError:
                    pass
        elif a == "--tail":
            i += 1
            tail = argv[i] if i < len(argv) else None
        else:
            rest.append(a)
        i += 1

    tail_n = None
    if tail is not None:
        try:
            tail_n = max(1, int(tail))
        except ValueError:
            tail_n = None

    # every NN[letter] arg is a target — supports `render 01g 01h 01i`, plus
    # dash ranges (01b-f, 01b-, 01-f) and the `all`/`sub` keywords.
    try:
        targets, passthrough = _expand_targets(rest)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2
    if not targets:
        print("usage: render NN[label] [NN[label] ...] [NN all|sub] [NNa-c|NNb-|NN-f] "
              "[--recompute] [--fast] [--quiet] [--tail N] [--frames T|N] [--padded [N]] "
              "[--thumb] [--state] [--check]")
        return 2

    if check:
        return _check_syntax(targets)

    # Thumbnails (scene 99) are independent images — skip re-rendering the ones
    # whose inputs are unchanged since their PNG (unless --recompute forces a rebuild).
    # The key (and PNG folder) is per-quality so a --fast PNG never satisfies a
    # full-res run.
    qtag = _qtag(fast, very_fast)
    skip, thumb_keys, thumb_mkey, manifest_path, manifest = (
        (set(), {}, {}, None, {}) if (recompute or state or extract)
        else _thumb_change_plan(targets, qtag))

    # lock per scene for actual renders (not the read-only --state/--extract modes)
    locks = None
    if not state and not extract:
        locks = _acquire_locks(sorted({t[:2] for t in targets}))
        if locks is None:
            return 1
    try:
        worst_rc = 0
        for target in targets:
            if target in skip:
                print(f"[render] {target} up to date — skipped "
                      f"(use --recompute to force)", file=sys.stderr)
                continue
            rc = _render_one(target, passthrough, recompute, fast, state,
                             frames_spec, quiet=quiet, tail=tail_n,
                             extract=extract, very_fast=very_fast, padded=padded,
                             thumb=thumb)
            worst_rc = worst_rc or rc
            if not state and not extract and rc == 0:
                print(f"Finished rendering {target}", file=sys.stderr)
                if target in thumb_keys and manifest_path:   # record the new key
                    manifest[thumb_mkey[target]] = thumb_keys[target]
                    _save_manifest(manifest_path, manifest)
        return worst_rc
    finally:
        _release_locks(locks)


def _render_one(target, passthrough, recompute, fast, state, frames_spec,
                quiet=False, tail=None, extract=False, very_fast=False, padded=None,
                thumb=False):
    """Resolve, (clean+render) or --state, and extract frames for one target.

    quiet -> pass `-v WARNING` to manim (suppresses its per-animation INFO log).
    tail  -> capture manim's output and print only its last `tail` lines (render's
             own [render]/frame-path/Finished lines still print). Both opt-in;
             without them manim streams live as before."""
    try:
        path, classname, output, letter = resolve.resolve(target)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    # Scene `99` is the reserved THUMBNAILS slot (every video), so it always renders
    # as a still image — no --thumb needed. --thumb still forces it for any scene.
    thumb = thumb or target[:2] == "99"

    if state:
        return _print_state(path, classname, letter)

    if extract:
        # post-process the ALREADY-rendered mp4 (extract frames and/or pad), no manim
        if frames_spec is None and padded is None:
            print("--extract needs --frames or --padded", file=sys.stderr)
            return 2
        mp4 = _output_mp4(output)
        if not mp4:
            print(f"[render] no existing mp4 for {output} — render it first",
                  file=sys.stderr)
            return 1
        if frames_spec is not None:
            for p in _extract_frames(mp4, _parse_frames(frames_spec, _duration(mp4))):
                print(p)
        if padded is not None:
            p = _pad_video(mp4, padded)
            if p:
                print(p)
        return 0

    # clean stale outputs for this slot
    for f in resolve.clean_stale(classname, target[:2], letter, output):
        print(f"[render] removed stale {f}", file=sys.stderr)

    # build the env (explicit -> no leak from a prior interrupted run)
    env = dict(os.environ)
    env.pop("SUBSCENE", None)
    env.pop("RECOMPUTE", None)
    if letter:
        env["SUBSCENE"] = letter
    if recompute:
        env["RECOMPUTE"] = "1"

    manim = _find_venv_manim()
    # --thumb wants a high-res still (4K, -qk) to give YouTube's downscale the most
    # data; --fast/--very-fast still win for a quick low-res layout check.
    if fast or very_fast:
        quality = "-ql"
    elif thumb:
        quality = "-qk"
    else:
        quality = "-qh"
    cmd = [manim, quality]
    if thumb:
        cmd += ["-s"]                            # save the LAST frame as a PNG (no video)
    if very_fast:
        cmd += ["-r", "256,144", "--fps", "3"]   # terrible res + 3 fps
    if quiet:
        cmd += ["-v", "WARNING"]
    cmd += [*passthrough, path, classname, "-o", output]
    print(f"[render] {' '.join(cmd)}  (SUBSCENE={letter or '-'})",
          file=sys.stderr)
    if tail is not None:
        proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        for ln in proc.stdout.splitlines()[-tail:]:
            print(ln, file=sys.stderr)
        rc = proc.returncode
    else:
        rc = subprocess.run(cmd, env=env).returncode
    if rc != 0:
        return rc

    if thumb:
        # -s writes the still to media/images/<module>/<output>.png (manim uses no
        # per-quality subfolder for images). MOVE it into a resolution subfolder so a
        # --fast test can't overwrite / be mistaken for the 4K upload asset.
        module_dir = os.path.join("media", "images", _thumb_scene_module_name(path))
        src = os.path.join(module_dir, f"{output}.png")
        if not os.path.exists(src):
            src = _output_png(output) or ""      # fallback if manim named it otherwise
        if src and os.path.exists(src):
            dest = os.path.join(module_dir, _QTAG_DIR[_qtag(fast, very_fast)],
                                f"{output}.png")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.replace(src, dest)
            # keep a single image per slot: drop any renamed-slot PNGs (all qualities)
            for f in _clean_stale_thumb(path, target[:2], letter, output):
                print(f"[render] removed stale {f}", file=sys.stderr)
            print(dest)
        else:
            print(f"[render] rendered but couldn't find output PNG for {output} "
                  f"under media/images/", file=sys.stderr)
        return rc

    if frames_spec is not None or padded is not None:
        mp4 = _output_mp4(output)
        if not mp4:
            print(f"[render] could not find output mp4 for {output}",
                  file=sys.stderr)
            return rc
        if frames_spec is not None:
            for p in _extract_frames(mp4, _parse_frames(frames_spec, _duration(mp4))):
                print(p)
        if padded is not None:
            p = _pad_video(mp4, padded)
            if p:
                print(p)
    return rc


if __name__ == "__main__":
    sys.exit(main())
