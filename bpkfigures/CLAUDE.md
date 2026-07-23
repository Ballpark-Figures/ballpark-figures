# Ballpark-Figures — shared animation conventions

Cross-video rules for all videos in this repo (`battleship/`, `yahtzee/`, …).
`bpkfigures/` is the shared package every video imports, so these conventions
load wherever you're working. Video-specific rules live in that video's own
`CLAUDE.md` (e.g. `yahtzee/CLAUDE.md`).

## Following instructions (read this first)
- **Do what the user explicitly asked, in the form they asked for.** When they
  name a file, format, or method ("put it in a CLAUDE.md", "use a tail flag"),
  that exact choice IS the spec — not a suggestion to improve on with your own
  judgment. Implement it literally ("disappear" ≠ "fade", "centered" =
  measure-and-center).
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
  `bpkfigures/` package; each video is its own nested git repo.
- Each video has TWO sides — know which one a file belongs to:
  - `math/` — the DATA/COMPUTATION pipeline: `math/data/` (source data, solver
    outputs, datasets, wordlists — tracked + synced), `math/notebooks/` (Jupyter),
    plus solver/helper modules. **A NEW data file/dataset/wordlist goes HERE.**
  - `animations/{config.py, assets/, scenes/NN<name>.py}` — the RENDER side: scene
    code, visual assets, per-scene render caches (`assets/<name>_data.py` +
    `<name>_cache.json`). `assets/` is NOT a home for raw source data.
  - **Rule of thumb:** raw/pipeline data → `math/data/`; a small render-time cache →
    `animations/assets/`. When unsure, `math/`.
- `footage/` and `music/` (video root) — the non-manim clips (talking heads, b-roll,
  e.g. yahtzee's THA–THL) and background audio cut into the final edit. Both gitignore
  their binaries (`*.mp4`/`*.mov`/`*.mp3`/`*.wav`), tracking only the folder + README
  (local, not synced); `/new-video` scaffolds them.
- **Finishing & publishing** (assemble in DaVinci → export `.mov` → YouTube) is the
  post-`manim` pipeline — see `bpkfigures/PUBLISHING.md`. **Set the DaVinci project fps
  + resolution to match the video's `manim.cfg` BEFORE importing any media** (1920×1080,
  Yahtzee 60 / Battleship 30) — DaVinci locks timeline fps once media is imported, and a
  mismatch is a painful migration. Deliverable: `<Video>.mov` at the repo root (H.264,
  1080p, timeline fps), gitignored; a `.drp` is a Resolve backup, never uploaded.
- Shared style: `bpkfigures/style.py` (`ACCENT_FILL`, `BG_COLOR`, `FONT`,
  `crisp_text`/`crisp_paragraph`). NB battleship defines its own `BOARD_FILL`.
- **Reserved scene-number slots (2-DIGIT prefixes — `resolve` slices `target[:2]`, so
  1/3-digit prefixes break subscene addressing).** `01`,`02`,… are content scenes; two
  META-files bookend them, each a normal `BpkScene` subclass:
  - **`00` = transitions** (`00transitions.py`, `class Transitions`) — part-title cards
    between scene groups: ONE `@subscene` per Part, a two-line card (`Part N` / title)
    that starts on screen, holds, then LEAVES to reveal blank bg. Text built under the
    ~24 crisp_text wrap threshold and `.scale()`d up so a long title never breaks.
    Yahtzee is the reference.
  - **`99` = thumbnails** (`99thumbnails.py`) — one **`@thumbnail`** each (NOT
    `@subscene`), a STATIC composition (`self.add`, no `self.play`) modelled on
    battleship's `00thumbnail.py` (bold black number/title + a prop, gradient bg, bold
    digit stroke to survive YouTube's JPEG pass) in brand `FONT`; keep the video's
    normal base (`class Thumbnails(YahtzeeScene)`) for `BG_COLOR`. **Why `@thumbnail`:**
    same `99a`/`99b` addressing, but the framework renders each from a CLEAN frame — no
    snapshot carry-over (would GHOST the prior thumbnail) and no save/replay. **Render
    with `render 99a`** (scene `99` auto-detects still mode → manim `-s -qk` 4K PNG under
    `media/images/**/`; `--fast` for a quick check). Numbers are still SOURCED. Yahtzee
    is the reference.
  - Tests/scratch take `98` and DOWN so they never collide with the meta-files.

## Canonical patterns index — BEFORE you hand-roll, check here
The recurring visual jobs and the ONE shared thing each routes through. About to
place, `.scale()`, or animate one of these BY HAND? Stop and use the listed helper —
hand-rolling is how conventions drift. Detail is in the named section/asset; this is
the "where do I look" map.

- **Any on-screen text** → `crisp_text`/`crisp_paragraph` (style.py). Never raw
  `Text(...)`. (§ Shared visual vocabulary.)
- **Any colour** → a `style.py` name (ACCENT_FILL/GOLD/CATEGORICAL…) or the video's
  `config.py` (semantic score green/red). Never a one-off hex. (§ Shared visual
  vocabulary.)
- **A free-floating panel/table/plot** → sit it on a card: `get_card`/`card_behind`
  (card.py). Not a raw RoundedRectangle.
- **Spotlight element(s)** → `highlight()` (highlight.py, holds by default).
  **Emphasise one OF a group** → dim the rest (save_state/Restore; scenes 07/08).
- **A frame-edge position** → read `config.frame_x_radius/​y_radius` (8.0/4.5) at
  runtime. Never hardcode/recall 7.11/4.0.
