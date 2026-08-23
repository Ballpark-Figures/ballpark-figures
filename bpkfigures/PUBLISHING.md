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
- **voiceover** — **recorded directly in DaVinci** onto an audio track (see
  "Recording the voiceover" below); no external DAW export step. (Battleship's
  older per-scene `*.wav` + Audacity `audio.aup3` workflow is superseded.)
- **music** — `music/` (video root): background track(s), `*.mp3`/`*.wav`.
- **footage** — `footage/` (video root): the NON-manim clips (talking-head
  segments `THA`–`THL`, b-roll, screen recordings), `*.mp4`/`*.mov`.

### Recording the voiceover (directly in DaVinci)

The VO is recorded onto an audio track in DaVinci — no external DAW. **Confirm
the timeline is the right fps/resolution (step 1) BEFORE recording**, so takes
land on the correct frame grid.

One-time setup (per project):
1. Add a VO audio track: right-click the timeline audio-track header → **Add
   Track → Mono** (mono for a single mic).
2. **Patch the mic input** *(hardware-dependent — adjust to your interface)*:
   **Fairlight** page → open the **Mixer** (top-right) → on the VO track's
   channel strip, click the **Input** slot at the top → **Input…** → pick your
   mic / audio interface as the source.

Each recording session:
3. **Arm the track**: click the **R** (record-enable) on that track's header (goes red).
   The channel meter only shows the **live input** when the track is armed.
4. Check levels while talking — aim for peaks around **−12 to −6 dB** (never clipping).
5. Move the playhead to the take's start point.
6. Press the round red **Record** in the transport → speak → **Stop**. The clip
   records onto the armed track at the playhead.
7. **Disarm** (click **R** off) when finished so a stray Record can't overwrite.

**Mic + monitoring (Shure MV7+) — the STABLE-device setup that avoids dropouts:**
- The mic is a **Shure MV7+** (USB). It's both an input AND an output (headphone
  jack on the mic), so use it as BOTH: **System Settings → Sound → Input = Shure
  MV7+ AND Output = Shure MV7+**, and **plug headphones into the mic's own
  headphone jack** (not the Mac). DaVinci playback returns over USB to the mic →
  your headphones, so you hear playback AND monitor your voice.
- **Why this matters:** DaVinci binds its audio device **at launch** and **drops
  the mic input whenever the macOS device set changes** — plugging headphones into
  the *Mac*, a mute/unmute, or replugging USB all trigger it (symptoms: meter
  freezes, or a rhythmic **click ~once/sec**). With input+output on the SAME single
  device (the MV7+) and headphones in the mic, nothing changes mid-session, so it
  holds. **Set the audio config FIRST, launch DaVinci LAST, then don't touch the
  hardware.** If it does drop: re-patch the input (step 2), or quit+relaunch DaVinci.
- **MV7+ red LED = MUTED** (easy to hit the touch panel by accident); tap the mute
  icon to clear it. The touch panel also controls mic gain / headphone volume /
  monitor mix — lock it in the **Shure MOTIV** app to avoid accidental taps.
  Match sample rates (Audio MIDI Setup device = DaVinci Fairlight rate = **48 kHz**).

**Noise gate (removes low-level room noise) — per-track, non-destructive:**
- On the VO track's Mixer strip, double-click the **Dynamics** graph → the
  **Dynamics** window (Expander/Gate · Compressor · Limiter). It's **per-track** (so
  all VO on this one track is covered, and the music track stays untouched) and
  applied on **playback** — the recorded files stay **raw/full**, so tweaks fix all
  existing takes retroactively.
- **Current setting:** the **"Breath Reduction"** factory preset, with **Hold = 150 ms**
  and **Release = 300 ms** (lengthened from the preset so word-ENDINGS don't get
  chopped — a gate closing too fast eats the volume tail-off of word-ends).
