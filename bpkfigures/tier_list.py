"""Tier list — the alphabet ranked into tiers: a coloured label CELL + a dark
content PANEL per tier, letters dropped into the panels.

PROMOTED from hangman/animations/assets/tier_list.py (2026-09-29) when wordle became
its second user. Hangman keeps its own copy UNCHANGED (shipped video, forward-only
promotion rule); new work imports this one. What moved is the video-agnostic part:
the builder, the label factories, the palette, filling, the comparison morph and
emphasis. The VIDEO-SPECIFIC letter orderings (which letter sits in which tier) did
NOT move — they are sourced data and live with each video.

Lives on the BRAND light-blue background (crisp_text labels, dark charcoal content
panels, classic S-tier rainbow label cells).

Stateless builder: `get_tier_list(labels)` returns a VGroup with handles
    .rows[i]      VGroup(cell, panel, label, contents) for tier i, top→bottom
    .cells / .panels / .labels / .contents   parallel lists
plus geometry (`.panel_left_x`, `.row_cys`) so a scene can drop letters into a
tier's `.contents`. Resting state is FULL opacity; `emphasize(tiers)` spotlights by
DIMMING every other tier, `reset` clears it.

Additions over the hangman copy (all backwards compatible):
  * a TOP group with ▲/▼ halves colours correctly: TOP▲ leans toward a deeper red
    notionally above TOP (`_A_ABOVE_TOP`, mirroring `_A_BELOW_LOW`) and TOP▼ toward
    HIGH, not MID. No hangman list ever split TOP, so nothing it drew changes.
  * `morph_into` accepts a `dst` with MORE rows than `src`: a dst row no src row
    maps onto has its cell/panel/label fade in during the morph.
  * `fill_tier` requires its letters (there is no default ordering here).
"""
import numpy as np
from manim import *

from bpkfigures.style import *   # crisp_text, style colours, LIGHT_* palette


# ── tier vocabulary ───────────────────────────────────────────────────────────
# Default 7 tier labels (classic S-tier grades) and their eventual NAMES.
LETTER_LABELS = ["S", "A", "B", "C", "D", "E", "F"]
NAME_LABELS   = [("TOP",  None),      # tier 0
                 ("HIGH", "up"),      # tier 1
                 ("HIGH", "down"),    # tier 2
                 ("MID",  "up"),      # tier 3
                 ("MID",  "down"),    # tier 4
                 ("LOW",  "up"),      # tier 5
                 ("LOW",  "down")]    # tier 6

# Letter layout inside a panel: fixed slot pitch + edge buff. The default panel is
# SIX letter slots wide (the hangman default, which was sized to its fullest tier);
# pass `panel_width=panel_width_for(letters)` for a list whose fullest tier differs.
LETTER_PITCH = 0.82
LETTER_BUFF  = 0.26


def panel_width_for(letters):
    """Panel width fitting the FULLEST tier of `letters` with equal side margins (a
    double counts `token_slots` letters)."""
    return 2 * LETTER_BUFF + max(sum(token_slots(c) for c in t) for t in letters) \
        * LETTER_PITCH


_DEFAULT_PANEL_W = 2 * LETTER_BUFF + 6 * LETTER_PITCH
# Classic S-tier rainbow (LIGHT_PALETTE ramp + a neutral grey for the last tier) —
# used while the labels are the S,A,B,… GRADES.
TIER_GREY   = ManimColor("#9AA0A6")
TIER_COLORS = [LIGHT_RED, LIGHT_ORANGE, LIGHT_YELLOW,
               LIGHT_GREEN, LIGHT_BLUE, LIGHT_PURPLE, TIER_GREY]

# Once the tiers are NAMED, the palette spreads the four name-groups EVENLY across
# the rainbow — TOP red → LOW blue, with HIGH and MID spaced evenly between (the
# LIGHT_* ramp, red…blue). Within a pair the ↑ tier leans slightly toward the group
# ABOVE and the ↓ tier toward the group BELOW (by ±_LEAN), so the two tiers of one
# word stay visibly CLOSER to each other than to the adjacent tier (grouped, NOT a
# gradient).
def _rainbow(t):
    """Colour at fraction `t` along the LIGHT_* rainbow red…blue (0 = red … 1 = blue)."""
    stops = LIGHT_PALETTE[:5]   # red, orange, yellow, green, blue (drop purple)
    t = min(max(t, 0.0), 1.0)
    seg = t * (len(stops) - 1)
    i = min(int(seg), len(stops) - 2)
    return stops[i].interpolate(stops[i + 1], seg - i)

