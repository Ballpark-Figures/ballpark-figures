from manim import *
import numpy as np

from bpkfigures.style import (FONT, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
                              ACCENT_FILL, crisp_text, crisp_paragraph,
                              place_on_baseline)


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
    y_min=0.0,                   # value mapped to the AXIS (bar base). Default 0 = bars
                                 # grow from zero; set > 0 for a zoomed/clipped y-axis
                                 # (bars + ticks measure from y_min, not 0).
    n_slots=None,
    orientation="vertical",
    bar_color=ACCENT_FILL,
    ink_color=BLACK,
    highlight=None,
    bar_ratio=0.75,
    bar_fill_opacity=1.0,        # (default filled Rectangle) fill opacity …
    bar_stroke_width=0,          # … and stroke width
    bar_outline=None,            # None → filled Rectangle. "open" → a 3-SIDED outline
                                 # (no base edge; the x-axis IS the base). "closed" →
                                 # a 4-sided outline. BOTH outline styles are ONE path
                                 # that STARTS at the bottom-left corner, so Create
                                 # draws up the left, across the top, down the right
                                 # (then, for "closed", the base back to the start).
    show_labels=True,
    label_factory=None,
    label_buff=0.28,
    baseline_labels=False,       # align labels on one text BASELINE (below), not by bbox
                                 # top — so ascender/descender labels don't drift. Opt-in
                                 # (default keeps the historical top-of-bbox placement).
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
    vspan = (vmax - y_min) or 1     # value range mapped across the bar height

    # baseline-label mode: drop labels by a reference ascender height so an ascender
    # label's TOP still lands ~label_buff below the bar (matches the top-align spacing)
    cap_h = (label_factory("A").height if (show_labels and baseline_labels) else 0.0)

    bars, labels, values = VGroup(), VGroup(), VGroup()
    bar_of, label_of, value_of, cols = {}, {}, {}, {}
    for i, (label, value) in enumerate(items):
        x = left + (i + 0.5) * slot
        h = max((value - y_min) / vspan * height, 1e-3)
        col = (highlight or {}).get(label, bar_color)
        bw = slot * bar_ratio
        if bar_outline in ("open", "closed"):
            # an outline whose path STARTS at the bottom-left corner: Create draws it
            # up the left, across the top, down the right — then, for "closed", the
            # base edge back to the start (leaning into the chalk-drawn look)
            x0, x1 = x - bw / 2, x + bw / 2
            pts = [[x0, base, 0], [x0, base + h, 0], [x1, base + h, 0], [x1, base, 0]]
            if bar_outline == "closed":
                pts.append([x0, base, 0])
            bar = VMobject(stroke_color=col, stroke_width=bar_stroke_width)
            bar.set_points_as_corners(pts)
        else:
            bar = Rectangle(width=bw, height=h, fill_color=col,
                            fill_opacity=bar_fill_opacity, stroke_color=col,
                            stroke_width=bar_stroke_width)
            bar.move_to(np.array([x, base + h / 2, 0]))
        bars.add(bar)
        bar_of[label] = bar
        col_parts = [bar]
        if show_labels:
            lab = label_factory(label)
            if baseline_labels:
                place_on_baseline(lab, [x, base - label_buff - cap_h],
                                  factory=label_factory, string=label)
            else:
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
            y = base + (t - y_min) / vspan * height
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
    elements.chart_geom = {"y_max": vmax, "y_min": y_min, "width": width,
                           "height": height, "n": n,
                           "center": np.array(center, dtype=float),
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


def grow_bars(scene, bars, run_time, *, lag=0.0, extra=()):
    """Reveal filled bars by GROWING each up from the axis (x fixed) — the house
    entrance for a bar chart. Promoted from the ``_grow_up`` that scenes 04/05 and
    yahtzee 07 each hand-rolled, so a bar chart stops reinventing its reveal.

    bars  : the chart's ``.bars`` (or any iterable of vertical bars).
    lag   : stagger the bars left→right, 0 = all at once (a small 0.05–0.10 reads well).
    extra : animations to play ALONGSIDE (e.g. ``FadeIn(chart.labels)``)."""
    bars = list(bars)
    for b in bars:
        b.save_state()
        b.stretch(1e-3, dim=1, about_edge=DOWN)         # collapse to the axis, x fixed
    grow = [Restore(b) for b in bars]
    anim = LaggedStart(*grow, lag_ratio=lag) if lag > 0 else AnimationGroup(*grow)
    scene.play(anim, *extra, run_time=run_time)


# ═══ grouped/paired bar chart over shared CATEGORIES ═════════════════════════
#
# Several series (each a (name, color, values) triple) plotted side by side over a
# shared category axis — e.g. avg misses per WORD LENGTH under two weightings (the
# "double plot" in scenes 17 and 19). Adds an x/y axis + y-ticks, per-category x
# labels, an x-axis title, a chart title, and a legend. Promoted from the identical
# `_strategy_chart`/`_double_chart` those two scenes each hand-rolled.

def _series_legend(series, ink_color, pos, fs):
    g = VGroup()
    for name, color, _ in series:
        sq = Square(side_length=0.28, fill_color=color, fill_opacity=1.0, stroke_width=0)
        g.add(VGroup(sq, crisp_text(name, font_size=fs, color=ink_color)).arrange(RIGHT, buff=0.18))
    return g.arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to(pos)


def grouped_bar_chart(categories, series, *, title=None, x_title=None,
                      ink_color=BLACK, y_ticks=(0, 2, 4, 6),
                      width=12.6, height=3.8, cy=-0.25,
                      bar_ratio=0.42, series_gap_frac=1 / 2.1, title_buff=1.15,
                      legend_pos=None, x_label_fs=20, x_title_fs=24,
                      title_fs=34, legend_fs=22, y_tick_fs=18):
    """A grouped bar chart over shared ``categories`` (list of x labels). ``series`` is a
    list of ``(name, color, values)`` triples, each ``values`` aligned to ``categories``;
    bars for the same category are offset side by side. Adds x/y axes with ``y_ticks``,
    per-category x labels, an ``x_title`` beneath, a ``title`` above, and a legend.

    Returns a VGroup with role handles: ``.series`` (the per-series get_bar_chart groups),
    ``.bars`` (flat list of every bar — pass to ``grow_bars``), ``.rest`` (axes + labels +
    titles + legend, i.e. everything that is NOT a bar — fade this in as the bars grow),
    ``.legend``, ``.title_mob``. Layout matches scenes 17/19's double plot; all text uses
    ``ink_color`` (pass a dark ink for a light bg). NB ``title`` is a short string rendered
    directly — a long one would wrap (crisp_text 240pt cap); pass a short chart title."""
    cats = [str(c) for c in categories]
    N = len(cats)
    slot = width / N
    ymax = max((v for _, _, vals in series for v in vals), default=1) or 1
    base_y = cy - height / 2
    step = slot * series_gap_frac
    n = len(series)

    series_groups = []
    for i, (_name, color, vals) in enumerate(series):
        off = (i - (n - 1) / 2) * step
        chart = get_bar_chart(list(zip(cats, vals)), center=[off, cy, 0], width=width,
                              height=height, y_max=ymax, n_slots=N, bar_color=color,
                              bar_ratio=bar_ratio, show_labels=False)
        series_groups.append(chart)

    axes = VGroup(Line([-width / 2, base_y, 0], [width / 2, base_y, 0], color=ink_color, stroke_width=3),
                  Line([-width / 2, base_y, 0], [-width / 2, base_y + height, 0], color=ink_color, stroke_width=3))
    for t in y_ticks:
        yy = base_y + t / ymax * height
        tick = Line([-width / 2 - 0.12, yy, 0], [-width / 2, yy, 0], color=ink_color, stroke_width=2)
        axes.add(tick, crisp_text(str(t), font_size=y_tick_fs, color=ink_color).next_to(tick, LEFT, buff=0.12))

    xlabels = VGroup(*[crisp_text(c, font_size=x_label_fs, color=ink_color).move_to(
                          [-width / 2 + (i + 0.5) * slot, base_y - 0.28, 0])
                       for i, c in enumerate(cats)])

    rest = VGroup(axes, xlabels)
    if x_title:
        rest.add(crisp_text(x_title, font_size=x_title_fs, color=ink_color).move_to([0, base_y - 0.78, 0]))
    title_mob = None
    if title:
        title_mob = crisp_text(title, font_size=title_fs, color=ink_color,
                               weight=BOLD).move_to([0, cy + height / 2 + title_buff, 0])
        rest.add(title_mob)
    legend = _series_legend(series, ink_color,
                            legend_pos if legend_pos is not None else [4.6, cy + height / 2 - 0.2, 0],
                            legend_fs)
    rest.add(legend)

    g = VGroup(*series_groups, rest)
    g.series = series_groups
    g.bars = [b for c in series_groups for b in c.bars]
    g.rest = rest
    g.legend = legend
    g.title_mob = title_mob
    return g


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
