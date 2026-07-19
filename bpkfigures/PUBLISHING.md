# Finishing & publishing a video

The post-`manim` pipeline: once a video's scenes are rendered and its numbers
are locked, this is how the finished video gets assembled, exported, and put on
YouTube. Cross-video (applies to every video in `Ballpark-Figures/`).

> Parts of the **Assemble** step below are reconstructed from the Battleship
> folder + working notes, not a written record — sanity-check them against what
> you actually do and correct anything that's off.

## 1. The pieces (where everything lives)

Everything here is a large binary, so it's **gitignored — local, not synced**
(only the folders + their READMEs are tracked):

- **manim renders** — `animations/**/media/videos/**/*.mp4`, produced by `render`.
  These are **silent** (no audio).
- **voiceover** — per-scene `*.wav` (Battleship keeps them in the video repo
  root, e.g. `01Intro.wav`; edited in an Audacity project `audio.aup3`). *(verify
  your own audio workflow)*
- **music** — `music/` (video root): background track(s), `*.mp3`/`*.wav`.
- **footage** — `footage/` (video root): the NON-manim clips (talking-head
  segments `THA`–`THL`, b-roll, screen recordings), `*.mp4`/`*.mov`.

## 2. Assemble (DaVinci Resolve)

Lay the timeline: the manim renders + talking-head footage on the video track,
voiceover + music on the audio tracks, cut to match the script order. *(This
step is the least documented — refine as needed.)*

- Keep a **project backup**: `File → Export Project` → `.drp`. This is the
  editable project (Battleship keeps these in `Resolve Project Backups/`). It is
  **NOT** the deliverable and is **never uploaded** — it only reopens in DaVinci.

## 3. Export the video (Deliver page)

Deliver → Custom Export, then **Add to Render Queue → Render All**. Settings that
match Battleship's shipped `.mov`:

| Setting | Value |
| --- | --- |
| Format | **QuickTime** (`.mov`) |
| Video codec | **H.264** |
| Resolution | **1920×1080** (match the timeline) |
| Frame rate | **match the video's `animations/manim.cfg` `frame_rate`** — Battleship **30**, Yahtzee **60** |
| Audio | **Export Audio** on; Linear PCM (Resolve's QuickTime default — Battleship: PCM 24-bit / 48 kHz / stereo) |
| Range | **Entire Timeline** |
| Location | the **video repo root** |
| Filename | the video name, e.g. `Yahtzee` → `Yahtzee.mov` |

The export lands at e.g. `Ballpark-Figures/<video>/<Video>.mov` (gitignored, like
Battleship's `Battleship.mov`). H.264 keeps the file ~1 GB; YouTube re-encodes
anyway, so no need for ProRes unless you want a mastering copy.

Sanity-check before rendering: scrub the very start and end of the timeline (no
clipped frames), and confirm audio is present and in sync.

## 4. Publish to YouTube

- **Upload the `.mov`** (the render from step 3) to YouTube Studio — **not** the
  `.drp` (that's a Resolve project file YouTube can't use).
- **Thumbnail**: `render 99a` (the `99thumbnails.py` slot) → a 4K PNG under
  `media/images/**/`; upload that as the thumbnail. Let YouTube do the single
  compression pass — don't pre-compress. (See the "99 = thumbnails" notes in the
  shared `CLAUDE.md`.)

## Quick reference

- Deliverable = **`<Video>.mov`** at the repo root (H.264, 1080p, timeline fps).
- `.drp` = project **backup**, never uploaded.
- Renders are silent; audio (voiceover + music) is added in DaVinci.
- Everything here is local/gitignored — nothing about the finished video is synced
  via git except this doc and the folder READMEs.
