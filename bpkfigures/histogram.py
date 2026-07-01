from manim import *
import numpy as np

from bpkfigures.style import (FONT, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
                              ACCENT_FILL, ACCENT_GOLD, crisp_text, crisp_paragraph)


def get_histogram_counts(data, min_val, max_val):
    values = list(range(min_val, max_val + 1))
    counts = {k: 0 for k in values}
    for x in data:
        counts[x] += 1
    return values, counts


def _nice_ticks(vmax, target=5):
    """Round tick values in (0, vmax] using a 1/2/2.5/5 ×10^k step."""
    if vmax <= 0:
        return []
    raw = vmax / target
    mag = 10 ** np.floor(np.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    ticks = []
    k = 1
    while k * step <= vmax + 1e-9:
        ticks.append(round(k * step, 10))
        k += 1
    return ticks


def _build_hist_bars(values, mag_lookup, max_mag, width, height, n,
                     bar_color, opacity, is_vertical, bar_ratio=0.9,
                     full_grid=False):
    """One Rectangle per value, scaled so max_mag == height. Positions match
    across calls (same values/width/n), so a base layer and an overlay layer line
    up bar-for-bar. ``bar_ratio`` is the fraction of each slot the bar fills
    (1.0 = no gaps). ``full_grid`` keeps a (near-zero) bar at EVERY value so two
    layers share one bar per slot — Transforming between them then changes each
    bar's HEIGHT in place (some grow, some shrink) instead of sliding bars."""
    bars = VGroup()
    bar_width = width / n
    for i, val in enumerate(values):
        c = mag_lookup.get(val, 0)
        if not full_grid and (c <= 0 or max_mag <= 0):
            continue
        h = (c / max_mag) * height if max_mag > 0 else 0
        if full_grid:
            h = max(h, 1e-3)
        if not is_vertical:
            bar = Rectangle(width=bar_width * bar_ratio, height=h,
                            fill_color=bar_color, fill_opacity=opacity,
                            stroke_width=0)
            x = (i - n / 2 + 0.5) * bar_width
            y = h / 2
        else:
            bar = Rectangle(width=h, height=bar_width * bar_ratio,
                            fill_color=bar_color, fill_opacity=opacity,
                            stroke_width=0)
            x = h / 2
            y = (i - n / 2 + 0.5) * bar_width
        bar.move_to(np.array([x, y, 0]))
        bars.add(bar)
    return bars


def get_histogram(
    data,
    center=ORIGIN,
    title=None,
    min_val=None,
    max_val=None,
    width=8,
    height=4,
    bar_color=ACCENT_FILL,
    is_vertical=False,
    x_axis_label=None,
    show_sim_count=False,
    counts=None,
    min_prob=None,
    show_y_axis=False,
    y_axis_label=None,
    y_ticks=4,
    overlays=None,
    base_label=None,
    base_opacity=0.4,
    x_tick_step=10,
    bar_ratio=0.9,
    median=None,
    median_color=ACCENT_GOLD,
    median_label="Median",
):
    # ── magnitudes: either supplied directly ({value: prob/weight}) or counted
    #    from raw samples. ``total`` (sum over the FULL set, pre-trim) anchors the
    #    percent y-axis. ──────────────────────────────────────────────────────
    if counts is not None:
        mag = dict(counts)
        if min_val is None:
            min_val = min(mag)
        if max_val is None:
            max_val = max(mag)
    else:
        if min_val is None:
            min_val = min(data)
        if max_val is None:
            max_val = max(data)
        _, mag = get_histogram_counts(data, min_val=min_val, max_val=max_val)

    total = sum(mag.values())

    # ── auto-trim the displayed range to where the frequency clears min_prob ──
    if min_prob is not None and total > 0:
        present = [v for v in range(min_val, max_val + 1)
                   if mag.get(v, 0) / total > min_prob]
        if present:
            min_val, max_val = min(present), max(present)

    values = list(range(min_val, max_val + 1))
    n = max_val - min_val + 1
    bar_width = width / n
    max_mag = max((mag.get(v, 0) for v in values), default=0)

    bars = _build_hist_bars(
        values, mag, max_mag, width, height, n, bar_color,
        opacity=(base_opacity if overlays else 1.0), is_vertical=is_vertical,
        bar_ratio=bar_ratio)

    elements = VGroup(bars)

    # ── overlays: sub-distributions drawn on top, same normalization ─────────
    overlay_groups = VGroup()
    if overlays:
        for ov_counts, ov_color, _ov_label in overlays:
            ov_bars = _build_hist_bars(
                values, dict(ov_counts), max_mag, width, height, n,
                ov_color, opacity=1.0, is_vertical=is_vertical, bar_ratio=bar_ratio)
            ov_bars.set_z_index(1)
            overlay_groups.add(ov_bars)
        elements.add(overlay_groups)

    if not is_vertical:
        axis = Line(
            start=np.array([-width / 2, 0, 0]),
            end=np.array([width / 2, 0, 0]),
            color=BLACK
        )
    else:
        axis = Line(
            start=np.array([0, -width / 2, 0]),
            end=np.array([0, width / 2, 0]),
            color=BLACK
        )
    elements.add(axis)

    # component handles (None unless the matching block below builds them) so a
    # scene / morph_histogram can address each piece by role
    y_axis = None
    y_tick_labels = None
    y_axis_text = None
    axis_label_text = None
    title_text = None

    # ── optional vertical axis with percent ticks (horizontal hist only) ─────
    if show_y_axis and not is_vertical:
        y_axis = Line(
            start=np.array([-width / 2, 0, 0]),
            end=np.array([-width / 2, height, 0]),
            color=BLACK
        )
        elements.add(y_axis)
        y_tick_labels = VGroup()
        max_frac = (max_mag / total) if total > 0 else 0
        vmax = max_frac * 100                       # tallest bar as a percent
        for pct in _nice_ticks(vmax, y_ticks):
            y = (pct / vmax) * height if vmax > 0 else 0
            tick = Line(
                start=np.array([-width / 2 - 0.1, y, 0]),
                end=np.array([-width / 2, y, 0]),
                color=BLACK
            )
            lab = crisp_text(f"{pct:g}%", font=FONT,
                             font_size=FONT_SIZE_SM, color=BLACK)
            lab.next_to(tick, LEFT, buff=0.1)
            y_tick_labels.add(tick, lab)
        elements.add(y_tick_labels)
        if y_axis_label is not None:
            y_axis_text = crisp_text(y_axis_label, font=FONT,
                                     font_size=FONT_SIZE_SM, color=BLACK)
            y_axis_text.rotate(PI / 2)
            y_axis_text.next_to(y_tick_labels, LEFT, buff=0.2)
            elements.add(y_axis_text)

    labels = VGroup()
    for i, val in enumerate(values):
        if val % x_tick_step != 0:
            continue
        if not is_vertical:
            x = (i - n / 2 + 0.5) * bar_width
            pos = np.array([x, -0.3, 0])
        else:
            y = (i - n / 2 + 0.5) * bar_width
            pos = np.array([-0.3, y, 0])
        label = crisp_text(str(val), font=FONT, font_size=FONT_SIZE_SM, color=BLACK)
        label.move_to(pos)
        labels.add(label)
    elements.add(labels)

    if x_axis_label is not None and not is_vertical:
        axis_label_text = crisp_text(
            x_axis_label,
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        axis_label_text.next_to(labels, DOWN, buff=0.3)
        elements.add(axis_label_text)

    if title is not None:
        title_text = crisp_paragraph(
            title,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_LG,
            color=BLACK
        )
        title_text.next_to(elements, UP, buff=0.5)
        title_text.set_x(axis.get_center()[0])   # centre on the plot, not the
        elements.add(title_text)                 # y-axis-label-heavy bounding box

    if show_sim_count:
        sim_label = crisp_text(
            f"{len(data):,} Simulations",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        sim_label.next_to(bars, UR, buff=0)
        sim_label.shift(LEFT * 1.0 + DOWN * 0.6)
        elements.add(sim_label)

    # ── legend: a swatch + label per series (base + each overlay) ────────────
    if overlays and (base_label is not None
                     or any(lbl is not None for _, _, lbl in overlays)):
        entries = []
        if base_label is not None:
            entries.append((bar_color, base_label))
        for _, ov_color, ov_label in overlays:
            if ov_label is not None:
                entries.append((ov_color, ov_label))
        rows = VGroup()
        for col, text in entries:
            swatch = Square(side_length=0.22, fill_color=col,
                            fill_opacity=1.0, stroke_width=0)
            txt = crisp_text(text, font=FONT, font_size=FONT_SIZE_SM,
                             color=BLACK)
            txt.next_to(swatch, RIGHT, buff=0.15)
            rows.add(VGroup(swatch, txt))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        # top-right, inset from the plot's upper-right corner
        rows.next_to(np.array([width / 2, height, 0]), DL, buff=0.0)
        rows.shift(LEFT * 0.2 + DOWN * 0.2)
        elements.add(rows)

    core = VGroup(bars, axis)
    shift = np.array(center) - core.get_center()
    elements.shift(shift)

    # geometry handles so a scene can build aligned overlay layers + legends and
    # animate them independently of the base plot
    elements.bars = bars
    elements.hist_geom = {
        "values": values, "mag": mag, "max_mag": max_mag, "width": width,
        "height": height, "n": n, "shift": shift, "bar_ratio": bar_ratio,
        "total": total,
    }

    # per-role handles (see morph_histogram); any may be None
    elements.x_axis = axis
    elements.y_axis = y_axis
    elements.y_ticks = y_tick_labels
    elements.y_axis_label_text = y_axis_text
    elements.x_labels = labels
    elements.x_axis_label_text = axis_label_text
    elements.title_text = title_text

    # ── optional median highlight + label (built in ABSOLUTE coords, so add it
    #    AFTER the shift above — median_marker applies the shift itself) ────────
    if median is not None:
        elements.median_group = median_marker(
            elements, median, color=median_color, label=median_label)
        elements.add(elements.median_group)
    else:
        elements.median_group = None

    return elements


def median_marker(plot, median, color=ACCENT_GOLD, label="Median",
                  show_value=True, font_size=FONT_SIZE_SM, label_buff=0.12):
    """Recolour the bar at score ``median`` and label it (e.g. "Median 248"),
    anchored to ``plot`` via its ``hist_geom`` (same convention as overlay_bars /
    make_hist_legend). ``median`` snaps to the nearest in-range value. Returns a
    VGroup(highlighted_bar, label); z-indexed above the base bars."""
    g = plot.hist_geom
    values, mag = g["values"], g["mag"]
    max_mag, width, height = g["max_mag"], g["width"], g["height"]
    n, shift, bar_ratio = g["n"], g["shift"], g["bar_ratio"]

    if median not in values:
        median = min(values, key=lambda v: abs(v - median))
    i = values.index(median)
    bar_width = width / n
    c = mag.get(median, 0)
    h = (c / max_mag) * height if max_mag > 0 else 0
    x = (i - n / 2 + 0.5) * bar_width + shift[0]
    y0 = shift[1]

    hl = Rectangle(width=bar_width * bar_ratio, height=max(h, 1e-3),
                   fill_color=color, fill_opacity=1.0, stroke_width=0)
    hl.move_to(np.array([x, y0 + h / 2, 0]))
    hl.set_z_index(2)

    txt = f"{label} {median}" if show_value else label
    lab = crisp_text(txt, font=FONT, font_size=font_size, color=BLACK,
                     weight="BOLD")
    lab.next_to(np.array([x, y0 + h, 0]), UP, buff=label_buff)
    lab.set_z_index(2)

    return VGroup(hl, lab)


def morph_histogram(old, new):
    """Animations that smoothly turn one get_histogram plot into another whose
    range / y-scale / title / median differ. Bars and axis lines Replacement
    Transform (bars morph in place, filling the same box); the tick-label groups,
    title, and median crossfade (values shift). Returns a list to splat into
    ``self.play(*morph_histogram(old, new), run_time=...)``; afterwards the NEW
    objects are the live ones, so track ``self.plot = new``."""
    anims = [ReplacementTransform(old.bars, new.bars),
             ReplacementTransform(old.x_axis, new.x_axis)]
    swaps = [
        ("y_axis", ReplacementTransform),
        ("y_ticks", FadeTransform),
        ("y_axis_label_text", ReplacementTransform),
        ("x_labels", FadeTransform),
        ("x_axis_label_text", ReplacementTransform),
        ("title_text", FadeTransform),
        ("median_group", FadeTransform),
    ]
    for attr, anim in swaps:
        o = getattr(old, attr, None)
        nw = getattr(new, attr, None)
        if o is not None and nw is not None:
            anims.append(anim(o, nw))
        elif o is not None:
            anims.append(FadeOut(o))
        elif nw is not None:
            anims.append(FadeIn(nw))
    return anims


def overlay_bars(plot, counts, color, opacity=1.0, full_grid=False):
    """A VGroup of overlay bars aligned bar-for-bar to ``plot`` (a get_histogram
    result), built from {value: prob}. Same normalization as the base, so each
    overlay bar never exceeds its base bar. With ``full_grid=True`` the layer has
    one bar per score, so Transforming between two such layers morphs heights in
    place (the battleship-style transition)."""
    g = plot.hist_geom
    bars = _build_hist_bars(
        g["values"], dict(counts), g["max_mag"], g["width"], g["height"],
        g["n"], color, opacity, is_vertical=False, bar_ratio=g["bar_ratio"],
        full_grid=full_grid)
    bars.shift(g["shift"])
    bars.set_z_index(1)
    return bars


def make_hist_legend(plot, entries, font_size=FONT_SIZE_SM, anchor=None):
    """Legend (swatch + label per (color, text) entry) anchored by its UPPER-LEFT
    corner so it never drifts as entries/label widths change. Defaults to the
    upper area just right of the plot's centre (where the bars are short)."""
    g = plot.hist_geom
    rows = VGroup()
    for col, text in entries:
        swatch = Square(side_length=0.22, fill_color=col, fill_opacity=1.0,
                        stroke_width=0)
        txt = crisp_text(text, font=FONT, font_size=font_size, color=BLACK)
        txt.next_to(swatch, RIGHT, buff=0.15)
        rows.add(VGroup(swatch, txt))
    rows.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    if anchor is None:
        anchor = np.array([g["shift"][0] + g["width"] * 0.06,
                           g["shift"][1] + g["height"] * 0.97, 0])
    rows.move_to(anchor, aligned_edge=UL)
    return rows


def get_dual_histogram(
    data_x,
    data_y,
    center=ORIGIN,
    min_val=None,
    max_val=None,
    square_size=5,
    marginal_size=1.25,
    x_label=None,
    y_label=None,
    above_color=BLUE,
    below_color=BLUE,
    title=None
):
    if min_val is None:
        min_val = min(min(data_x), min(data_y))
    if max_val is None:
        max_val = max(max(data_x), max(data_y))

    values_x, counts_x = get_histogram_counts(data_x, min_val=min_val, max_val=max_val)
    values_y, counts_y = get_histogram_counts(data_y, min_val=min_val, max_val=max_val)

    x_counts = np.array([counts_x[v] for v in values_x], dtype=float)
    y_counts = np.array([counts_y[v] for v in values_y], dtype=float)

    x_probs = x_counts / x_counts.sum()
    y_probs = y_counts / y_counts.sum()

    joint = np.outer(y_probs, x_probs)

    n = max_val - min_val + 1
    cell_size = square_size / n

    vmin = joint.min()
    vmax = joint.max()

    def get_color(val, coord_diff):
        alpha = (val - vmin) / (vmax - vmin) if vmax > vmin else 0
        if coord_diff > 0:
            dark_color = above_color
        elif coord_diff < 0:
            dark_color = below_color
        else:
            dark_color = (above_color + below_color) / 2
        return interpolate_color(0.2 * dark_color + 0.8 * WHITE, dark_color, alpha)

    heatmap = VGroup()
    for r in range(n):
        for c in range(n):
            square = Square(
                side_length=cell_size * 1.1,
                fill_color=get_color(joint[r, c], r - c),
                fill_opacity=1.0,
                stroke_width=0
            )
            x = -square_size / 2 + (c + 0.5) * cell_size
            y = -square_size / 2 + (r + 0.5) * cell_size
            square.move_to(np.array([x, y, 0]))
            heatmap.add(square)

    border = SurroundingRectangle(heatmap, color=BLACK, stroke_width=2, buff=0)
    heatmap_group = VGroup(heatmap, border)

    bottom_hist = get_histogram(
        data_x,
        center=ORIGIN,
        min_val=min_val,
        max_val=max_val,
        width=square_size,
        height=marginal_size,
        is_vertical=False,
        bar_color=above_color
    )

    left_hist = get_histogram(
        data_y,
        center=ORIGIN,
        min_val=min_val,
        max_val=max_val,
        width=square_size,
        height=marginal_size,
        is_vertical=True,
        bar_color=below_color
    )

    heatmap_group.shift(np.array([square_size / 2, square_size / 2, 0]))
    bottom_hist.shift(np.array([square_size / 2, -marginal_size, 0]))
    left_hist.shift(np.array([-marginal_size, square_size / 2, 0]))

    labels = VGroup()

    if x_label is not None:
        x_text = crisp_paragraph(
            x_label,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        x_text.next_to(bottom_hist, DOWN, buff=0.4)
        labels.add(x_text)

    if y_label is not None:
        y_text = crisp_paragraph(
            y_label,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        y_text.rotate(PI / 2)
        y_text.next_to(left_hist, LEFT, buff=0.4)
        labels.add(y_text)

    if title is not None:
        title_text = crisp_paragraph(
            *title.split("\n"),
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_MD,
            color=BLACK
        )
        title_text.next_to(heatmap_group, RIGHT, buff=0.4)
        labels.add(title_text)

    elements = VGroup(left_hist, heatmap_group, bottom_hist, labels)
    elements.move_to(center)
    return elements, joint


def get_win_percents(arr, first_player=False):
    rows, cols = arr.shape
    below = 0.0
    above = 0.0
    diag = 0.0

    for r in range(rows):
        for c in range(cols):
            if r > c:
                below += arr[r, c]
            elif r < c:
                above += arr[r, c]
            else:
                diag += arr[r, c]

    total = arr.sum()

    if first_player:
        below_pct = (below + diag) / total
    else:
        below_pct = (below + diag / 2) / total
    above_pct = 1 - below_pct

    return below_pct, above_pct


def get_diagonal_line(border, color=BLACK, stroke_width=2):
    return Line(
        border.get_corner(DL),
        border.get_corner(UR),
        color=color,
        stroke_width=stroke_width
    )


def get_diagonal_labels(
    arr,
    border,
    font_size=FONT_SIZE_SM,
    decimals=1,
    above_color=BLACK,
    below_color=BLACK,
    first_player=False,
    opacity_diff=True,
):
    below_pct, above_pct = get_win_percents(arr, first_player=first_player)

    top_left = border.get_corner(UL)
    bottom_right = border.get_corner(DR)

    above_label = crisp_text(
        f"{100 * below_pct:.{decimals}f}%",
        font=FONT,
        font_size=font_size,
        color=(above_color + BLACK) / 2,
    )
    if opacity_diff:
        above_label.set_opacity(0.5)
    above_label.next_to(top_left, DR, buff=0.1)

    below_label = crisp_text(
        f"{100 * above_pct:.{decimals}f}%",
        font=FONT,
        font_size=font_size,
        color=(below_color + BLACK) / 2,
    )
    below_label.next_to(bottom_right, UL, buff=0.1)

    return VGroup(above_label, below_label)


def get_diagonal_annotation(
    dual_histogram,
    color=BLACK,
    stroke_width=2,
    font_size=FONT_SIZE_SM,
    decimals=1,
    above_color=BLACK,
    below_color=BLACK,
    first_player=False,
    opacity_diff=True,
):
    elements, arr = dual_histogram
    left_hist, heatmap_group, bottom_hist, labels = elements
    heatmap, border = heatmap_group

    line = get_diagonal_line(border, color=color, stroke_width=stroke_width)
    labels = get_diagonal_labels(arr, border, font_size=font_size, decimals=decimals, above_color=above_color, below_color=below_color, first_player=first_player, opacity_diff=opacity_diff)

    return VGroup(line, labels)