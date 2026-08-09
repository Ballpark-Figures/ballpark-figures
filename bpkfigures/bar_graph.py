from manim import *
import numpy as np

from bpkfigures.style import (FONT, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
                              ACCENT_FILL, crisp_text, crisp_paragraph)


# ═══ general categorical / metric BAR CHART (one value per label) ═════════════
#
# The shared home for a vertical bar chart of a value PER LABEL — avg-misses by
# word length, a sorted letter-frequency chart, words-by-length, etc. Distinct
# from get_histogram (a DISTRIBUTION over an integer value-axis) and from
# get_bar_graph above (a horizontal double-bar comparison TABLE).
#
# Every text role (category labels, value readouts, y-tick numbers, title) is
# rendered by a FACTORY (str/number -> mobject) defaulting to crisp_text in
# `ink_color`; pass a chalk factory (chalk_letter / a written-font number) to
# render on the dark chalkboard. `highlight={label: color}` recolours specific
# bars; `y_max` fixes the value mapped to full height (default = max value) so a
# SERIES of charts shares one scale and morph_bar_chart can pair them by position.

def _crisp_factory(ink):
    return lambda s: crisp_text(str(s), font=FONT, font_size=FONT_SIZE_SM, color=ink)


def get_bar_chart(
    items,
    *,
    center=ORIGIN,
    width=8.0,
    height=4.0,
    y_max=None,
    n_slots=None,
    orientation="vertical",
    bar_color=ACCENT_FILL,
    ink_color=BLACK,
    highlight=None,
    bar_ratio=0.75,
    bar_fill_opacity=1.0,        # set 0 + bar_stroke_width>0 for OUTLINE-only bars
    bar_stroke_width=0,          # (drawable as a continuous chalk line via Create)
    show_labels=True,
    label_factory=None,
    label_buff=0.28,
    value_labels=False,
    value_factory=None,
    value_fmt=str,
    value_buff=0.10,
    x_axis=False,
    y_axis=False,
    y_ticks=None,
    y_tick_factory=None,
    y_tick_buff=0.12,
    title=None,
    title_mobject=None,
    title_factory=None,
    title_buff=0.5,
):
    """A vertical bar chart of ``[(label, value), …]`` (in display order — caller
    sorts). See the module comment above for the factory / highlight / y_max
    contract.

    Returns a VGroup with per-role handles: ``.bars`` ``.labels`` ``.values``
    (parallel VGroups in item order), ``.bar_of`` / ``.label_of`` / ``.value_of``
    ({label: mobject}), ``.cols`` ({label: VGroup(bar[, label][, value])}),
    ``.x_axis`` ``.y_axis`` ``.yticks`` ``.title`` (any may be None), and
    ``.chart_geom`` (scale/geometry, so morph_bar_chart can pair two charts)."""
    if orientation != "vertical":
        raise NotImplementedError(
            "get_bar_chart currently builds VERTICAL bars only; a horizontal mode "
            "is an additive extension (add it here rather than hand-rolling)")

    label_factory = label_factory or _crisp_factory(ink_color)
    value_factory = value_factory or (
        lambda v: crisp_text(value_fmt(v), font=FONT, font_size=FONT_SIZE_SM,
                             color=ink_color))
    y_tick_factory = y_tick_factory or _crisp_factory(ink_color)

    n = max(len(items), 1)
    cx, cy = center[0], center[1]
    left, right = cx - width / 2, cx + width / 2
    base = cy - height / 2
    # slot count: default one slot per item; pass n_slots to FIX the column pitch
    # (bars fill the leftmost slots, rest empty) so a SERIES with varying item
    # counts keeps each column at the same x — morph_bar_chart then never slides.
    slot = width / (n_slots if n_slots else n)
    vmax = y_max if y_max is not None else max((v for _, v in items), default=1) or 1

    bars, labels, values = VGroup(), VGroup(), VGroup()
    bar_of, label_of, value_of, cols = {}, {}, {}, {}
    for i, (label, value) in enumerate(items):
        x = left + (i + 0.5) * slot
        h = max(value / vmax * height, 1e-3)
        col = (highlight or {}).get(label, bar_color)
        bar = Rectangle(width=slot * bar_ratio, height=h, fill_color=col,
                        fill_opacity=bar_fill_opacity, stroke_color=col,
                        stroke_width=bar_stroke_width)
        bar.move_to(np.array([x, base + h / 2, 0]))
        bars.add(bar)
        bar_of[label] = bar
        col_parts = [bar]
        if show_labels:
            lab = label_factory(label)
            lab.next_to(np.array([x, base, 0]), DOWN, buff=label_buff).set_x(x)
            labels.add(lab)
            label_of[label] = lab
            col_parts.append(lab)
        if value_labels:
            val = value_factory(value)
            val.next_to(bar, UP, buff=value_buff).set_x(x)
            values.add(val)
            value_of[label] = val
            col_parts.append(val)
        cols[label] = VGroup(*col_parts)

    xa = Line([left, base, 0], [right, base, 0], color=ink_color,
              stroke_width=3) if x_axis else None
    ya = Line([left, base, 0], [left, base + height, 0], color=ink_color,
              stroke_width=3) if y_axis else None
    yticks = VGroup()
    if y_ticks:
        for t in y_ticks:
            y = base + t / vmax * height
            tick = Line([left - 0.12, y, 0], [left, y, 0], color=ink_color,
                        stroke_width=2)
            tl = y_tick_factory(t)
            tl.next_to(tick, LEFT, buff=y_tick_buff)
            yticks.add(tick, tl)

    elements = VGroup(bars, labels, values)
    for m in (xa, ya):
        if m is not None:
            elements.add(m)
    if len(yticks):
        elements.add(yticks)

    title_text = None
    if title_mobject is not None:
        title_text = title_mobject
    elif title is not None:
        title_text = (title_factory(title) if title_factory
                      else crisp_text(title, font=FONT, font_size=FONT_SIZE_LG,
                                      color=ink_color))
    if title_text is not None:
        title_text.next_to(elements, UP, buff=title_buff)
        title_text.set_x(cx)
        elements.add(title_text)

    elements.bars, elements.labels, elements.values = bars, labels, values
    elements.bar_of, elements.label_of, elements.value_of = bar_of, label_of, value_of
    elements.cols = cols
    elements.x_axis, elements.y_axis = xa, ya
    elements.yticks = yticks if len(yticks) else None
    elements.title = title_text
    elements.chart_geom = {"y_max": vmax, "width": width, "height": height,
                           "n": n, "center": np.array(center, dtype=float),
                           "base": base, "bar_ratio": bar_ratio}
    return elements