- **Every `run_time`** → an inlined literal at the call site (named local only for a
  lockstep loop). (§ Scene structure.)
- **Any displayed number** → SOURCED from the pipeline (data module + committed cache),
  never computed at render. (§ The numbers are the product.)
- **A prop's entrance/exit/flash / multi-prop layout** → the existing asset method
  other scenes use — GREP the scenes first; reusable motions belong in the asset. (§
  Reuse over reinvention.) Yahtzee: single scorecard `Scorecard.slide_in`; **two
  side-by-side `get_two_scorecards` + `slide_two_in`** (full size, canonical centres —
  never `.scale()`/hand-place; scenes 04/05/12); demo flash `Scorecard.flash_rows`; row
  emphasis `Scorecard.highlight_rows`; dice keep/reroll `DiceBoard.keep`/`roll_rest` +
  `show_keep_anims`/`regroup_anims`; a big right-side number + caption beside a left-sat
  card follows scene 05's `perfect_average` (caption above, number below — a promote
  candidate).

**A job that ISN'T listed and you're copying from another scene IS the signal** — grep,
PROMOTE the pattern into the shared asset, add a row here. Each video keeps its own
prop-specific index too.

## Shared visual vocabulary — USE THESE, don't hand-pick (read before styling)
Pull colours and surfaces from the shared package instead of inventing ad-hoc values:
- **The frame is 16 wide × 9 tall, NOT manim's default 14.22 × 8.** Every video's
  `manim.cfg` sets `frame_width=16`/`frame_height=9` (and `/new-video` scaffolds the
  same), so the half-extents are **x-radius 8.0, y-radius 4.5**. READ them at runtime
  (`config.frame_x_radius`/`frame_y_radius`) — do NOT assume manim's default 7.11/4.0
  (16:9 renders look standard, but the unit size differs, so a recalled default silently
  makes every margin calc wrong). A frame bound comes from `config`, never your head.
- **Colours come from `style.py`, in a fixed hierarchy** (canonical version + rationale
  in `style.py`'s header block):
  1. **Primary** `ACCENT_FILL` (deep blue) — data/bars/fills; a one-colour scene uses this.
  2. **Highlight** `ACCENT_GOLD` — the "notice this" accent (highlights, medians, peaks).
     Reserve it; don't spend gold as a generic categorical fill.
  3. **Categorical** — several colours at once: pull `CATEGORICAL_PALETTE` in order (warm
     GOLD/ORANGE/RED, then cool GREEN/PURPLE/PINK). No fixed meaning.
  - **Semantic score colours are NOT accents:** points=green, zeroed/loss=red live in the
    *video's* `config.py` (`SCORE_GREEN`/`SCORE_RED`, deliberately darker) — don't reuse
    `ACCENT_GREEN`/`ACCENT_RED` for good/bad.
  - Don't introduce one-off hex unless asked; a genuinely new shade goes in `style.py`,
    not buried in a scene.
- **ALL text goes through `crisp_text`/`crisp_paragraph`** — never raw `Text(...)`. They
  render at brand `FONT` (defaulted now) and supersample. Match a neighbouring element's
  `font_size`/`color`; a number in an asset (e.g. a scorecard cell) uses that asset's
  size/colour, not your own. (Symptom this prevents: text in manim's built-in font
  because a hand-built `Text` omitted the font — subtly wrong next to everything.)
- **Panels sit on a card** — `get_card`/`card_behind` (`bpkfigures/card.py`) for the
  standard rounded surface, over a raw `RoundedRectangle`.
- **To spotlight element(s), use the shared `highlight()`** (`bpkfigures/highlight.py`,
  exported via `from config import *`): fades a tinted (`ACCENT_GOLD`) overlay onto the
  targets, HOLDS ~1s, fades out. Targets are Mobjects or `(center, w, h)` regions.
  **Default to HOLD, not a flash** (the user's near-universal preference); `pulse=True`
  for a there-and-back flash (e.g. a highlight that WALKS across rows), `persist=True` to
  fade in and leave it. `Scorecard.highlight_rows` (thick border + bold label) follows
  the same hold-by-default rule. Don't hand-roll `FadeIn(rect, rate_func=there_and_back)`.
- **Emphasise by DIMMING THE REST, not just bolding the focus.** To spotlight element(s)
  in a group (chart lines, bar rows, list items), fade every OTHER member to ~0.2 opacity
  while the focus stays full. `save_state()` each before dimming, `Restore` after, so each
  returns to its own opacity (a 0.85-tint bar comes back to 0.85). The house move in
  scenes 07/08. (Complementary to `highlight()`: dim when emphasising one OF a group;
  overlay against an un-dimmed field.)
- Changing these shared defaults still follows the "ASK before editing `bpkfigures/`" rule.
- You can reference any video's files on disk even if not in the workspace — "Do this
  like the Battleship video" always works.

## New video / new machine
Use `/new-video <name>` to scaffold a new video, and `/sync-videos` to set up a
second machine. The operational specifics (account, machine layout, private-repo
mechanics) live in the private companion file that auto-loads alongside this one
via the import below (a symlink to the `dotclaude` repo; absent → notes skipped):

@CLAUDE.private.md

## Concurrent sessions — one shared branch (NOT per-scene branches)
The user works several scenes at once as **multiple chat tabs in ONE VSCode window**.
The extension CANNOT scope a tab to its own folder — every tab shares the window's
working directory, hence ONE branch. Per-scene branches are fundamentally incompatible (a
tab switching branches yanks the others' files and any in-flight render — real breakage
here: a render used another branch's older scene file, a mid-render switch crashed a
snapshot save).
- **Keep ALL concurrent work on ONE shared branch — `main`.** Different scenes are
  different files, so tabs don't collide; do NOT create `scene-NN-*` branches.
- **The one habit that makes this safe: stage by EXPLICIT PATH** — `git add
  animations/scenes/NN<name>.py`, never `git add -A`/`.`. The shared working tree means a
  bulk add sweeps EVERY tab's in-progress files into one commit; commit only the file(s)
  that tab changed.
- **Shared resources** (`bpkfigures/`, `config.py`, `assets/`): don't have two tabs
  editing the SAME shared file at once — sequence those. (Editing a shared file while
  another tab merely renders is fine.)
- Per-scene branches ARE possible but ONLY via git worktrees in SEPARATE windows — more
  window management than the user wants, so reach for it only if truly isolated branches
  are needed.

## Where instructions live (which CLAUDE.md, and CLAUDE.md vs memory)
How the user wants the agent to record things worth remembering:
- **General/cross-video preferences go in `bpkfigures/CLAUDE.md` (this file), NOT a
  video's.** Anything about how the agent works in general — conduct, workflow, tooling,
  process, instruction-following — belongs here so it loads for every video; a video's
  own `CLAUDE.md` is ONLY for rules specific to THAT video (script, layout, assets). When
  unsure, treat it as general and put it here.
- **Be PROACTIVE about recording a video's conventions in its CLAUDE.md as they emerge —
  don't wait to be told.** The moment a reusable decision crystallizes (a recurring
  layout/colour/naming/helper pattern, a "we always do X for this prop," an ambiguity the
  user just resolved that the next scene will hit), capture it — in that video's
  `CLAUDE.md` if specific to it, or here if general. The tell: you just GREPPED another
  scene to copy how it did something, or the user clarified a choice that ISN'T a
  one-off. Record the video-specific factual ones proactively and say you did; for a new
  BEHAVIOURAL rule, propose the text and ASK first (§ Following instructions). Either way
  SURFACE it in the moment — else the convention lives only in one scene's code and the
  next scene re-breaks it.
- **Default to CLAUDE.md** for anything the user wants the agent to know: loaded every
  session and synced across machines via git — unlike memory, which is local to one
  machine and only surfaces via recall. When unsure where something goes, don't
  deliberate — put it in CLAUDE.md and say so.
- **Use memory ONLY for facts that genuinely can't be committed** (private URLs,
  credentials) AND that have a clear, nameable trigger for the memory's `description` so
  recall fires. If it's private but its trigger is fuzzy, don't silently rely on memory —
  say so and ask the user to re-mention it when it comes up.
