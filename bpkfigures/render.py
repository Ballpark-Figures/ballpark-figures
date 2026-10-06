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
    render 01d --stills              # stage 01d into <repo>/edit_clips/ (anim copy + its
                                     # leading still; the last subscene adds the end still),
                                     # and with DaVinci open, import it into the Media Pool
                                     # (per-scene bin) — or refresh it in place on a
                                     # re-render. Supersedes --padded. Ranges: 04d- --stills
                                     # Only into the clip's OWN project (Wordle / Wordle
                                     # Bonus); with another open it is QUEUED instead
    render 01d --stills --switch     # ...or open the clip's project, import, and reopen
                                     # the one you had (saving both)
    render --pending                 # import everything queued for the open project
    render 01 all                    # all subscenes, then the full scene — the full
                                     # scene is STITCHED from the subscene clips (trim
                                     # one framework hold per seam + concat), NOT a
                                     # fresh manim pass, so it reuses them wholesale.
                                     # A bare `render 01` is still a full manim render.
    render 01b-f                     # subscenes b through f (ranges are DASH-delimited)
    render 01b-                      # subscene b through the end
    render 01-f                      # the beginning through subscene f
    render 06za                      # a multi-char subscene label (a..z, then za..zz, ...)
    render 01g --recompute           # ignore the snapshot cache AND re-render even
                                     # an unchanged subscene (see below)
    (any subscene whose code, imports, assets/ files and sound effects are unchanged
     since its last render at this quality is SKIPPED — "unchanged — skipped" — and
     with --stills is re-staged/imported only if edit_clips/ or the pool lacks it)
    render 01g --frames "1.0,2.0,-0.3"   # render then extract those frames
    render 01g --frames 5            # 5 evenly-spaced frames
    render 01g --frames "1.0,-0.3" --extract  # extract from the EXISTING mp4
                                              # (no re-render); then Read the PNGs
    render 01 sub --padded           # render each subscene + a first/last-frame-
                                     # padded copy (10s/side) under padded_videos/
    render 01g --padded 3            # render, then pad with 3s each side
    render 01g --padded --extract    # pad the EXISTING mp4 (no re-render)
    render 93a                       # a @still subscene: renders a STILL PNG (manim -s)
                                     # into media/images/<scene>/<res>/, NOT a video
    render 93 all                    # a @still-only scene: one PNG per subscene, no
                                     # combined full-scene render
    render 99a                       # scene 99 = thumbnails (@thumbnail extends @still):
                                     # a 4K PNG (-s -qk) into media/images/<scene>/2160p/
    render 99a --fast                # same, but a quick low-res PNG (→ …/480p/)
    render 99 all                    # every thumbnail — but ONLY the ones whose inputs
                                     # changed re-render (unchanged ones are skipped)
    render 07a --thumb               # force a 4K still PNG for ANY scene (99 is automatic)