_A_TOP       = _rainbow(0.0)                        # red
_A_HIGH      = _rainbow(1 / 3)                      # evenly between red and blue
_A_MID       = _rainbow(2 / 3)
_A_LOW       = _rainbow(1.0)                        # blue
_A_BELOW_LOW = ManimColor("#2B6CB0")               # deeper blue, notional below LOW
_A_ABOVE_TOP = ManimColor("#C53030")               # deeper red, notional above TOP —
                                                   # the mirror of _A_BELOW_LOW (both
                                                   # are the Tailwind -700 of their hue)
_LEAN = 0.15                                         # small: keep same-word tiers grouped

NAME_TIER_COLORS = [
    _A_TOP,                                     # TOP
    _A_HIGH.interpolate(_A_TOP, _LEAN),         # HIGH ↑  → toward TOP  (above)
    _A_HIGH.interpolate(_A_MID, _LEAN),         # HIGH ↓  → toward MID  (below)
    _A_MID.interpolate(_A_HIGH, _LEAN),         # MID  ↑  → toward HIGH (above)
    _A_MID.interpolate(_A_LOW, _LEAN),          # MID  ↓  → toward LOW  (below)
    _A_LOW.interpolate(_A_MID, _LEAN),          # LOW  ↑  → toward MID  (above)
    _A_LOW.interpolate(_A_BELOW_LOW, _LEAN),    # LOW  ↓  → toward deeper purple (below)
]

# Group base colours + the neighbour each up/down tier leans toward. Drives both the
# fixed NAME_TIER_COLORS above and name_colors() for a CUSTOM tier structure (e.g. the
# 6-tier frequency list, whose single HIGH takes the base colour with no lean).
_GROUP_BASE  = {"TOP": _A_TOP,  "HIGH": _A_HIGH, "MID": _A_MID,  "LOW": _A_LOW}
_GROUP_ABOVE = {"TOP": _A_ABOVE_TOP, "HIGH": _A_TOP,  "MID": _A_HIGH, "LOW": _A_MID}
_GROUP_BELOW = {"TOP": _A_HIGH, "HIGH": _A_MID,  "MID": _A_LOW,  "LOW": _A_BELOW_LOW}


def name_colors(tier_names):
    """Per-tier cell colours for a named tier structure `tier_names` (list of
    (word, arrow)). A single tier of a group (arrow None) takes the group base; an
    up/down tier leans by ±_LEAN toward the group above/below; a "square" (middle) tier
    takes the group base. name_colors(NAME_LABELS) reproduces NAME_TIER_COLORS."""
    out = []
    for word, arrow in tier_names:
        base = _GROUP_BASE[word]
        if arrow == "up":
            out.append(base.interpolate(_GROUP_ABOVE[word], _LEAN))
        elif arrow == "down":
            out.append(base.interpolate(_GROUP_BELOW[word], _LEAN))
        else:
            out.append(base)
    return out


PANEL_FILL   = ManimColor("#2B2B2B")   # dark charcoal content row (letters pop on it)
PANEL_STROKE = ManimColor("#15151A")
LABEL_COLOR  = BLACK                   # reads on every bright cell + the grey
LETTER_COLOR = WHITE                   # (legacy) neutral tier letter colour
DIM_OPACITY  = 0.28                    # a tier's muted / un-emphasised look