def morph_bar_chart(old, new):
    """Animations turning one get_bar_chart into another, pairing bars/labels/values
    BY POSITION (index): each bar ReplacementTransforms (height/colour in place)
    while its label + value crossfade; surplus columns fade out/in when the two
    charts differ in length. Axes/title (if any) crossfade. Returns a list to splat
    into ``self.play(*morph_bar_chart(old, new), run_time=…)``; afterwards the NEW
    objects are live, so track them (e.g. ``self.bars = new``)."""
    anims = []
    nb = min(len(old.bars), len(new.bars))
    for i in range(nb):
        anims.append(ReplacementTransform(old.bars[i], new.bars[i]))
    for i in range(nb, len(old.bars)):
        anims.append(FadeOut(old.bars[i]))
    for i in range(nb, len(new.bars)):
        anims.append(FadeIn(new.bars[i]))
    for attr in ("labels", "values"):
        o, nw = getattr(old, attr), getattr(new, attr)
        k = min(len(o), len(nw))
        for i in range(k):
            anims.append(FadeTransform(o[i], nw[i]))
        for i in range(k, len(o)):
            anims.append(FadeOut(o[i]))
        for i in range(k, len(nw)):
            anims.append(FadeIn(nw[i]))
    for attr in ("x_axis", "y_axis", "yticks", "title"):
        o, nw = getattr(old, attr, None), getattr(new, attr, None)
        if o is not None and nw is not None:
            anims.append(FadeTransform(o, nw))
        elif o is not None:
            anims.append(FadeOut(o))
        elif nw is not None:
            anims.append(FadeIn(nw))
    return anims