Still images (@still / @thumbnail / --thumb) are independent, so a still-only scene's
`… all` renders one PNG per subscene with no combined render. For the 99 slot,
`render 99 all` also skips any thumbnail whose code (or a shared helper/asset it uses)
is unchanged since its PNG — keyed the same way the snapshot cache keys subscenes, with
a quality tag; `--recompute` forces a rebuild. Each PNG lands in a per-RESOLUTION
subfolder (`media/images/<scene>/2160p|480p/…`) so a low-res --fast test can't be
mistaken for the full-res asset, and a slot keeps a single image per quality (a renamed
subscene's old PNG is swept). A plain @still renders at -qh; 99/--thumb default to 4K.
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
import signal
import subprocess
import sys

from bpkfigures import resolve
from bpkfigures import davinci


def _run_manim(cmd, env, tail=None):
    """Run manim, FORWARDING SIGTERM/SIGINT to it. Without this, killing `render` (e.g. to
    free the per-scene lock, as the refuse message invites) kills only this wrapper and
    ORPHANS the manim child, which keeps rendering headless. With it, `kill <render-pid>`
    stops the child too. Use a plain `kill` (SIGTERM) — `kill -9` bypasses this handler."""
    kw = dict(env=env)
    if tail is not None:
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    proc = subprocess.Popen(cmd, **kw)

    def _forward(_signum, _frame):
        try:
            proc.terminate()
        except Exception:
            pass
        raise SystemExit(130)

    prev = [(s, signal.signal(s, _forward)) for s in (signal.SIGTERM, signal.SIGINT)]
    try:
        if tail is not None:
            out, _ = proc.communicate()
            for ln in (out or "").splitlines()[-tail:]:
                print(ln, file=sys.stderr)
        else:
            proc.wait()
    finally:
        for s, old in prev:
            signal.signal(s, old)
    return proc.returncode


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
def _probe(mp4, streams, entries):
    out = subprocess.run([_ffprobe(), "-v", "error", *streams,
                          "-show_entries", entries, "-of", "csv=p=0", mp4],
                         capture_output=True, text=True)
    return out.stdout.strip()


def _probe_fields(mp4, streams, entries):
    """`{key: value}` for one probe. Keyed, NOT positional: ffprobe emits the fields
    in ITS order, not the order they were asked for (`nb_frames,r_frame_rate` comes
    back rate-first), so indexing a csv row reads the wrong field."""
    out = subprocess.run([_ffprobe(), "-v", "error", *streams,
                          "-show_entries", entries,
                          "-of", "default=noprint_wrappers=1", mp4],
                         capture_output=True, text=True)
    fields = {}
    for line in out.stdout.splitlines():
        key, _, val = line.partition("=")
        if key and key not in fields:          # first stream wins
            fields[key] = val.strip()
    return fields


def _duration(mp4):
    """Seconds of VIDEO in `mp4` — deliberately not the container duration.

    Every caller measures the PICTURE: _stitch_full trims a hold off each clip,
    _parse_frames spreads sample times, _extract_one_frame seeks from the end. A
    clip carrying audio can have a container longer than its video (manim's mux
    passes `shortest`, which is an ffmpeg CLI flag and NOT an mp4 muxer option, so
    it is ignored), and reading `format=duration` would then quietly stretch all
    of that. Prefer the frame count over the frame rate — exact, and immune to the
    same skew — then the video stream's own duration, then the container.
    """
    f = _probe_fields(mp4, ["-select_streams", "v:0"], "stream=nb_frames,r_frame_rate")
    try:
        frames = int(f.get("nb_frames", ""))
        num, _, den = f.get("r_frame_rate", "").partition("/")
        rate = float(num) / float(den or 1)
        if frames > 0 and rate > 0:
            return frames / rate
    except (ValueError, ZeroDivisionError):
        pass
    for streams, entries in ((["-select_streams", "v:0"], "stream=duration"),
                             ([], "format=duration")):
        try:
            return float(_probe(mp4, streams, entries))
        except ValueError:
            continue
    return None


def _has_audio(mp4):
    """True if `mp4` carries an audio stream at all (empty probe output = silent)."""
    return bool(_probe(mp4, ["-select_streams", "a"], "stream=codec_type"))


def _previewable_audio(mp4):
    """Re-encode an mp4's audio to MP3 in place. No-op on a clip with no audio.

    WHY, and it is not cosmetic: VSCode's video preview is a Chromium webview whose
    Electron build ships NO AAC DECODER, so an ordinary H.264+AAC render shows
    picture and plays SILENCE there — which makes iterating on sound impossible,
    since clicking the file in the explorer is how these get watched. MEASURED
    2026-09-18 by A/B: the identical clip with MP3 audio plays, with AAC does not.
    Nothing else about the file was wrong — faststart, stream dispositions, start
    times and codec profile were all checked and normal.

    MP3-in-mp4 costs nothing that matters: DaVinci reads it, the video stream is
    STREAM-COPIED so the picture is untouched, and these mp4s are intermediates for
    the edit, never deliverables (the deliverable is a .mov out of Resolve). An
    audio-only re-encode of a short clip is a fraction of a second.

    A SILENT CLIP IS LEFT ALONE ENTIRELY — not remuxed, not rewritten — so a video
    that uses no sound effects keeps producing byte-identical output.
    """
    if not mp4 or not os.path.exists(mp4) or not _has_audio(mp4):
        return
    if _probe(mp4, ["-select_streams", "a:0"], "stream=codec_name") == "mp3":
        return                                   # already previewable
    tmp = mp4 + ".mp3audio.mp4"
    r = subprocess.run([_ffmpeg(), "-y", "-v", "error", "-i", mp4,
                        "-c:v", "copy", "-c:a", "libmp3lame", "-b:a", "192k", tmp],
                       capture_output=True)
    if r.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        print(f"[render] could not convert audio to MP3 for preview "
              f"({r.stderr.decode(errors='replace')[-200:]}) — the clip keeps its "
              f"AAC track and will be silent in VSCode", file=sys.stderr)
        return
    os.replace(tmp, mp4)


def _drop_audio_intermediates(mp4):
    """Delete manim's leftover audio files beside a rendered clip.

    `combine_to_movie` exports the scene's audio to `<clip>.wav`, converts that to
    `<clip>.aac` (or `.ogg` for webm), muxes the result into the mp4 — and then
    leaves them all on disk. They are dead once the mux is done: the mp4 carries the
    audio, and these are bit-for-bit recoverable from it anyway.

    It matters because `media/videos/<scene>/<res>/` is the folder you click through
    to WATCH renders, and a stray file per sounded clip doubles what is in it — the
    wavs here were 254 KB each, bigger than several of the mp4s they belonged to.

    Deliberately narrow: only extensions manim itself writes, only a stem that
    exactly matches this clip's, only in the clip's own directory. It never removes
    an unrelated file that happens to sit nearby.
    """
    if not mp4 or not os.path.exists(mp4):
        return
    stem = os.path.splitext(mp4)[0]
    for ext in (".wav", ".aac", ".ogg"):
        leftover = stem + ext
        if os.path.exists(leftover):
            try:
                os.remove(leftover)
            except OSError:
                pass                     # cosmetic cleanup; never fail a render for it


def _play(path):
    """Open `path` in the system video player — `--play`.

    Detached, like the finished chime: the point is to WATCH the clip, not to hold
    the terminal until the window closes. Says whether the file carries audio,
    because "I heard nothing" has two very different causes — a silent render and a
    muted player — and the probe distinguishes them before you go looking.
    """
    if not path or not os.path.exists(path):
        print(f"[render] --play: nothing to open", file=sys.stderr)
        return
    sound = "with audio" if _has_audio(path) else "SILENT (no audio stream)"
    print(f"[render] playing {os.path.basename(path)} — {sound}", file=sys.stderr)
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([opener, path], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as e:
        print(f"[render] --play failed ({e}); the file is at {path}", file=sys.stderr)


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
    `videos/` (same substructure). ffmpeg's tpad clones the end frames. Returns the
    output path (or None on failure). Re-encodes (tpad can't stream-copy) at
    near-lossless crf 18.

    The copy is SILENT (`-an`) even when the source carries sound effects: tpad pads
    the VIDEO only, so ffmpeg's default stream selection would carry the audio across
    unshifted and leave it `seconds` out of sync with the picture. This is a legacy
    editing aid superseded by `--stills` (which byte-copies and keeps its audio), so
    dropping the track beats shipping a desynced one."""
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
    r = subprocess.run([_ffmpeg(), "-y", "-i", mp4, "-vf", vf, "-an",
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out],
                       capture_output=True)
    if r.returncode != 0:
        print(f"[render] ffmpeg pad failed for {mp4}:\n"
              f"{r.stderr.decode(errors='replace')[-600:]}", file=sys.stderr)
        return None
    return out


def _repo_root():
    """Walk up from cwd (run from animations/scenes/) to the git repo root, which
    holds edit_clips/ at the top. Falls back to cwd if no .git is found."""
    d = os.path.abspath(os.getcwd())
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(os.getcwd())


def _tree_name():
    """The name of the animations TREE this render runs in: the folder above the
    `scenes/` dir (render runs from scenes/). `animations` for a video's main tree;
    anything else (e.g. `bonus`) is a separate tree with its own staging dir and bin."""
    return os.path.basename(os.path.abspath(os.path.join(os.getcwd(), "..")))


def _edit_dir():
    """The --stills staging dir for this tree: `<repo>/edit_clips/` for the main
    `animations/` tree (unchanged), `<repo>/edit_clips_<tree>/` for any other, so a
    bonus 01a can never overwrite, clean, or swap the main video's 01a."""
    tree = _tree_name()
    name = "edit_clips" if tree == "animations" else f"edit_clips_{tree}"
    return os.path.join(_repo_root(), name)


def _bin_name(scene_module):
    """DaVinci Media Pool bin: per scene for the main tree (unchanged), one bin named
    after the tree (`Bonus`) for any other."""
    tree = _tree_name()
    return scene_module if tree == "animations" else tree.capitalize()


def _project_name():
    """The DaVinci project this tree's clips belong in. An explicit name in
    `<tree>/davinci_project` wins; otherwise it is derived the way new-video names
    the project — the repo name in PascalCase (`wheel-of-fortune` -> `WheelOfFortune`)
    — plus ` Bonus` (the tree name) for any tree other than `animations/`. ingest()
    refuses to import into any other open project."""
    override = os.path.join(os.getcwd(), "..", "davinci_project")
    if os.path.isfile(override):
        with open(override, encoding="utf-8") as f:
            name = f.read().strip()
        if name:
            return name
    repo = os.path.basename(_repo_root())
    name = "".join(w[:1].upper() + w[1:] for w in repo.split("-"))
    tree = _tree_name()
    return name if tree == "animations" else f"{name} {tree.capitalize()}"


def _stage_image(letter, output, png, scene_module):
    """--stills for a @still subscene: copy its PNG into the staging dir as
    `NN<letter>_<method>.png` and ingest it into DaVinci, imported if new and
    refreshed in place (timeline instances included) if already there. A whole-scene
    target is skipped, as for video clips."""
    if not letter:
        print(f"[stills] skipping {output}: whole-scene files are not staged, "
              f"only subscenes")
        return
    edit_dir = _edit_dir()
    os.makedirs(edit_dir, exist_ok=True)
    name = f"{output}.png"
    shutil.copy2(png, os.path.join(edit_dir, name))
    _ingest_staged(edit_dir, [name], scene_module)


# --switch: when the clip's project is not the open one, open it, import, and
# reopen the original (davinci.in_project) instead of queueing. Set by main().
_SWITCH = False


def _print_flushed(edit_dir, results):
    for name, status in results:
        print(f"[stills] pending {os.path.basename(edit_dir)}/{name}: {status}")


def _ingest_staged(edit_dir, names, scene_module, then=None, refresh=True):
    """THE one route from a staging dir into DaVinci, for clips and stills alike.
    Imports `names` into this tree's project. With that project open: first imports
    anything QUEUED for it earlier, then `names`. With another project open: queues
    them (davinci.ingest does) — or, under --switch, opens the right project, does the
    work there, and reopens the original. `then()` runs inside the right project
    (the orphan report), and only when it is open."""
    project, bin_name = _project_name(), _bin_name(scene_module)

    def work():
        _print_flushed(edit_dir, davinci.flush_pending(edit_dir))
        for name in names:
            status = davinci.ingest(edit_dir, name, bin_name=bin_name, project=project,
                                    refresh=refresh)
            print(f"[stills] {os.path.basename(edit_dir)}/{name}: {status}")
        if then:
            then()

    open_name = davinci.open_project_name()
    if _SWITCH and open_name is not None and open_name != project:
        with davinci.in_project(project) as ok:
            if ok:
                work()
                return
    work()


def _flush_all_pending():
    """`render --pending`: import everything queued in ANY of this repo's staging
    dirs (edit_clips/, edit_clips_bonus/, ...) that belongs in the open project, and
    list what is still waiting for another project. Returns an exit code."""
    root = _repo_root()
    dirs = sorted(d for d in glob.glob(os.path.join(root, "edit_clips*"))
                  if os.path.isdir(d))
    open_name = davinci.open_project_name()
    print(f"[pending] open project: {open_name!r}")
    waiting = 0
    for d in dirs:
        _print_flushed(d, davinci.flush_pending(d))
        for name, entry in sorted(davinci.pending(d).items()):
            waiting += 1
            print(f"[pending] still waiting for {entry.get('project')!r}: "
                  f"{os.path.basename(d)}/{name}")
    if not waiting:
        print("[pending] nothing waiting")
    return 0


def _extract_one_frame(mp4, t, out):
    """Write ONE frame (t<0 = seconds-from-end, like ffmpeg -sseof) to `out`.
    Returns True on success. Used for the held first/last frames (the stills)."""
    seek = ["-sseof", str(t)] if t < 0 else ["-ss", str(t)]
    r = subprocess.run([_ffmpeg(), "-y", *seek, "-i", mp4, "-frames:v", "1", out],
                       capture_output=True)
    return r.returncode == 0


# The --stills naming scheme. Each subscene stages its OWN LEADING still (its first
# frame, i.e. the hold before it) named `<output>_still.png`, which sorts just BEFORE
# `<output>.mp4` in DaVinci (it orders `_` ahead of `.`); the scene's LAST subscene
# also stages the scene's closing hold under the NEXT letter, `<NN><next>_scene_end_
# still.png`, so it sorts after everything. Until 2026-10-06 each subscene staged a
# TRAILING still under the same `_still.png` name plus one `NN_lead_still.png` per
# scene, which DaVinci sorted before its clip. STILLS_SCHEME is stamped into the
# staging dir so a dir staged under the old scheme is never mistaken for current.
STILLS_SCHEME = "2"
END_STILL = "scene_end"


def _still_files(prefix, letter, output):
    """[(file name, seconds into the clip)] of the stills this subscene stages; a
    negative time counts from the end. THE one statement of the naming scheme."""
    out = [(f"{output}_still.png", 0.05)]
    letters = resolve.subscene_letters(prefix)
    if letters and letter == letters[-1]:
        nxt = resolve.index_to_label(len(letters))
        out.append((f"{prefix}{nxt}_{END_STILL}_still.png", -0.1))
    return out


def _scheme_path(edit_dir):
    return os.path.join(edit_dir, ".stills_scheme.json")


def _scheme_staged(edit_dir):
    """The subscene outputs staged under the CURRENT scheme. Per subscene, not per
    dir: a dir-wide flag would be set by the first subscene re-staged and then wave
    every later unchanged subscene through with its old-scheme stills."""
    try:
        with open(_scheme_path(edit_dir), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return set()
    return set(data.get("staged", [])) if data.get("scheme") == STILLS_SCHEME else set()


def _mark_staged(edit_dir, output):
    staged = _scheme_staged(edit_dir) | {output}
    tmp = _scheme_path(edit_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"scheme": STILLS_SCHEME, "staged": sorted(staged)}, f, indent=1)
    os.replace(tmp, _scheme_path(edit_dir))


def _stills(prefix, letter, output, mp4, scene_module):
    """--stills: stage this subscene into `<repo>/edit_clips/` for DaVinci — a plain
    byte-copy of the mp4 (no re-encode) plus the stills `_still_files` names: this
    subscene's LEADING still, and for the scene's last subscene the closing still
    under the next letter. Filenames sort into timeline order: `NNa_<m>_still.png`,
    `NNa_<m>.mp4`, `NNb_<m>_still.png`, `NNb_<m>.mp4`, …, `NN<next>_scene_end_still.png`.
    Then, if Resolve is open, INGEST each file into the Media Pool (a per-scene bin
    named `scene_module`): new files are imported, already-imported ones are refreshed
    in place (which also updates any timeline instances). Matched by letter-agnostic
    identity, so re-lettering is handled. Prints each staged file + its pool status.

    A between-subscene still is the FIRST frame of the following subscene, which is
    the same image as the previous subscene's last frame (each subscene starts from
    the previous one's end state) — but it comes from the FOLLOWING clip's render.

    A WHOLE-SCENE target (no letter) is never staged: the edit is built from the
    subscene clips and their stills, so `render NN all --stills [--extract]` sends
    exactly those and skips the full-scene mp4 (the user's call, 2026-10-04)."""
    if not letter:
        print(f"[stills] skipping {output}: whole-scene files are not staged, "
              f"only subscenes")
        return
    edit_dir = _edit_dir()
    os.makedirs(edit_dir, exist_ok=True)
    old_lead = os.path.join(edit_dir, f"{prefix}_lead_still.png")   # pre-2026-10-06
    if letter == "a" and os.path.exists(old_lead):
        os.remove(old_lead)
        print(f"[stills] removed {os.path.basename(edit_dir)}/{prefix}_lead_still.png "
              f"(old naming scheme; subscene a's own still replaces it)")
    staged = []
    for name, t in _still_files(prefix, letter, output):
        if _extract_one_frame(mp4, t, os.path.join(edit_dir, name)):
            staged.append(name)
    anim = f"{output}.mp4"                       # NN<letter>_<method>.mp4 — stable import name
    shutil.copy2(mp4, os.path.join(edit_dir, anim))
    staged.insert(1 if staged else 0, anim)      # still, clip, [end still]
    _mark_staged(edit_dir, output)
    # report placed clips whose subscene was merged/removed — can't auto-delete an edit.
    # Best-effort: never let the (advisory) orphan report break the staging/swap above.
    def report_orphans():
        try:
            orphans = davinci.orphan_clips(prefix, resolve.subscene_methods(prefix),
                                           scope=os.path.basename(edit_dir),
                                           project=_project_name())
        except Exception:
            orphans = []
        for p in orphans:
            print(f"[stills] ORPHAN on timeline: {os.path.basename(p)} — its subscene "
                  f"no longer exists; delete this clip in DaVinci")

    _ingest_staged(edit_dir, staged, scene_module, then=report_orphans)


def _output_mp4(output):
    """Find the rendered mp4 for `output` under media/videos/**/."""
    hits = glob.glob(os.path.join("media", "videos", "**", f"{output}.mp4"),
                     recursive=True)
    # newest wins if multiple qualities
    return max(hits, key=os.path.getmtime) if hits else None


def _stitch_full(prefix, full_output):
    """Build the full-scene mp4 for `prefix` by CONCATENATING the per-subscene clips
    just rendered in `all` mode — no separate full manim pass.

    Each subscene clip is HOLD·body·HOLD (a leading + trailing framework hold, see
    bpkfigures.scene.SUBSCENE_HOLD), while the full scene is HOLD·a·HOLD·b·…·N·HOLD —
    a SINGLE shared hold between adjacent subscenes. So every interior seam would
    otherwise carry two holds; we trim ONE (the trailing hold) off every clip except
    the last, then concat. That reproduces the full-scene pacing EXACTLY while reusing
    the subscene renders wholesale.

    Why not just let a fresh full pass reuse manim's partial-movie cache? A subscene
    render rebuilds its incoming state from a PICKLED snapshot, which serializes to a
    different cache hash than the fresh state a full pass builds — so the full pass
    cache-misses on every carried-state animation and re-renders it. Stitching sidesteps
    that: both the clips and the full scene come from the same (snapshot-based) basis.

    Returns the stitched mp4 path, or None if a clip / its duration is missing (the
    caller then falls back to a normal full manim render). Re-encodes once (crf 18,
    near-lossless) so the tail-trim is frame-exact. Audio rides along only when some
    clip actually has a track — see the branch below."""
    from bpkfigures.scene import SUBSCENE_HOLD    # single source of truth for the hold
    letters = resolve.subscene_letters(prefix)
    if not letters:
        return None
    clips = []
    for L in letters:
        _p, _c, out, _l = resolve.resolve(prefix + L)
        mp4 = _output_mp4(out)
        if not mp4:
            print(f"[render] stitch: missing subscene clip {out}.mp4 — falling back "
                  f"to a full render", file=sys.stderr)
            return None
        clips.append(mp4)

    # Carry audio only if some clip HAS any. A scene whose subscenes are all silent
    # must stitch exactly as it always did — giving it a silent audio track would be
    # a regression for every video that uses no sound effects.
    with_audio = any(_has_audio(m) for m in clips)
    AFMT = "aformat=sample_rates=48000:channel_layouts=mono"

    inputs, filt = [], []
    for i, mp4 in enumerate(clips):
        inputs += ["-i", mp4]
        dur = _duration(mp4)
        if dur is None and (i < len(clips) - 1 or with_audio):
            print(f"[render] stitch: can't read duration of {mp4} — falling back",
                  file=sys.stderr)
            return None
        if i < len(clips) - 1:                   # trim one trailing hold off all but last
            end = max(0.0, dur - SUBSCENE_HOLD)
            filt.append(f"[{i}:v]trim=0:{end:.6f},setpts=PTS-STARTPTS[v{i}]")
        else:                                    # last clip: keep its trailing hold
            end = dur
            filt.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        if with_audio:
            # concat with a=1 needs every segment at one rate and layout, and needs a
            # segment even for a silent clip — anullsrc is a filter SOURCE, so it slots
            # straight in rather than costing an extra -i whose index would collide
            # with the [{i}:v] numbering above.
            if _has_audio(mp4):
                filt.append(f"[{i}:a]atrim=0:{end:.6f},asetpts=PTS-STARTPTS,{AFMT}[a{i}]")
            else:
                filt.append(f"anullsrc=r=48000:cl=mono,atrim=0:{end:.6f},"
                            f"asetpts=N/SR/TB,{AFMT}[a{i}]")

    if with_audio:
        concat = "".join(f"[v{i}][a{i}]" for i in range(len(clips)))
        concat += f"concat=n={len(clips)}:v=1:a=1[out][aout]"
        # MP3, not AAC — see _previewable_audio: VSCode's preview cannot decode AAC,
        # and the stitched full scene is the clip most worth watching.
        maps = ["-map", "[out]", "-map", "[aout]",
                "-c:a", "libmp3lame", "-b:a", "192k"]
    else:
        concat = "".join(f"[v{i}]" for i in range(len(clips)))
        concat += f"concat=n={len(clips)}:v=1:a=0[out]"
        maps = ["-map", "[out]"]
    dest = os.path.join(os.path.dirname(clips[0]), f"{full_output}.mp4")

    cmd = [_ffmpeg(), "-y", *inputs, "-filter_complex", ";".join(filt) + ";" + concat,
           *maps, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dest]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"[render] stitch ffmpeg failed:\n"
              f"{r.stderr.decode(errors='replace')[-600:]}", file=sys.stderr)
        return None
    return dest


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
        S._files_hash(S._import_closure(scene_path, [bpk, project_root],
                                        [project_root, os.path.dirname(bpk)]) - tooling),
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
        with open(path, encoding="utf-8") as f:
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
        _cn, subs, _st = resolve._parse(path0)
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


# ── video change-detection (skip re-rendering unchanged subscenes) ─────────────
# A subscene's clip is a function of the code that builds its END STATE and its
# own animation — setup_scene plus subscenes a..itself, and whatever project code
# the scene imports — plus the non-code files it reads. So each rendered clip gets
# a key over exactly those, recorded in media/videos/<module>/.render_keys.json
# (gitignored, machine-local), and a later run whose key matches and whose mp4 is
# still the one recorded SKIPS the manim run. Until 2026-10-05 only thumbnails did
# this, so `render 01 ... 24 sub --stills` re-rendered the whole video every time.
#
# The code terms are the snapshot cache's own (bpkfigures.scene `_prefix_key`), so
# a skip is exactly as trustworthy as a snapshot hit, with the same blind spot: a
# CLASS attribute read via `self.X`. Non-code inputs are covered COARSELY — every
# non-.py file under this tree's assets/ (the render caches, images) and every sound
# effect file — so regenerating any cache re-renders every scene once, which errs
# the safe way. A scene that opens a file anywhere else is not tracked: use
# --recompute after changing one.
_VIDEO_KEYS = ".render_keys.json"


def _video_manifest_path(scene_path):
    return os.path.join("media", "videos", _thumb_scene_module_name(scene_path),
                        _VIDEO_KEYS)


def _content_hash(paths):
    h = hashlib.md5()
    for p in sorted(paths):
        try:
            with open(p, "rb") as f:
                h.update(p.encode())
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()


def _non_code_inputs_hash():
    """Content hash of every non-code file a scene can read at render time: this
    tree's assets/ (caches, images) and the sound-effect library."""
    paths = []
    assets = os.path.realpath(os.path.join(os.getcwd(), "..", "assets"))
    for dirpath, dirnames, filenames in os.walk(assets):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        paths += [os.path.join(dirpath, f) for f in filenames
                  if not f.endswith((".py", ".pyc"))]
    try:
        from bpkfigures.sfx import sfx_roots
        for root in sfx_roots():
            if os.path.isdir(root):
                paths += [os.path.join(root, f) for f in os.listdir(root)
                          if f.endswith(".wav")]
    except Exception:
        pass
    return _content_hash(paths)


def _video_key(cls, scene_path, names, idx, qtag, no_sfx, inputs_hash):
    """The change-key for video subscene `names[idx]`: the snapshot prefix-key's
    terms for 0..idx (version, the project code the scene imports minus every scene
    file and the CLI tooling, the scene digest of setup_scene + subscenes 0..idx),
    plus the quality, whether sound effects are baked in, and the non-code inputs."""
    from bpkfigures import scene as S
    bpk = S._BPK_DIR
    scene_path = os.path.realpath(scene_path)
    project_root = os.path.dirname(os.path.dirname(scene_path))
    scene_dir = os.path.dirname(scene_path)
    tooling = {os.path.realpath(os.path.join(bpk, f)) for f in ("render.py", "resolve.py")}
    siblings = {os.path.realpath(os.path.join(scene_dir, f))
                for f in os.listdir(scene_dir) if f.endswith(".py")}
    deps = S._import_closure(scene_path, [bpk, project_root],
                             [project_root, os.path.dirname(bpk)])
    srcs = [
        f"v{S.SNAPSHOT_VERSION}",
        f"q:{qtag}",
        f"sfx:{0 if no_sfx else 1}",
        S._files_hash(deps - siblings - tooling),
        S._scene_source_digest(cls, ["setup_scene"] + list(names[: idx + 1])),
        inputs_hash,
    ]
    return hashlib.md5("".join(srcs).encode()).hexdigest()


def _video_change_plan(targets, qtag, no_sfx):
    """For the video SUBSCENE targets (not thumbnails, not @still images, not whole
    scenes), decide which are up to date. Returns (skip:{target: mp4},
    record:{target: (manifest_path, manifest_key, key)}). Per scene, any failure
    renders that scene in full and says why; it never blocks a render."""
    skip, record = {}, {}
    by_prefix = {}
    for t in targets:
        if len(t) > 2 and not _is_thumb_prefix(t[:2]):
            by_prefix.setdefault(t[:2], []).append(t)
    if not by_prefix:
        return skip, record
    inputs_hash = _non_code_inputs_hash()
    for prefix, tt in by_prefix.items():
        try:
            path, classname, _o, _l = resolve.resolve(tt[0])
            cls = _load_scene_class(path, classname)
            _cn, subs, _st = resolve._parse(path)
            manifest_path = _video_manifest_path(path)
            manifest = _load_manifest(manifest_path)
            for t in tt:
                if resolve.is_still(t):
                    continue
                _p, _c, output, letter = resolve.resolve(t)
                idx = resolve.label_to_index(letter)
                key = _video_key(cls, path, subs, idx, qtag, no_sfx, inputs_hash)
                mkey = f"{qtag}/{output}"
                record[t] = (manifest_path, mkey, key)
                entry = manifest.get(mkey)
                if isinstance(entry, dict) and entry.get("key") == key:
                    mp4 = entry.get("mp4")
                    if mp4 and os.path.exists(mp4) and \
                            os.path.getmtime(mp4) == entry.get("mtime"):
                        skip[t] = mp4
        except Exception as e:
            print(f"[render] change-check skipped for scene {prefix} — rendering it "
                  f"all ({type(e).__name__}: {e})", file=sys.stderr)
    return skip, record


def _record_video_key(record_entry, output):
    """After a successful render, note the clip's key, path and mtime."""
    manifest_path, mkey, key = record_entry
    mp4 = _output_mp4(output)
    if not mp4:
        return
    manifest = _load_manifest(manifest_path)
    manifest[mkey] = {"key": key, "mp4": mp4, "mtime": os.path.getmtime(mp4)}
    _save_manifest(manifest_path, manifest)


def _staged_current(prefix, letter, output, mp4):
    """True if edit_clips/ already holds THIS mp4 (copy2 keeps size and mtime) and
    its stills, so a skipped subscene need not be re-staged."""
    edit_dir = _edit_dir()
    staged = os.path.join(edit_dir, f"{output}.mp4")
    try:
        same = (os.path.getsize(staged) == os.path.getsize(mp4) and
                os.path.getmtime(staged) == os.path.getmtime(mp4))
    except OSError:
        return False
    needed = [n for n, _t in _still_files(prefix, letter, output)]
    return (same and output in _scheme_staged(edit_dir) and
            all(os.path.exists(os.path.join(edit_dir, n)) for n in needed))


def _skipped_outputs(target, mp4, frames_spec, padded, stills):
    """A skipped subscene still honours --frames / --padded / --stills, from the
    existing mp4. --stills re-stages only if edit_clips/ is stale, and otherwise
    just makes sure each file is IN the DaVinci pool (imported if missing, never
    refreshed — the bytes did not change)."""
    path, _c, output, letter = resolve.resolve(target)
    if frames_spec is not None:
        for p in _extract_frames(mp4, _parse_frames(frames_spec, _duration(mp4))):
            print(p)
    if padded is not None:
        p = _pad_video(mp4, padded)
        if p:
            print(p)
    if stills:
        module = os.path.splitext(os.path.basename(path))[0]
        if _staged_current(target[:2], letter, output, mp4):
            names = [f"{output}.mp4"] + [n for n, _t in
                                         _still_files(target[:2], letter, output)]
            _ingest_staged(_edit_dir(), names, module, refresh=False)
        else:
            _stills(target[:2], letter, output, mp4, module)


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
    """Turn `rest` into (targets, passthrough, stitch_fulls). Handles the `all`/`sub`
    keywords (all subscenes, plus the full scene for `all`) and the range forms above.

    `stitch_fulls` is the set of full-scene targets (bare `NN`) that were appended by
    `all` mode. Those are built by CONCATENATING the just-rendered subscene clips
    rather than a separate full manim pass (see `_stitch_full`), so the full scene
    reuses 100% of the subscene renders instead of re-rendering the ones a fresh pass
    can't cache-reuse. A bare `NN` typed on its own is NOT in this set — it stays a
    normal full render (its subscenes may be absent/stale).

    Thumbnails (scene `99`) have no whole-scene image, so a bare `99` expands to
    each thumbnail and `all` does NOT append the full-scene target (that produced a
    meaningless combined `99_thumbnails.png`)."""
    mode = "all" if "all" in rest else ("sub" if "sub" in rest else None)
    toks = [a for a in rest if a not in ("all", "sub")]
    digit_toks = [a for a in toks if len(a) >= 2 and a[:2].isdigit()]
    passthrough = [a for a in toks if a not in digit_toks]

    targets, stitch_fulls = [], set()
    for tok in digit_toks:
        prefix, spec = tok[:2], tok[2:]
        # A still-IMAGE scene (every subscene @still, incl. 99 thumbnails) is a set of
        # independent images — there is no meaningful combined full-scene render.
        still_scene = resolve.is_still(prefix)
        if mode and spec == "":
            letters = resolve.subscene_letters(prefix)
            targets += [prefix + L for L in letters]
            if mode == "all" and not still_scene:
                targets.append(prefix)                   # full scene last
                stitch_fulls.add(prefix)                 # …built by stitching the clips
        elif spec == "" and still_scene:                 # bare `NN`: each still image
            targets += [prefix + L for L in resolve.subscene_letters(prefix)]
        elif "-" in spec:                                # dash-delimited range
            targets += _expand_one(prefix, spec, resolve.subscene_letters(prefix))
        else:
            targets.append(tok)                          # NN (full) or NN<label> — as-is
    return targets, passthrough, stitch_fulls


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
            with open(p, encoding="utf-8") as f:
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
    # --no-sound: suppress the 'render finished' chime. The chime signals the USER's own
    # renders, so the agent always passes --no-sound (see bpkfigures/CLAUDE.md).
    global _PLAY_DING
    _PLAY_DING = "--no-sound" not in argv
    # --no-sfx: render WITHOUT the scene's sound effects. Distinct from --no-sound,
    # which is about the chime on THIS machine and never touches the media; this one
    # changes what lands in the mp4. It rides to the scene process as an env var, the
    # way SUBSCENE and RECOMPUTE do, so no manim argument is involved.
    no_sfx = "--no-sfx" in argv
    # --play: open the finished video when the run ends, so a clip with sound can
    # actually be HEARD. Without it, watching a render means digging out
    # media/videos/<scene>/<res>/<name>.mp4 by hand every time — which is most of
    # the friction in iterating on sound.
    play = "--play" in argv
    frames_spec = None
    padded = None                # --padded [N]: also write a first/last-frame-padded copy
    stills = "--stills" in argv  # --stills: stage anim+stills into edit_clips/ + swap-if-live
    # --switch: a staged clip whose project is not the open one gets imported by
    # opening that project and reopening yours afterwards, instead of being queued.
    global _SWITCH
    _SWITCH = "--switch" in argv
    # --pending: import everything queued for the open project, from every staging
    # dir in this repo, and list what still waits for another one. No targets.
    if "--pending" in argv:
        return _flush_all_pending()
    tail = None                  # --tail N: capture manim output, emit only its last N lines
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--recompute", "--hq", "--state", "--fast", "--very-fast", "-ql",
                 "--quiet", "--check", "--extract", "--thumb", "--thumbnail", "--no-sound",
                 "--no-sfx", "--play", "--stills", "--switch"):
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
        targets, passthrough, stitch_fulls = _expand_targets(rest)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2
    if not targets:
        print("usage: render NN[label] [NN[label] ...] [NN all|sub] [NNa-c|NNb-|NN-f] "
              "[--recompute] [--fast] [--quiet] [--tail N] [--frames T|N] [--padded [N]] "
              "[--stills [--switch]] [--pending] [--thumb] [--state] [--check] [--play] [--no-sound] "
              "[--no-sfx]")
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
    # ...and the same for ordinary video subscenes (see _video_change_plan).
    # --recompute still RECORDS the keys of what it renders (so the next run skips it);
    # it just never skips.
    vskip, vrecord = (({}, {}) if (state or extract or check)
                      else _video_change_plan(targets, qtag, no_sfx))
    if recompute:
        vskip = {}
    rendered_prefixes = set()     # scenes with a subscene actually re-rendered this run

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
            if target in vskip:
                print(f"[render] {target} unchanged — skipped "
                      f"(use --recompute to force)", file=sys.stderr)
                _skipped_outputs(target, vskip[target], frames_spec, padded, stills)
                continue
            if target in stitch_fulls and not state and not extract \
                    and target[:2] not in rendered_prefixes and _stitch_current(target):
                print(f"[render] {target} unchanged — skipped (no subscene "
                      f"re-rendered)", file=sys.stderr)
                continue
            # `all` mode's full scene: STITCH the just-rendered subscene clips instead
            # of a fresh full pass (reuses them wholesale; see _stitch_full). Only in a
            # real render — --state/--extract fall through to _render_one below. A None
            # rc means stitching wasn't possible (a clip missing) → fall back to a
            # normal full render below.
            if target in stitch_fulls and not state and not extract:
                rc = _stitch_one(target, frames_spec, padded)
                if rc is not None:
                    worst_rc = worst_rc or rc
                    if rc == 0:
                        print(f"Finished rendering {target}", file=sys.stderr)
                    continue
            rc = _render_one(target, passthrough, recompute, fast, state,
                             frames_spec, quiet=quiet, tail=tail_n,
                             extract=extract, very_fast=very_fast, padded=padded,
                             thumb=thumb, stills=stills, no_sfx=no_sfx)
            worst_rc = worst_rc or rc
            if not state and not extract and rc == 0:
                print(f"Finished rendering {target}", file=sys.stderr)
                rendered_prefixes.add(target[:2])
                if target in vrecord:                        # record the clip's key
                    _record_video_key(vrecord[target], resolve.resolve(target)[2])
                if target in thumb_keys and manifest_path:   # record the new key
                    manifest[thumb_mkey[target]] = thumb_keys[target]
                    _save_manifest(manifest_path, manifest)
        if play and not state and not check:
            # The LAST target, which is the one you meant: `NN all` appends the
            # combined scene last, so this opens the whole thing rather than nine
            # windows, and a single `NNc --play` opens that clip.
            _p, _c, out, _l = resolve.resolve(targets[-1])
            _play(_output_mp4(out))
        return worst_rc
    finally:
        _release_locks(locks)


def _stitch_current(target):
    """True if the stitched full-scene mp4 exists and is newer than every one of its
    subscene clips — nothing to re-stitch."""
    try:
        full = _output_mp4(resolve.resolve(target)[2])
        if not full:
            return False
        clips = [_output_mp4(resolve.resolve(target + L)[2])
                 for L in resolve.subscene_letters(target[:2])]
        return all(clips) and all(os.path.getmtime(full) >= os.path.getmtime(c)
                                  for c in clips)
    except Exception:
        return False


def _stitch_one(target, frames_spec, padded):
    """`all`-mode full scene: assemble it by stitching the just-rendered subscene
    clips (see `_stitch_full`), then honor --frames/--padded on the result.

    Returns an rc (0 = ok), or None if stitching isn't possible (a subscene clip is
    missing) so the caller falls back to a fresh full manim render."""
    try:
        _path, classname, full_output, _l = resolve.resolve(target)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return None
    prefix = target[:2]
    # drop a stale full-scene mp4 from a renamed class (mirrors _render_one). The slot
    # glob is `NN_*` (letter=""), which never matches a subscene clip (`NN<letter>_*`).
    for f in resolve.clean_stale(classname, prefix, "", full_output):
        print(f"[render] removed stale {f}", file=sys.stderr)
    for f in resolve.clean_orphans(prefix):
        print(f"[render] removed orphan {f}", file=sys.stderr)
    dest = _stitch_full(prefix, full_output)
    if dest is None:
        return None
    print(dest)
    if frames_spec is not None:
        for p in _extract_frames(dest, _parse_frames(frames_spec, _duration(dest))):
            print(p)
    if padded is not None:
        p = _pad_video(dest, padded)
        if p:
            print(p)
    return 0


def _render_one(target, passthrough, recompute, fast, state, frames_spec,
                quiet=False, tail=None, extract=False, very_fast=False, padded=None,
                thumb=False, stills=False, no_sfx=False):
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

    # A @still subscene (incl. its @thumbnail specialization) renders as a STILL IMAGE
    # (a PNG via manim -s), not a video — that's what a "series of images" scene is.
    # Scene `99` (thumbnails) and --thumb additionally want a 4K upload-grade still; a
    # plain @still renders at the normal quality (-qh, or -ql with --fast).
    force_4k = thumb or target[:2] == "99"
    image = force_4k or resolve.is_still(target)

    if state:
        return _print_state(path, classname, letter)

    if extract:
        # post-process the ALREADY-rendered mp4 (extract frames / pad / stage stills), no manim
        if frames_spec is None and padded is None and not stills:
            print("--extract needs --frames, --padded, or --stills", file=sys.stderr)
            return 2
        if image:
            # a @still: re-stage the ALREADY-rendered PNG (no re-render). Prefer the
            # full-quality one; a --fast PNG is used only if nothing better exists.
            if not stills:
                print("--extract on a @still only supports --stills", file=sys.stderr)
                return 2
            hits = glob.glob(os.path.join("media", "images", "**", f"{output}.png"),
                             recursive=True)
            hits.sort(key=lambda h: (_QTAG_DIR["hq"] not in h, -os.path.getmtime(h)))
            if not hits:
                print(f"[render] no existing PNG for {output} — render it first",
                      file=sys.stderr)
                return 1
            _stage_image(letter, output, hits[0],
                         os.path.splitext(os.path.basename(path))[0])
            return 0
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
        if stills:
            _stills(target[:2], letter, output, mp4,
                    os.path.splitext(os.path.basename(path))[0])
        return 0

    # clean stale outputs for this slot (also the flat edit_clips/ dir when --stills)
    _edit = _edit_dir() if stills else None
    for f in resolve.clean_stale(classname, target[:2], letter, output, edit_dir=_edit):
        print(f"[render] removed stale {f}", file=sys.stderr)
    # ...and sweep whole slots past the current last subscene (removed subscenes)
    for f in resolve.clean_orphans(target[:2], edit_dir=_edit):
        print(f"[render] removed orphan {f}", file=sys.stderr)

    # build the env (explicit -> no leak from a prior interrupted run)
    env = dict(os.environ)
    env.pop("SUBSCENE", None)
    env.pop("RECOMPUTE", None)
    env.pop("BPK_NO_SFX", None)
    if letter:
        env["SUBSCENE"] = letter
    if recompute:
        env["RECOMPUTE"] = "1"
    if no_sfx:
        env["BPK_NO_SFX"] = "1"

    manim = _find_venv_manim()
    # A 4K still (-qk) is the upload-grade thumbnail/`--thumb` default — it gives
    # YouTube's downscale the most data; --fast/--very-fast still win for a quick
    # low-res layout check, and a plain @still image renders at the normal -qh.
    if fast or very_fast:
        quality = "-ql"
    elif force_4k:
        quality = "-qk"
    else:
        quality = "-qh"
    cmd = [manim, quality]
    if image:
        cmd += ["-s"]                            # save the LAST frame as a PNG (no video)
    if very_fast:
        cmd += ["-r", "256,144", "--fps", "3"]   # terrible res + 3 fps
    if quiet:
        cmd += ["-v", "WARNING"]
    cmd += [*passthrough, path, classname, "-o", output]
    print(f"[render] {' '.join(cmd)}  (SUBSCENE={letter or '-'})",
          file=sys.stderr)
    rc = _run_manim(cmd, env, tail)
    if rc != 0:
        return rc

    if image:
        # -s writes the still to media/images/<module>/<output>.png (manim uses no
        # per-quality subfolder for images). MOVE it into a resolution subfolder so a
        # --fast test can't overwrite / be mistaken for the full-res asset.
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
            if stills:
                _stage_image(letter, output, dest,
                             os.path.splitext(os.path.basename(path))[0])
        else:
            print(f"[render] rendered but couldn't find output PNG for {output} "
                  f"under media/images/", file=sys.stderr)
        return rc

    # Make the clip's audio previewable BEFORE anything copies or derives from it,
    # so --stills stages a file that plays in VSCode rather than one that doesn't;
    # then clear manim's mux leftovers out of the folder you browse to watch renders.
    _previewable_audio(_output_mp4(output))
    _drop_audio_intermediates(_output_mp4(output))

    if frames_spec is not None or padded is not None or stills:
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
        if stills:
            _stills(target[:2], letter, output, mp4,
                    os.path.splitext(os.path.basename(path))[0])
    return rc


# Whether the 'render finished' chime plays on exit. main() sets it False for
# --no-sound; the chime is reserved for the user's own renders (the agent always
# passes --no-sound), so it defaults True for a bare CLI invocation.
_PLAY_DING = True


def _ding():
    """Best-effort 'render finished' sound — fired on exit unless --no-sound. Never
    raises. Detached so it plays even as the process exits; falls back to the terminal
    bell off macOS."""
    if not _PLAY_DING:
        return
    try:
        if sys.platform == "darwin":
            # Submarine: a low sonar 'bloop', deliberately distinct from Claude Code's
            # own prompt/finish chimes so a finished render is unmistakable by ear.
            subprocess.Popen(["afplay", "/System/Library/Sounds/Submarine.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        else:
            sys.stderr.write("\a")
            sys.stderr.flush()
    except Exception:
        pass


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        _ding()
    sys.exit(rc)
