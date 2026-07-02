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

## The numbers are the product — NEVER invent a calculation (read this first)
This channel's job is: do rigorous math, then present it. So every quantity on
screen (EV, probability, count, aggregate) is the PRODUCT — it must be correct and
traceable to the user's OWN computations, never re-derived by the agent.
- **Never write new math for a displayed value.** If producing a number would
  require implementing ANY calculation — scoring, probability, EV, a reroll/
  combinatorial sum, a simulation, an aggregation — STOP and ASK FIRST, even when
  you're certain it's correct. (This bit us: a hand-rolled single-box EV in a scene
  asset was both unsanctioned AND wrong, and shipped silently.)
- **Source, don't compute.** Before showing a number, find where it already lives:
  a solver output / data file (`math/data/…`), a notebook/module helper (`math/…`,
  e.g. `state_explorer.py`), or a value the user gave you — and read it from there.
  The machinery already exists; use it. If two sources exist, ask which is canonical.
- **A blank is fine; a silent number is not.** Leaving a value stubbed and FLAGGED
  is always acceptable. Filling it with a number you computed yourself is not.
- **If it genuinely isn't available**, stop and flag. Then the user points you to
  the source, fills it, or explicitly approves a method BEFORE you write it — and an
  approved computation lives in the shared math pipeline (notebook/module), not
  buried in a scene.
- **Provenance on handoff.** When a scene shows numbers, report each one → its
  source (file / helper / solver field). If the honest source is "the agent worked
  it out," the rule was already broken — surface it.

## Repo layout
- `Ballpark-Figures/` umbrella repo: one sub-project per video plus the shared
  `bpkfigures/` package. Each video is its own git repo nested in the umbrella.
- Each video: `animations/{config.py, assets/, scenes/NN<name>.py}`.
- Shared style: `bpkfigures/style.py` (`ACCENT_FILL`, `BG_COLOR`, `FONT`,
  `crisp_text`/`crisp_paragraph`). NB: battleship defines its own `BOARD_FILL`.