- The public GitHub repo intentionally shows how the user works, so workflow/preference
  content in committed CLAUDE.md is fine — reliable loading beats repo cleanliness.
- **Never write the user's real name (or other personal identifiers) into any public-repo
  file** — `bpkfigures/` and the video repos are public; refer to "the user." Identity
  facts belong only in the private `dotclaude` repo (pulled in via `@CLAUDE.private.md`).

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
- **Build lazily, in the OWNER subscene — not up front in `setup_scene`.** Each
  subscene builds the mobjects it OWNS (the ones that first appear in it) as
  `self.<name>`, via a `_setup_<name>()` helper called at its start; `setup_scene`
  holds ONLY things on screen from frame 0 (often empty). Why: a snapshot pickles
  the whole scene state, so front-loading makes every snapshot heavy and makes any
  `setup_scene` edit invalidate EVERY subscene — lazy building keeps snapshots light
  and localizes invalidation to the owner subscene onward.
- **Carry-over is automatic — don't rebuild.** An object left in `self` is restored
  (same object + mutated state) when the next subscene loads the snapshot, so later
  subscenes just REFERENCE `self.<name>`. Rules: every reused object needs a `self.`
  handle; ONE owner per object (a second `self.foo = …` silently replaces the carried
  one — a real bug); drop a consumed carry-over (`self.foo = None`) to keep snapshots
  light.
- **A `@subscene` BODY should read as ANIMATION — push construction into
  `_setup_<name>()`** (called at the body's top to build every mobject it OWNS); the
  body is then just `self.play`/`self.wait`. If it can go in setup, it should. Only
  THREE kinds of code stay in the body: (1) offscreen ENTRANCE positioning that
  depends on carried-in geometry (build at home in setup, `shift` offscreen, animate
  back in the body); (2) a mobject carrying a LAMBDA updater (`always_redraw(lambda …)`
  / `.add_updater(lambda …)`) — the lambda can't be pickled (a BARE `ValueTracker`
  pickles fine → build in setup, attach the updater in the body); (3) construction
  whose geometry only exists AFTER an earlier play in the same subscene.
  `scenes/05reductions.py` is the model.
- **Subscene continuity:** a subscene starts from the previous one's END state.
  Anything not on screen at the previous subscene's end must be ANIMATED IN at the
  next one's start (don't silently `add` — it pops); things appearing together animate
  in together.
- **How a scene ENDS depends on what follows in the script.** If it cuts straight to
  another animated scene (NOT followed by a talking head `THA`–`THL`), the last
  subscene must end with NOTHING on screen (fade/clear out) so animated scenes never
  hard-cut between two full frames. If a talking head follows, it may end with content
  on screen (the head covers the transition) — usually restore any mid-scene emphasis
  (dimmed/hidden elements) to the clean end state. Check the script's segment order.
