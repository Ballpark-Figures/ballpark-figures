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
- **Getting pipeline numbers INTO a scene — cache, don't compute at render.** The
  house pattern: a per-scene data module (`animations/assets/<name>_data.py`)
  computes the handful of numbers by calling the SHARED solver/pipeline helpers
  (never reinventing the math) and persists them to a COMMITTED cache file
  (`<name>_cache.json`) beside it; the SCENE imports the data module and the RENDER
  never imports the solver (it reads the cache, so renders need no heavy deps and
  the numbers sync between machines via git). Keep a runnable provenance script
  that PRINTS where each number comes from, separate from the render path. The
  video-specific specifics (which venv, which solver module, exact file names) live
  in that video's CLAUDE.md — yahtzee `assets/line_data.py` is the reference user.

## Repo layout
- `Ballpark-Figures/` umbrella repo: one sub-project per video plus the shared
  `bpkfigures/` package. Each video is its own git repo nested in the umbrella.
- Each video has TWO sides — know which one a file belongs to:
  - `math/` — the DATA / COMPUTATION pipeline: `math/data/` (source data, solver
    outputs, datasets, wordlists — tracked and synced between machines),
    `math/notebooks/` (Jupyter exploration), plus solver/helper modules beside
    them. **A NEW data file, dataset, or wordlist goes HERE.**
  - `animations/{config.py, assets/, scenes/NN<name>.py}` — the RENDER side:
    scene code, visual assets, and per-scene render caches
    (`assets/<name>_data.py` + `<name>_cache.json` that a SCENE imports at render
    time). `assets/` is NOT a home for raw source data.
  - **Rule of thumb:** raw/pipeline data → `math/data/`; a small precomputed cache
    a scene reads at render → `animations/assets/`. When unsure, it's `math/`.
- Shared style: `bpkfigures/style.py` (`ACCENT_FILL`, `BG_COLOR`, `FONT`,
  `crisp_text`/`crisp_paragraph`). NB: battleship defines its own `BOARD_FILL`.

## Canonical patterns index — BEFORE you hand-roll, check here
A quick lookup of the recurring visual jobs and the ONE shared thing each goes
through. If you're about to place, `.scale()`, or animate one of these BY HAND,
stop and use the listed helper — hand-rolling is exactly how conventions drift
(three scenes ended up with three different two-card positions before this index
existed; a scaled-down two-card layout and a wrong-style number readout shipped
in scene 04 because the convention lived only in other scenes, uncallable). The
detail for each row is in the section/asset named; this is just the "where do I
look" map.

- **Any on-screen text** → `crisp_text` / `crisp_paragraph` (style.py). Never a
  raw `Text(...)`. (§ Shared visual vocabulary.)
- **Any colour** → a name from `style.py` (ACCENT_FILL/GOLD/CATEGORICAL…) or the
  video's `config.py` (semantic score green/red). Never a one-off hex. (§ Shared
  visual vocabulary.)
- **A free-floating panel/table/plot** → sit it on a card: `get_card` /
  `card_behind` (card.py). Not a raw RoundedRectangle.
- **Spotlight element(s)** → `highlight()` (highlight.py, holds by default).
  **Emphasise one OF a group** → dim the rest (save_state/Restore; scenes 07/08).
- **A frame-edge position** → read `config.frame_x_radius/​y_radius` (8.0 / 4.5)
  at runtime. Never hardcode / recall 7.11/4.0.
- **Every `run_time`** → an inlined literal at the call site (named local only for
  a lockstep loop). (§ Scene structure.)
- **Any displayed number** → SOURCED from the pipeline (data module + committed
  cache), never computed at render. (§ The numbers are the product.)
