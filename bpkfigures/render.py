"""One render path for both the user and the agent.

Wraps `bpkfigures.resolve` (subscene resolution + stale-output cleanup) and the
SUBSCENE/RECOMPUTE env the snapshot cache uses, and adds: auto-locating the venv,
multiple targets, one-shot frame extraction, and a no-render `--state` peek at a
subscene's start state. Quality defaults to HIGH (-qh); use --fast for -ql.

Usage (run from the dir holding the NN*.py scene files, e.g. animations/scenes/):
    render 01g                       # subscene g (high quality)
    render 01g --fast                # quick low-res check (-ql)
    render 01g 01h 01i               # several in sequence
    render 01                        # full scene
    render 01 sub                    # all subscenes, in order
    render 01 all                    # all subscenes, then the full scene
    render 01bf                      # subscenes b through f
    render 01b-                      # subscene b through the end
    render 01-f                      # the beginning through subscene f
    render 01g --recompute           # ignore the snapshot cache
    render 01g --frames "1.0,2.0,-0.3"   # render then extract those frames
    render 01g --frames 5            # 5 evenly-spaced frames
    render 01g --frames "1.0,-0.3" --extract  # extract from the EXISTING mp4
                                              # (no re-render); then Read the PNGs
    render 01h --state               # print mobjects at h's start (no render)
    render 01 --check                # AST-parse the scene + assets only (no manim)

Negative frame times are seconds-from-end (like ffmpeg -sseof). If `render`
isn't on PATH, use `<repo>/.venv/bin/python -m bpkfigures.render ...`.
"""
import glob
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


def _output_mp4(output):
    """Find the rendered mp4 for `output` under media/videos/**/."""
    hits = glob.glob(os.path.join("media", "videos", "**", f"{output}.mp4"),
                     recursive=True)
    # newest wins if multiple qualities
    return max(hits, key=os.path.getmtime) if hits else None