# Vowel/consonant colouring of the letters (the vowel/consonant arc, scene 08 on):
# BRIGHT on the dark tier panels; DARK on the light bg (the big corner letter + the
# ngram anchor). Consonants keep the existing blue (ACCENT_FILL) on the light bg.
VOWELS = set("aeiouy")                 # Y always a vowel (matches scene 08)
VOWEL_TILE_COLOR = LIGHT_RED           # vowel letter on a dark tier panel
CONS_TILE_COLOR  = LIGHT_BLUE          # consonant letter on a dark tier panel
# On the light bg, consonants keep the existing ACCENT_FILL blue (LIGHT_BLUE would wash
# out). Vowels: the big corner letter + ngram anchor use CRIMSON (the yahtzee scorecard
# Yahtzee/Total-row red); the position-frequency heatmap keeps the pure heatmap red.
VOWEL_INK_COLOR  = CRIMSON             # vowel big-letter + ngram anchor
CONS_INK_COLOR   = ACCENT_FILL
VOWEL_HEAT_COLOR = CRIMSON             # vowel heatmap high end (match the corner/ngram)
CONS_HEAT_COLOR  = ACCENT_FILL


def tile_color(ch):
    """Bright tier-panel colour for `ch`: vowel red / consonant blue."""
    return VOWEL_TILE_COLOR if ch.lower() in VOWELS else CONS_TILE_COLOR


def ink_color(ch):
    """Big corner letter + ngram anchor colour for `ch` on the light bg:
    vowel CRIMSON / consonant blue."""
    return VOWEL_INK_COLOR if ch.lower() in VOWELS else CONS_INK_COLOR


def heat_color(ch):
    """Position-frequency heatmap high-end colour for `ch`: vowel red / consonant blue."""
    return VOWEL_HEAT_COLOR if ch.lower() in VOWELS else CONS_HEAT_COLOR


# ── label factories (Transform one state into the next across beats) ───────────
def letter_label(i, *, height=0.44, color=LABEL_COLOR):
    """The grade label for tier `i` (S, A, B, …)."""
    lab = crisp_text(LETTER_LABELS[i], font_size=FONT_SIZE_LG, color=color,
                     weight=BOLD)
    return lab.set_height(height)


def number_label(i, *, height=0.44, color=LABEL_COLOR):
    """The grade letter's numerical position in the alphabet (S→19, A→1, …) —
    the deliberately-absurd beat before the tiers get real names."""
    n = ord(LETTER_LABELS[i].upper()) - 64
    lab = crisp_text(str(n), font_size=FONT_SIZE_LG, color=color, weight=BOLD)
    return lab.set_height(height)


def name_label_spec(word, arrow, *, height=0.34, color=LABEL_COLOR):
    """The named tier label for a (word, arrow) spec: a word (TOP/HIGH/MID/LOW) with an
    optional marker to its RIGHT: an up/down arrow, or "square" for the MIDDLE tier of
    a three-way split (▲ ■ ▼). `height` is the word's cap height."""
    txt = crisp_text(word, font_size=FONT_SIZE_LG, color=color, weight=BOLD)
    txt.set_height(height)
    if arrow is None:
        return VGroup(txt).move_to(ORIGIN)
    if arrow == "square":
        tri = Square(fill_color=color, fill_opacity=1.0, stroke_width=0)
        tri.set_height(height * 0.50)          # optically matches the triangles
    else:
        tri = Triangle(fill_color=color, fill_opacity=1.0, stroke_width=0)
        tri.set_height(height * 0.62)
    if arrow == "down":
        tri.rotate(PI)
    tri.next_to(txt, RIGHT, buff=height * 0.32)
    return VGroup(txt, tri).move_to(ORIGIN)


def name_label(i, *, height=0.34, color=LABEL_COLOR):
    """The named tier label for default tier `i` (reads NAME_LABELS)."""
    return name_label_spec(*NAME_LABELS[i], height=height, color=color)