- If word-ends still cut: raise **Release**/**Hold**, lower **Threshold**, or reduce
  **Range** (attenuate rather than fully mute). If room noise creeps in between
  phrases: raise **Threshold** a few dB. Keep **Attack** fast (~1–2 ms) so word-STARTS
  aren't clipped.

## 3. Assemble (DaVinci Resolve)

Lay the timeline: the manim renders + talking-head footage on the video track,
voiceover + music on the audio tracks, cut to match the script order. *(This
step is the least documented — refine as needed.)*

- Keep a **project backup**: `File → Export Project` → `.drp`. This is the
  editable project (Battleship keeps these in `Resolve Project Backups/`). It is
  **NOT** the deliverable and is **never uploaded** — it only reopens in DaVinci.

### Audio loudness — make it consistent AND match YouTube

Mix to **LUFS** (perceived loudness), not peak volume. **YouTube plays back at
≈ −14 LUFS integrated and only turns LOUDER uploads DOWN — it never turns a quiet
one UP.** So a mix under −14 just stays quiet (the "why is my video quieter than
everyone else's" symptom). Target **≈ −14 LUFS integrated** for the final mix.

1. **Match every dialogue clip to each other** (fixes talking-heads-quieter-than-VO):
   select the clips (**Cmd+A** grabs all; silent manim renders are skipped
   automatically), **right-click → Normalize Audio Levels…**, and set:
   - **Normalization Mode: ITU-R BS.1770-4**
   - **Target Loudness: −16 LKFS** (LKFS = LUFS; −16 is the per-clip working level,
     leaving headroom under the −14 master target)
   - **Target Level: −2.0 dBTP** (true-peak ceiling — leave as-is)
   - **Set Level: INDEPENDENT** — the critical one: normalizes EACH clip separately
     to the target so all sources land at the same loudness. *Relative* applies one
     shared gain and would PRESERVE the mismatch — not what you want.
2. **Lift the whole mix to YouTube level:** on the **Fairlight** page watch the
   **Loudness** meter (read **Integrated / I**), put a **Limiter** on the Master /
   Bus 1 with a **−1 dBTP** true-peak ceiling, and nudge the **master fader** until
   Integrated reads **≈ −14 LUFS** over a representative play-through.
3. **Music sits under dialogue:** roughly **−23 LUFS or lower**, ducked a few dB
   further under speech.

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

### Upload-form settings — the reusable choices (same every video)

These are the deliberate per-upload settings that carry over from video to video.
The description body, chapters, and the specific tag list are per-video content
(don't reuse those verbatim) — everything below is the standing convention:

- **Category:** Education · **Type:** Real life application.
- **Audience:** *Not* made for kids. **Age restriction:** No. **Paid promotion:** No.
- **AI use:** **No** — stylized `manim` animation + the creator's own voiceover meets
  none of the three disclosure criteria (no real person made to say/do something, no
  altered real footage, no realistic scene that didn't occur). It still must be
  actively selected each time — the form starts blank and won't publish until answered.
- **Video language: English — set it every time.** Auto-dubbing is enabled channel-wide,
  and the source language is the prerequisite for dubbing + auto-captions to generate.
- **Caption certification:** "This content has never aired on television in the U.S."
- **License:** Standard YouTube · Distribution Everywhere · embedding on · publish-to-feed
  + notify subscribers on · remixing video+audio allowed.
- **Comments:** On · Basic moderation · Anyone · Sort by Top · show like count on.
- **A/B title test:** up to 3 title variants, and **each variant can be paired with its
  own thumbnail** (so two entries with the same title text but different thumbnails is a
  valid distinct test, not a duplicate).
- **Description structure:** one-line hook → Substack blog-post link → link to the most
  relevant reference video (e.g. Jan Misali's hangman video) → chapters.
- **Tags: worth adding** (the creator confirms they help). Mix per-video topic tags with
  the standing math/CS set — probability, statistics, expected value, dynamic programming,
  algorithms, game theory, combinatorics, math, word games — plus the specific game/topic.

## Quick reference

- **Set the DaVinci project fps + resolution to match `manim.cfg` BEFORE importing**
  (1920×1080, Yahtzee 60 / Battleship 30) — it's locked once media is in.
- Deliverable = **`<Video>.mov`** at the repo root (H.264, 1080p, timeline fps).
- `.drp` = project **backup**, never uploaded.
- Renders are silent; audio (voiceover + music) is added in DaVinci.
- Everything here is local/gitignored — nothing about the finished video is synced
  via git except this doc and the folder READMEs.
