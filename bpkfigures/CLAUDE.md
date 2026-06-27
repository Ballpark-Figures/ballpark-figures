# Ballpark-Figures — shared animation conventions

Cross-video rules for all videos in this repo (`battleship/`, `yahtzee/`, …).
`bpkfigures/` is the shared package every video imports, so these conventions
load wherever you're working. Video-specific rules live in that video's own
`CLAUDE.md` (e.g. `yahtzee/CLAUDE.md`).

## Following instructions (read this first)
- **Do what the user explicitly asked, in the form they asked for.** When they
  name a file, format, or method ("put it in a CLAUDE.md", "use a tail flag"),
  that exact choice IS the spec — not a suggestion to improve on with your own
  judgment.
- **Disagreeing is fine; silently overriding is NOT.** If you think a different
  approach is better, FLAG IT AND ASK FIRST, then follow the user's decision.
  Willfully deviating from an explicit instruction — even when your alternative
  seems reasonable — is a serious error that can cause major problems later.
  Flagging-then-asking is always acceptable; substituting without asking is not.
- **A promise about future behavior changes nothing unless it's WRITTEN DOWN —
  so when you catch yourself making one, ASK whether to record it.** Any "I'll fix
  it" / "I'll do better next time" / "I'll remember to X" / "going forward I'll…"
  does NOT survive context compaction or a session restart, so on its own it's
  empty. The only thing that carries forward is an edit to the relevant CLAUDE.md
  (or memory). But don't unilaterally add such a rule either (that over-corrects).
  Instead, treat the urge to promise as a prompt to ask the user: "Should I add
  this to a CLAUDE.md?" If yes, make the edit that turn; if no, drop it — just
  don't leave it as a hollow promise that quietly evaporates.

## Repo layout
- `Ballpark-Figures/` umbrella repo: one sub-project per video plus the shared
  `bpkfigures/` package. Each video is its own git repo nested in the umbrella.
- Each video: `animations/{config.py, assets/, scenes/NN<name>.py}`.
- Shared style: `bpkfigures/style.py` (`ACCENT_FILL`, `BG_COLOR`, `FONT`,
  `crisp_text`/`crisp_paragraph`). NB: battleship defines its own `BOARD_FILL`.
- You can reference any video's files even if it's not in the open workspace —
  the agent reads them on disk. "Do this like the Battleship video" always works.

## New video / new machine
Use `/new-video <name>` to scaffold a new video, and `/sync-videos` to set up a
second machine. The operational specifics (account, machine layout, private-repo
mechanics) live in the private companion file that auto-loads alongside this one
via the import below (a symlink to the `dotclaude` repo; absent → notes skipped):

@CLAUDE.private.md

## Where instructions live (which CLAUDE.md, and CLAUDE.md vs memory)
How the user wants the agent to record things worth remembering:
- **General/cross-video preferences go in `bpkfigures/CLAUDE.md` (this file), NOT
  a video's `CLAUDE.md`.** Anything about how the agent should work in general —
  conduct, workflow, tooling, process, instruction-following — belongs here so it
  loads for every video. A video's own `CLAUDE.md` (e.g. `yahtzee/CLAUDE.md`) is
  ONLY for rules specific to THAT video (its script, layout, assets). When unsure
  whether a preference is general or video-specific, treat it as general and put
  it here.
- **Default to CLAUDE.md** for anything the user wants the agent to know. It's
  loaded every session (guaranteed) and syncs across machines via git pull —
  unlike agent memory, which is local to one machine and only surfaces via recall.
- **When unsure where something goes, don't deliberate** — put it in CLAUDE.md and
  say so. Only reach for memory if it literally cannot be committed (a secret).
- **Use memory ONLY for facts that genuinely can't be committed** (private URLs,
  credentials — anything that shouldn't land in the public repo) AND that have a
  clear, nameable trigger that can go in the memory's `description` so recall
  reliably fires.