# ── the tier list ─────────────────────────────────────────────────────────────
def get_tier_list(labels="letter", *, center=ORIGIN, panel_width=_DEFAULT_PANEL_W,
                  cell_width=1.75, row_height=0.82, row_gap=0.10,
                  cell_gap=0.08, colors=None, dimmed=False, names=None,
                  panel_fill=None):
    """A tier list: a coloured grade CELL on the left + a dark content PANEL on the
    right, per tier, top (best) → bottom (worst). Default is 7 rows.

    labels : "letter" | "number" | "name" — which label state to build.
    names  : optional list of (word, arrow) NAME specs for a CUSTOM tier structure
             (e.g. the 6-tier frequency-weighted list, whose two HIGH tiers merge into
             one). Forces labels="name" and sets the number of rows; colours default to
             `name_colors(names)`.
    dimmed : start every row muted (for the beat-06 emphasis build-up).
    colors : per-tier cell colours; default = the S-tier rainbow for grade labels,
             the grouped TOP/HIGH/MID/LOW palette once the tiers are NAMED.

    Returns VGroup(*rows) with `.rows` (list of VGroup(cell, panel, label,
    contents)), parallel `.cells/.panels/.labels/.contents`, and geometry
    `.panel_left_x` / `.row_cy(i)` for placing letters later.
    """
    if names is not None:
        labels = "name"
    tier_names = names if names is not None else NAME_LABELS
    n = len(tier_names) if labels == "name" else len(LETTER_LABELS)
    if colors is None:
        colors = name_colors(tier_names) if labels == "name" else TIER_COLORS
    pitch = row_height + row_gap
    total_h = n * row_height + (n - 1) * row_gap
    top_cy = total_h / 2 - row_height / 2
    full_w = cell_width + cell_gap + panel_width
    left = -full_w / 2
    cell_cx = left + cell_width / 2
    panel_cx = left + cell_width + cell_gap + panel_width / 2
    panel_left = left + cell_width + cell_gap

    def build_label(i):
        if labels == "name":
            return name_label_spec(*tier_names[i])
        return (letter_label if labels == "letter" else number_label)(i)

    rows, cells, panels, labs, contents = [], [], [], [], []
    for i in range(n):
        cy = top_cy - i * pitch
        cell = RoundedRectangle(width=cell_width, height=row_height,
                                corner_radius=0.06)
        cell.set_fill(colors[i], opacity=1.0).set_stroke(PANEL_STROKE, width=2)
        cell.move_to([cell_cx, cy, 0])

        panel = RoundedRectangle(width=panel_width, height=row_height,
                                 corner_radius=0.06)
        panel.set_fill(PANEL_FILL if panel_fill is None else panel_fill,
                       opacity=1.0).set_stroke(PANEL_STROKE, width=2)
        panel.move_to([panel_cx, cy, 0])

        lab = build_label(i)
        lab.move_to([cell_cx, cy, 0])

        cont = VGroup()   # letters get dropped in here by later scenes
        row = VGroup(cell, panel, lab, cont)
        if dimmed:
            row.set_opacity(DIM_OPACITY)
        rows.append(row)
        cells.append(cell); panels.append(panel); labs.append(lab)
        contents.append(cont)

    tl = VGroup(*rows).shift(center)
    tl.rows = rows
    tl.cells = cells
    tl.panels = panels
    tl.labels = labs
    tl.contents = contents
    tl.panel_left_x = panel_left + center[0]
    tl.row_cys = [(top_cy - i * pitch) + center[1] for i in range(n)]
    tl.n = n
    return tl


# ── filling a tier with its letters ───────────────────────────────────────────
DOUBLE_SMALL = 0.62          # a double's first copy, as a fraction of full height
DOUBLE_GAP = 0.06            # between a double's two copies (units at height 0.5)
DOUBLE_SLOTS = 1.6           # a double's slot width, in single-letter slots


def token_slots(token):
    """How many letter slots a TOKEN takes: 1 for a letter, DOUBLE_SLOTS for a double."""
    return 1.0 if len(token) == 1 else DOUBLE_SLOTS


def letter_box(ch, side, box, *, color=None):
    """A single letter IN A BOX: a square `side` wide styled by `box` (a dict:
    `fill`, `stroke_color`, `stroke_width`, optional `letter_frac`, the letter's
    height over the side, default 0.58) with the letter centred on it. Returns
    VGroup(square, glyph) with `.box` / `.glyph` handles."""
    if len(ch) != 1:
        raise ValueError(f"boxed tokens must be single letters, not {ch!r}")
    if color is None:
        color = tile_color(ch)
    sq = Square(side_length=side).set_fill(box["fill"], opacity=1.0) \
        .set_stroke(box["stroke_color"], width=box["stroke_width"])
    g = crisp_text(ch.upper(), font_size=FONT_SIZE_LG, color=color, weight=BOLD)
    g.set_height(side * box.get("letter_frac", 0.58)).move_to(sq.get_center())
    out = VGroup(sq, g)
    out.box, out.glyph = sq, g
    return out


