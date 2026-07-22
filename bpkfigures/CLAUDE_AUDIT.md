# CLAUDE.md audit ledger

Tracking the conservative shrink of the shared `CLAUDE.md` (1000+ lines, mostly
scar tissue). The plan: **promote enforceable rules into mechanical checks
(`lint.py` / hooks) WITHOUT deleting the prose yet.** Once a check is trusted in
practice, the prose it fully covers becomes removable. This file records what has
been promoted and — honestly — how much prose each promotion actually makes
removable, for a later review pass.

**Nothing here is removed yet.** Each entry is a *candidate*, flagged with how
complete its mechanical coverage is. Patrick reviews and decides removal.

Legend for coverage:
- **FULL** — the check catches every form of the violation; the prose is safe to delete.
- **PARTIAL** — the check catches the common/mechanical form but not all of it; keep a trimmed conceptual note.
- **BACKSTOP** — the check is defense-in-depth; the real failure mode is non-textual (a value recalled in your head), so the prose must STAY. Value is catching the slip, not shrinking the doc.

---

## Promoted so far

### 1. Recalled default frame bounds → `lint.py` (7.11 / 14.22 float literal)
- **Commit:** bpkfigures `898e991`
- **Enforces:** shared CLAUDE.md "The frame is 16 wide × 9 tall … do NOT hardcode
  or assume manim's default 7.11/4.0" (§ Shared visual vocabulary) and the verify
  note "frame bounds recalled as 7.11/4.0 instead of the real 8.0/4.5" (§
  Rendering during iteration).
- **Coverage: BACKSTOP.** The lint only sees a `7.11`/`14.22` *literal in code*.
  The scene-06 bug was recalling the wrong bound *in a mental calc* — no literal
  ever appears, so the lint can't catch it. **Keep the prose.** This is worth
  having anyway (it catches the one form that IS textual), but it does not shrink
  the doc. Removable text: **none.**

### 2. Scaled scorecard factory → `lint.py` (`get_scorecard(...).scale(...)`)
- **Commit:** bpkfigures `898e991`
- **Enforces:** yahtzee CLAUDE.md "Do NOT `.scale()` or hand-place two cards
  (scene 04b did and it read tiny)" (§ Scorecard) and the canonical-patterns-index
  row "never `.scale()`/hand-place" (shared).
- **Coverage: PARTIAL.** Catches `.scale()` chained on the factory. Does NOT catch
  (a) hand-placing two separate cards without the factory, or (b) `.scale()` on a
  card held in a variable across statements. **Trim, don't delete:** the `.scale()`
  clause is now backstopped; the "hand-place" clause is not. Removable text:
  **the "`.scale()`" half of that clause, once trusted — keep the "hand-place" half.**

---

## Observations for the broader audit (not yet acted on)

- The highest-value promotions will be rules that are FULLY mechanical (a check
  can catch every form), not the BACKSTOP kind above. Candidates to assess:
  raw `RoundedRectangle(` in a scene (→ get_card), a `self.wait(` as the first/last
  statement of a subscene body (framework owns the boundary holds), a `run_time=`
  literal missing on a `self.play(` (default-1.0 reliance).
- The bigger doc-shrink lever is probably STRUCTURAL, not per-rule: splitting the
  1000-line doc into a short always-loaded core + a grep-able appendix of
  situational war-stories. That removes nothing but changes what must be obeyed
  every session. Assess separately from the lint promotions.
