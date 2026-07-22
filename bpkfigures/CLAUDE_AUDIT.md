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

## Classification pass (sample — nothing removed yet)

**Correction (the appendix trap):** an "appendix" only read when the agent
decides to grep it is subject to the exact unreliable-recall failure mode
CLAUDE.md exists to avoid — the doc loads unconditionally *because* we can't
count on on-demand lookup. So the split that matters is NOT importance, it's:
- **PROACTIVE** — must fire unprompted (the trigger is the agent noticing the
  situation). Can NEVER leave always-loaded context. Stays.
- **REFERENCE** — consulted only when the agent already has a concrete question;
  not knowing it proactively causes a lookup, not a silent error. Can leave
  always-loaded context **only if a hook mechanically injects it** on a
  deterministic trigger (e.g. touching `scenes/NN*.py` injects scene rules).
  Without that hook, relocating it is a downgrade.

So the safe shrink levers that DON'T weaken the load-everything guarantee:
- **DEAD** — redundant (restated elsewhere) / superseded / done-migration text.
  Removing a duplicate doesn't reduce coverage.
- **TRIM** — cut history/verbosity from a rule that STAYS loaded; just shorter.
- **CHECK** — mechanically enforceable (→ `lint.py`); prose stays until trusted.

The CORE/APPENDIX relocation is gated on building the injection-hook — a separate,
bigger decision, NOT part of the conservative shrink.

### Sample: "Snapshot cache" section (lines ~630–661)
- **Bullet 1** (loads latest snapshot, replays gap) — **REFERENCE.** Its PROACTIVE
  consequence ("render only the changed subscene") is already loaded at 665–667,
  so the mechanism itself is consult-on-question. Relocatable ONLY via hook;
  otherwise stays. No safe removal now.
- **Bullet 2** (snapshot key composition, what invalidates what) — **REFERENCE.**
  The proactive nugget ("shared-asset edit invalidates all → batch") is loaded at
  668. Composition detail is consult-on-question. Same: hook-gated, else stays.
- **Bullet 3** (module-constant capture, rewritten 2026-07-22) — **TRIM.** Rule
  stays loaded; cut the ~80% that is history. Once trusted, shrink to ~1 line:
  *constant edits invalidate; if one seems ignored → `--recompute` (rare edge:
  address-repr objects / huge arrays).* SAFE removal (history only).
- **Bullet 4** (don't build un-picklable objects in `setup_scene`) — **PROACTIVE,
  CONFLICTS with line 378.** ⚠️ 378 lists `ValueTracker counters` as un-picklable
  (→ body); 656 says keep `ValueTracker` in setup (picklable). Truth: a bare
  ValueTracker IS picklable (setup fine); an `always_redraw`+lambda is NOT (body).
  656 is closer; 378 is imprecise. **Reconcile, don't delete** — stays loaded.
- **Bullet 5** (auto-cleans stale / old `manim()` override removed / quality HIGH)
  — **DEAD (redundant).** All three clauses restated at 569 and 580–581; the
  "override removed" clause is a done past-tense migration note. SAFE removal.

**Section verdict (corrected):** the safe, load-guarantee-preserving wins are
just **bullet 5 (DEAD)** and **bullet 3's history (TRIM)** — a modest shrink, not
"half the section." Bullets 1–2 only shrink if we build the injection-hook. One
contradiction surfaced (378↔656) to reconcile. Lesson: DEAD+TRIM are the honest
conservative levers; relocation is a bigger, hook-gated project.

## DEAD/TRIM sweep — full doc (verified, nothing removed yet)

Swept all 19 sections. Findings below; the high-confidence DEAD items were
grep-VERIFIED against the file (line numbers exact ±1). The Canonical patterns
index (123–163) and the new-scene PREFLIGHT (904–922) restate rules BY DESIGN
(pointers/gates with explicit cross-refs) — deliberately NOT flagged.

### DEAD — high confidence (verified duplication)
1. **run_time-on-@subscene-signature** rule stated 3×: primary **481–487**;
   restated at **961** (in 959–963) and **1000–1001** (in 999–1003). The two
   restatements sit inside section-local lists (Starting a new scene / Process),
   so the call is "point to 481–487 vs restate" — not a blind delete. ~6–9 lines.
2. **`manim()` zsh override "is gone / was removed"** — DONE-MIGRATION note at
   **569** and **660**. Not a rule; removable from both. ~2 lines.
3. **cd+git always prompts / run git standalone** — full rule 2×: **322–327**
   (§ Shell commands) and **815–820** (§ Keep commands). Drop one. (Line 768 is a
   pointer — keep.) ~6 lines.
4. **Chains auto-approve; separators split, control-flow never does** — full rule
   2×: primary **317–336** (§ Shell commands, more complete), restated **760–769**
   (§ Keep commands). Fold 760–769 into A. ~10 lines.
5. **Quality defaults to HIGH / --fast / auto-cleans stale** — primary **580–582**
   (+ 580 for auto-clean); restated at **659–661**. Remove 659–661. ~3 lines.

### DEAD — medium confidence (needs your eye; the "dup" adds a nuance)
- Recurring-motion-to-asset: **529–538** vs **547–558** (B is a superset w/ the
  "check scenes too" nuance + scene-06 example → primary B; A candidate to merge).
- Explicit-path staging: **850** vs **258–261** (258–261 fuller; 850 compact).
- "Implement literally / exact wording is the spec": **980–981** vs **9–12**
  (980–981 adds the "disappear ≠ fade" example).

### TRIM — history/war-story tails to cut from rules that STAY
173–178 (scene-06 frame calc) · 438–441 (`_zero_flash`) · 518–525 (grey `0`) ·
549–551 (`_show_keep`) · 650–655 (scalar-whitelist backstory, from our own fix) ·
680–685 (480p/wrong-constant) · 691–694 (card-taller-than-frame) · 702–703
(scene-04 seams) · 724–727 (scene-04 montage) · 975–977 (scene-11c Ones).
Each ~2–6 lines of history; the rule itself stays.

### Rough totals
DEAD-removable ≈ 35–45 lines (25–30 high-confidence). TRIM ≈ 30–40 lines. Net
potential shrink ≈ 65–85 lines (~7% of the doc) with ZERO loss of a live rule —
all of it is duplication, done-migration notes, or backstory.

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