- **A transient annotation you ADD (footnote, callout, one-off caption) has a BOUNDED
  lifetime — fade it OUT by scene end (or when its context ends); don't leave it
  lingering into unrelated beats.** This holds even when the scene's PERSISTENT content
  (a card, a board) stays on through a following talking head — a one-off note isn't
  that content, so plan its exit when you add it. Default answer to "should this come
  out?" is YES, by scene end, unless the user says it stays.
- **Every subscene is auto-framed by a static hold — do NOT add your own start/end
  wait.** `scene.py` plays one leading `self.wait(SUBSCENE_HOLD=1.0s)` per render plus
  one trailing hold after each subscene (so adjacent subscenes share a SINGLE 1s pause,
  not two). A subscene body must NOT begin or end with `self.wait(...)` — it stacks on
  the framework's hold and doubles the pause. Mid-subscene pacing waits are fine.
- **Every `run_time` is an explicit NUMBER inlined at the call — not a one-use local.**
  Write `self.play(…, run_time=1.2)`, not `rt = 1.2` … `run_time=rt` (the point is the
  user tweaks the literal in place). Pass an explicit `run_time=` to every `self.play`
  (don't rely on manim's 1.0 default); a HELPER that plays takes a `run_time` PARAMETER
  passed the literal at the call site — never a hardcoded run_time buried where the
  caller can't reach it. The ONE exception: a named local for the lockstep case (the
  SAME value driving several same-length plays in sync).
- **Every animation WE author exposes a single `run_time` that scales the WHOLE
  animation.** Any method/closure we write that plays (scene helper, ASSET method,
  local `roll()`/`count_in()`) takes ONE `run_time` meaning the ENTIRE duration: when
  it fires several plays with holds between, compute `r = run_time / <default total>`
  once and scale EVERY sub-duration — each play AND each hold — by `r` (the scorecard
  scoring methods, `upper(run_time=1.7)` with internal `1.1·r`+`0.6·r`, are the model).
  Do NOT scale only some plays and leave holds fixed (a `fade`-only knob with a
  hardcoded `hold` does NOT scale the animation). Add a second timing knob only when a
  part genuinely needs to be independent, and say why; a knob named anything but
  `run_time` (`fade`/`dur`/`speed`/`t`) is the smell to fix.
- **Do NOT hide DISTINCT script beats in a `for` loop — UNROLL it, one explicit step
  per beat.** The moment iterations are different things the VOICEOVER walks through
  one at a time (three example turns, several cases), the loop's single shared
  `run_time`/`wait` can't give each beat its own timing — the timing the user re-tunes
  most. Loops are only for the lockstep case (identical steps, one continuous
  narration); otherwise write consecutive `self._step(...)` / `self.wait(...)` lines
  with per-step literals (keep SOURCED numbers referenced from their data list). Ref:
  scenes 12a, 05.
- **A DENSE, multi-phase subscene → split each phase into a private helper taking its
  `run_time`s as PARAMETERS, so the BODY reads as a timeline of `self._phase(1.0)`
  calls.** The inline-literal rule above stays the default for a SIMPLE subscene; but
  when a body grows long with `ValueTracker`/`always_redraw`/closure machinery that
  can't move to `_setup`, pull each phase into a helper (`self._gt_count_up(2.2)` /
  `self._gt_cull(1.0)` …). Each `run_time` is still a call-site literal and the method
  name labels its animation — every knob visible in one screen, the machinery hidden.
  Caveat: a BUILD-TIME pattern (adopt it writing a scene phase-by-phase) — don't
  RETROFIT it onto a working scene (phases share live state; retrofitting risks the
  render).
- **Do NOT put timing (or any tunable) on the `@subscene` signature.** Subscenes are
  invoked with NO args (`getattr(self, name)()`), so a `def beat(self, run_time=3.0)`
  is a dead, misleading knob. Put the number in the BODY; an `@subscene`'s signature is
  always just `(self)`.
- **Make every new scene fast to NAVIGATE and RE-TIME** (the user's main edit loop is
  tuning waits/run_times). On every new scene, alongside the run_time-inline rule:
  - a **`# <letter> : <one-liner>` banner above every `@subscene`** (findable by
    rendered letter; scene 04 is the reference) — fix letters when you reorder beats;
  - a **BEAT MAP in the class docstring** (one `<method> — <one-liner>` per subscene,
    in order; scenes 04/05);
  - a trailing **`# VO`** on any long `self.wait(…)` that covers a voiceover paragraph,
    so those big re-timed holds stand out from mid-beat pacing waits.
- **Apply these navigability conventions GOING FORWARD, not retroactively.** New scenes
  and any NEW code you add follow them; do NOT reformat an existing pre-convention scene
  just because you touched it (yahtzee 01–07 predate them — leave their beats unless
  asked to sweep). "Migrate on touch" = new code matches convention, not whole-file
  churn.

## Reuse over reinvention
- **The convention-check is NOT a new-scene gate — it fires on every EDIT too, and the
  tripwire is INVENTING A VALUE.** The new-scene PREFLIGHT styling pass applies identically
  when you ADD an element while editing: **the moment you type a NEW literal/constant — a
  colour/hex, opacity, font size, run_time feel, positioned number — STOP and grep the
  scene (then siblings) for how that KIND of element is already rendered, and match it.** A
  fresh `X = <value>` is almost never right when the scene renders that element one grep
  away (e.g. a one-off `ZERO_COLOR = GREY` for a "0" already drawn in its tier colour) —
  reusing the STRUCTURE but hand-picking the VALUE is the same miss; the value is part of
  the convention. Can't find a precedent? ASK before inventing. And when a search concludes
  "the convention is X," check X predates your own edits — code you just wrote is not a
  precedent.