def letter_tile(ch, *, height=0.5, color=None):
    """One tier TOKEN, drawn on the dark panel — coloured vowel-red / consonant-blue
    by default (`tile_color`); pass `color` to override. A token is a letter, or a
    DOUBLE ("ee", the second copy of a letter): a small copy followed by a full-size
    one, sitting on one baseline."""
    if color is None:
        color = tile_color(ch[0])
    def glyph(h):
        return crisp_text(ch[0].upper(), font_size=FONT_SIZE_LG, color=color,
                          weight=BOLD).set_height(h)
    if len(ch) == 1:
        return glyph(height)
    small, full = glyph(height * DOUBLE_SMALL), glyph(height)
    small.next_to(full, LEFT, buff=DOUBLE_GAP * height / 0.5).align_to(full, DOWN)
    return VGroup(small, full)


BOX_FILL_FRAC = 0.9          # a boxed letter's square, as a fraction of its slot (a
                             # Wordle board's tile : tile + gap)


def fill_tier(tl, i, letters, *, height=0.5, buff=LETTER_BUFF,
              pitch=LETTER_PITCH, box=None):
    """Lay tier `i`'s `letters` (a sourced string, or a list of TOKENS, top tier
    first) left→right in its panel — each centred in a fixed-width slot (`pitch`, or
    `token_slots` of it for a double) so they stay evenly spaced regardless of glyph
    width — and add them to the tier's `.contents` (so later emphasis dims them with
    the row). Returns the VGroup of new tiles.

    `box` (optional, a `letter_box` style dict) draws each letter IN A BOX of side
    `BOX_FILL_FRAC * pitch` instead of bare; `height` is then ignored. Default None
    leaves every existing list exactly as it was."""
    cy = tl.row_cys[i]
    x = tl.panel_left_x + buff
    tiles = VGroup()
    for ch in letters:
        w = token_slots(ch) * pitch
        tile = (letter_tile(ch, height=height) if box is None
                else letter_box(ch, BOX_FILL_FRAC * pitch, box))
        tiles.add(tile.move_to([x + w / 2, cy, 0]))
        x += w
    tl.contents[i].add(*tiles)
    return tiles


# ── comparison (a filled list, and a piece-by-piece morph between two) ─────────
def filled_list(letters, *, names=None, scale=1.0, panel_width=_DEFAULT_PANEL_W,
                panel_fill=None, box=None):
    """A tier list with each tier's `letters` filled in — default the 7-tier NAMED
    structure, or a custom `names` (list of (word, arrow)) — scaled and ready to
    `.move_to(...)`. `letters` is one string (or list of TOKENS) per tier, top→bottom. The shared builder
    behind the scene-17 / scene-22 tier COMPARISONS. `box`: see `fill_tier`."""
    kw = dict(panel_width=panel_width, panel_fill=panel_fill)
    tl = (get_tier_list("name", **kw) if names is None
          else get_tier_list(names=names, **kw))
    for i, lets in enumerate(letters):
        fill_tier(tl, i, lets, box=box)
    return tl.scale(scale)


def tile_map(tl, letters):
    """{letter_char (UPPER): its tile mobject} for a list filled with `letters`
    (contents[i][k] == letters[i][k]). For emphasising specific letters."""
    return {ch.upper(): tl.contents[i][k]
            for i, lets in enumerate(letters) for k, ch in enumerate(lets)}


