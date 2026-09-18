"""Sound-effect library resolution for `BpkScene.sfx()`.

Two tiers, and deliberately only two:

  1. `BPK_SFX_DIR` — an env override, the scratch path for trying an effect out
     without committing it anywhere.
  2. `<umbrella>/music-library/sfx/` — THE library. `music-library` is the private
     repo that already holds the licensed background music, with a `catalog.md`
     recording provenance; sound effects are the same kind of asset under the same
     licensing constraints, so they live beside it rather than in a new repo.

**There is deliberately NO per-video `animations/assets/sfx/` tier.** Every video's
`.gitignore` carries an UNANCHORED `*.wav`, so a file there is untracked by
construction — it would exist on exactly one machine, which is the failure the
private-library decision exists to avoid. Supporting one properly would mean adding
a `!` un-ignore rule to five separate repos. `BPK_SFX_DIR` already covers the "try a
sound without committing it" case, so that tier buys nothing but a way to lose work.

**The library root is anchored on this file, not on the cwd.** `bpkfigures` is
editable-installed into each video's venv, so `__file__` points at the real source
tree and `dirname(_BPK_DIR)` is the umbrella root however `render` was invoked and
from whichever directory. A cwd-relative `../../..` happens to work when rendering
from `animations/scenes/` and breaks the first time anything renders from elsewhere.

**Absolute paths are the point.** `sfx_path` returns an absolute path, which means
manim's `assets_dir` is never consulted: `seek_full_path_from_defaults` tries the
path AS GIVEN first and returns it when it exists. That matters because no
`manim.cfg` in this repo sets `assets_dir`, and manim's default would resolve it
relative to the cwd — `animations/scenes/assets`, which does not exist. (Same
approach as hangman's `youtube_media/`, resolved from `__file__` and handed to
ImageMobject as an absolute path.)

**`.wav` only.** manim re-decodes any other format to a NamedTemporaryFile on EVERY
`add_sound` call -- there is a literal TODO in `scene_file_writer.py` about not
caching that -- so an mp3 library would pay a decode per cue per render.
"""

import os
import wave

_BPK_DIR = os.path.dirname(os.path.realpath(__file__))

# <umbrella>/music-library/sfx/ -- bpkfigures/ is a directory of the umbrella repo,
# and music-library is its sibling there (ignored wholesale by the umbrella's
# .gitignore because it is its own private repo).
LIBRARY = os.path.join(os.path.dirname(_BPK_DIR), "music-library", "sfx")

EXT = ".wav"

# The house authoring spec. Files are normalised ONCE, at author time (so a baked
# effect arrives at a consistent level and the edit rarely has to touch it), and
# mono to match PUBLISHING.md's 3-mono-track timeline. Rate matters for a second
# reason: manim's initial segment is AudioSegment.silent() at 11025 Hz mono and
# pydub's _sync upgrades a mix to the highest spec present, so cues at mixed rates
# make the exported format depend on which cue happened to be richest.
WANT_RATE = 48000
WANT_CHANNELS = 1
WANT_SAMPWIDTH = 2          # 16-bit PCM

# Effects are PEAK-normalised, not loudness-normalised, and that is a real choice.
# The loudness standard measures in 400 ms blocks, so a 120 ms click is SHORTER THAN
# ONE BLOCK: the meter averages it against the silence around it, and hitting an
# integrated LUFS target means cranking the click enormously. (Same mechanism as the
# Cmd+A normalize hazard in PUBLISHING.md -- LUFS is for SUSTAINED material, and
# effects are transients.) Peak is predictable, never clips, and leaves the handful
# of effects that still sit wrong to a per-call `gain` in dB, which no single
# automatic measure would have got right across material this varied.
PEAK_DBFS = -3.0


def sfx_roots():
    """The directories searched, in order. Override first, then the library."""
    roots = []
    override = os.environ.get("BPK_SFX_DIR")
    if override:
        roots.append(override)
    roots.append(LIBRARY)
    return roots


def sfx_path(name):
    """Absolute path to sound effect `name` (with or without a `.wav` suffix).

    Raises FileNotFoundError naming every root searched. A MISSING EFFECT MUST NEVER
    SILENTLY NO-OP: a sound that doesn't play is the single hardest failure to notice
    in a render, so this is loud and early rather than quiet and late.
    """
    if os.path.isabs(name):                 # an explicit path is taken as given
        if os.path.exists(name):
            return name
        raise FileNotFoundError(f"sfx: no such file {name!r}")

    stem = name[:-len(EXT)] if name.endswith(EXT) else name
    roots = sfx_roots()
    for root in roots:
        cand = os.path.join(root, stem + EXT)
        if os.path.exists(cand):
            return cand

    tried = "\n".join(f"    {os.path.join(r, stem + EXT)}" for r in roots)
    hint = ""
    if not os.path.isdir(LIBRARY):
        hint = (f"\n  The library directory does not exist: {LIBRARY}\n"
                f"  music-library is a separate private repo — run /sync-videos to "
                f"clone it.")
    raise FileNotFoundError(
        f"sfx: no sound effect named {stem!r}. Searched:\n{tried}{hint}\n"
        f"  (set BPK_SFX_DIR to point at a scratch directory of .wav files)")


def wav_info(path):
    """(duration_seconds, channels, rate, sampwidth) read from the WAV header.

    Uses the stdlib `wave` module, so it costs a header read rather than a decode --
    which is the whole reason the library is .wav-only. The duration is what lets
    `_finalize_audio` audit a cue that overruns the end of its clip.
    """
    with wave.open(path, "rb") as w:
        frames, rate = w.getnframes(), w.getframerate()
        return (frames / float(rate) if rate else 0.0,
                w.getnchannels(), rate, w.getsampwidth())


def spec_complaints(path):
    """Human-readable ways `path` departs from the house authoring spec (may be empty).

    Advisory only -- an off-spec file still plays. It is worth saying because a
    stereo or 44.1 kHz file silently changes the format of the WHOLE exported
    segment (see WANT_RATE above), so the damage shows up on a different cue than
    the one that caused it.
    """
    try:
        _dur, channels, rate, width = wav_info(path)
    except Exception as e:                  # not a PCM wav, truncated, etc.
        return [f"could not read as PCM wav ({type(e).__name__})"]
    out = []
    if rate != WANT_RATE:
        out.append(f"{rate} Hz (house spec is {WANT_RATE})")
    if channels != WANT_CHANNELS:
        out.append(f"{channels} channels (house spec is mono)")
    if width != WANT_SAMPWIDTH:
        out.append(f"{width * 8}-bit (house spec is 16-bit PCM)")
    return out