# ── --state: peek at a subscene's starting mobjects (no render) ────────────────
def _print_state(path, classname, letter):
    """Load the PRIOR subscene's snapshot and list the mobjects on screen at the
    start of subscene `letter` (idx-1). Reuses the snapshot the cache wrote."""
    if not letter:
        print("--state needs a subscene letter (e.g. 01h --state)")
        return 1
    idx = ord(letter) - ord("a")
    if idx == 0:
        print(f"subscene '{letter}' is the first — starts from an empty scene.")
        return 0
    import pickle
    prev = chr(ord("a") + idx - 1)
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
    concrete targets. "" → full scene; "g" → that subscene; "bf" → b..f; "b-" →
    b..last; "-f" → first..f."""
    if spec == "":
        return [prefix]                                  # full scene
    if len(spec) == 1 and spec.isalpha():
        return [prefix + spec]                           # single subscene
    if len(spec) == 2 and spec.endswith("-") and spec[0].isalpha():
        lo, hi = spec[0], letters[-1]                    # "b-"  → b..last
    elif len(spec) == 2 and spec.startswith("-") and spec[1].isalpha():
        lo, hi = letters[0], spec[1]                     # "-f"  → first..f
    elif len(spec) == 2 and spec.isalpha():
        lo, hi = spec[0], spec[1]                        # "bf"  → b..f
    else:
        return [prefix + spec]                           # leave odd specs to resolve
    if lo not in letters or hi not in letters:
        raise IndexError(f"range {prefix}{spec} out of {prefix}'s subscenes "
                         f"({letters[0]}..{letters[-1]})")
    i0, i1 = letters.index(lo), letters.index(hi)
    step = 1 if i0 <= i1 else -1
    return [prefix + L for L in letters[i0:i1 + step:step]]


def _expand_targets(rest):
    """Turn `rest` into (targets, passthrough). Handles the `all`/`sub` keywords
    (all subscenes, plus the full scene for `all`) and the range forms above."""
    mode = "all" if "all" in rest else ("sub" if "sub" in rest else None)
    toks = [a for a in rest if a not in ("all", "sub")]
    digit_toks = [a for a in toks if len(a) >= 2 and a[:2].isdigit()]
    passthrough = [a for a in toks if a not in digit_toks]

    targets = []
    for tok in digit_toks:
        prefix, spec = tok[:2], tok[2:]
        if mode and spec == "":
            letters = resolve.subscene_letters(prefix)
            targets += [prefix + L for L in letters]
            if mode == "all":
                targets.append(prefix)                   # full scene last
        elif len(spec) == 2 or (len(spec) == 1 and spec in "-"):
            targets += _expand_one(prefix, spec, resolve.subscene_letters(prefix))
        else:
            targets.append(tok)                          # NN or NNx — as-is
    return targets, passthrough


# ── --check: fast syntax check (no manim) ─────────────────────────────────────
def _check_syntax(targets):
    """AST-parse the target scene file(s) plus every assets/*.py they sit next to,
    with NO manim import — an instant catch for syntax errors before paying for a
    render. Returns 0 if all parse, 1 otherwise."""
    import ast
    paths = []
    for target in targets:
        try:
            scene_path = resolve.resolve(target)[0]
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 1
        paths.append(os.path.abspath(scene_path))
    # the shared assets the scenes import live in ../assets/ (run from scenes/)
    paths += [os.path.abspath(p) for p in glob.glob(os.path.join("..", "assets", "*.py"))]

    rc = 0
    for p in dict.fromkeys(paths):     # dedup, keep order
        try:
            with open(p) as f:
                ast.parse(f.read(), filename=p)
        except SyntaxError as e:
            print(f"{p}:{e.lineno}: {e.msg}", file=sys.stderr)
            rc = 1
    if rc == 0:
        print("syntax OK")
    return rc


# ── main ──────────────────────────────────────────────────────────────────────
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    # flags. Quality defaults to HIGH (-qh, matching the old alias / manim.cfg);
    # use --fast (or -ql) for a quick low-res check.
    recompute = "--recompute" in argv
    fast = ("--fast" in argv) or ("-ql" in argv)
    hq = "--hq" in argv          # accepted but redundant (hq is the default)
    state = "--state" in argv
    check = "--check" in argv    # AST-parse the scene + assets (no manim, instant)
    extract = "--extract" in argv  # extract --frames from the EXISTING mp4 (no render)
    quiet = "--quiet" in argv    # pass -v WARNING to manim (drops per-animation INFO spam)
    frames_spec = None
    tail = None                  # --tail N: capture manim output, emit only its last N lines
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--recompute", "--hq", "--state", "--fast", "-ql", "--quiet",
                 "--check", "--extract"):
            pass
        elif a == "--frames":
            i += 1
            frames_spec = argv[i] if i < len(argv) else None
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
    # ranges (01bf, 01b-, 01-f) and the `all`/`sub` keywords.
    try:
        targets, passthrough = _expand_targets(rest)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2
    if not targets:
        print("usage: render NN[letter] [NN[letter] ...] [NN all|sub] [NNbf|NNb-|NN-f] "
              "[--recompute] [--fast] [--quiet] [--tail N] [--frames T|N] [--state] [--check]")
        return 2

    if check:
        return _check_syntax(targets)

    worst_rc = 0
    for target in targets:
        rc = _render_one(target, passthrough, recompute, fast, state, frames_spec,
                         quiet=quiet, tail=tail_n, extract=extract)
        worst_rc = worst_rc or rc
        if not state and not extract and rc == 0:
            print(f"Finished rendering {target}", file=sys.stderr)
    return worst_rc


def _render_one(target, passthrough, recompute, fast, state, frames_spec,
                quiet=False, tail=None, extract=False):
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

    if state:
        return _print_state(path, classname, letter)

    if extract:
        # pull --frames from the ALREADY-rendered mp4, no manim run
        if frames_spec is None:
            print("--extract needs --frames", file=sys.stderr)
            return 2
        mp4 = _output_mp4(output)
        if not mp4:
            print(f"[render] no existing mp4 for {output} — render it first",
                  file=sys.stderr)
            return 1
        for p in _extract_frames(mp4, _parse_frames(frames_spec, _duration(mp4))):
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
    quality = "-ql" if fast else "-qh"
    cmd = [manim, quality]
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

    if frames_spec is not None:
        mp4 = _output_mp4(output)
        if not mp4:
            print(f"[render] could not find output mp4 for {output}",
                  file=sys.stderr)
            return rc
        times = _parse_frames(frames_spec, _duration(mp4))
        for p in _extract_frames(mp4, times):
            print(p)
    return rc


if __name__ == "__main__":
    sys.exit(main())
