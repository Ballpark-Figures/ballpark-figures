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
- **A request that states a CONVENTION applies EVERYWHERE that convention holds — not
  just the spot in front of you; and "all"/"everywhere"/"2 decimals" means LITERALLY all.**
  The failure mode is treating each message as the smallest local edit that satisfies its
  sentence: the user says "2 decimal places for average misses" and you change only the beat
  you're on, or "cycle through all the candidates" and you cycle one. Before editing, ask
  "is this a one-off or a RULE?" — a format, a behaviour, a layout/motion convention, a
  rounding, a naming — and if it's a rule, apply it to every place it holds AND make that the
  default going forward. When the same rule then forces you to edit many call sites, that is
  itself the signal to CENTRALIZE (see § Reuse over reinvention: one source of truth). Making
  the user come back and say "I meant everywhere" is the tell you scoped it too narrowly.
  (Bit us on hangman scene 05: "all candidates", "2 dp", "bare numbers", "one at a time" each
  had to be repeated because they were first applied to only the current beat.)
- **Disagreeing is fine; silently overriding is NOT.** If you think a different
  approach is better, FLAG IT AND ASK FIRST, then follow the user's decision.
  Willfully deviating from an explicit instruction — even when your alternative
  seems reasonable — is a serious error that can cause major problems later.
  Flagging-then-asking is always acceptable; substituting without asking is not.