- **If something is private but its trigger is fuzzy** (recall can't be trusted),
  don't silently rely on memory — say so and ask the user to re-mention it when it
  comes up.
- The public GitHub repo intentionally shows how the user works, so workflow/
  preference content in committed CLAUDE.md is fine — reliable loading beats repo
  cleanliness.
- **Never write the user's real name (or other personal identifiers) into any
  file in a public repo** — bpkfigures/ and the video repos are public. Refer to
  them as "the user." Real-name/identity facts belong only in the private
  `dotclaude` repo (which the `@CLAUDE.private.md` import pulls in).

## Shell commands (agent)
- **Prefer a single command over a pipe.** The permission allowlist matches one
  command at a time, so chaining/piping allowed commands together (`find … | grep`,
  `pip list | grep`) can still trigger a prompt even when each piece is allowed.
  Most read/inspect pipes have a clean single-command form — use it:
  `rg PATTERN <path>` over `cat … | grep`; `rg --files -g "*.md"` (auto-skips
  `.venv`/gitignored) over `find … | grep`; `pip show X` over `pip list | grep X`;
  `git log -n N` over `git log | head`.
- When a genuine multi-stage transform is unavoidable, run the stages as separate
  calls (or accept the one prompt) rather than inventing a broad pipe allowlist.
- **Edits/Writes in the project tree auto-approve — so before a MAJOR rewrite of a
  file, make sure it's committed (or commit it first).** That way the prior version
  is recoverable from git if the edit goes wrong. Deletions (`rm`) stay gated and
  prompt every time.

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
- **Every animation/wait must expose its `run_time` at the subscene level** so
  the user can tweak timing later when editing the video. Concretely: pass an
  explicit `run_time=` to every `self.play(...)` (don't rely on manim's default
  1.0); `self.wait(t)` already shows its duration. If a subscene calls a HELPER
  that plays animations (e.g. `_grow_step`, or a local `roll()`/`count_in()`
  closure), give that helper a `run_time` parameter and pass it from the call
  site — never bury a hardcoded run_time inside a helper where it can't be
  reached. Default the param to the current value so behavior is unchanged.

## Reuse over reinvention
- Read the existing assets and a reference scene (e.g. yahtzee `99test.py`)
  BEFORE building a gameplay-style beat. Use the existing helpers.
- **Don't override a helper's default args** unless asked or genuinely required
  — defaults are deliberate and shared. If a layout seems to "need" a non-default
  value, the layout is probably wrong; fix the layout.
- Measure real mobject geometry (edges/centers) when placement matters; don't
  approximate positions.

## Rendering — use the `render` script (`bpkfigures/render.py`)
- **Render with `bpkfigures/render`, NOT hand-rolled `manim` calls.** It's the
  single render path for user + agent (the old `manim()` zsh override is gone).
  Run from the `scenes/` dir. If `render` isn't on PATH, invoke
  `<repo>/.venv/bin/python -m bpkfigures.render` (it auto-locates the venv).
- `render 01g` → subscene g, cleans stale, names `01g_<name>.mp4`. Quality
  defaults to HIGH (`-qh`); add `--fast` for a quick `-ql` check (the agent
  should usually use `--fast` for verification). `render 01g 01h 01i` → several
  in sequence ("Finished rendering 01g" after each). `render 01` → full scene.
  `--recompute` ignores the snapshot cache. Clears `SUBSCENE`/`RECOMPUTE` per run
  (no leak into a later full render).
- `render 01g --frames "1.0,2.0,-0.3"` renders THEN extracts those PNG frames
  (negative = seconds-from-end) into a `frames/` dir beside the mp4 and prints
  paths — one command instead of render+ffmpeg. `--frames N` = N evenly spaced.
- `render 01h --state` (no render) prints the mobjects on screen at subscene h's
  START (from the prior snapshot) — use to reason about starting state cheaply.

## Snapshot cache (`bpkfigures/scene.py`)
- Rendering one subscene loads the prior subscene's snapshot instead of replaying.
- Snapshot key = `SNAPSHOT_VERSION` + hash of project source (EXCLUDING the
  scene file) + a per-subscene dependency digest. Editing a later subscene (or
  code only it uses) leaves earlier snapshots valid; editing an asset/config/
  shared helper invalidates them. Bump `SNAPSHOT_VERSION` to force-invalidate.
- Don't build un-picklable objects (e.g. `always_redraw` with a lambda) in
  `setup_scene` — it breaks the whole scene's snapshot. Build those in the
  subscene; keep picklable parts (`ValueTracker`, static text) in setup.
- `render` auto-cleans stale `NN<letter>_*` videos (`resolve --clean`). Both the
  user and agent now use `render` (the old `manim()` zsh override was removed).
  Quality defaults to HIGH; `--fast` gives a quick `-ql` check.

## Git / new repos
- Each video is its own git repo. The FIRST thing to do when creating a new
  video repo is add a `.gitignore` — otherwise generated renders get committed.
  Per-repo `.gitignore` must cover at minimum:
  `media/`, `**/media/`, `*.mp4 *.mov *.wav *.mp3`, `__pycache__/`, `*.py[cod]`,
  `.venv/ venv/`, `.DS_Store`, AND the manim snapshot cache `animations/**/cache/`
  (50+ MB pickles per subscene — pure build artifact). (Media + cache are
  project-specific so they live in the per-repo .gitignore, not a global one.
  battleship/.gitignore is a good reference template.)
- NEVER commit `media/` renders OR the `animations/**/cache/` snapshot pickles.
  If already tracked, untrack with `git rm -r --cached <dir>` (keeps files on
  disk). CAUTION: scope cache/pkl ignores to the animations tree — do NOT
  blanket-ignore `*.pkl`, because solver data under `math/data/` and
  `math/notebooks/data/` is intentionally tracked (synced between machines).

## Starting a new scene
How the user likes a brand-new `scenes/NN<name>.py` built:
- **Orient before writing.** First read the OTHER scenes in this video to match
  their structure and conventions. If this is the video's FIRST scene, read a
  previous video's scenes instead. Also keep in mind what already exists: this
  video's `animations/assets/` and the shared `bpkfigures/` package — reuse, don't
  reinvent.
- **Start from a blank scene** (the setup_scene/@subscene pattern below), not a
  copy — but informed by what you read above.
- **Build from the script.** Stick to what `Script.md` (column 2) calls for:
  don't invent extra content, don't deliberately omit. Fill gaps only where the
  script is genuinely ambiguous, and flag those. (See the literal-implementation
  and verify-render notes under Process.)
- **Changing `assets/` or `bpkfigures/` is welcome — but ASK FIRST.** If a scene
  would benefit from a new/modified shared asset or package change, propose it
  before making the change; don't silently edit shared code.
- **Timing:** make sensible run_time guesses and name them on handoff (see
  Process). Every animation/wait in a subscene must expose a tunable `run_time`,
  even when it calls a helper that performs the animation (see the run_time note
  in the scene-structure section).

## Process
- `Script.md` is reference, not a spec to enforce: do what the user asks and
  flag deviations.
- Implement specific requests **literally** — exact wording is the spec
  ("disappear" ≠ "fade", "centered" = measure-and-center).
- For animation FEEL/timing: build a quick ROUGH version, render + grab frames,
  iterate from the user's reaction. Don't over-build the first pass. Render and
  verify after every visual change.
- **Rough means low-polish, not partial scope.** When the user asks for a first
  pass at a scene, rough in the WHOLE scene end-to-end (every beat wired up with
  guessed timings) — don't stop after the first few beats. The user wants to
  react to the complete arc, not a fragment. Keep each beat rough; cover them all.
- **Verify-render division of labor** (the user renders right after the agent,
  so split the work to minimize TOTAL time): the agent renders 1–3 fast frames
  to catch OBJECTIVE issues before handoff — wrong position/overlap, clipping/
  z-order, an object that didn't appear or move, an off-screen label, a wrong
  number, frame overflow, a size mismatch. These cost the user a full round-trip
  if missed, so the agent should catch them. The agent does NOT iterate on
  subjective FEEL (exact run_times, easing, hold durations, whether an overlap
  is "enough") — the user judges that better/faster from the actual video. On
  handoff, the agent explicitly NAMES which timing/feel knobs it left at a guess
  so the user knows what to watch.
- **Every animation/wait exposes its `run_time`** at the subscene level (pass
  explicit `run_time=` to every `self.play`; give helpers that play a `run_time`
  param) so the user can retime when editing the video. See the run_time note in
  the scene-structure section if present.
- **Use extended thinking for scene-building** (geometry + animation sequencing).
  The costly mistakes here are spatial — overlaps, a label centered on the panel
  edge instead of the cell, dice rolling into a guide line — and timing/sequencing
  ones; working the coordinates out before emitting code prevents a wasted
  render-and-review round-trip, which dwarfs the thinking cost. Skip it for quick
  edits, lookups, and config back-and-forth where it's pure overhead.