def morph_into(scene, src, dst, src_letters, dst_letters, row_map, run_time, *,
               extra=(), split_from=None):
    """Transform a COPY of filled tier list `src` into `dst`: per-role structure
    (cell/panel/label of src row i → dst row `row_map[i]`, so two rows can MERGE onto
    one) + per-LETTER moves (each letter slides to its dst tile). `src` stays put; `dst`
    is left on screen at the end. `extra` plays ALONGSIDE (e.g. a title fading in).
    Piece-by-piece via role handles, never a blob morph — see bpkfigures CLAUDE.md.
    (Promoted from hangman scene 17's `_morph_into`.) A dst TOKEN that src lacks (a
    double added to the list) rides in with its row, fading in as it moves.

    SPLITTING — the reverse of a merge: pass `split_from`, one src row index PER DST
    row (and `row_map=None`), and every dst row's cell/panel/label grows out of a copy
    of that src row, so one src tier can become two and every tier travels in from
    `src`. Without it, a dst row no src row maps onto fades in where it stands.
    Letters are always drawn ABOVE the moving structure."""
    dst_tile = {ch: dst.contents[i][k]
                for i, lets in enumerate(dst_letters) for k, ch in enumerate(lets)}
    if split_from is not None:
        assert row_map is None and len(split_from) == dst.n, "one src row per dst row"
        row_pairs = [(i, j) for j, i in enumerate(split_from)]
    else:
        row_pairs = list(enumerate(row_map))
    pairs = []
    for i, j in row_pairs:
        pairs += [(src.cells[i], dst.cells[j]), (src.panels[i], dst.panels[j]),
                  (src.labels[i], dst.labels[j])]
    for i, lets in enumerate(src_letters):
        for k, ch in enumerate(lets):
            pairs.append((src.contents[i][k], dst_tile[ch]))
    covered = {j for _, j in row_pairs}
    fresh = [VGroup(dst.cells[j], dst.panels[j], dst.labels[j]).copy()
             for j in range(dst.n) if j not in covered]
    # new tokens (dst has, src lacks) RIDE IN WITH THEIR ROW: each starts where it
    # would sit in the src row its dst row grows out of, invisible, and moves to its
    # place as it fades in; a token in an uncovered row fades in where it stands
    src_tokens = {ch for lets in src_letters for ch in lets}
    src_of = {}
    for i, j in row_pairs:
        src_of.setdefault(j, i)
    riders, fades = [], []
    for j, lets in enumerate(dst_letters):
        for ch in lets:
            if ch in src_tokens:
                continue
            tile = dst_tile[ch]
            if j in src_of:
                sp, dp = src.panels[src_of[j]], dst.panels[j]
                # the same place along the SRC panel (its width can differ)
                rel = (tile.get_center() - dp.get_left()) * \
                    np.array([sp.width / dp.width, sp.height / dp.height, 1.0])
                start = tile.copy().scale(sp.height / dp.height)
                start.move_to(sp.get_left() + rel).set_opacity(0)
                riders.append((start, tile))
            else:
                fades.append(tile.copy())
    scene.add(*fresh)                  # under the letters, which are added last
    movers = [a.copy() for a, _ in pairs]
    for m in movers:
        scene.add(m)
    scene.add(*[r for r, _ in riders], *fades)
    scene.play(*[Transform(m, b.copy()) for m, (_, b) in zip(movers, pairs)],
               *[Transform(r, t.copy()) for r, t in riders],
               *[FadeIn(f) for f in fresh + fades], *extra, run_time=run_time)
    scene.remove(*movers, *fresh, *[r for r, _ in riders], *fades)
    scene.add(dst)


# ── emphasis (resting state is FULL; emphasise by DIMMING THE REST) ────────────


# ── emphasis (resting state is FULL; emphasise by DIMMING THE REST) ────────────
def emphasize(tl, tiers):
    """Animations that emphasise tier(s) `tiers` (an int or an iterable of ints)
    by fading EVERY OTHER tier down to `DIM_OPACITY` while the emphasised ones
    stay at full. Passing all tiers (or the resting call `reset`) clears the dim.
    Returns a flat list — unpack into `self.play(*emphasize(tl, {0, 1}))`. Idempo-
    tent: a tier already in the right state animates in place (no visible change),
    so beats can pass a GROWING set to accumulate emphasis."""
    idx = {tiers} if isinstance(tiers, int) else set(tiers)
    return [tl.rows[i].animate.set_opacity(1.0 if i in idx else DIM_OPACITY)
            for i in range(tl.n)]


def reset(tl):
    """Animations returning every tier to the full (un-dimmed) resting state."""
    return [row.animate.set_opacity(1.0) for row in tl.rows]