- **A prop's entrance / exit / flash / a multi-prop layout** → the existing asset
  method other scenes already use — GREP the scenes before hand-rolling. Reusable
  motions belong in the asset, not a scene. (§ Reuse over reinvention.) Yahtzee
  reference implementations: single scorecard enters with `Scorecard.slide_in`;
  **two scorecards side-by-side use `get_two_scorecards` + `slide_two_in`** (full
  size, canonical centres, slide up from below — never `.scale()`/hand-place; ref
  scenes 04/05/12); demo fill flash = `Scorecard.flash_rows`; row emphasis =
  `Scorecard.highlight_rows`; dice keep/reroll = `DiceBoard.keep`/`roll_rest` +
  `show_keep_anims`/`regroup_anims`; a big right-side number + caption beside a
  left-sat card follows scene 05's `perfect_average` (caption above, big number
  below — a promote candidate, not yet a shared helper).

**When a job ISN'T listed and you catch yourself copying from another scene, that
IS the signal** — grep the scenes, then PROMOTE the pattern into the shared asset
(see "a recurring ENTRANCE/EXIT/emphasis is an asset too") and add a row here.
Each video also keeps its own prop-specific index in its own CLAUDE.md.

## Shared visual vocabulary — USE THESE, don't hand-pick (read before styling)
Keep every video visually consistent by pulling colours and surfaces from the
shared package instead of inventing ad-hoc hex values:
- **The frame is 16 wide × 9 tall (units), NOT manim's default 14.22 × 8.** Every
  video's `manim.cfg` (both `animations/` and `animations/scenes/`) sets
  `frame_width = 16`, `frame_height = 9` — and `/new-video` scaffolds the same — so
  the useful half-extents are **x-radius 8.0, y-radius 4.5** (left edge −8.0, top
  edge +4.5). When positioning against the frame, READ them at runtime
  (`from manim import config; config.frame_x_radius / config.frame_y_radius`) — do
  NOT hardcode or assume manim's default 7.11/4.0. Assuming the default (from
  memory, because 16:9 renders "look" standard — the aspect IS 16:9, only the unit
  size differs) made every margin/centring calc in scene 06 wrong and cost a huge
  number of rounds. If a layout calc needs a frame bound, the bound comes from
  `config`, never from your head.
