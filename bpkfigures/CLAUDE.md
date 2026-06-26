# Ballpark-Figures — shared animation conventions

Cross-video rules for all videos in this repo (`battleship/`, `yahtzee/`, …).
`bpkfigures/` is the shared package every video imports, so these conventions
load wherever you're working. Video-specific rules live in that video's own
`CLAUDE.md` (e.g. `yahtzee/CLAUDE.md`).

## Repo layout
- `Ballpark-Figures/` umbrella repo: one sub-project per video plus the shared
  `bpkfigures/` package. Each video is its own git repo nested in the umbrella.
- Each video: `animations/{config.py, assets/, scenes/NN<name>.py}`.
- Shared style: `bpkfigures/style.py` (`ACCENT_FILL`, `BG_COLOR`, `FONT`,
  `crisp_text`/`crisp_paragraph`). NB: battleship defines its own `BOARD_FILL`.
- You can reference any video's files even if it's not in the open workspace —
  the agent reads them on disk. "Do this like the Battleship video" always works.

## The Battleship video is the model
Match its visual look and its **sparse on-screen text** — not necessarily its
exact animation primitives. Render ONLY text the script's column 2 explicitly
calls for; no titles/labels/narration that weren't asked for.

## Scene structure (the "Battleship pattern")
- `setup_scene()` builds and positions **every** mobject as `self.<name>` (+ any
  data the animations consume). Many subscenes → split into `_setup_<name>()`
  helpers called in order.
- `@subscene` methods contain **only animations** — nothing is constructed there.
- **Subscene continuity:** a subscene starts from the previous one's END state.
  Anything not on screen at the end of the previous subscene must be ANIMATED IN
  at the start of the next (don't silently `add` — it pops). Things appearing
  together should animate in together.

## Reuse over reinvention
- Read the existing assets and a reference scene (e.g. yahtzee `99test.py`)
  BEFORE building a gameplay-style beat. Use the existing helpers.
- **Don't override a helper's default args** unless asked or genuinely required
  — defaults are deliberate and shared. If a layout seems to "need" a non-default
  value, the layout is probably wrong; fix the layout.
- Measure real mobject geometry (edges/centers) when placement matters; don't
  approximate positions.

## Snapshot cache + rendering (`bpkfigures/scene.py`)
- Render one subscene at a time via the `manim NN<letter>` alias
  (`SUBSCENE=<letter>`); it loads the prior subscene's snapshot instead of
  replaying. Run it from the dir holding the `NN*.py` files (`scenes/`).
- Snapshot key = `SNAPSHOT_VERSION` + hash of project source (EXCLUDING the
  scene file) + a per-subscene dependency digest. Editing a later subscene (or
  code only it uses) leaves earlier snapshots valid; editing an asset/config/
  shared helper invalidates them. Bump `SNAPSHOT_VERSION` to force-invalidate.
- Don't build un-picklable objects (e.g. `always_redraw` with a lambda) in
  `setup_scene` — it breaks the whole scene's snapshot. Build those in the
  subscene; keep picklable parts (`ValueTracker`, static text) in setup.
- The alias auto-cleans stale `NN<letter>_*` videos and clears
  `SUBSCENE`/`RECOMPUTE` at the start of each run. After editing it,
  `source ~/.zshrc`.

## Process
- `Script.md` is reference, not a spec to enforce: do what the user asks and
  flag deviations.
- Implement specific requests **literally** — exact wording is the spec
  ("disappear" ≠ "fade", "centered" = measure-and-center).
- For animation FEEL/timing: build a quick ROUGH version, render + grab frames,
  iterate from the user's reaction. Don't over-build the first pass. Render and
  verify after every visual change.