## Shared visual vocabulary — USE THESE, don't hand-pick (read before styling)
Keep every video visually consistent by pulling colours and surfaces from the
shared package instead of inventing ad-hoc hex values:
- **Colours come from `style.py`.** `ACCENT_FILL` is the primary accent (deep
  blue) — default for bars/fills. The secondary trio `ACCENT_GOLD` /
  `ACCENT_ORANGE` / `ACCENT_RED` (also `ACCENT_PALETTE`) is for categorical /
  overlay / highlight roles. Reuse these; do NOT introduce new one-off hex
  colours unless the user asks. If a new shade is genuinely needed, add it to
  `style.py` (so it's reusable) rather than burying it in a scene.
- **Panels sit on a card.** Use `bpkfigures/card.py` (`get_card` / `card_behind`)
  for the standard rounded surface (matches the scorecard look) — prefer it over
  a raw `RoundedRectangle`. Lean toward putting free-floating text/tables/plots
  on a card rather than straight on the background.
- These are shared defaults; changing them still follows the "ASK before editing
  `bpkfigures/`" rule.
- You can reference any video's files even if it's not in the open workspace —
  the agent reads them on disk. "Do this like the Battleship video" always works.

## New video / new machine
Use `/new-video <name>` to scaffold a new video, and `/sync-videos` to set up a
second machine. The operational specifics (account, machine layout, private-repo
mechanics) live in the private companion file that auto-loads alongside this one
via the import below (a symlink to the `dotclaude` repo; absent → notes skipped):

@CLAUDE.private.md

## Concurrent sessions — one shared branch (NOT per-scene branches)
The user works several scenes at once as **multiple chat tabs in ONE VSCode
window** (the new-chat icon). Verified against the Claude Code docs: the extension
CANNOT scope a chat tab to its own folder — every tab in a window shares that
window's working directory, hence ONE branch. So per-scene branches are
fundamentally incompatible with this workflow (a tab switching branches yanks the
others' files and any in-flight render; that has caused real breakage here — a
render silently used another branch's older scene file, and a mid-render branch
switch crashed a snapshot save).
- **Keep ALL concurrent work on ONE shared branch — `main`.** Different scenes are
  different files (`scenes/NN*.py`, that scene's assets), so tabs don't collide.
  Do NOT create `scene-NN-*` branches for parallel work.
- **The one habit that makes this safe: stage by EXPLICIT PATH** — `git add
  animations/scenes/NN<name>.py`, never `git add -A` / `git add .`. The shared
  working tree means a bulk add sweeps up EVERY tab's in-progress files into one
  commit. Commit only the file(s) that tab changed.
- **Shared resources** (`bpkfigures/`, `config.py`, `assets/`): don't have two tabs
  editing the SAME shared file at the same moment — sequence those. (Editing a
  shared file while another tab merely renders is fine; worst case a cache rebuild,
  and the snapshot digest no longer crashes on it.)
- Per-scene branches ARE possible, but ONLY via git worktrees in SEPARATE windows
  (one folder per branch). That's more window management than the user wants, so
  it's not the default — reach for it only if truly isolated branches are needed.

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
- **Chains auto-approve when EVERY subcommand matches an allow rule.** Claude Code
  splits on `&&`, `||`, `;`, `|`, `&` and newlines and checks each piece
  independently, so chaining *allowlisted* read-only commands (`grep …`, `ls …`,
  `git log …`) is fine and does NOT prompt. The earlier "any chain prompts" advice
  was wrong. What actually forces prompts:
  - **`cd` combined with `git` in one compound command ALWAYS prompts** — even
    when both are individually allowed (a hardcoded safety rule). This was the #1
    source of needless prompts here. The Bash tool's **cwd persists between
    calls**, so NEVER write `cd "<repo>" && git commit …`. Instead `cd` once in
    its own call (or just rely on the already-current dir) and run each `git add`
    / `git commit` / `git push` as a STANDALONE command.
  - **Any non-allowlisted subcommand drags the whole line into a prompt** — most
    often an ad-hoc interpreter (`python3 <<EOF …`, `*/.venv/bin/python
    script.py`). Don't shell out to throwaway python: use Edit/Write + the
    dedicated tools, or a FIXED `-m` module. For peeking at solver `.npz` data use
    `python -m bpkfigures.inspect_npz <path>` (allowlisted, safe — loads with
    `allow_pickle=False`) instead of a probe script.
  - **Subshells `( … )`, command-substitution `$( … )`, `for`/`while` loops, exec
    wrappers (`watch`, `xargs -flags`), and `find -exec/-delete`** never
    auto-approve — split them into separate simple calls.
- There is NO syntax to allowlist a compound pattern (rules are per-subcommand),
  so the fix is always behavioral: standalone calls + the right tool. Prefer the
  clean single-command read form anyway: `rg PATTERN <path>` over `cat … | grep`;
  `pip show X` over `pip list | grep X`; `git log -n N` over `git log | head`.
- **Edits/Writes in the project tree auto-approve — so before a MAJOR rewrite of a
  file, make sure it's committed (or commit it first).** That way the prior version
  is recoverable from git if the edit goes wrong. Deletions (`rm`) stay gated and
  prompt every time.

## The Battleship video is the model
Match its visual look and its **sparse on-screen text** — not necessarily its
exact animation primitives. Render ONLY text the script's column 2 explicitly
calls for; no titles/labels/narration that weren't asked for.

## Scene structure (LAZY per-subscene building)
- **Build lazily, in the OWNER subscene — not all up front in `setup_scene`.**
  Each subscene builds (as `self.<name>`) the mobjects it OWNS = the ones that
  first appear in it, typically via a `_setup_<name>()` helper it calls at its
  start; then it animates. `setup_scene` holds ONLY things on screen from frame 0
  (a persistent background/scorecard) — often it's empty. Why this over the old
  "build everything in setup_scene" pattern: a snapshot pickles the whole scene
  state, so front-loading made every snapshot heavy AND made any setup edit
  invalidate EVERY subscene's snapshot. Lazy building keeps snapshots light and
  makes a setup edit invalidate only its owner subscene onward. (See the snapshot
  cache + render notes.)
- **Carry-over is automatic — don't rebuild.** An object built in subscene N and
  left in `self` is restored (same object, same mutated state) when N+1 loads N's
  snapshot, so later subscenes just REFERENCE `self.<name>`. Two rules: (1) every
  reused object needs a `self.` handle (a local mobject can't be named next
  subscene); (2) ONE owner per object — if two subscenes both `self.foo = …`, the
  second silently replaces the carried one (a real bug). When a carry-over is
  consumed/no longer needed, drop it (`self.foo = None`) so later snapshots stay
  light.
- `@subscene` methods are **build-its-own + animate** — they construct what they
  own (or call its `_setup_<name>()`) then play; they never rebuild a carried-over
  object.
- **Subscene continuity:** a subscene starts from the previous one's END state.
  Anything not on screen at the end of the previous subscene must be ANIMATED IN
  at the start of the next (don't silently `add` — it pops). Things appearing
  together should animate in together.
- **Every animation/wait's `run_time` lives as an editable value in the subscene
  BODY** — a local variable (or inline literal) the user can see and tweak right
  there — so timing is retunable without digging into helpers. Concretely: pass an
  explicit `run_time=` to every `self.play(...)` (don't rely on manim's default
  1.0); `self.wait(t)` already shows its duration. If a subscene calls a HELPER
  that plays animations (e.g. `_grow_step`, or a local `roll()`/`count_in()`
  closure), give that HELPER a `run_time` PARAMETER and pass the value from the
  subscene body — never bury a hardcoded run_time inside a helper where it can't be
  reached.
- **Do NOT put timing (or any tunable) on the @subscene method's own signature.**
  Subscenes are invoked with NO arguments (`getattr(self, name)()` in `scene.py`),
  so a `def beat(self, run_time=3.0)` param is NEVER overridden — it's a dead,
  misleading "knob" that looks callable but isn't. Put the value in the BODY:
  `def beat(self):` then `run_time = 3.0` at the top, used below. "Expose at the
  subscene level" means in the subscene's BODY, not its signature — the signature
  of an `@subscene` is always just `(self)`.

## Reuse over reinvention
- Read the existing assets and a reference scene (e.g. yahtzee `99test.py`)
  BEFORE building a gameplay-style beat. Use the existing helpers.
- **Read assets to CALL them, not just to imitate their look.** The reference
  scene shows *which methods do the work*: a keep/reroll beat IS `DiceBoard.keep`
  + `roll_rest` (exactly what `99test.py` shows), not hand-placed coordinates.
  Before a gameplay beat, name the exact asset method each sub-beat calls, and
  trace the dice/card state through it (which boxes are open, where each die
  sits). If you're re-deriving something an asset already provides, stop and call
  the asset — reading code only to copy its *look* is how reinvention, and
  "wrong-box"/"wrong-dice" mistakes, sneak in.
- **Don't override a helper's default args** unless asked or genuinely required
  — defaults are deliberate and shared. If a layout seems to "need" a non-default
  value, the layout is probably wrong; fix the layout.
- Measure real mobject geometry (edges/centers) when placement matters; don't
  approximate positions. For NUMBERS, the bar is even higher: don't guess AND don't
  compute them yourself — SOURCE every displayed value from the user's pipeline, or
  stub-and-flag it. See "The numbers are the product — NEVER invent a calculation".

## Rendering — use the `render` script (`bpkfigures/render.py`)
- **Render with `bpkfigures/render`, NOT hand-rolled `manim` calls.** It's the
  single render path for user + agent (the old `manim()` zsh override is gone).
  Run from the `scenes/` dir.
- **Invoke it as BARE `render …` (the shell alias) — NOT the
  `"<repo>/.venv/bin/python" -m bpkfigures.render` fallback.** Bare `render`
  auto-approves (allowlist `render *`) and the alias expands fine in the agent
  shell; the fallback needs the space-containing repo path QUOTED, and the quote
  breaks the allowlist glob so it PROMPTS on every call. (That one slip made
  ~every render in a whole scene prompt.) `cd` to `scenes/` in its OWN call, then
  run `render …` standalone (a `cd && render` chain trips the cd-chain guard).
  Only fall back to the venv-python form if bare `render` genuinely fails (it's
  now allowlisted quoted too, but bare `render` is the default).
- `render 01g` → subscene g, cleans stale, names `01g_<name>.mp4`. Quality
  defaults to HIGH (`-qh`); add `--fast` for a quick `-ql` check (the agent
  should usually use `--fast` for verification). `render 01g 01h 01i` → several
  in sequence ("Finished rendering 01g" after each). `render 01` → full scene.
  `--recompute` ignores the snapshot cache. Clears `SUBSCENE`/`RECOMPUTE` per run
  (no leak into a later full render).
- `render 01g --frames "1.0,2.0,-0.3"` renders THEN extracts those PNG frames
  (negative = seconds-from-end) into a `frames/` dir beside the mp4 and prints
  paths — one command instead of render+ffmpeg. `--frames N` = N evenly spaced.
- `render 01g --frames "1.0,-0.3" --extract` extracts those frames from the
  ALREADY-rendered mp4 (NO re-render) into `frames/` and prints paths — use it to
  grab frames from a heavy subscene without rebuilding it. Then READ the PNGs with
  the Read tool; never hand-roll `ffmpeg … && ffmpeg …` chains.
- `render 01h --state` (no render) prints the mobjects on screen at subscene h's
  START (from the prior snapshot) — use to reason about starting state cheaply.
- **`render` takes a per-scene lockfile** (`cache/locks/`), so a SECOND render of
  the same scene while one is running is REFUSED (concurrent manim runs corrupt
  partial movies / the snapshot cache — don't do it). A stale lock from a dead
  process is auto-taken-over, so there's nothing to clean up by hand. `--check`,
  `--state`, and `--extract` don't lock (they don't render).

## Snapshot cache (`bpkfigures/scene.py`)
- Rendering one subscene loads the LATEST VALID snapshot at or before the prior
  subscene, then replays only the gap (frames skipped). So after editing subscene
  h, `render NNi` loads g's still-valid snapshot and replays just h — it does NOT
  rebuild the whole prefix. Combined with lazy building (above), editing a
  subscene's `_setup_<name>` invalidates only that subscene onward, so the heavy
  early build-up stays cached.
- Snapshot key = `SNAPSHOT_VERSION` + hash of project source (EXCLUDING the scene
  file AND the render/resolve CLI tooling, which never affect output) + a
  per-subscene dependency digest. Editing a later subscene (or code only it uses)
  leaves earlier snapshots valid; editing an asset/config/shared helper (or
  `scene.py`/`style.py`) invalidates them; editing `render.py`/`resolve.py` does
  NOT. Bump `SNAPSHOT_VERSION` to force-invalidate.
- Don't build un-picklable objects (e.g. `always_redraw` with a lambda) in
  `setup_scene` — it breaks the whole scene's snapshot. Build those in the
  subscene; keep picklable parts (`ValueTracker`, static text) in setup.
- `render` auto-cleans stale `NN<letter>_*` videos (`resolve --clean`). Both the
  user and agent now use `render` (the old `manim()` zsh override was removed).
  Quality defaults to HIGH; `--fast` gives a quick `-ql` check.

## Rendering during iteration (agent — keep the loop fast)
The slowest mistakes here are render round-trips, not thinking. Defaults:
- **Render ONLY the subscene(s) you changed**, never the whole scene (`NN sub` /
  `NN all`) unless geometry genuinely changed everywhere. `render NNk` replays the
  prefix once; `NN sub` rebuilds all subscenes (much slower).
- **Editing a shared asset (`assets/`, `bpkfigures/`) invalidates ALL snapshots**
  (see the cache key above), so BATCH asset edits and render once, rather than
  re-rendering after each small asset tweak.
- **Verify with ≤2 frames, for OBJECTIVE issues only** (wrong number/position/
  overlap/clipping). The user judges feel/timing from the actual video far better
  and faster than the agent does from stills — don't frame-hunt.
- **After changing a beat, render THAT beat and glance at its NEIGHBOURS.** Beats
  carry shared state (same dice, label, running number), so a change often reads
  wrong only in the beat before/after — a value that equals the previous beat's, a
  die that dips down then straight back up across a hand-off, text that now
  overflows a column. A `--check` (syntax) is NOT a render: render the beat, look,
  then scan the seams with its neighbours. (Each of those examples shipped in
  scene-04 because the change was made but the beat/neighbour wasn't looked at.)
- **TRIP-WIRE: a 2nd render of the same subscene to re-judge how it LOOKS means
  you're frame-hunting feel — STOP and hand off.** One objective-check render per
  change, then the user takes over. Stills judge only objective spatial facts
  (count/position/overlap-as-geometry/clipping); they CANNOT judge motion or
  whether an animation "reads" — so never diagnose or "fix" a motion/feel problem
  from a still. If a still looks off but the issue is motion, that's the user's
  call from the video, not a reason to iterate.
- **TRIP-WIRE #2: built a beat WRONG twice for the same conceptual reason? STOP and
  ASK what it should depict — do NOT re-guess.** A repeated conceptual miss (wrong
  game state, wrong quantity, wrong turn) is a comprehension gap, not an
  implementation bug: the fix is a QUESTION, not another render. Re-iterating on a
  misunderstood beat burns rounds and ships confidently-wrong output — it's what
  turned scene-04's montage into many painful rounds (polishing a beat built on the
  wrong state/quantity instead of asking what column 1 said it was). If you're
  unsure what a beat IS, that uncertainty is itself the trigger to ask BEFORE
  building — don't treat a comprehension problem as an implementation one.
- **If a fix to a USER-SPECIFIED shape/layout hits a snag, revert to exactly what
  they asked and flag-ask — do NOT swap in a different design.** Substituting your
  own concept (even to solve a real problem) is a silent override, the worst kind
  of error here. The minimal animation/timing tweak is in scope; changing the
  shape/structure the user named is not.
- **Default to "minimal verify"**: render the changed subscene(s) + ≤2 frames,
  then hand off. For a pure feel/timing pass, prefer **edit-only** (make the edits,
  let the user render) — it matches the user's fastest loop.
- **Animation timing/visuals: use trackers/updaters** (value- or `dt`-driven), NOT
  computed-time guesses (`Succession(Wait(t_guess), …)`). Guessed timings are
  fragile and cause repeated rework; a value-/dt-driven effect fires correctly
  regardless of how the surrounding animation is paced.

### Keep commands allowlist-friendly (avoid permission prompts)
The permission allowlist already covers the core loop (`render`, `manim`,
`ffmpeg`/`ffprobe`, `grep`/`rg`/`ls`/`cat`/`head`/`tail`/`wc`/`sort`/`tr`,
`cd`/`echo`/`mkdir`). Friction comes from working AROUND it; so:
- **Separators split and auto-approve; control-flow constructs never do.**
  Plain separators — `&&`, `||`, `;`, `|` — are parsed and each subcommand is
  matched independently, so a chain of *allowlisted* commands runs prompt-free.
  But `for`/`while`/`until` loops, subshells `( … )`, and command-substitution
  `$( … )` always prompt (the evaluator can't see inside them) — split those into
  separate one-command tool calls. Terse one-liner verification loops
  (`for x in …; do …; done`) and the `( cmd || fallback )` subshell idiom are the
  classic traps. NB: a chain still prompts if ANY one subcommand isn't allowlisted
  (e.g. ad-hoc `python`), or if it's the `cd`+`git` combo (always prompts — see
  the git note below).
- **Syntax check with `render NN --check`** (instant AST parse of the scene +
  `assets/*.py`, no manim) — NOT a separate `python -c "import ast …"`, which
  isn't allowlisted and prompts every time.
- **Validate JSON with `python3 -m json.tool <file>`** (allowlisted) — NOT
  `python -c "import json …"`. `json.tool` only parses/echoes JSON so it's safe
  to allow; arbitrary `python -c`/`python3 -c` is real code execution, stays
  gated, and prompts every time. General rule: reach for a FIXED, safe
  invocation (a stdlib `-m` module, a wrapper script) over ad-hoc `-c`.
- **Run renders via `run_in_background`, then READ the task's `.output` file with
  the Read tool** — NOT `tail`/`grep`/`sed`/`| head` on it (those pipes prompt
  every time; the Read tool never does). Don't build `cd … && render … > log; grep`
  chains or `until grep …; do sleep; done` poll loops — the harness notifies on
  completion.
  - **Confirm the cwd is `scenes/` before firing a background render.** The Bash
    cwd persists across calls, so a `cd <repo-root>` done for a git commit leaves
    you at the repo root; a later `render NN` then fails silently-ish with "No file
    matching NN*.py" (the error is only in `.output`, so you don't see it until you
    read the file). After any git work, `cd` back to `scenes/` in its own call
    first.
- **Grab render frames with `render … --frames … --extract`, then READ the PNGs**
  (Read tool) — one allowlisted call, no re-render. NOT hand-rolled
  `M=… && ffmpeg … && ffmpeg …` chains (the `&&`, `$VAR`, and `select='eq(n\,N)'`
  quoting all force a prompt).
- **Run git as STANDALONE calls — never `cd <repo> && git …`.** The `cd`+`git`
  combo ALWAYS prompts (hardcoded safety block), and it was the #1 source of
  needless prompts. The Bash cwd PERSISTS between calls, so `cd <repo>` once in
  its own call (or just rely on the current dir — yahtzee is the primary working
  dir) and then run `git add` / `git commit` / `git push` each standalone, with no
  `cd` prefix, pipe, or `2>&1`.
- **Edit files with the Edit/Write tools, never `python - <<'EOF'` splices** —
  arbitrary `python`/`python3` isn't (and shouldn't be) allowlisted, and file
  rewrites via heredoc are easy to get wrong.
- Use `rg`/`ls` (allowed) instead of `find` for inspection.
- `pkill`/`kill`/`rm` stay gated on purpose — don't reach for process-killing as a
  normal step; if a render seems stuck, prefer `run_in_background` + waiting.

## Git / new repos
- **Commit and push WITHOUT asking — this OVERRIDES Claude Code's default.** The
  built-in default is to commit/push only when the user explicitly asks; in this
  project the agent has standing permission to do both as a normal part of the
  workflow: checkpoint WIP, commit before a major rewrite, push when a chunk is
  done. Still branch off `main` for non-trivial work (don't pile experimental
  commits straight onto `main`), and keep the commit-message footer convention.
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
- **PREFLIGHT before writing OR editing a scene — write the map down first.** This
  operationalizes the sparse-text and reuse rules into a gate; skipping it is HOW
  they get violated. Produce, in the chat, a short explicit map:
  (1) each beat → the reference scene/section it must match and the exact
  conventions to copy from it (grid shape, `flow_order`/ordering, sizes, buffs,
  helpers). A beat that visually parallels another scene (e.g. "the 252 from
  scene 1") MUST reuse that scene's actual layout, not a re-derivation.
  (2) every on-screen text element → the literal column-2 phrase that licenses it.
  Anything that doesn't map to column 2 (titles, counts, helper labels) gets
  DROPPED or flagged to the user for approval — NEVER silently added.
  (3) **the WHOLE of column 2 as a clause-by-clause checklist** — quote EVERY
  clause verbatim, animation directions included ("move dice down a row", "remove
  4kind", "3 other configurations", "counter to increase EV remaining"), and next
  to each write the exact thing you'll build for it. A clause you intend to
  deviate from, can't build, or would paraphrase gets FLAGGED-and-ASKED, never
  silently changed or dropped. Paraphrasing column 2 into your own words is HOW
  "wrong box" / "dropped instruction" / "ignored the row structure" errors happen
  — the exact words ARE the spec (numbers, counts, "row", which box). Do this
  before writing; **re-run the same table against the built scene at handoff** and
  report every clause that still doesn't match.
  (4) **each beat → the column-1 VOICEOVER sentence(s) it pairs with — READ
  COLUMN 1, not column 2 alone.** Column 2 (animation notes) is often terse or
  elliptical ("skip most of the stuff", "montage"); the VOICEOVER is what pins
  down what a beat actually depicts, so quote the paired column-1 text next to
  each beat BEFORE writing code. When column 2 is vague or you're unsure which
  game state / turn / quantity a beat refers to, the voiceover disambiguates it —
  e.g. a montage whose voiceover says "the second reroll of turn 12, then the
  first reroll of turn 12" is the *specific* two-open-box turn-12 state (and its
  numbers are rest-of-GAME EVs), NOT a generic single-box illustration. If the
  two columns still don't pin it down, FLAG-and-ASK rather than guessing. (This
  rule exists because reading column 2 in isolation repeatedly produced the wrong
  state/quantity for such beats.)
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
  Process). Every animation/wait must expose a tunable `run_time` as a value in the
  subscene BODY (not on the @subscene signature — subscenes take no args), even when
  it calls a helper that performs the animation (see the run_time note in the
  scene-structure section).

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
- **Every animation/wait exposes its `run_time`** as a value in the subscene BODY —
  NOT on the @subscene signature (subscenes are called with no args, so a signature
  param is a dead knob). Pass explicit `run_time=` to every `self.play`; give helpers
  that play a `run_time` param and pass the body's value in. So the user can retime
  when editing the video. See the run_time note in the scene-structure section.
- **Use extended thinking for scene-building** (geometry + animation sequencing).
  The costly mistakes here are spatial — overlaps, a label centered on the panel
  edge instead of the cell, dice rolling into a guide line — and timing/sequencing
  ones; working the coordinates out before emitting code prevents a wasted
  render-and-review round-trip, which dwarfs the thinking cost. Skip it for quick
  edits, lookups, and config back-and-forth where it's pure overhead.