- Read the existing assets and the video's gameplay REFERENCE scene (its CLAUDE.md's named
  canonical example) BEFORE building a gameplay-style beat. Use the existing helpers.
- **A recurring ENTRANCE/EXIT/emphasis motion is an asset — grep the other SCENES
  (not just the asset) before hand-rolling one; a reusable primitive may live in a
  scene, not the asset.** Bringing a shared prop on screen (the scorecard, a card, a
  board), flashing a cell, filling a box, a dice keep/reroll: before you write the
  animation inline, grep the other scenes for how they do it. If it's already
  consistent, call the same thing; if several scenes each reinvent it — or the
  primitive is buried as a scene-private helper another scene would want — PROMOTE it
  to a shared method (with the convention documented), flag it, and use it everywhere,
  so the next scene can find it. Concretely: the scorecard entrance was hand-written
  three different ways until it became `Scorecard.slide_in`; the demo-fill flash is
  `Scorecard.flash_rows`. Hand-rolling a motion an asset/scene already does — "it's
  just a FadeIn" — is the thought that produces four different entrances, and itself
  the red flag that a shared primitive is missing.
- **Read assets to CALL them, not just to imitate their look.** The reference scene shows
  *which methods do the work*: a keep/reroll beat IS `DiceBoard.keep` + `roll_rest`, not
  hand-placed coordinates. Before a gameplay beat, name the exact asset method each sub-beat
  calls and trace the dice/card state through it (which boxes open, where each die sits).
  Re-deriving something an asset provides — copying its *look* instead of calling it — is
  how reinvention and wrong-box/wrong-dice mistakes sneak in.
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
- **`render 99a` renders a STATIC thumbnail automatically** — scene `99` is the
  reserved thumbnails slot, so any `99*` target passes manim's `-s` (save the last
  frame, no video) at `-qk` (4K, 3840×2160) and needs NO flag. This is the ONE path
  for thumbnails; don't hand-roll `manim -s -qk`. It targets like any render, so a
  per-thumbnail `@thumbnail` is just `render 99a`; `--fast` gives a quick low-res PNG
  to check layout, and the 4K PNG is the upload asset (let YouTube do the single
  compression pass — don't pre-compress). To force a still PNG for a NON-99 scene,
  pass `--thumb`. `media/` is gitignored, so the PNG stays local like every render.
  Two behaviours mirror the video pipeline:
  - **Per-RESOLUTION subfolder** (`media/images/<scene>/2160p/`, `…/480p/`) — no fps
    (meaningless for a still) — so a low-res `--fast` test can't be mistaken for or
    overwrite the 4K upload asset. A slot keeps ONE PNG per quality: a renamed
    subscene's old-named PNG is swept (like `resolve.clean_stale`).
  - **Change-detection on `render 99 all`** — thumbnails are independent, so only the
    ones whose code (or a shared helper/asset they reach) changed re-render; the rest
    are skipped. Keyed per-subscene + per-quality in a gitignored `.render_keys.json`
    beside the PNGs. `--recompute` forces a rebuild.
- `render 01h --state` (no render) prints the mobjects on screen at subscene h's
  START (from the prior snapshot) — use to reason about starting state cheaply.
- **`render` takes a per-scene lockfile** (`cache/locks/`), so a SECOND render of
  the same scene while one is running is REFUSED (concurrent manim runs corrupt
  partial movies / the snapshot cache — don't do it). A stale lock from a dead
  process is auto-taken-over, so there's nothing to clean up by hand. `--check`,
  `--state`, and `--extract` don't lock (they don't render).
- **You're WELCOME to HALT the user's in-progress render when you need to render**
  (e.g. to verify a fix) — the user prefers that over you waiting or deferring. The
  refusing message names the live pid, and `cache/locks/render-<NN>.lock` holds it;
  kill that pid to free the lock, then render. For thumbnails / independent renders
  this is always safe (just re-render); for a long animated-scene render a mid-render
  kill only costs that subscene's snapshot (rebuilt next time), so it's fine too.
  (`kill` is gated, so it prompts — that's expected; go ahead and take over.)

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
- **A scene-file MODULE CONSTANT the subscene reads IS captured in its digest —
  editing it invalidates the snapshot.** The digest repr's the VALUE of every
  module-level constant a subscene's code closure references, of ANY stable-repr
  type — scalars, `np.ndarray` position vectors (`LEFT_SC`, a `COL4_W`), enums,
  dataclasses — so tuning a top-of-file layout constant re-renders correctly. Two
  residual edge cases where the digest can still miss a real change, so
  reach for `--recompute` if a constant edit seems to do nothing: a constant whose
  `repr` carries a memory address (`<Foo at 0x…>`, e.g. a module-level Mobject —
  deliberately not captured, as the address would poison the cache) and a *huge*
  numpy array (numpy truncates its repr with `…`, so two differ only past the
  cutoff). Ordinary layout/position/size constants are safe.
- Don't build a mobject carrying a LAMBDA updater (`always_redraw(lambda …)` or
  `.add_updater(lambda …)`) in `setup_scene` — the lambda can't be pickled, which
  breaks the whole scene's snapshot. Build those in the subscene. A BARE
  `ValueTracker` and static text pickle fine — keep them in setup and attach any
  updater in the body.

## Rendering during iteration (agent — keep the loop fast)
The slowest mistakes here are render round-trips, not thinking. Defaults:
- **Render ONLY the subscene(s) you changed**, never the whole scene unless geometry
  changed everywhere. `render NNk` replays the prefix once; `NN sub`/`NN all` rebuilds
  all subscenes (much slower).
- **Editing a shared asset (`assets/`, `bpkfigures/`) invalidates ALL snapshots**, so
  BATCH asset edits and render once.
- **Verify with ≤2 frames, for OBJECTIVE issues only** (wrong number/position/
  overlap/clipping). The user judges feel/timing from the video far better than the
  agent from stills — don't frame-hunt.
- **Every spatial/quantitative claim carries its SOURCE inline — the printed number
  you pulled, or the words "eyeballed, not verified."** A bare spatial claim ("margins
  look even", "it's centred") IS the violation: the missing number is the tell you
  LOOKED instead of measured. Two ways a "measurement" is really a guess: (a) squinting
  at a 480p thumbnail — MEASURE means real coordinates (`get_left/right/top/bottom/
  center` via a one-off `print`), because margins/fit read deceptively at low res;
  (b) reading true coords but comparing them to a MADE-UP constant (frame bounds
  recalled as 7.11/4.0 vs the real 8.0/4.5) — a correct ruler at the wrong zero
  confirms nonsense, so any constant a claim rests on is READ from config, not
  recalled. NEVER pronounce how something LOOKS as fine — show the user; objective =
  a number you measured, not an impression.
- **A conclusion that contradicts what the render plainly shows means a wrong
  ASSUMPTION — STOP and find it, don't assert past it.** "The card is taller than the
  frame" while the frame shows the whole card with margins is impossible — the
  impossibility signals a false input (here, the frame size). When your numbers and the
  picture disagree, hunt the bad input before more edits, don't repeat the claim louder.
- **After changing a beat, render THAT beat and glance at its NEIGHBOURS.** Beats carry
  shared state (same dice, label, running number), so a change often reads wrong only in
  the beat before/after — a value equal to the previous beat's, a die that dips then
  straight back up across a hand-off, text that now overflows. A `--check` is NOT a
  render: render the beat, look, scan the seams.
- **ALWAYS run `render NN --check` before handing off a scene you touched.** Instant,
  and it LINTS (warn-only) for the slips prose can't catch mid-edit (raw `Text(...)`,
  inlined-hex/off-palette colour, one-use `run_time` local). FIX every `[lint]
  file:line` or flag why it stays — a lint line you neither fixed nor mentioned is a
  miss you shipped. It's additional to rendering the beat to LOOK, not a substitute; a
  nudge, never a gate.
- **TRIP-WIRE: a 2nd render of the same subscene to re-judge how it LOOKS = frame-
  hunting feel — STOP and hand off.** One objective-check render per change, then the
  user takes over. Stills judge only objective spatial facts (count/position/overlap/
  clipping), NOT motion or whether an animation "reads" — never diagnose a motion/feel
  problem from a still; that's the user's call from the video.
- **TRIP-WIRE #2: built a beat WRONG twice for the same conceptual reason? STOP and ASK
  what it should depict — do NOT re-guess.** A repeated conceptual miss (wrong game
  state, quantity, turn) is a comprehension gap, not an implementation bug — the fix is
  a QUESTION. Re-iterating a misunderstood beat burns rounds and ships confidently-wrong
  output. If you're unsure what a beat IS, that uncertainty is itself the trigger to ask
  BEFORE building.
- **If a fix to a USER-SPECIFIED shape/layout hits a snag, revert to exactly what they
  asked and flag-ask — do NOT swap in a different design.** Substituting your own
  concept, even to solve a real problem, is a silent override — the worst error here. A
  minimal animation/timing tweak is in scope; changing the shape/structure the user
  named is not.
- **Default to "minimal verify":** render the changed subscene(s) + ≤2 frames, then hand
  off. For a pure feel/timing pass, prefer edit-only (let the user render) — their
  fastest loop.
- **Animation timing: use trackers/updaters** (value- or `dt`-driven), NOT computed-time
  guesses (`Succession(Wait(t_guess), …)`) — guessed timings are fragile; a value/dt-
  driven effect fires correctly regardless of surrounding pacing.
- **Manim gotchas that each cost render round-trips:**
  - **`mob.animate(rate_func=…).set_value(…)` — the CALL form — silently fails to
    animate a `ValueTracker` inside a multi-animation `play()`** (reads as a jump at the
    end). Use plain `mob.animate.set_value(…)`; put the rate_func on the `play()`.
  - **Two separate `ValueTracker`s driving ONE visual desync** — value on one,
    position/scale on another, so the motion finishes while the value lags. Drive linked
    properties from ONE tracker (value = `lerp(v0, v1, t)`, pos/scale from the same `t`).
  - **`scene.remove(submobject)` restructures the submobject's PARENT group** (detaches
    with side effects, can leave the group behind). Only `remove()` TOP-LEVEL mobjects;
    to drop an in-group text, rebuild the group or hard-clear (`for m in
    list(self.mobjects): self.remove(m)`).