- **Colours come from `style.py`, picked in a fixed hierarchy** (the canonical
  version, with rationale, is the header block in `style.py` — read it before
  styling):
  1. **Primary** `ACCENT_FILL` (deep blue) — data/bars/fills; a one-colour scene
     uses this.
  2. **Highlight** `ACCENT_GOLD` — the "notice this" accent (highlights, medians,
     peaks, the emphasised element). Reserve it for that; don't spend gold as a
     generic categorical fill when the scene also needs a highlight colour.
  3. **Categorical** — when several colours must differ AT ONCE, pull from
     `CATEGORICAL_PALETTE` in order (warm `ACCENT_GOLD`/`ACCENT_ORANGE`/`ACCENT_RED`,
     then cool `ACCENT_GREEN`/`ACCENT_PURPLE`/`ACCENT_PINK`). No fixed meaning.
  - **Semantic score/status colours are NOT accents:** points = green, zeroed/loss
    = red live in the *video's* `config.py` (e.g. yahtzee `SCORE_GREEN`/`SCORE_RED`),
    deliberately darker — don't reuse `ACCENT_GREEN`/`ACCENT_RED` for "good/bad".
  - Reuse these; do NOT introduce new one-off hex colours unless the user asks. If
    a new shade is genuinely needed, add it to `style.py` (so it's reusable) rather
    than burying it in a scene.
- **ALL text goes through `crisp_text` / `crisp_paragraph`** (from `style.py`) —
  never a raw `Text(...)`. They render at the brand `FONT` (they now default it,
  so you can't forget) and supersample for crispness. Match a neighbouring
  element's `font_size`/`color` rather than inventing values; a number that sits
  in an asset (e.g. a scorecard cell) must use that asset's `font_size` and
  colour, not your own. Symptom this prevents: text rendered in manim's built-in
  font because a hand-built `Text` (or an old `crisp_text` call) omitted the font
  — it looks subtly wrong next to everything else. If you catch yourself styling
  text from scratch, stop and pull the size/colour/font from `style.py` (or the
  asset you're drawing into).
- **Panels sit on a card.** Use `bpkfigures/card.py` (`get_card` / `card_behind`)
  for the standard rounded surface (matches the scorecard look) — prefer it over
  a raw `RoundedRectangle`. Lean toward putting free-floating text/tables/plots
  on a card rather than straight on the background.
- **To spotlight specific element(s), use the shared `highlight()`; don't
  hand-roll it per scene.** `bpkfigures/highlight.py`'s `highlight(scene,
  targets, …)` fades a tinted (`ACCENT_GOLD`) overlay onto the targets, HOLDS it
  (default ~1 s), then fades out. It's exported through `from config import *`.
  Targets are Mobjects (their bounding box) or `(center, w, h)` regions (for a
  span no single mobject covers). **Default to HOLD, not a flash** — a held
  highlight reads far better; the user's near-universal preference is "let it sit
  for a second or two." Only pass `pulse=True` when you specifically want a
  there-and-back flash (e.g. a highlight that WALKS across rows with `lag_ratio`);
  `persist=True` fades in and leaves it (caller removes the returned rects). The
  scorecard's richer row version (`Scorecard.highlight_rows`, adds a thick border
  + bold label) follows the same rule: holds by default, `pulse=True` to walk.
  Do NOT write bespoke `FadeIn(rect, rate_func=there_and_back)` highlight code in
  a scene — reach for `highlight()`.
- **Emphasise by DIMMING THE REST, not just bolding the focus.** To spotlight
  element(s) in a group (lines in a chart, rows in a bar graph, items in a list),
  fade every OTHER member to ~0.2 opacity while the focused one(s) stay full — the
  dimmed field makes the focus pop far better than only bolding/recolouring it.
  `save_state()` each element before dimming and `Restore` after, so each keeps
  its own original opacity (e.g. a 0.85-tint bar comes back to 0.85, not 1.0). Now
  the house move in scenes 07 (bar-graph rows) and 08 (lines). (Dimming-the-rest
  and `highlight()`-the-target are complementary: dim when emphasising one OF a
  group; overlay when calling out element(s) against an un-dimmed field.)
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
- **A `@subscene` BODY should read as ANIMATION — push construction into
  `_setup_<name>()`.** The subscene calls `self._setup_<name>()` at its top to
  build every mobject it OWNS (cards, tables, labels, example states, props),
  then the body is just `self.play(...)` / `self.wait(...)` with each `run_time`
  as a local variable — so the user can retune timing without wading through
  construction. If it can go in setup, it should. Only THREE kinds of code
  legitimately stay in the body: (1) offscreen ENTRANCE positioning that depends
  on the carried-in geometry (build at home in setup, then `shift` offscreen and
  animate back in the body); (2) un-picklable animation machinery (`always_redraw`
  / `ValueTracker` counters — they can't live in a snapshot); (3) construction
  whose geometry only exists AFTER an earlier play in the same subscene. Building
  a mobject inline right next to its `play()` "because it's small" is the habit to
  break — extract it. `scenes/05reductions.py` is the current model of this shape;
  older scenes (02, 04, 07) still build inline and can be migrated when touched.
  (They never rebuild a carried-over object — see carry-over above.)
- **Subscene continuity:** a subscene starts from the previous one's END state.
  Anything not on screen at the end of the previous subscene must be ANIMATED IN
  at the start of the next (don't silently `add` — it pops). Things appearing
  together should animate in together.
- **How a scene ENDS depends on what follows it in the script.** If a scene is NOT
  immediately followed by a talking-head segment (`THA`–`THL`) — i.e. it cuts
  straight to the next animated scene — its last subscene must end with NOTHING on
  screen (fade/clear everything out), so animated scenes never hard-cut between two
  full frames. If a scene IS followed by a talking head, it may end with its final
  content still on screen (the talking head covers the transition) — often the
  right call is to restore any mid-scene emphasis (dimmed/hidden elements) to the
  full, clean end state. Check the script's segment order to know which case
  applies.
- **Every subscene is auto-framed by a static hold — do NOT add your own start/end
  wait.** `scene.py` plays one leading `self.wait(SUBSCENE_HOLD)` at the very start
  of a render plus one trailing hold after each subscene (`SUBSCENE_HOLD = 1.0s`).
  So a single-subscene render is `HOLD·sub·HOLD` (a standalone clip padded 1s each
  side, handy for editing) and a full-scene render is `HOLD·a·HOLD·b·…·N·HOLD` — a
  SINGLE shared 1s pause between adjacent subscenes, not two. The framework OWNS the
  boundary holds; a subscene body must NOT begin or end with a `self.wait(...)` (it
  would stack on the framework's hold / double the between-subscene pause). Waits in
  the MIDDLE of a subscene (pacing between its own steps) are fine and expected.
- **Every animation/wait's `run_time` is an explicit NUMBER inlined in the call —
  do NOT bind it to a one-use local first.** Write `self.play(…, run_time=1.2)`,
  NOT `rt = 1.2` … `run_time=rt`. The intermediate variable is pure indirection:
  the literal is already right there in the body (that's the point — the user sees
  and tweaks it in place), so naming it just adds a line to read past. Pass an
  explicit `run_time=` to every `self.play(...)` (don't rely on manim's default
  1.0); `self.wait(t)` already shows its duration. If a subscene calls a HELPER
  that plays animations (e.g. `_grow_step`, or a local `roll()`/`count_in()`
  closure), give that HELPER a `run_time` PARAMETER and pass the LITERAL at the
  call site — never bury a hardcoded run_time inside a helper where it can't be
  reached. (The ONE case a named local is fine: the SAME value must drive several
  plays in lockstep — e.g. a loop whose every step is the same length — where the
  name keeps them in sync. A value used once is always inlined.)
- **A DENSE, multi-phase subscene → split each phase into a private helper that
  takes its `run_time`s as PARAMETERS, so the BODY reads as a timeline of
  `self._phase(1.0)` calls.** The inline-literal rule above is the default and
  stays that way for a SIMPLE subscene (little around each `self.play`, so nothing
  to hunt for). But when a body grows long — many phases interleaved with
  `ValueTracker`/`always_redraw`/closure machinery that can't move to `_setup`
  (yahtzee scene 01's `grand_total`/1j is the motivating case: ~120 lines, and the
  `run_time` knobs you actually edit are scattered through the machinery) — pull
  each phase into a helper and let the subscene body become a short score:
  `self._gt_count_up(2.2)` / `self._gt_cull(1.0)` / …, one line per beat. This is
  NOT a competing convention: each `run_time` is still a call-site LITERAL (so the
  no-one-use-local rule holds), and the method NAME labels which animation it
  drives — so, unlike a top-of-body `t_cull = 1.0` timing block, there's no
  name→play lookup to maintain (that indirection is exactly what makes such a block
  hard to edit). Every knob is visible in one screen; the dense machinery hides in
  the helpers. Caveat: this is a BUILD-TIME pattern — clean when you write the scene
  phase-by-phase from the start, fiddly and render-risky to RETROFIT onto a working
  scene (phases share live state — an `always_redraw` built in one phase is removed
  in a later one — so retrofitting means threading that state across helpers without
  perturbing the render). So adopt it when building; don't refactor existing scenes
  into it just for tidiness.
- **Do NOT put timing (or any tunable) on the @subscene method's own signature.**
  Subscenes are invoked with NO arguments (`getattr(self, name)()` in `scene.py`),
  so a `def beat(self, run_time=3.0)` param is NEVER overridden — it's a dead,
  misleading "knob" that looks callable but isn't. Put the number in the BODY,
  inlined in the call: `def beat(self):` … `self.play(…, run_time=3.0)`. "Expose at
  the subscene level" means in the subscene's BODY, not its signature — the
  signature of an `@subscene` is always just `(self)`.

## Reuse over reinvention
- Read the existing assets and a reference scene (e.g. yahtzee `99test.py`)
  BEFORE building a gameplay-style beat. Use the existing helpers.
- **A recurring ENTRANCE/EXIT/emphasis is an asset too — grep other scenes before
  hand-rolling one.** Bringing a shared prop on screen (the scorecard, a card, a
  board), flashing a cell, filling a box: if you're about to write the animation
  inline, first grep the OTHER scenes for how they do it. If it's already
  consistent, call the same thing; if several scenes each reinvent it, that's the
  signal to PROMOTE it to a shared method and use it everywhere. Concretely: the
  scorecard entrance was hand-written three different ways across scenes until it
  became `Scorecard.slide_in`; the synced red/green "demo fill" flash is
  `Scorecard.flash_rows`. Prefer these over re-deriving the motion. "It's just a
  FadeIn" is exactly the thought that produces four different entrances.
- **Read assets to CALL them, not just to imitate their look.** The reference
  scene shows *which methods do the work*: a keep/reroll beat IS `DiceBoard.keep`
  + `roll_rest` (exactly what `99test.py` shows), not hand-placed coordinates.
  Before a gameplay beat, name the exact asset method each sub-beat calls, and
  trace the dice/card state through it (which boxes are open, where each die
  sits). If you're re-deriving something an asset already provides, stop and call
  the asset — reading code only to copy its *look* is how reinvention, and
  "wrong-box"/"wrong-dice" mistakes, sneak in.
- **Check the ASSET *and* the reference SCENES before hand-rolling a gameplay
  motion — a reusable primitive may live in a scene, not the asset.** The dice
  "keep-illustration" convention (push a keep forward, reroll dice to the right,
  band-per-reroll) existed only as scene 04's private `_show_keep`, so it was
  invisible when building scene 06 — which reinvented it wrong. So: (a) grep the
  scenes, not just the asset, for an existing helper; and (b) **when a gameplay/
  animation motion is reusable, it belongs in the shared asset, not a scene.** If
  you catch yourself writing a scene-private helper another scene would want (or
  you find one already buried in a scene), PROMOTE it to the asset (with the
  convention documented) and flag it — don't leave a convention where the next
  scene can't find it. Hand-rolling a motion an asset/scene already does is itself
  the red flag that a shared primitive is missing.
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
- `render 01 sub --padded` writes, beside each rendered mp4, a copy with its FIRST
  frame frozen at the head and LAST frame frozen at the tail (default 10s/side;
  `--padded 3` = 3s) into a `padded_videos/` tree mirroring `videos/` — an editing
  aid (handles around each subscene). Composes: `--padded --extract` pads an EXISTING
  mp4 with no re-render. Re-encodes (crf 18); renders are silent so no audio sync.
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
- **A scene-file MODULE CONSTANT changed between renders does NOT reliably
  invalidate the per-subscene digest.** The scene file is excluded from the
  project hash, and the digest keys on each subscene's code closure — NOT the
  runtime VALUES of module globals it reads. So tuning a top-of-file layout
  constant (`COL4_W`, `DICE_DX`, a position vector) can leave you rendering the
  OLD value straight from cache: the edit appears to do nothing (or something
  contradictory), and you "verify" a STALE frame as if it reflected the change.
  When iterating on layout/positioning driven by such constants, render with
  `--recompute` (or bump `SNAPSHOT_VERSION`). This burned many scene-06 rounds —
  frames judged "correct" were pre-edit output.
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
- **Every spatial/quantitative claim carries its SOURCE inline — the printed
  number you pulled, or the explicit words "eyeballed, not verified."** A bare
  spatial claim with no number ("margins look even", "it's centred") is itself the
  violation: the missing number is the tell that you LOOKED instead of measured.
  This is the enforceable core of measure-don't-eyeball — it makes "did you
  actually measure?" visible in the handoff, where the user can catch it. Two ways
  a "measurement" is really a guess (both shipped WRONG in scene 06): (a) squinting
  at a 480p thumbnail — that's "I looked," not "I measured"; MEASURE means real
  coordinates (`get_left/right/top/bottom/center` via a one-off `print`, removed
  after), because margins/centering/fit read deceptively at low res; (b) reading
  true coords but comparing them to a MADE-UP constant (frame bounds recalled as
  7.11/4.0 instead of the real 8.0/4.5) — a correct ruler at the wrong zero
  "confirms" nonsense, so any constant a claim rests on must be READ from
  config/source, not recalled. And NEVER pronounce how something LOOKS as
  fine/correct — show the user and let them judge; objective = a number you
  measured, not an impression.
- **A conclusion that contradicts what the render plainly shows means a wrong
  ASSUMPTION — STOP and find it, don't assert past it.** Claiming "the card is
  taller than the frame" while the frame clearly shows the whole card with margins
  is impossible; the impossibility is the signal that an input (here, the frame
  size) is wrong. When your numbers and the picture disagree, one of your inputs is
  false — hunt it down before making any more edits, rather than repeating the
  claim with more confidence.
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
- **Manim gotchas that each cost real render round-trips (scene 05):**
  - **`mob.animate(rate_func=…).set_value(…)` — the CALL form — silently fails to
    animate a `ValueTracker` inside a multi-animation `play()`.** The tracker just
    doesn't move (reads as a jump at the very end). Use plain
    `mob.animate.set_value(…)`; put the rate_func on the `play()` if you need one.
  - **Two separate `ValueTracker`s driving ONE visual desync.** If a number's
    VALUE is on one tracker and its POSITION/SCALE on another, the motion finishes
    while the value lags (looks like it jumps, then moves). Drive linked
    properties from ONE tracker (value = `lerp(v0, v1, t)`, pos/scale from the same
    `t`).
  - **`scene.remove(submobject)` restructures the submobject's PARENT group** (it
    detaches it, with side effects, and can leave the parent group itself behind).
    Only `remove()` TOP-LEVEL mobjects; to drop an in-group text, rebuild the group
    or hard-clear everything (`for m in list(self.mobjects): self.remove(m)`).

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
- **The thing that forces a `render`/pipe to prompt is a REDIRECTION, not the
  pipe (verified).** `render *`, `tail *`, `grep *`, `head *` are all allowlisted
  and rules match per-subcommand, so `render … | tail -3` and `render … --frames
  … | tail` AUTO-APPROVE. But append `2>/dev/null` (or any `>`/`2>`/`>>`) and the
  WHOLE line prompts every time — a redirection can write a file, so the matcher
  bails regardless of the target (even `/dev/null`). So: pipe freely to
  `tail`/`grep`/`head`, but NEVER add `2>/dev/null` to a command you want
  auto-approved. (For a foreground `render … --frames …`, you don't even need the
  pipe — the frame-PNG paths are deterministic; just Read them by path.)
- **For a BACKGROUND render, READ the task's `.output` file with the Read tool**
  rather than shelling out to inspect it. Don't build `cd … && render … > log; grep`
  chains (the `> log` redirect prompts) or `until grep …; do sleep; done` poll
  loops — the harness notifies on completion.
  - **Confirm the cwd is `scenes/` before firing a background render.** The Bash
    cwd persists across calls, so a `cd <repo-root>` done for a git commit leaves
    you at the repo root; a later `render NN` then fails silently-ish with "No file
    matching NN*.py" (the error is only in `.output`, so you don't see it until you
    read the file). After any git work, `cd` back to `scenes/` in its own call
    first. **This happens even when you NEVER `cd` for git** — running `git -C
    <repo> …` standalone (or just having a background task in between) still leaves
    the next background `render` launching from the repo root. So don't reason "I
    used `git -C`, so my cwd is safe": treat ANY git command as having reset the
    cwd, and re-`cd scenes/` (its own call) immediately before EVERY background
    render batch that follows git. (Cost ~3 failed renders in one session.)
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
- **Commit at each working checkpoint — do NOT batch a multi-step change into one
  big commit at the end.** The user prefers frequent, granular commits (one per
  working step that leaves the code in a good state) over a single squashed
  commit. When a change lands in several iterations, commit each as it works,
  staging only that step's files by explicit path.
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
  (5) **each on-screen element → the shared helper/value it renders through — a
  STYLING pass, not just a content one.** Before writing an element, name what it
  comes from: text → `crisp_text` (defaults to `FONT`; still give it the right
  `font_size`/`color`), never a raw `Text` or ad-hoc size; colours → the specific
  `style.py` / video-`config.py` name (semantic score green/red, the gold
  highlight, `ACCENT_FILL`…), never a hand-picked hex or manim default; a prop's
  ENTRANCE or a box fill/flash → the existing asset method other scenes use
  (`Scorecard.slide_in`, `flash_rows`, the dice helpers), never a hand-rolled
  FadeIn/opacity. A cell you can't map to a shared helper is the flag to STOP and
  find it (or ask). **Re-run this pass at handoff:** on a verification frame,
  actively read the STYLING — is the text in `FONT`? are highlights/colours the
  semantic ones? do reused props (dice, scorecard) render as they do elsewhere? —
  not just position/overlap. (This exists because a scene built "from scratch"
  shipped wrong fonts, wrong-count dice pips, and off-palette highlights that all
  had to be corrected in review — the conventions were documented; the miss was
  not checking each element against them, up front AND on the render.)
- **Beats within a scene are delimited by a literal `---` in BOTH columns — split
  on it to recover the beat↔voiceover↔animation mapping.** `Script.md` is a
  2-column Google-Doc table exported to Markdown, and that export FLATTENS each
  cell to ONE space-joined line (no `<br>`/newlines), which would otherwise leave a
  scene's voiceover and animation as two run-on blobs with all beat boundaries
  lost. The user separates beats with `---` in EACH cell; parse a scene by
  splitting BOTH cells on `---` and zipping them, so segment *i* of the voiceover
  pairs with segment *i* of the animation = one beat = one subscene (order a, b,
  c…). If segments are letter-tagged (e.g. `a)` … `b)` …), pair by the tag instead
  of by position. This is what makes items (3)/(4) above actually possible.
- **If a multi-beat scene's row has NO `---` delimiters, STOP and ASK the user to
  add them before building — do NOT guess the beat boundaries.** Without them the
  mapping is unrecoverable from the flattened export (the root cause of the beat-h
  mess). A genuinely single-beat scene needs none; the trigger is several beats'
  worth of content crammed into one run-on cell. Watch too for a MISMATCHED count
  of `---` between the two columns (an empty beat should still be an empty segment,
  e.g. `… --- (no change) --- …`) — a mismatch silently shifts the pairing, so
  flag it rather than zipping blindly.
- **A beat with an EMPTY animation column (voiceover-only) gets NO subscene.**
  When column 2 for a beat is blank (just narration, nothing to show), do NOT
  create a do-nothing subscene that only `self.wait`s — its voiceover simply
  plays over the neighbouring beats' framework holds. Still COUNT it when zipping
  the columns (so later beats stay aligned), but skip it when emitting subscenes.
  Removing a subscene shifts every LATER subscene's letter, which orphans the
  old highest-letter video (`resolve --clean` only cleans the slot of a letter
  you actually render, so the now-out-of-range last letter never gets swept) —
  delete that orphaned `NN<letter>_*.mp4` by hand after the change.
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
- **When an iteration changes WHAT'S DEPICTED — a game/card STATE, a value, which
  box is filled vs. open — RE-READ that beat's `Script.md` row FIRST.** Timing,
  layout, and colour polish can be reasoned from the code, but a change to the
  depicted state must be checked against the script, because such a detail is
  often the POINT of the beat, not a free cosmetic choice. The failure mode: deep
  in polish you stop consulting the script and reason LOCALLY from the scene's
  constants ("opening this box makes the highlight read better"), silently
  breaking the beat's meaning. (Scene 11 c: col 2 says "everything filled except
  yahtzee and small straight," so Ones is FULL — highlighting the *used* Ones box
  red is the whole lesson; opening Ones to tidy the score bar broke it.) The build
  PREFLIGHT reads column 1+2 for every beat; this keeps that grounding alive
  through the ITERATION passes, where it tends to lapse.
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
