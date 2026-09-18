"""Convert a source sound file into a library-spec effect in `music-library/sfx/`.

    python -m bpkfigures.sfx_import <file> [<file> ...] [--name NAME] [--dry-run]

A stock download is never to spec — typically 44.1 kHz stereo 24-bit with leading
silence at whatever level the publisher chose. This does the mechanical part, once,
at author time, so `self.sfx("click")` arrives consistent and the edit rarely has to
touch it:

  1. 48 kHz, mono, 16-bit PCM         (see sfx.py for why each of those)
  2. leading silence trimmed          (`at=` positions the START OF THE FILE, so head
                                       silence is an invisible delay on every use)
  3. PEAK-normalised to sfx.PEAK_DBFS (NOT loudness — sfx.py's PEAK_DBFS says why)

**The spec lives in `sfx.py`, not here.** This module imports WANT_RATE / WANT_CHANNELS
/ WANT_SAMPWIDTH / PEAK_DBFS rather than restating them, so the converter and the
render-time checker can never disagree about what "to spec" means.

It prints a ready-to-paste `catalog.md` row for each file — the md5 of the OUTPUT (the
rename-proof anchor, matching the music table's column) and the original filename, so
provenance survives the conversion. It REFUSES to overwrite an existing effect without
`--force`: the library is committed, and silently replacing a sound every scene already
calls is not something to do by accident.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

from bpkfigures.sfx import (LIBRARY, EXT, PEAK_DBFS, WANT_RATE, WANT_CHANNELS,
                            WANT_SAMPWIDTH, wav_info, spec_complaints)

# The level below which leading audio counts as silence to trim. Deliberately well
# under any real content but above dither/noise-floor, so a fade-in is kept.
TRIM_THRESHOLD_DB = -60


def _ffmpeg():
    return shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def _run(args):
    return subprocess.run([_ffmpeg(), "-y", "-v", "error", *args],
                          capture_output=True, text=True)


def _measure_peak(path):
    """Peak level in dBFS, from ffmpeg's volumedetect. None if it cannot be read."""
    r = subprocess.run([_ffmpeg(), "-v", "info", "-i", path,
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def _slug(path):
    """`Whoosh Impact 03.wav` -> `whoosh-impact-03` — the name a scene will call."""
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem or "effect"


def convert(src, dest, dry_run=False):
    """Convert `src` to spec at `dest`. Returns a dict describing what was done."""
    peak_before = _measure_peak(src)
    if dry_run:
        return {"dest": dest, "peak_before": peak_before, "dry_run": True}

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        # Pass 1 — format + trim. The trim runs BEFORE the peak is measured, since
        # cutting the head can only change where the maximum sits.
        r = _run(["-i", src,
                  "-af", f"silenceremove=start_periods=1:start_duration=0:"
                         f"start_threshold={TRIM_THRESHOLD_DB}dB",
                  "-ar", str(WANT_RATE), "-ac", str(WANT_CHANNELS),
                  "-c:a", f"pcm_s{WANT_SAMPWIDTH * 8}le", tmp])
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg convert failed: {r.stderr.strip()[-300:]}")

        # Pass 2 — measure, Pass 3 — apply the single gain that lands on PEAK_DBFS.
        peak = _measure_peak(tmp)
        if peak is None:
            raise RuntimeError("could not measure peak level")
        gain = PEAK_DBFS - peak
        r = _run(["-i", tmp, "-af", f"volume={gain:.3f}dB",
                  "-c:a", f"pcm_s{WANT_SAMPWIDTH * 8}le", dest])
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg normalise failed: {r.stderr.strip()[-300:]}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    with open(dest, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    return {"dest": dest, "peak_before": peak_before, "gain": gain,
            "peak_after": _measure_peak(dest), "md5": md5,
            "info": wav_info(dest), "dry_run": False}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="python -m bpkfigures.sfx_import",
        description="Convert sound files into library-spec effects in music-library/sfx/.")
    ap.add_argument("sources", nargs="+", help="source audio file(s), any format ffmpeg reads")
    ap.add_argument("--name", help="output name (one source only); default is a slug of "
                                   "the source filename")
    ap.add_argument("--out", default=LIBRARY, help=f"output directory (default {LIBRARY})")
    ap.add_argument("--force", action="store_true",
                    help="replace an effect that already exists")
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be written, convert nothing")
    a = ap.parse_args(argv)

    if a.name and len(a.sources) > 1:
        ap.error("--name takes a single source")
    if not a.dry_run:
        os.makedirs(a.out, exist_ok=True)

    rows, rc = [], 0
    for src in a.sources:
        if not os.path.exists(src):
            print(f"[sfx] {src}: no such file", file=sys.stderr)
            rc = 1
            continue
        name = a.name or _slug(src)
        dest = os.path.join(a.out, name + EXT)
        if os.path.exists(dest) and not a.force and not a.dry_run:
            print(f"[sfx] {name}: already in the library — pass --force to replace "
                  f"(every scene calling self.sfx({name!r}) would change)", file=sys.stderr)
            rc = 1
            continue
        try:
            res = convert(src, dest, dry_run=a.dry_run)
        except Exception as e:
            print(f"[sfx] {name}: {e}", file=sys.stderr)
            rc = 1
            continue

        if a.dry_run:
            print(f"[sfx] would write {dest}  (source peak "
                  f"{res['peak_before'] if res['peak_before'] is not None else '?'} dBFS)")
            continue

        dur, ch, rate, width = res["info"]
        print(f"[sfx] {name}{EXT}: {dur:.3f}s  {rate} Hz  "
              f"{'mono' if ch == 1 else f'{ch}ch'}  {width * 8}-bit   "
              f"peak {res['peak_before']:+.1f} -> {res['peak_after']:+.1f} dBFS "
              f"(gain {res['gain']:+.1f} dB)")
        for c in spec_complaints(dest):          # must be empty; a belt-and-braces gate
            print(f"[sfx] {name}: STILL OFF SPEC — {c}", file=sys.stderr)
            rc = 1
        rows.append(f"| {name} | — | — | — | — | `{os.path.basename(src)}` | "
                    f"`{res['md5']}` |")

    if rows:
        print("\nPaste into music-library/catalog.md (Sound effects), filling in the "
              "title/usage/source columns:\n")
        print("\n".join(rows))
    return rc


if __name__ == "__main__":
    sys.exit(main())