### Keep commands allowlist-friendly (avoid permission prompts)
The permission allowlist already covers the core loop (`render`, `manim`,
`ffmpeg`/`ffprobe`, `grep`/`rg`/`ls`/`cat`/`head`/`tail`/`wc`/`sort`/`tr`,
`cd`/`echo`/`mkdir`). Friction comes from working AROUND it; so:
- **Separators split and auto-approve; control-flow constructs never do** (full
  rule in § Shell commands). The classic traps to split into separate calls: terse
  one-liner verification loops (`for x in …; do …; done`) and the `( cmd || fallback )`
  subshell idiom — the evaluator can't see inside a loop / subshell / `$( … )`.
- **Syntax check with `render NN --check`** (instant AST parse of the scene +
  `assets/*.py`, no manim) — NOT a separate `python -c "import ast …"`, which
  isn't allowlisted and prompts every time. `--check` ALSO runs a **warn-only style
  linter** (`bpkfigures/lint.py`) over the scene file: it flags the mechanical
  convention slips prose rules rely on you remembering — a raw `Text(...)` (use
  `crisp_text`), an inlined hex or raw manim palette colour (use a `style.py` /
  `config.py` name), a one-use `run_time` local (inline the literal). It NEVER fails
  the check or blocks a render (syntax errors still do); a `[lint] file:line: …`
  line is a nudge, not a gate. It only catches the statically-checkable class — the
  judgment conventions still live here. When you add a new mechanical convention,
  prefer adding a check there over more prose (see the postmortem rationale under §
  Reuse over reinvention's value-tripwire). Shared, so every video gets it.
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
- **Run git as STANDALONE calls — never `cd <repo> && git …`** (the cd+git combo
  always prompts; the full rule + cwd-persists mechanics are in § Shell commands).
- **Edit files with the Edit/Write tools, never `python - <<'EOF'` splices** —
  arbitrary `python`/`python3` isn't (and shouldn't be) allowlisted, and file
  rewrites via heredoc are easy to get wrong.
