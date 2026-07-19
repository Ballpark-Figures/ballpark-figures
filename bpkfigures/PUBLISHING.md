# Finishing & publishing a video

The post-`manim` pipeline: once a video's scenes are rendered and its numbers
are locked, this is how the finished video gets assembled, exported, and put on
YouTube. Cross-video (applies to every video in `Ballpark-Figures/`).

> Parts of the **Assemble** step below are reconstructed from the Battleship
> folder + working notes, not a written record — sanity-check them against what
> you actually do and correct anything that's off.

## 1. Project setup — match the renders (DO THIS FIRST)

**Set the DaVinci project's resolution + frame rate to match the manim renders
BEFORE you import a single clip.** DaVinci **locks the timeline frame rate once any
media is in the project** (the setting greys out), so getting it wrong means a
painful migration later (see the recovery note below).

- Read the spec from the video's `animations/manim.cfg`: `pixel_width` ×
  `pixel_height` and `frame_rate`. Every video so far is **1920×1080**; fps is
  per-video — **Battleship 30, Yahtzee 60**, and **60 for every video going
  forward** unless that video's `manim.cfg` says otherwise.
- In DaVinci, on a **fresh project, before importing**: `File → Project Settings →
  Master Settings →` **Timeline resolution 1920×1080**, **Timeline frame rate =
  that fps**.
- Why it matters: renders are silent `.mp4`s at that fps; if the timeline fps
  doesn't match, smooth motion judders (60→24 is the worst — uneven), and you won't
  notice until export.

**If the project is ALREADY the wrong frame rate** (media imported, so it's locked)
— you can't flip it; migrate to a new timeline:
1. `File → New Timeline`, uncheck *Use Project Settings* → **Format** tab → set the
   correct **Timeline Frame Rate** → Create. (If it's still greyed, make a
   brand-new *project* at the right fps and re-import — the media's already on disk.)
2. Copy all clips from the old timeline (**Cmd+A → Cmd+C**) and paste into the new
   one. Expect two side effects, both fixable:
   - **Audio drifts / levels get messed up.** Don't fix it clip-by-clip: from the
     OLD (correct) timeline, `Deliver → Format: Wave` (Linear PCM, 24-bit, Entire
     Timeline) to bounce the whole mix to one `.wav`; drop that on a fresh audio
     track at frame 0 in the new timeline. Audio is sample-based, so it's immune to
     the frame-grid change.
   - **A few-frame gaps appear at some cuts** (clip starts snapped to the new frame
     grid → black slivers). **Lock the audio track**, step the playhead cut-to-cut
     with the **↓/↑ arrows**, and close each gap by trimming a neighbouring clip
     edge (a few frames of hold is invisible). Do NOT ripple-close — it shifts
     everything against the audio anchor.

(This recovery is the Yahtzee 24→60 fix, 2026-07 — captured so it never has to be
re-derived.)

## 2. The pieces (where everything lives)

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

## 3. Assemble (DaVinci Resolve)

Lay the timeline: the manim renders + talking-head footage on the video track,
voiceover + music on the audio tracks, cut to match the script order. *(This
step is the least documented — refine as needed.)*

- Keep a **project backup**: `File → Export Project` → `.drp`. This is the
  editable project (Battleship keeps these in `Resolve Project Backups/`). It is
  **NOT** the deliverable and is **never uploaded** — it only reopens in DaVinci.

## 4. Export the video (Deliver page)

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

Gotcha: if you just bounced audio (a `Wave` export), the render settings stay on
**Format: Wave** with **Export Video unchecked** and a small (~MB) size estimate.
Re-check **Export Video**, switch **Format → QuickTime / Codec → H.264**, and
confirm the estimate jumps to **GB** — that's how you know it's exporting video,
not audio.

Sanity-check before rendering: scrub the very start and end of the timeline (no
clipped frames), and confirm audio is present and in sync.

## 5. Publish to YouTube

- **Upload the `.mov`** (the render from step 4) to YouTube Studio — **not** the
  `.drp` (that's a Resolve project file YouTube can't use).
- **Thumbnail**: `render 99a` (the `99thumbnails.py` slot) → a 4K PNG under
  `media/images/**/`; upload that as the thumbnail. Let YouTube do the single
  compression pass — don't pre-compress. (See the "99 = thumbnails" notes in the
  shared `CLAUDE.md`.)

## Quick reference

- **Set the DaVinci project fps + resolution to match `manim.cfg` BEFORE importing**
  (1920×1080, Yahtzee 60 / Battleship 30) — it's locked once media is in.
- Deliverable = **`<Video>.mov`** at the repo root (H.264, 1080p, timeline fps).
- `.drp` = project **backup**, never uploaded.
- Renders are silent; audio (voiceover + music) is added in DaVinci.
- Everything here is local/gitignored — nothing about the finished video is synced
  via git except this doc and the folder READMEs.