- **A user's inline description of an ANIMATION is a spec — run the same
  clause-by-clause checklist you'd run on a `Script.md` column.** When the user
  describes an effect in prose ("little green lines, one at a time, very quickly,
  around the word, removed with the letters"), EVERY clause is a requirement, not
  flavour — enumerate them and build to each; a clause about the MOTION ("one at a
  time", "drawn like a hand", "all at once", "then fades") is as binding as one about
  placement or colour. The failure mode is latching onto the gestalt ("a flash near
  the word") and honouring the shape while dropping a motion/timing clause. And when
  the prose is genuinely ambiguous, a quick options AskUserQuestion (e.g. outline vs.
  radial burst vs. whole-thing flash) BEFORE building beats guessing wrong and
  building an elaborate throwaway. (Bit us on hangman scene 02: "appear one at a time"
  was dropped through TWO builds — a box then a burst, both simultaneous — before it
  stuck; three rounds of churn a clause-check or an early options-ask would have saved.)
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
- **Don't invent the QUESTION or the METHOD, not just the number.** This rule extends
  upstream and to EXPLORATORY code: producing an analytical RESULT (a ranking, a "best"
  anything, an aggregate, a comparison, an optimization) or choosing the MODELING that
  defines it (which metric/objective, what distribution, which word/state universe, what
  counts as "optimal") is the USER'S call, made explicitly BEFORE any code computes an
  answer — even in `math/`, even when nothing is displayed yet, even as a "quick
  prototype." The user must understand and be able to OWN every computation that could
  reach a video. So: BUILD the requested primitives/plumbing/data (a bare correctness
  smoke-test is fine), but do NOT run analyses, rank/score/optimize, or bake in a metric
  until the user has defined the problem and said go. This SHARPENS "hand over a runnable
  prototype early" (§ Process): the prototype is machinery to hand over, not results to
  generate. When you catch yourself about to compute a result that wasn't explicitly
  specified — STOP and ask. (Bit us: an unrequested entropy-based opener ranking, with an
  unstated metric + uniform-distribution assumption, computed and run on the agent's own
  initiative during a "copy the primitives over" task.)
- **Never write new math for a displayed value.** If producing a number would
  require implementing ANY calculation — scoring, probability, EV, a reroll/
  combinatorial sum, a simulation, an aggregation — STOP and ASK FIRST, even when
  you're certain it's correct. (This bit us: a hand-rolled single-box EV in a scene
  asset was both unsanctioned AND wrong, and shipped silently.)
- **Source, don't compute.** Before showing a number, find where it already lives:
  a solver output / data file (`math/data/…`), a notebook/module helper (`math/…`,
  e.g. `state_explorer.py`), or a value the user gave you — and read it from there.
  The machinery already exists; use it. If two sources exist, ask which is canonical.
- **The METRIC/UNIT is part of the product too — use the pipeline's exact definition,
  don't substitute a plausible proxy.** When a scene visualizes a quantity the pipeline
  already defines (a weighting, an EV, a frequency, a probability), encode it the SAME way
  the pipeline does — e.g. the frequency WEIGHTING the solver uses is the linear
  `round(10**zipf)` per-billion rate (`wordlist.freq_weights`), NOT the log `zipf`. Picking
  a different-but-related encoding because it "reads cleaner" (log for linear, raw for
  normalized, a smoothed/binned version) silently swaps the metric — that's inventing the
  MODELING, same class of error as inventing the number. When two encodings of the same
  quantity exist, use the one the pipeline/weighting actually uses, or ASK. (Bit us on
  scene 17: defaulted the "word frequency" bars to log zipf when the weighting is the
  linear rate — the user caught it. NB flagging a resulting ugly VISUAL for the user to
  decide on is RIGHT; quietly switching the metric to dodge the ugliness is the error.)
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
- **YouTube stats live in the `analytics` DB — SOURCE them, don't invent.** Real
  view counts / durations / publish dates for the channel's own videos, tracked
  competitor channels, and specifically-PINNED one-off videos (e.g. Jan Misali's
  "hangman is a weird game", id `le5uGqHKll8`) all come from the `analytics` service's
  Neon Postgres — never a made-up number. Schema: `videos` (title, `published_at`,
  `duration_seconds`), `samples` (append-only cumulative `view_count`; the LATEST row
  = current views), `channels`, and a `pinned` flag opting a video into sampling. It
  IS reachable from any machine: `analytics/.env` holds `DATABASE_URL` (Neon) and the
  analytics venv has `psycopg` — allow-listed as `Bash("*/analytics/.venv/bin/python"
  *)` so a query runs promptless. Get it into a scene the SAME cached way: a data
  module (`animations/assets/<name>_data.py`) queries the DB and writes a COMMITTED
  `<name>_cache.json`, the scene reads the cache, the RENDER never touches the DB
  (no psycopg/network at render, and the numbers sync via git). It's a POINT-IN-TIME
  snapshot — re-run the data module to refresh. hangman `assets/youtube_data.py` is
  the reference. Do NOT have the scene query the DB at render time (breaks reproducible
  renders + needs DB deps in the manim env).

## Repo layout
- `Ballpark-Figures/` umbrella repo: one sub-project per video plus the shared
  `bpkfigures/` package; each video is its own nested git repo.
- Each video has TWO sides — know which one a file belongs to:
  - `math/` — the DATA/COMPUTATION pipeline: `math/data/` (source data, solver
    outputs, datasets, wordlists — tracked + synced), `math/notebooks/` (Jupyter),
    plus solver/helper modules. **A NEW data file/dataset/wordlist goes HERE.**
    - **Every notebook's setup cell sets `pd.set_option('display.max_rows', 200)`**
      (right after `import pandas as pd`) — pandas otherwise collapses any table
      over ~60 rows to a head/tail preview, silently hiding rows in the exploratory
      tables. Add this line whenever you author a new notebook (or first touch one
      that lacks it).
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
- **`@still` = the GENERAL still-IMAGE decorator** (`bpkfigures/scene.py`, exported via
  `from config import *`) — for a scene that's just a SERIES OF IMAGES with no animation
  BETWEEN them (e.g. a mock-UI walk-through: card → watch page → homepage). Two behaviours,
  both keyed off the DECORATOR (detected by `resolve` via AST — NOT the scene number):
  (1) it renders from a CLEAN, EMPTY frame with NO carry-over and NO snapshot save/replay,
  so you don't hand-roll a `_clear()`/FadeOut between beats — build each frame with a
  static `self.add`; (2) `render` emits it as a still PNG (manim `-s`) under
  `media/images/<scene>/<res>/`, NOT a video, so `render NN all` produces one PNG per
  subscene and no combined full-scene render. Addressed like any subscene (`render NNa`).
  **`@thumbnail` EXTENDS `@still`** — the SAME still-image behaviour, specialized for the
  reserved `99` slot: 4K (`-qk`) by default as an upload asset, plus change-detection on
  `render 99 all`. A plain `@still` renders at the normal `-qh` (or `-ql` with `--fast`).
  So: `@thumbnail` in the `99` slot; `@still` for any other image series (hangman
  `93youtube_test.py` is the reference). No `new-video` change needed — the scaffolded
  `from bpkfigures.scene import *` exports `still` automatically.

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
- **A bar chart / histogram / distribution** → `bpkfigures.histogram.get_histogram`
  (standing or horizontal bars, x-ticks, title, per-bar labels, median highlight;
  pass `ink_color=CHALK` for dark/chalkboard scenes). For a labelled horizontal
  double-bar comparison, `bar_graph.get_bar_graph`. For SEVERAL series of a value-per-
  category plotted side by side (grouped/paired bars over a shared x axis — e.g. avg misses
  per WORD LENGTH under two weightings), `bar_graph.grouped_bar_chart(categories, series,
  …)` (each series a `(name, color, values)` triple; adds x/y axes + y-ticks, per-category
  labels, x-title, title, legend; returns role handles `.series`/`.bars`/`.rest`/`.legend`
  for `grow_bars` + a fade-in of the rest). Used by hangman scenes 17 (optimal uniform vs
  zipf) and 19 (uniform vs best-opener) — pass the two series + labels, don't hand-roll axes.
  A bar chart's ENTRANCE is
  `bar_graph.grow_bars(scene, chart.bars, run_time, lag=…, extra=…)` (bars rise from the
  axis; `lag` staggers them L→R, `extra` fades the labels in alongside) — don't hand-roll
  a `FadeIn` or a per-scene `_grow_up`. NEVER hand-roll `Rectangle`
  bars — the `lint.py` check flags fill-only `Rectangle` bars built in a loop. If
  the shared helper lacks a knob you need (a colour, a label style, a mode), EXTEND
  it (backwards-compatible optional param) rather than rebuild — see "IMPROVE THE
  ASSET" under § Reuse over reinvention. NOTE the split: `get_histogram` is for a
  DISTRIBUTION (counts/probabilities over an integer value-axis, `crisp_text`
  labels); a categorical / metric bar chart (a value per label — e.g. hangman scene
  04's avg-misses-by-length, or a sorted letter-frequency chart with written-font
  labels + a morphing mode) is a DIFFERENT asset. Don't force-fit one into the
  other — improve/extend the right shared helper (or build it if missing).
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
- **A generic ENTRANCE/REVEAL (fade-in, rise-in, grow-in) of a chart/group** → route it
  through a SHARED motion; don't hand-roll a fresh `FadeIn` per scene. Bars → the bar
  chart's `bar_graph.grow_bars`; a row-by-row list/grid rise → the `_rise` cascade (tier
  scenes / scene 08); spotlight-then-hold → `highlight(persist=True)`; a plain group
  appear → a bare `FadeIn` is fine, but choose it deliberately. Reinventing an entrance
  every scene is a drift the user has explicitly flagged (`_grow_up` was hand-rolled in
  scenes 04/05 + yahtzee 07 before it became `grow_bars`). On the 2nd hand-roll of the
  same entrance, PROMOTE it to a shared helper (a backwards-compatible addition you can
  just make and mention — see § Reuse over reinvention).

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
  - **A LONG single-line `crisp_text` string WRAPS/clips — build it small and scale up.**
    `crisp_text` supersamples up to a 240pt cap (`TEXT_SS_MAX_FONT`), so at any
    `font_size >= 24` the underlying `Text` renders at ~240pt, where a long phrase
    exceeds pango's line width and wraps (or drops trailing words). A chart TITLE or any
    long label is the usual victim. Fixes: `crisp_text(text, font_size=10, …)
    .scale_to_fit_width(w)` (low underlying pt → one line, then scaled up), or lay the
    words/letters out yourself (what hangman's chalk `_chalk_phrase` does). `get_bar_chart`'s
    own `title=` string hits this too — pass a pre-built, scaled mobject. Short strings are
    unaffected. (Bit us on hangman `05optimal`'s "Average Misses by Word Length" title.)
  - **Aligning SEVERAL strings on one line (a table row/column, a row of labels)? Anchor
    them by BASELINE, not `.move_to()`.** `crisp_text`/manim `Text` CENTRE each string's
    bounding box, so ascender/descender words (`jog`, `say`) drift up/down off the line
    when centred at the same `y` — and a word won't line up with the number beside it.
    Use `crisp_text(s, …, baseline_at=(x, y))` (or `place_on_baseline(mob, (x, y))`,
    both in `style.py`) to sit the string on its text BASELINE (descenders hang below), so
    a row/column of mixed strings lines up. Bar labels get this via
    `get_bar_chart(baseline_labels=True)`. A SINGLE isolated label doesn't need it — this
    is specifically for a set that must share a line. (Bit us on hangman 18: bar labels,
    then the beat-a table, both centred so descender words rode ~0.07u high.)
  - **A COUNTING / animated number WITH a label → ONE `crisp_text` rebuilt via `become()`,
    NOT a static label + a separate animated number you then align.** Splitting
    "Average Misses: 4.23" into a label mobject + a number mobject forces you to hand-align
    their baselines — and the label's descenders/ascenders differ from the digits, so they
    drift vertically (the same trap as above). Instead build the WHOLE string as one
    `crisp_text` and drive it with an updater that `become()`s the full string from a
    `ValueTracker`: `num.add_updater(lambda m: m.become(crisp_text(f"…: {tr.get_value():.2f}",
    …)))` — label + number then share a baseline for free. Keep it from jittering/resizing
    with a FIXED left edge + a FIXED scale (measure a reference string ONCE for the scale;
    do NOT `scale_to_fit_width` per frame — the digit-width variation would resize it). The
    fixed PREFIX keeps its height/baseline constant as the number changes. (Recurred across
    scenes/videos as a label-vs-number misalignment; the single-text form is the fix — hangman 18.)
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
- **Promoting a value to `bpkfigures/` is FORWARD-LOOKING — do NOT retroactively rewire a
  previous video's config to reference it.** When you lift a colour/constant into shared
  `style.py` (or another shared module), new and in-progress work uses the shared name, but
  leave already-shipped videos on their own literals. A same-value refactor still risks a
  finished video's render, and the DRY benefit isn't worth touching shipped work. Rule of
  thumb: as long as we don't break a previous video, config changes apply going forward only.
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
- **Commit with a PATHSPEC, don't just stage by explicit path — `git commit <paths> -m
  …`, never a bare `git commit`.** Staging by path (`git add animations/scenes/NN<name>.py`,
  never `git add -A`/`.`) is necessary but NOT sufficient: a bare `git commit` commits the
  whole INDEX, and on the shared working tree another tab (or a running `/push-videos`) may
  have OTHER files staged — so a bare commit sweeps them into yours even though your own
  `git add` was clean. Naming the paths on the `commit` itself (`git commit path1 path2 -m
  …`) builds the commit from just those paths' working-tree changes, ignoring whatever else
  sits in the shared index. (Bit us 2026-08-08: a bare `git commit` of a scene, run while a
  `/push-videos` was in flight in another tab, swept staged solver-output JSON into the
  scene commit — harmless data-wise, tracked anyway, but a mixed, mislabeled commit.)
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
- **RECORD-ON-CORRECTION: when the user corrects a TERM or CONVENTION you misread, write
  its definition into the right CLAUDE.md THAT TURN — don't just fix the one instance.**
  A misunderstood domain term ("written font" = the hand-drawn chalk strokes, not the Inter
  `crisp_text`) or a convention you got wrong is a re-guess waiting to happen in the next
  scene or the next video; fixing only the current use leaves the wrong assumption live.
  Recording the DEFINITION (video-specific → that video's CLAUDE.md; general → here) puts
  it in-context for every future session, so it can't be re-guessed. This is a FACTUAL
  correction, so record it proactively and say you did (it's not a new behavioural rule
  needing approval). The tell: the user asks some version of "do you not know what that
  means?" — that means a definition is missing from the docs. (Bit us: "written font" was
  guessed as Inter through two builds; the fix was the definition in the video CLAUDE.md,
  not just the one swap.)
- **Default to CLAUDE.md** for anything the user wants the agent to know: loaded every
  session and synced across machines via git — unlike memory, which is local to one
  machine and only surfaces via recall. When unsure where something goes, don't
  deliberate — put it in CLAUDE.md and say so.
- **Use memory ONLY for facts that genuinely can't be committed** (private URLs,
  credentials) AND that have a clear, nameable trigger for the memory's `description` so
  recall fires. If it's private but its trigger is fuzzy, don't silently rely on memory —
  say so and ask the user to re-mention it when it comes up.
- **TRIP-WIRE: about to write a learning to MEMORY? Unless it's an uncommittable secret,
  STOP — it belongs in a committed doc.** A correction, a workflow/tooling habit, a "do X
  next time" — memory is the WRONG home (machine-local, unreviewed, invisible to your
  curation; it won't reach the other machine). It goes in a CLAUDE.md, or — when it's
  about a slash command's behavior — in that command's file under `dotclaude/commands/`
  (which syncs to the desktop; memory does not). Reaching for memory to record a habit is
  itself the drift to catch. (Bit us 2026-07-25: two `/push-videos` learnings — the
  commit-sweep rule and the bare-invocation rule — got filed in machine-local memory
  instead of the command file; migrated to `push-videos.md`/`sync-videos.md`.)
- The public GitHub repo intentionally shows how the user works, so workflow/preference
  content in committed CLAUDE.md is fine — reliable loading beats repo cleanliness.
- **Never write the user's real name (or other personal identifiers) into any public-repo
  file** — `bpkfigures/` and the video repos are public; refer to "the user." Identity
  facts belong only in the private `dotclaude` repo (pulled in via `@CLAUDE.private.md`).

## Shell commands — keep them allowlist-friendly (agent)
The allowlist covers the core loop (`render`, `manim`, `ffmpeg`/`ffprobe`,
`grep`/`rg`/`ls`/`cat`/`head`/`tail`/`wc`/`sort`/`tr`, `cd`/`echo`/`mkdir`). Friction
comes from working AROUND it.
- **A permission prompt is NOT a reason to SKIP a genuinely useful action.** If a task
  needs data or a tool behind a prompt — a DB read, a query, running a helper — DO it;
  a one-off approval for a legitimate action is cheap. This whole section is about
  avoiding UNNECESSARY prompts where a promptless path ALREADY EXISTS (bare git over
  `git -C` in-workspace, the right tool over an ad-hoc heredoc) — it is NOT license to
  decline necessary work because it would prompt. If a prompt-gated action RECURS, make
  it frictionless by adding an allowlist entry (as with the analytics venv), don't just
  keep avoiding it. (Bit us: held off querying the `analytics` DB for a real view count
  because it "would prompt" — should have just run it, and added the allow-rule.)
- **BUT hitting an unexpected blocker and pivoting to a DIFFERENT or OUTWARD-FACING
  workaround is a STOP-AND-FLAG moment — not a silent route-around.** The rule just above
  ("don't skip sanctioned work over a prompt") is NOT license to quietly work around a
  FAILURE. When the intended path breaks — a missing key/credential, a 403, an
  unavailable tool — and you're about to switch to a materially different approach,
  especially an outward-facing one (SCRAPING a page, a new external source/service, an
  action that leaves the machine), STOP: surface the blocker (a missing local secret is
  itself useful info about the setup) and get the user's call BEFORE proceeding. Reach
  confidently for the SANCTIONED path even if it prompts; PAUSE before an unsanctioned
  detour. (Bit us: the local `analytics` Data-API key was missing, so instead of saying
  so, silently scraped a channel page for a video's avatar — should have flagged it.)
- **Chains auto-approve when EVERY subcommand is allowlisted.** Claude Code splits on
  `&&`, `||`, `;`, `|`, `&` and newlines and checks each piece independently, so a chain
  of allowlisted read-only commands does NOT prompt. What DOES force a prompt:
  - **`cd` + `git` in one compound command ALWAYS prompts** (a hardcoded safety rule) —
    the #1 source of needless prompts here. The Bash **cwd persists between calls**, so
    NEVER `cd "<repo>" && git …`; `cd` once in its own call (or rely on the current dir),
    then run each `git add`/`commit`/`push` STANDALONE.
  - **Any non-allowlisted subcommand drags the whole line into a prompt** — usually
    ad-hoc python (`python3 <<EOF`, `.venv/bin/python script.py`). Don't shell out to
    throwaway python: use Edit/Write + the tools, or a FIXED `-m` module — JSON via
    `python3 -m json.tool <file>`, peek solver `.npz` via `python -m bpkfigures.inspect_npz
    <path>` (safe, `allow_pickle=False`); NEVER ad-hoc `python -c`/heredoc.
  - **Subshells `( … )`, `$( … )`, `for`/`while` loops, `watch`/`xargs`, `find
    -exec/-delete`** never auto-approve — split into separate calls (classic traps: a
    one-liner verification loop, the `( cmd || fallback )` idiom).
  - **A REDIRECTION forces a prompt regardless of target** — `>`/`2>`/`>>`, even
    `2>/dev/null`, because it can write a file. Pipes are fine (per-subcommand), so
    `render … | tail` auto-approves; just never append `2>/dev/null` to a command you
    want auto-approved.
- No syntax allowlists a compound pattern (rules are per-subcommand), so the fix is
  always behavioral: standalone calls + the right tool. Prefer the clean single-command
  form (`rg PATTERN <path>` over `cat … | grep`; `pip show X` over `pip list | grep X`;
  `git log -n N` over `git log | head`).
- **Explore/search with the Grep/Glob/Read TOOLS, not bash `find`/`grep -r`/`cat`/`sed` —
  and NEVER delegate a broad bash sweep.** The tools don't touch the allowlist so never
  prompt; bash `find`/`sed`, `xargs`/subshells, and any space-path (`"My Documents"/…`,
  the quote breaks the allowlist glob) prompt one at a time — worst CROSS-REPO (reading
  `battleship/` needs space-paths). A general-purpose subagent defaults to bash and fires
  DOZENS of prompts; do repo lookups INLINE with Grep/Read, or constrain a subagent to
  ONLY Grep/Glob/Read.
- **Edits/Writes in the project tree auto-approve** — so before a MAJOR rewrite, commit
  first (the prior version is then recoverable). Deletions (`rm`) and `pkill`/`kill` stay
  gated — don't reach for process-killing as a normal step; if a render seems stuck,
  prefer `run_in_background` + waiting.
- **Syntax-check a scene with `render NN --check`** (instant AST parse of the scene +
  `assets/*.py`, no manim — not `python -c "import ast"`). It also runs the warn-only
  `bpkfigures/lint.py` (flags a raw `Text(...)`, an inlined-hex/palette colour, a one-use
  `run_time` local): a `[lint] file:line` is a nudge, never a gate. When you add a
  mechanical convention, prefer a check there over more prose.
- **For a BACKGROUND render, READ the task's `.output` file** (Read tool) — don't build
  `render … > log; grep` chains (the redirect prompts) or `until grep …; do sleep; done`
  polls (the harness notifies on completion). **Confirm cwd is `scenes/` before a
  background render:** ANY git command (even `git -C`) leaves cwd at the repo root, so a
  later `render NN` fails with "No file matching NN*.py" (visible only in `.output`) —
  re-`cd scenes/` in its own call before every background render batch that follows git.
- **Grab render frames with `render … --frames … --extract`, then READ the PNGs** (Read
  tool) — one allowlisted call, no re-render, no hand-rolled `ffmpeg` chains.

## The Battleship video is the model
Match its visual look and its **sparse on-screen text** — not necessarily its
exact animation primitives. Render ONLY text the script's column 2 explicitly
calls for; no titles/labels/narration that weren't asked for.
- **A number or phrase in the VOICEOVER (column 1) does NOT license putting it ON
  SCREEN — column 1 is what's SPOKEN, column 2 is what's DISPLAYED.** This is the single
  most common way "text not in column 2" sneaks in: a beat's narration cites stats ("__%
  of words start with a consonant", "the 2nd letter is a vowel __% of the time") and the
  agent captions them onto the view — but column 2 only asked for the view/chart. Show
  ONLY what column 2 names; the narrated numbers are HEARD, not captioned. (A chart/view's
  own CANONICAL title from an established convention — e.g. the letter view's "Location
  Frequencies" — IS part of the view and fine; a fresh number, callout, or explanatory
  label is not.) Corollary: a chart the script DOES call for (a pie, a bar) inherently
  shows its value — that's the chart, not an added caption. If you think an extra on-screen
  number/label would genuinely help, ASK; never add it silently. (Bit us repeatedly on
  hangman scene 08: captioned the voiceover's start/end/2nd-position percentages onto the
  frequency grid the script only asked to "put in".)

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
- **A TRANSITION between two framings/states is a SEAM — design it FIRST, working
  BACKWARDS from the more-constrained end.** When a scene morphs between two setups (a
  full-frame chalk game → a zoomed-in decision tree; one board layout → another), the hard
  part is the INTERFACE, not either side. Before polishing either, ask: what must stay
  CONTINUOUS across the seam? — usually the CAMERA, sometimes a shared prop's scale. Then
  make ONE side CONFORM to the other's frame so nothing is bridged mid-animation; do NOT
  build each side in its own natural frame and reconcile them with a moving camera / scale
  ramp during the transition. **A moving camera re-projects EVERYTHING**, so any element not
  explicitly counter-animated to it drifts/pops — every element becomes its own coupled
  sub-problem, and you'll chase symptoms forever (see TRIP-WIRE #2). Concretely: PIN the
  camera at the downstream pose (e.g. the dive's start) for the whole run-up and BUILD the
  upstream content INSIDE that fixed frame (a small design-coords→frame-coords mapping);
  if the camera genuinely must move, ISOLATE the move (nothing else animating during it).
  Corollary: when several beats will hand off to a fixed downstream setup, PROTOTYPE THE
  SEAM before finishing the downstream scene — building the downstream piece first hardens a
  frame without de-risking the interface that actually breaks. (Bit us 2026-08-07: bridging
  a full-frame chalk game to a width-3 tree with a mid-transition zoom coupled every element
  — ~a dozen rounds of band-aids; pinning the camera at the tree pose and placing the chalk
  game in that frame turned the whole transition into a clean in-frame morph in one change.)
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
- **Touching many call sites for ONE logical change is a SMELL — centralize, don't fan out.**
  When you catch yourself "updating every place that formats the value / draws the badge /
  computes the offset," STOP: that's duplication asking to be a single source of truth. Extract
  ONE helper (`_fmt`, `_value_label`, a builder) that every site routes through, so the next
  change to that concept is a one-line edit in one spot instead of a hunt. "I need to find every
  place X happens" is the trigger to refactor, not a checklist to grind. (Bit us on hangman
  scene 05: avg-miss formatting was scattered across ~6 callers with hand-rolled `:g`/hard-coded
  strings/per-call decimals; "2 dp everywhere" only stuck once it routed through one `_fmt`.)
- **REUSE AUDIT before you animate/build a beat: grep how the SAME job is already done — in this
  scene AND its sibling beats — and CALL it; don't hand-roll a worse copy.** The recurring
  failure is reinventing a motion the scene already has (a reveal, a reflow, a transform,
  a label) because you didn't look. Before writing an animation: (1) name the SIBLING beat this
  one mirrors (the previous level's version, the reference scene) and the EXACT helpers/patterns
  it reuses (`_transform_move` ride-in, the `_gap_up` reflow, `_ctree`, the value-label builder);
  (2) if the pattern lives inline in a sibling and you're about to copy it, that's the signal to
  PROMOTE it to a shared helper (ask first) and have both call it. Repeated beats (a per-level
  back-up, a per-turn play-out) are the SAME operation with different handles — write the
  operation once. (Bit us on hangman scene 05: hand-rolled node-reveals, per-beat reflows, and
  the "one at a time" value handling instead of reusing the drill's ride-in / one `_gap_up` /
  one label builder — the user: "you seem to be constantly trying to reinvent things.")
- **When a scene evolves a repeating STRUCTURE, write the RECIPE into its docstring so the
  repeats are mechanical.** A per-level back-up, a per-turn walk-through, a montage of N cases:
  once the first one or two are built and approved, record the step-by-step (which beats, which
  helpers, which convention each step obeys) in the scene docstring — so the remaining repeats
  reuse it verbatim and survive context compaction instead of being re-derived (and re-broken).
  (hangman scene 05's "BACK-UP BEAT RECIPE" is the reference.)
- **When a shared asset ALMOST fits but is missing something, IMPROVE THE ASSET — do
  NOT hand-roll your own version.** This is the DEFAULT, and the single most important
  rule here: if `get_histogram` / a scorecard / a card / any `bpkfigures` helper can't do
  what a scene needs (a dark-theme colour, a written-font label, a categorical/sorted
  mode, a new entrance), the fix is to EXTEND the shared helper so it can — not to build a
  parallel local copy that drifts. Preserve backwards compatibility to whatever degree
  possible (add an OPTIONAL param defaulting to today's behaviour, so existing callers are
  byte-identical), and prefer an additive change. A backwards-compatible ADDITION you can
  just make (and mention at handoff); a change that alters existing behaviour/output or
  can't stay backwards-compatible still gets flagged first (§ "ASK before editing
  bpkfigures/"). Reaching for a local hand-rolled variant because the shared asset "doesn't
  quite do it" is the exact move that produced hangman scene 04's private `_vbars`/
  `_avg_chart` bar charts (and nearly a third copy in scene 03) — improving the shared bar
  chart was the right move all along. Corollary: don't MISUSE a near-neighbour asset to
  dodge the work either (a categorical bar chart is not a `get_histogram`); if the honest
  home doesn't exist yet, build/extend it, don't force-fit.
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
  - **TRIP-WIRE — before you type `FadeIn`/`Write`/`Create`/`LaggedStart`/`GrowFrom`/a
    `.scale()` transition to bring an element ON or OFF screen, STOP and ask "does this
    ELEMENT already appear in another scene?"** A titled view (a heatmap/plot + its
    title), a board, a card, a prop, a tier list — if it (or its kind) shows up
    elsewhere, it almost certainly has an ESTABLISHED entrance; find it and call it. Do
    NOT reason about which primitive "looks right" until you've looked. If the motion is
    trapped in a BASE CLASS or a sibling scene (so your scene can't call it), that is NOT
    licence to hand-roll — PROMOTE it to a shared helper (ASK first) and call it from
    both. (Bit us on hangman 16: the position-frequency view's row-by-row rise + its
    title FadeIn live in `tier_letter_scene`; scene 16 isn't a subclass, so instead of
    extracting them to a shared `views.py` and reusing, a `Write(title)` + ad-hoc
    `LaggedStart(FadeIn…)` got invented — twice. The fix was `assets/views.py`
    (`rise`/`view_title`), used by both.) The reuse map (preflight item 5) must name the
    SOURCE method for every entrance/exit, grep-verified — an entrance you can't name a
    source for is a HARD STOP.
- **The extraction TRIGGER is duplication across the SECOND scene — not "several," not
  "someday."** The moment a prop/layout/motion that already lives inline in one scene is
  needed by a second, EXTRACT it to a shared asset (ASK first for the shared change) and
  have both use it — don't inline a second copy. Leaving it duplicated is what makes the
  NEXT reinvention easy: when reuse means "copy another scene's constants by hand," a
  fresh hand-rolled variant is the path of least resistance, so the duplication silently
  breeds a third divergent copy. Make reuse a one-line import and reinvention stops being
  the easy option. (Bit us: the hangman board lived inline in 02 AND 94; a third scene
  invented its own layout instead — the fix was extracting `assets/game_board.py` and
  migrating all three, which should have happened when the 2nd scene needed it.)
- **Read assets to CALL them, not just to imitate their look.** The reference scene shows
  *which methods do the work*: a keep/reroll beat IS `DiceBoard.keep` + `roll_rest`, not
  hand-placed coordinates. Before a gameplay beat, name the exact asset method each sub-beat
  calls and trace the dice/card state through it (which boxes open, where each die sits).
  Re-deriving something an asset provides — copying its *look* instead of calling it — is
  how reinvention and wrong-box/wrong-dice mistakes sneak in.
- **Don't override a helper's default args** unless asked or genuinely required
  — defaults are deliberate and shared. If a layout seems to "need" a non-default
  value, the layout is probably wrong; fix the layout.
- **When you PORT or ADAPT reference code, carry its constants/defaults over
  VERBATIM — a changed value must be FLAGGED, never silent.** Copying a
  solver/helper/scene from another video (or an earlier file) means its literals —
  heartbeat intervals, tolerances, thresholds, run_times, default args — come across
  UNCHANGED unless the user asked or the new context genuinely forces it (and then
  you SAY SO, at handoff). Do NOT "improve," round, or re-pick a value in passing;
  the source's value IS the spec, same as a user-named one. If you think a different
  value is better, FLAG IT AND ASK — don't substitute. And on handoff of ported code,
  explicitly LIST any value that differs from the source and why, so a silent drift
  becomes visible in review instead of buried. (Bit us: porting hangman's winprob,
  the 60s heartbeat was silently changed to 30s, and a since-removed `eps` was
  carried back in — both unflagged.) Same silently-overriding failure the §Following
  instructions rule names, applied to adapted code.
- Measure real mobject geometry (edges/centers) when placement matters; don't
  approximate positions. For NUMBERS, the bar is even higher: don't guess AND don't
  compute them yourself — SOURCE every displayed value from the user's pipeline, or
  stub-and-flag it. See "The numbers are the product — NEVER invent a calculation".

## Rendering — use the `render` script (`bpkfigures/render.py`)
- **Render with `bpkfigures/render`, NOT hand-rolled `manim`.** Single render path for
  user + agent (the old `manim()` zsh override is gone); run from the `scenes/` dir.
- **The agent ALWAYS passes `--no-sound`.** The 'render finished' chime signals the
  USER's OWN renders, so the agent must never trigger it — append `--no-sound` to every
  `render` invocation (it's a no-op for `--check`/`--state`/`--extract` too, so just
  always include it). A bare `render …` without the flag is the user's; the agent's is
  `render … --no-sound`.
- **Invoke it as BARE `render …` (the shell alias), NOT the `.venv/bin/python -m
  bpkfigures.render` fallback.** Bare `render` auto-approves (allowlist `render *`); the
  fallback needs the space-containing repo path QUOTED, and the quote breaks the allowlist
  glob so it PROMPTS. `cd` to `scenes/` in its OWN call, then `render …` standalone (a `cd
  && render` chain trips the cd-guard). Fall back to venv-python only if bare `render` fails.
- `render 01g` → subscene g (cleans stale, names `01g_<name>.mp4`). Quality defaults to
  HIGH; `--fast` is a quick `-ql` check and `--very-fast` is 3fps @ 256×144. `render
  01g 01h 01i` → several in sequence; `render 01` → full scene. `--recompute` ignores the
  snapshot cache.
- **The agent DEFAULTS to `--very-fast`; escalate to `--fast` ONLY when a check needs
  detail.** Most agent checks are GROSS (did it render, is X present, is the bg navy vs
  light-blue, coarse layout) and 144p answers them — faster wall-clock (big on the heavy
  tree scenes) AND far fewer image tokens when you READ the PNG. Reach for `--fast` only
  when the check genuinely needs pixels: glyph legibility, a subtle artifact the user
  flagged, fine spacing. And remember: motion/feel is the USER's call (stills can't judge
  it), and precise spatial facts come from MEASURED coordinates (`get_left/right/center`
  via a print), not squinting at pixels — so the render is usually just gross confirmation,
  which `--very-fast` covers. Note `--very-fast` at 3fps snaps `--frames T` to the nearest
  ~0.33s frame (coarser sampling; fine for gross checks).
- `render 01g --frames "1.0,2.0,-0.3"` renders THEN extracts those PNG frames (negative =
  seconds-from-end) beside the mp4 and prints paths (`--frames N` = N evenly spaced). Add
  `--extract` to pull frames from the ALREADY-rendered mp4 with NO re-render — then READ the
  PNGs; never hand-roll `ffmpeg` chains.
- `render 01 sub --padded` writes, beside each mp4, a copy with its first/last frame frozen
  at head/tail (default 10s/side, `--padded 3` = 3s) into `padded_videos/` — an editing aid.
  Composes with `--extract` (pad an existing mp4, no re-render); re-encodes (crf 18).
- **`render 99a` renders a STATIC thumbnail automatically** — scene `99` is the reserved
  slot, so any `99*` target passes manim `-s -qk` (4K) with NO flag (the ONE path for
  thumbnails; don't hand-roll `manim -s -qk`). `--fast` gives a quick low-res PNG; the 4K
  PNG is the upload asset (let YouTube do the single compression pass). `--thumb` forces a
  still for a NON-99 scene. Two behaviours: **per-resolution subfolder**
  (`media/images/<scene>/2160p/`, `…/480p/`) so a `--fast` test can't overwrite the 4K
  asset; **change-detection on `render 99 all`** — only thumbnails whose code/reachable
  helpers changed re-render (keyed in a gitignored `.render_keys.json`; `--recompute` forces
  a rebuild).
- `render 01h --state` (no render) prints the mobjects on screen at subscene h's START —
  reason about starting state cheaply.
- **`render` takes a per-scene lockfile**, so a SECOND render of the same scene while one
  runs is REFUSED (concurrent manim runs corrupt the cache); a stale lock from a dead
  process is auto-taken-over. `--check`/`--state`/`--extract` don't lock.
- **On a REFUSED render (lock held): ALWAYS kill the pid the refuse message names, then
  re-render. NEVER wait, and NEVER set up a monitor/`until` loop on the lock.** The user
  prefers you halt their render over waiting — waiting (or worse, building a background
  wait-for-the-lock monitor) is the wrong reflex, full stop. The refuse message names the
  live pid (also in `cache/locks/render-<NN>.lock`); `kill <pid>` (now allowlisted —
  `Bash(kill *)`, no longer prompts), then render. Safe for thumbnails/independent renders;
  for a long scene render a mid-render kill only costs that subscene's snapshot (rebuilt
  next time). Corollary: don't `grep` away the "refusing…" line — surface it so you SEE the
  conflict and kill, instead of stumbling into a silent wait. (Bit us 2026-08-07: twice set
  up an `until [ ! -f …lock ]` wait instead of killing.)
- **Use a PLAIN `kill <pid>` (SIGTERM) — NOT `kill -9`.** `render.py` now forwards SIGTERM/
  SIGINT to the manim child it spawns, so a plain `kill` of the pid the refuse message names
  stops the WHOLE render (wrapper + manim). `kill -9` bypasses that handler and re-ORPHANS
  the manim child (it keeps rendering, ppid→1, writing the media dir → concurrency/corruption
  if you then start your own render). If you ever DID orphan a manim child, find it with
  `ps -Ao pid,ppid,command | grep manim` and `kill` that pid directly, then `--recompute` the
  next render. (Bit us 2026-08-07: `kill <render-pid>` before this fix left the manim child
  running.)
- **NEVER `rm`/delete a lock file — to take over, KILL THE PID the refuse message names,
  full stop.** The lock is an ACTIVE mutex held by a LIVE process, not stale detritus; the
  render script AUTO-TAKES-OVER a lock whose holder is dead, so killing the holder is
  sufficient AND complete — the file cleans itself up. Manually `rm`-ing
  `cache/locks/render-<NN>.lock` bypasses the mutex and lets TWO renders run the same scene
  CONCURRENTLY, which is the exact cache-corruption the lock prevents. "Free the lock" ≡
  "kill its holder", NEVER "delete the file". If a render then seems refused by a truly dead
  lock, kill nothing and just re-run — the auto-takeover handles it. (Bit us 2026-08-07: an
  `rm -f` of the lock ran the agent's render on top of the user's, orphaning the user's
  manim child and risking cache corruption — recover with `--recompute`.)
- **`InvalidDataError` at the concat step = a CORRUPT PARTIAL MOVIE FILE from an interrupted
  render — find + delete it, it's NOT a scene bug.** A killed/crashed render truncates the
  partial it was mid-writing (no `moov` atom), and manim REUSES partials by hash — so a LATER
  render of ANY subscene whose concat list includes that partial fails at the ffmpeg combine
  with `InvalidDataError: Invalid data found`. The traceback points at manim's
  `combine_to_movie`, not your code, which is the tell. Fix: open the scene's
  `media/videos/<scene>/<res>/partial_movie_files/<Scene>/partial_movie_file_list.txt`,
  `ffprobe` each listed file (the corrupt one errors `moov atom not found`), delete THAT
  file, and re-render (manim regenerates it clean). Scan the whole `partial_movie_files/
  <Scene>/` for any that fail `ffprobe` to catch others. Nuking the folder also works
  (regenerable build artifact) but forces a full re-render. (Bit us 2026-08-13: agent
  fast-iterate kills left one truncated partial that blocked `render 18a` and the full scene.)

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
- **Inspect a render ADVERSARIALLY — not "the end looks right".** For any change, check
  (a) the SPECIFIC element that changed + its neighbours, (b) the CORNERS/CENTRE for
  leftovers/duplicates, and (c) for a MOTION change, at least one MID-frame. The END
  frame HIDES objective motion bugs — a lingering copy, a switched-out source, a blob
  morph — even when it can't judge feel. "End grid looks right → done" shipped a doubled
  tree, a source switch-out, and lingering tallies on hangman `05optimal` before the user
  caught them. (This is OBJECTIVE artifact-hunting via mid-frames; motion FEEL is still
  the user's call, per the trip-wire below.)
- **When the user names a SPECIFIC beat/element as broken — or asks whether you CHECKED
  it — render THAT EXACT thing and LOOK at it FIRST, before any other work and before
  answering.** Do NOT verify a NEIGHBOUR (the beat before/after, the empty state before
  the change, the end state) and infer the flagged thing works; do NOT answer "did you
  check X?" by talking about something else. Render X, read the frame, THEN respond. A
  render of the specific broken beat is the ONLY acceptable evidence that it's fixed —
  a passing `--check`, a neighbour that looks right, or an OLD frame from before a
  restructure are all worthless here. (Bit us badly on hangman scene 16: the tier-fill
  beats e–i rendered NOTHING for several iterations; each "verification" looked only at
  the neighbouring beats — the empty grid before the fills, the win after — and inferred
  the fills worked from a stale pre-restructure frame, so the break survived multiple
  rounds, including one where the user asked point-blank whether it had been checked and
  got an answer about an unrelated bug instead of a render.)
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
  - **If the problem IS motion — drift, pop, a fade that "reads wrong", camera coupling —
    it is UNVERIFIABLE from a still, FULL STOP.** Say so and hand the render to the user;
    do NOT declare a motion beat "fixed"/"working"/"verified" from a frame. Doing so spins
    a poison loop: patch a symptom → "confirm" it from a still → ship → the user watches the
    VIDEO and finds it still broken → repeat. (Bit us 2026-08-07 for ~a dozen rounds on one
    transition: each still "looked right" while the motion was wrong.) A still can confirm
    the END STATE is correct; it can say NOTHING about the path taken to get there.
- **TRIP-WIRE #2: the SAME thing broke twice? STOP patching symptoms — name the ROOT CAUSE
  and the fork out loud before attempt three.** Two flavours, both fatal to iterate past:
  (a) a repeated *comprehension* miss (wrong game state, quantity, turn) — the fix is a
  QUESTION about what the beat depicts, not another guess; (b) a repeated *mechanism* miss —
  the same machinery keeps producing new artifacts (fix the drift → now it pops → fix the
  pop → now an edge shows). (b) is an ARCHITECTURE problem, not an implementation bug: the
  symptoms are all downstream of ONE wrong structural choice, so patching them one at a time
  never converges. Stop, state "these are all symptoms of X", and either reframe X or surface
  the design fork to the user — do NOT ship attempt three of a band-aid. (Bit us 2026-08-07:
  letter-drift/dot-pop/board-edge were all one moving-camera coupling; ~10 band-aids before
  the one-line reframe — pin the camera — dissolved them all.)
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
- **A complex/novel beat: LOCK THE STATIC END-FRAME before animating.** Build the final
  composition, render the STILL, iterate structure/layout/colour/text to the user's
  approval FIRST — only then wire the motion. Animating while the target still changes
  guarantees rework: every design tweak invalidates the motion. (Bit us on hangman
  `05optimal` e/f: ~5 rounds re-doing motion on a static design still changing under it.)
- **Design an animation as a per-mobject LEDGER, not a choice of primitive.** Before
  coding a transition, write down for EACH on-screen mobject: does it MOVE (to where),
  TRANSFORM into which target, get CREATED, or get DESTROYED (how). REUSE existing
  mobjects by default; only create genuinely-new things. Transitions are PIECE-BY-PIECE
  (each node → its node, each edge → its edge); a whole-object `Transform`/
  `ReplacementTransform`/`TransformFromCopy` of a COMPOSITE (a tree, a card) pairs
  submobjects by index and reads as a chaotic blob morph or a switch-out. Give the
  builders ROLE HANDLES (`.root_dot`, `.kid[pat]`, `.levels`) so the pairing is by role,
  not fragile indices. (Bit us on `05optimal` e/f for ~6 rounds of exactly this.)
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
  - **A whole-object `Transform`/`ReplacementTransform`/`TransformFromCopy` of a COMPOSITE
    (tree, grid cell) pairs its submobjects BY INDEX** → a blob morph (parts fly to the
    wrong counterparts). Pair pieces EXPLICITLY by role and transform each to its match.
  - **Regrouping existing submobjects into a NEW `VGroup`, animating that, then
    `remove(original_container)` leaves the pieces ON SCREEN.** The original container is
    no longer in `scene.mobjects` (only its pieces are, added top-level), so `remove`/
    `FadeOut(container)` is a no-op → a lingering duplicate. Track and fade the ACTUAL
    on-screen mobjects, not the stale container.
  - **After a copy-based reveal (`TransformFromCopy` into nested pieces) the on-screen
    mobjects are dual-tracked** (top-level + nested), so later `FadeOut`/`remove` misbehave.
    `self.clear()` + `self.add(*clean_groups)` at the end re-establishes clean containers
    (seamless — the pieces are already at their final pose).

## Git / new repos
- **Commit and push WITHOUT asking — this OVERRIDES Claude Code's default.** In this
  project the agent has standing permission to checkpoint WIP, commit before a major
  rewrite, and push when a chunk is done. **Work on `main` — do NOT create side
  branches** (see § Concurrent sessions — one shared branch; a worktree in a separate
  window is the only sanctioned isolation). Keep the commit-message footer convention.
- **Commit at each working checkpoint — do NOT batch a multi-step change into one big
  commit.** The user prefers frequent, granular commits (one per working step that leaves
  the code good), staging each step's files by explicit path.
- **Write commit messages as literal `-m` flags (repeat `-m` per paragraph) — NEVER
  `git commit -m "$(cat <<EOF … EOF)"`.** The `$(…)`/heredoc is a command substitution,
  which NEVER auto-approves (forces a prompt) regardless of how the git allow-rules are
  set — the biggest single source of commit prompts a whole session (2026-07-27). Use
  `-m "subject" -m "body para" -m "footer"` instead.
- **Keep `<` and `>` OUT of commit-message text (and any allowlisted command's args) —
  they read as REDIRECTIONS and force a prompt even inside a quoted `-m` string.** The
  permission checker scans the raw command for `<`/`>` (per the redirection rule above)
  BEFORE it honours quoting, so an arrow like `A->B`, `X <-> Y`, or `foo->bar` in a
  commit message trips it every time (bit us 2026-08-11 — an `A <-> B` message prompted).
  Write "A to B", "X vs Y", "foo yields bar" — plain words, no angle brackets. Same for
  `|`, `&`, `;`, `(`, `)` if they'd land unquoted-looking in a message; safest to avoid
  shell metacharacters in `-m` text entirely.
- **For the CURRENT workspace repo, use BARE `git` (no `-C`).** Bare `git add <path>` /
  `git commit -m …` match the standing `Bash(git add *)` / `Bash(git commit *)` rules and
  do NOT prompt (verified 2026-07-28: a bare `git commit` ran clean where the SAME
  `git -C "<workspace abs-path>" commit` had prompted). **Do NOT use `git -C <abs-path>`
  for the workspace** — it prompts; an earlier "`git -C <working dir>` auto-approves"
  reading was a session-approval artifact, not the rule actually matching. cwd stays
  inside the workspace and git resets it to the repo root after any git call, so bare
  `git add <path-relative-to-cwd>` then a bare `git commit` just works. `git -C` is needed
  for OTHER repos (`bpkfigures`/`dotclaude`/umbrella) where cwd can't reach them; the
  allowlist now carries a catch-all **`Bash(git -C *)`** (a single trailing wildcard that
  matches any `git -C …`, spaces and all — the per-subcommand `git -C * <sub>:*` rules
  fail on space-paths) so those are prompt-free too. It's broad (any subcommand, any dir),
  so don't run destructive git via `-C` casually.
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
- **Before the AGENT spins up a TEST/scratch scene, check the number isn't taken** —
  `ls animations/scenes/` for ANY file with that 2-digit prefix. Two files sharing a
  prefix (`95treewalk.py` + `95letterheat_test.py`) COLLIDE: `resolve` slices
  `target[:2]`, so `render 95` is ambiguous and addressing breaks. And usually a new
  test scene isn't even warranted — the work belongs in an EXISTING scene (more
  letter-view beats → the existing letter-view test scene, not a fresh file). So for
  agent-initiated test scenes: reuse the relevant scene, or pick a FREE prefix; don't
  blindly `Write` a new `NN<name>.py`. (This bit us: an unprompted new `95` test file
  collided with `95treewalk.py`.)
- **For CONTENT scenes the number is the USER'S call, NOT a free-slot search.** They
  usually already have the number in mind, and may deliberately INSERT a scene mid-
  sequence and bump the rest down (a renumber). Don't auto-avoid a "taken" number there
  or pick your own — follow the user's intended numbering, and do the renumbering they
  ask for.
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
  pass, not just content. Write this out as a REUSE MAP, and put it in the scene's
  DOCSTRING (not just the chat) so it's permanent, greppable, and reviewable later.**
  One line per major element → the EXACT existing source it comes from: text →
  `crisp_text` (right `font_size`/`color`), never a raw `Text`; colours → the specific
  `style.py`/`config.py` name (score green/red, gold highlight, `ACCENT_FILL`), never a
  hand-picked hex; a prop / its ENTRANCE / box fill / flash / on-screen LAYOUT → the
  existing asset or a SIBLING scene's actual constants (`Scorecard.slide_in`, `flash_rows`,
  dice helpers, `game_board`'s `BLANK_*`/`HANG_*`), never a hand-rolled FadeIn or a
  re-derived layout. **This is the gate that catches REINVENTION: the failure mode isn't
  copying a constant and tweaking it — it's building a plausible NEW variant of something
  that already exists (a whole board layout, a chart style). Naming the source for every
  element forces you to look; an element you CANNOT name an existing source for is a HARD
  STOP — grep the assets AND the sibling scenes, and if there's genuinely no source,
  FLAG-and-ASK before building it. Never invent a variant of a thing a sibling scene
  already renders.** (Because the map is user-visible at preflight, an invented entry gets
  caught BEFORE any code is built on it — the cheapest possible point.) **Re-run at
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
- **SUBSCENE COUNT MUST EQUAL BEAT COUNT — one `@subscene` per `---`/`—`-delimited
  script beat, NEVER more.** The subscene letters (a, b, c…) map 1:1 onto the beats, in
  order. Do NOT invent extra subscenes, and do NOT split ONE beat across several. The
  trap is a MULTI-STEP beat — a whole played-out game, a montage, a several-guess
  sequence: it is written as ONE beat (one `—` segment), so it stays ONE subscene whose
  BODY unrolls the steps (a lockstep `for` over the guesses, or explicit per-step calls
  each with its own `run_time`). It does NOT become one subscene per guess. (A per-guess
  subscene is right ONLY when the SCRIPT gives each guess its own beat — e.g. the
  standalone 94chalkgame, where each guess IS a `—` segment; contrast the game INSIDE
  hangman scene 16's single beat j, which is one subscene.) Conversely a no-op beat (the
  thing it asks for is already true — "move the list to centre" when it's already centred)
  still gets its beat's subscene, but with an EMPTY/near-empty body (its VO plays over the
  static hold) — do NOT replace it with an invented animation. **At handoff, re-zip:
  list the beats a,b,c… and confirm exactly one subscene per beat, same letters.** (Bit
  us on hangman 05 and 16: a played-out game and an "establish" flourish were split/
  invented into extra subscenes, drifting the letter↔beat mapping the user tunes against.)
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
- **A CONTENT choice — WHICH words / examples / samples a beat SHOWS — is governed by the
  beat's VOICEOVER (`Script.md` column 1), not just column 2's mechanic; CITE the clause it
  serves at the point of decision.** Picking which items to display (the cutoff-region
  words, an example set, a sampled subset, a montage's words) must SERVE the voiceover's
  point, not merely satisfy column 2's slot. Before/while choosing, re-read that beat's
  column-1 voiceover, let its INTENT constrain the pick, and then RECORD that intent as a
  comment BESIDE the content flag (in the data module / asset) so the pick — and the next
  edit — can't drift from it. This extends the build-preflight "read column 1, not column 2
  alone" to DATA authoring and ITERATION, where the mechanic can look right while the
  SELECTION quietly misses the point. There's no static check for "does this content serve
  the voiceover" (it's semantic), so the enforcement IS this discipline: the flag cites its
  clause. (Bit us: scene-03's cutoff words were all recognizable, silently breaking the
  voiceover's "a cutoff where I knew about HALF the words near it" — the whole point of the
  beat. The fix was a familiar/obscure mix + the intent recorded on the flag.)
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
- **Do NOT offer, propose, or ask about a "timing pass" — the user ALWAYS does timing
  themselves, AFTER recording the voiceover.** Leave every `run_time`/`wait` as an inlined,
  editable guess (per the run_time rules) and move on; do NOT end a handoff with "want me
  to do a timing pass?" or similar. Timing is entirely the user's, done later against the
  VO — the agent's job is the objective build, not the pacing. (No need to enumerate the
  timing knobs at handoff either; they're all inline literals the user will sweep anyway.)
- **Every animation/wait exposes its `run_time`** in the subscene body so the user can
  retime — full rule in the run_time note under Scene structure.
- **Use extended thinking for scene-building** (geometry + sequencing): the costly mistakes
  are spatial (overlaps, a label centered on the panel edge not the cell, dice into a guide
  line) and timing ones — working coordinates out before coding prevents a render
  round-trip that dwarfs the thinking cost. Skip it for quick edits/lookups/config.
- **Build scenes ONE AT A TIME, by yourself — do NOT fan scene-building out to
  sub-agents.** A bulk pass (all scenes at once, and via agents) lost fidelity to
  column 2 and injected unwanted on-screen text — the user stashed the whole commit.
  One scene, implemented directly and iterated with the user, is the reliable path.
  (Read-only research/audit agents are fine; this is about scene CONSTRUCTION.)
- **For an algorithm/perf/math EXPERIMENT the user proposed, hand over a clean runnable
  PROTOTYPE early — don't run long measurement loops first.** The user is hands-on and
  drives the experimentation themselves. Put the prototype somewhere durable (a committed
  `math/` script, not scratchpad), expose the knobs clearly, do ONE quick correctness
  smoke-test, then hand off with a short usage note. Offer to help interpret or extend, but
  don't run long comparison sweeps on their behalf unless asked.