- Use `rg`/`ls` (allowed) instead of `find` for inspection.
- **Explore/search with the Grep/Glob/Read TOOLS, not bash `find`/`grep -r`/`cat`/
  `sed` — and NEVER delegate a broad bash sweep.** The dedicated tools don't touch
  the shell allowlist, so they never prompt; bash `find`/`sed` (not allowlisted),
  `xargs`/subshells/command-substitution (never auto-approve), and any absolute path
  with spaces (`"My Documents"/…` — the quote can break an allowlist glob) each
  prompt, one command at a time. This bites hardest CROSS-REPO — reading
  `battleship/` from the yahtzee working dir needs absolute space-paths. A
  general-purpose subagent (e.g. Explore) defaults to bash `find`/`grep`/`sed` and
  will fire DOZENS of approval prompts in a row, quietly undoing the low-friction
  loop — so do repo lookups INLINE with Grep/Read; if you must delegate, constrain
  the subagent to ONLY the Grep/Glob/Read tools (no bash find/xargs/sed/cat).
- `pkill`/`kill`/`rm` stay gated on purpose — don't reach for process-killing as a
  normal step; if a render seems stuck, prefer `run_in_background` + waiting.

## Git / new repos
- **Commit and push WITHOUT asking — this OVERRIDES Claude Code's default.** In this
  project the agent has standing permission to checkpoint WIP, commit before a major
  rewrite, and push when a chunk is done. Still branch off `main` for non-trivial work,
  and keep the commit-message footer convention.
- **Commit at each working checkpoint — do NOT batch a multi-step change into one big
  commit.** The user prefers frequent, granular commits (one per working step that leaves
  the code good), staging each step's files by explicit path.
- Each video is its own git repo. The FIRST thing on a new video repo is a `.gitignore`
  (else renders get committed), covering at minimum: `media/`, `**/media/`, `*.mp4 *.mov
  *.wav *.mp3`, `__pycache__/`, `*.py[cod]`, `.venv/ venv/`, `.DS_Store`, AND the manim
  snapshot cache `animations/**/cache/` (50+ MB pickles/subscene — pure build artifact).
  These are project-specific (per-repo, not global); `battleship/.gitignore` is the
  template.
- NEVER commit `media/` renders OR `animations/**/cache/` pickles (if tracked, `git rm -r
  --cached <dir>` keeps them on disk). CAUTION: scope cache/pkl ignores to the animations
  tree — do NOT blanket-ignore `*.pkl`, since solver data under `math/data/` and
  `math/notebooks/data/` is intentionally tracked.