def _make_bar(length, height, color, opacity=1.0, fade=False, n_seg=16):
    """A left-anchored horizontal bar whose LEFT edge sits at local x=0.
    ``fade`` renders it as segments whose opacity drops left→right (used to show
    that a box doesn't always pay full points even on success)."""
    length = max(length, 1e-3)
    if not fade:
        bar = Rectangle(width=length, height=height, fill_color=color,
                        fill_opacity=opacity, stroke_width=0)
        bar.move_to(np.array([length / 2, 0, 0]))
        return bar
    grp = VGroup()
    seg_w = length / n_seg
    for i in range(n_seg):
        op = opacity * (1 - 0.82 * i / (n_seg - 1))
        seg = Rectangle(width=seg_w * 1.02, height=height, fill_color=color,
                        fill_opacity=op, stroke_width=0)
        seg.move_to(np.array([(i + 0.5) * seg_w, 0, 0]))
        grp.add(seg)
    return grp


def get_bar_graph(
    rows,
    bar_max_width=4.0,
    row_height=0.42,
    row_buff=0.34,
    label_buff=0.3,
    pct_buff=0.35,
    center=ORIGIN,
    long_color=interpolate_color(ACCENT_FILL, WHITE, 0.72),   # light accent tint
    short_color=ACCENT_FILL,
    pct_color=BLACK,
    label_color=BLACK,
    title=None,
    pct_header=None,
    show_values=False,
    value_color=WHITE,
):
    """Horizontal double-bar table. ``rows`` is a list of dicts:
        {label, max_value, expected_value, pct, fade=False, color=None}
    Per row: a long bar (length ∝ max_value, light) with an overlapping short bar
    (length ∝ expected_value, saturated) and a "{pct}%" readout to the right.
    Optional: ``title`` above the table; ``pct_header`` (may contain "\\n") above
    the percentage column; ``show_values`` writes expected_value to 1 dp at the
    right end of each short bar in ``value_color``. All rows share one
    value→length scale. Returns a VGroup whose ``[i]`` is row ``i`` (rows come
    first; any title/header are appended after). Each row VGroup is
    (label, long_bar, short_bar, pct[, value])."""
    max_value = max(r["max_value"] for r in rows) or 1
    scale = bar_max_width / max_value
    pct_x = bar_max_width + pct_buff

    table = VGroup()
    for i, r in enumerate(rows):
        y = -i * (row_height + row_buff)
        col = r.get("color", short_color)

        long_bar = _make_bar(r["max_value"] * scale, row_height, long_color,
                             opacity=0.85, fade=r.get("fade", False))
        short_bar = _make_bar(r["expected_value"] * scale, row_height, col,
                              opacity=1.0)
        short_bar.set_z_index(1)
        long_bar.shift(UP * y)
        short_bar.shift(UP * y)

        label = crisp_text(r["label"], font=FONT, font_size=FONT_SIZE_SM,
                           color=label_color)
        label.move_to(np.array([0, y, 0]))
        label.next_to(np.array([-label_buff, y, 0]), LEFT, buff=0)

        pct = crisp_text(f"{r['pct']:.0f}%", font=FONT, font_size=FONT_SIZE_SM,
                         color=pct_color)
        pct.move_to(np.array([pct_x, y, 0]))
        pct.align_to(np.array([pct_x, y, 0]), LEFT)

        row = VGroup(label, long_bar, short_bar, pct)
        if show_values:
            value = crisp_text(f"{r['expected_value']:.1f}", font=FONT,
                               font_size=FONT_SIZE_SM * 0.85, color=value_color)
            value.set_z_index(2)
            value.next_to(short_bar.get_right(), LEFT, buff=0.12)
            row.add(value)
        table.add(row)

    n = len(rows)
    if pct_header is not None:
        header = crisp_paragraph(*pct_header.split("\n"), alignment="center",
                                 font=FONT, font_size=FONT_SIZE_SM * 0.85,
                                 color=pct_color)
        header.move_to(np.array([table[0][3].get_center()[0],
                                 row_height / 2 + 0.45, 0]))
        table.add(header)
    if title is not None:
        title_text = crisp_text(title, font=FONT, font_size=FONT_SIZE_MD,
                                color=BLACK, weight="BOLD")
        title_text.next_to(table, UP, buff=0.45)
        table.add(title_text)

    table.move_to(center)
    return table
