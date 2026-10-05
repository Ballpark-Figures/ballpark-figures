"""A data TABLE on a card — the shared helper for "make a graphic of a table".

    tab = get_table(["opener", "total", "avg"],
                    [["salet", "7920", "3.4212"], ["reast", "7923", "3.4225"]],
                    title="Best openers")
    self.add(tab)

Every cell goes through ``crisp_text`` and sits on its row's TEXT BASELINE, so a
row of mixed strings (descender words, digits) lines up. Columns are sized to their
widest cell. Alignment per column is ``"l"``, ``"c"`` or ``"r"``; by default a column
whose every body cell reads as a number is right-aligned (digits line up) and every
other column is left-aligned.

The table only LAYS OUT what it is handed: cells are shown exactly as given (a
non-string is ``str()``-ed), so number formatting is the caller's, and the numbers
themselves come from the pipeline (see "The numbers are the product").

Role handles on the returned VGroup, for highlighting or animating by role:
  ``.card``    the card behind everything (None with ``card=False``)
  ``.title``   the title text (None without one)
  ``.header``  VGroup of header cells
  ``.rule``    the line under the header
  ``.rows``    list of VGroups, one per body row
  ``.cells``   cells[r][c] for the body
  ``.stripes`` VGroup of zebra stripes (empty with ``stripes=False``)
"""
import re

from manim import *

from bpkfigures.card import card_behind
from bpkfigures.style import (FONT_SIZE_LG, FONT_SIZE_MD, crisp_text, fit_to_frame,
                              place_on_baseline)

_NUMBER = re.compile(r"^[+\-−]?[$£€]?[\d,]*\.?\d+(e[+\-]?\d+)?%?$", re.IGNORECASE)


def _is_number(s):
    return bool(_NUMBER.match(s.strip())) if s.strip() else False


def _default_align(headers, rows):
    out = []
    for c in range(len(headers)):
        body = [r[c] for r in rows if r[c].strip()]
        out.append("r" if body and all(_is_number(s) for s in body) else "l")
    return out


def get_table(headers, rows, *, title=None, align=None, font_size=FONT_SIZE_MD,
              title_size=FONT_SIZE_LG, ink=BLACK, header_color=None, title_color=None,
              col_gap=0.9, row_pitch=1.55, stripes=True, stripe_color=GREY_B,
              stripe_opacity=0.18, card=True, card_pad=0.45, center=ORIGIN,
              fit=True, fit_buff=0.4, **card_kwargs):
    """Build a table. ``headers``: list of column titles. ``rows``: list of rows, each
    as long as ``headers``. ``row_pitch`` is the baseline-to-baseline distance as a
    multiple of the font's line height. ``fit=True`` scales the finished table (card
    included) DOWN to fit the frame, never up. Extra kwargs go to the card."""
    headers = [str(h) for h in headers]
    rows = [[str(v) for v in r] for r in rows]
    ncol = len(headers)
    for i, r in enumerate(rows):
        if len(r) != ncol:
            raise ValueError(f"row {i} has {len(r)} cells, want {ncol}: {r}")
    align = list(align) if align is not None else _default_align(headers, rows)
    if len(align) != ncol or any(a not in "lcr" for a in align):
        raise ValueError(f"align must be {ncol} of 'l'/'c'/'r', got {align!r}")
    header_color = header_color or ink
    title_color = title_color or ink

    # Line height from a probe holding an ascender and a descender.
    line_h = crisp_text("Hg", font_size=font_size).height
    pitch = line_h * row_pitch
    # A row's visual middle is half the cap height above its baseline (capitals and
    # digits span baseline to cap height), so the stripe is centred there.
    mid_above_baseline = crisp_text("H", font_size=font_size).height / 2

    def cell(s, **kw):
        return crisp_text(s or " ", font_size=font_size, **kw)

    header_mobs = [cell(h, color=header_color, weight=BOLD) for h in headers]
    body_mobs = [[cell(v, color=ink) for v in r] for r in rows]

    widths = [max([header_mobs[c].width] + [r[c].width for r in body_mobs])
              for c in range(ncol)]
    total_w = sum(widths) + col_gap * (ncol - 1)
    lefts, x = [], -total_w / 2
    for w in widths:
        lefts.append(x)
        x += w + col_gap

    def place(mob, text, c, y):
        crisp_x = lefts[c] + widths[c] / 2
        place_on_baseline(mob, (crisp_x, y), string=text or " ")
        if align[c] == "l":
            mob.shift(RIGHT * (lefts[c] - mob.get_left()[0]))
        elif align[c] == "r":
            mob.shift(RIGHT * (lefts[c] + widths[c] - mob.get_right()[0]))
        return mob

    y = 0.0
    header = VGroup(*[place(m, headers[c], c, y) for c, m in enumerate(header_mobs)])
    rule_y = y - pitch * 0.42
    rule = Line([-total_w / 2 - 0.15, rule_y, 0], [total_w / 2 + 0.15, rule_y, 0],
                color=ink, stroke_width=3)
    y -= pitch * 1.05

    row_groups, stripe_list = [], []
    for r, mobs in enumerate(body_mobs):
        row_groups.append(VGroup(*[place(m, rows[r][c], c, y)
                                   for c, m in enumerate(mobs)]))
        if stripes and r % 2 == 1:
            band = Rectangle(width=total_w + 0.3, height=pitch,
                             fill_color=stripe_color, fill_opacity=stripe_opacity,
                             stroke_width=0)
            band.move_to([0, y + mid_above_baseline, 0])
            stripe_list.append(band)
        y -= pitch

    stripe_group = VGroup(*stripe_list)
    content = VGroup(stripe_group, header, rule, *row_groups)
    title_mob = None
    if title:
        title_mob = crisp_text(title, font_size=title_size, color=title_color,
                               weight=BOLD)
        title_mob.next_to(content, UP, buff=pitch * 0.7)
        content.add(title_mob)

    group = VGroup()
    card_mob = None
    if card:
        card_mob = card_behind(content, pad=card_pad, **card_kwargs)
        group.add(card_mob)
    group.add(content)
    group.move_to(center)
    if fit:
        fit_to_frame(group, buff=fit_buff)

    group.card = card_mob
    group.title = title_mob
    group.header = header
    group.rule = rule
    group.rows = row_groups
    group.cells = [list(g.submobjects) for g in row_groups]
    group.stripes = stripe_group
    return group