## Starting a new scene
How the user likes a brand-new `scenes/NN<name>.py` built:
- **Orient before writing.** Read the OTHER scenes in this video first to match their
  structure/conventions (if it's the video's FIRST scene, read a previous video's).
  Reuse what exists — this video's `animations/assets/` and the shared `bpkfigures/`.
- **PREFLIGHT before writing OR editing a scene — write the map down first** (this
  turns the sparse-text and reuse rules into a gate; skipping it is HOW they get
  violated). In the chat, produce:
  (1) **each beat → the reference scene/section it matches** and the exact conventions
  to copy (grid shape, `flow_order`/ordering, sizes, buffs, helpers). A beat
  paralleling another scene ("the 252 from scene 1") MUST reuse that scene's actual
  layout, not a re-derivation.
  (2) **every on-screen text element → the literal column-2 phrase that licenses it.**
  Anything not in column 2 (titles, counts, helper labels) is DROPPED or flagged for
  approval — never silently added.
  (3) **the WHOLE of column 2 as a clause-by-clause checklist** — quote EVERY clause
  verbatim (animation directions included: "move dice down a row", "remove 4kind",
  "3 other configurations"), and next to each write what you'll build. A clause you'd
  deviate from, can't build, or would paraphrase gets FLAGGED-and-ASKED. The exact
  words ARE the spec (numbers, counts, "row", which box) — paraphrasing is HOW
  "wrong box"/"dropped instruction" errors happen. **Re-run this table against the
  built scene at handoff** and report every clause that still doesn't match.
  (4) **each beat → the column-1 VOICEOVER it pairs with — READ COLUMN 1, not column 2
  alone.** Column 2 is often terse ("skip most of the stuff", "montage"); the voiceover
  pins down what a beat actually depicts, so quote the paired column-1 text next to each
  beat before coding. When column 2 is vague about which game state/turn/quantity, the
  voiceover disambiguates (e.g. "the second reroll of turn 12" is the specific
  two-open-box turn-12 state with rest-of-GAME EVs, not a generic single-box
  illustration). If neither column pins it down, FLAG-and-ASK.
  (5) **each on-screen element → the shared helper/value it renders through — a STYLING
  pass, not just content.** Name what each element comes from: text → `crisp_text`
  (right `font_size`/`color`), never a raw `Text`; colours → the specific
  `style.py`/`config.py` name (score green/red, gold highlight, `ACCENT_FILL`), never a
  hand-picked hex; a prop ENTRANCE or box fill/flash → the existing asset method
  (`Scorecard.slide_in`, `flash_rows`, dice helpers), never a hand-rolled FadeIn. A cell
  you can't map to a helper is the flag to STOP and find it (or ask). **Re-run at
  handoff** on a verification frame: read the STYLING (text in `FONT`? colours semantic?
  reused props render as elsewhere?), not just position/overlap. **NOT new-scene-only —
  it re-runs whenever you ADD an element while EDITING; the tripwire is typing a new
  value/constant (see § Reuse over reinvention).**
- **Beats are delimited by a literal `---` in BOTH columns — split on it to recover the
  beat↔voiceover↔animation mapping.** `Script.md` is a 2-column Google-Doc table whose
  Markdown export FLATTENS each cell to ONE line (no newlines), so without the `---` a
  scene's voiceover and animation are two run-on blobs with beat boundaries lost. Parse
  by splitting BOTH cells on `---` and zipping: segment *i* of voiceover pairs with
  segment *i* of animation = beat *i* = subscene (a, b, c…). If segments are
  letter-tagged (`a)` … `b)` …), pair by tag. This is what makes items (3)/(4) possible.
- **If a multi-beat scene's row has NO `---` delimiters, STOP and ASK the user to add
  them — do NOT guess the boundaries** (the mapping is unrecoverable from the flattened
  export). A genuinely single-beat scene needs none; the trigger is several beats
  crammed into one run-on cell. Watch too for a MISMATCHED `---` count between columns
  (an empty beat still needs an empty segment, `… --- (no change) --- …`) — a mismatch
  silently shifts the pairing, so flag it.
- **A beat with an EMPTY animation column (voiceover-only) gets NO subscene** — don't
  create a do-nothing `self.wait` subscene; its voiceover plays over the neighbours'
  framework holds. Still COUNT it when zipping (so later beats stay aligned), but skip
  emitting it. Removing a subscene shifts every LATER letter, orphaning the old
  highest-letter video (`resolve --clean` only cleans letters you render) — delete that
  orphaned `NN<letter>_*.mp4` by hand.
- **Start from a blank scene** (the setup_scene/@subscene pattern), not a copy — but
  informed by what you read above.
- **Build from the script.** Stick to what `Script.md` column 2 calls for — don't invent
  extra content, don't deliberately omit; fill genuine ambiguities only, and flag them.
  (See literal-implementation + verify-render under Process.)
- **Changing `assets/` or `bpkfigures/` is welcome — but ASK FIRST**; propose the shared
  change before making it, don't silently edit shared code.
- **Timing:** make sensible run_time guesses and name them on handoff (see Process);
  every animation/wait exposes a tunable `run_time` in the subscene body — see the
  run_time note in Scene structure.

## Process
- `Script.md` is reference, not a spec to enforce: do what the user asks and flag
  deviations.
- **When an iteration changes WHAT'S DEPICTED — a game/card STATE, a value, which box is
  filled — RE-READ that beat's `Script.md` row FIRST.** Timing/layout/colour polish can be
  reasoned from the code, but a depicted-state change must be checked against the script —
  it's often the POINT of the beat. The failure mode: deep in polish you reason LOCALLY
  from the scene's constants ("opening this box reads better") and silently break the
  beat's meaning. The build PREFLIGHT reads column 1+2 per beat; this keeps that grounding
  alive through the ITERATION passes, where it lapses.
- **For animation FEEL/timing: build a quick ROUGH version, render + grab frames, iterate
  from the user's reaction.** Don't over-build the first pass; render and verify after
  every visual change.
- **Rough means low-polish, not partial scope.** On a first pass, rough in the WHOLE scene
  end-to-end (every beat wired up with guessed timings) — don't stop after a few beats; the
  user reacts to the complete arc.
- **Verify-render division of labor** (the user renders right after the agent): the agent
  renders 1–3 fast frames for OBJECTIVE issues (wrong position/overlap, clipping/z-order,
  an object that didn't appear, off-screen label, wrong number, frame overflow, size
  mismatch) — these cost a full round-trip if missed. The agent does NOT iterate on
  subjective FEEL (exact run_times, easing, holds) — the user judges that from the video.
  On handoff, NAME which timing/feel knobs you left at a guess.
- **Every animation/wait exposes its `run_time`** in the subscene body so the user can
  retime — full rule in the run_time note under Scene structure.
- **Use extended thinking for scene-building** (geometry + sequencing): the costly mistakes
  are spatial (overlaps, a label centered on the panel edge not the cell, dice into a guide
  line) and timing ones — working coordinates out before coding prevents a render
  round-trip that dwarfs the thinking cost. Skip it for quick edits/lookups/config.
