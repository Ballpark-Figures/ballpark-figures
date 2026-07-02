from manim import *
import numpy as np

from bpkfigures.style import (FONT, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
                              ACCENT_FILL, ACCENT_PALETTE, crisp_text,
                              crisp_paragraph)
from bpkfigures.histogram import _nice_ticks


def get_line_graph(
    series,
    x_values,
    center=ORIGIN,
    width=8.0,
    height=4.0,
    y_min=0.0,
    y_max=None,
    y_ticks=5,
    x_tick_step=1,
    title=None,
    x_axis_label=None,
    y_axis_label=None,
    line_stroke=4.0,
    show_dots=False,
    dot_radius=0.055,
    palette=ACCENT_PALETTE,
):
    """A multi-series line graph on a shared x-domain (turn # vs avg points, …).

    ``series`` is a list of dicts, one per line:
        {label, values, color=None, dashed=False, stroke=None}
    where ``values`` is a list aligned 1:1 with ``x_values`` (use ``None`` for a
    gap / missing point). Series with no explicit ``color`` cycle through
    ``palette``. All series share one x- and y-scale.

    Everything is built in local coords then shifted so the plot BOX (the axes
    rectangle) centers on ``center``. Returns a VGroup with per-role handles so a
    scene can animate each piece independently:
        .lines        VGroup, one polyline per series (``[i]`` = series i)
        .dots         VGroup, one dot-group per series (empty unless show_dots)
        .x_axis .y_axis
        .x_ticks .y_ticks          each a VGroup of (tick, label) pairs
        .x_axis_label_text .y_axis_label_text .title_text   (any may be None)
        .plot_geom    dict for mapping data->screen (see ``line_point``)

    The per-series colour is also stored on each line as ``.series_color`` and the
    label as ``.series_label`` so legends / end-labels can be built afterwards
    (see ``make_line_legend``)."""
    xmin, xmax = min(x_values), max(x_values)
    x_span = (xmax - xmin) or 1

    # ── y-scale: nice round ticks from 0..data_max unless y_max is pinned ──────
    all_vals = [v for s in series for v in s["values"] if v is not None]
    data_max = max(all_vals) if all_vals else 1.0
    ticks = _nice_ticks(y_max if y_max is not None else data_max, y_ticks)
    if y_max is None:
        y_max = max(ticks[-1], data_max) if ticks else data_max
    y_span = (y_max - y_min) or 1

    def x_of(x):
        return -width / 2 + (x - xmin) / x_span * width

    def y_of(y):
        return (y - y_min) / y_span * height

    # ── axes (an L at the plot box's bottom-left) ─────────────────────────────
    # z-index 2 keeps the axes ABOVE the lines (z 1), so a line's very first point
    # sitting on the y-axis (or a zero value on the x-axis) doesn't smudge over it.
    x_axis = Line([-width / 2, 0, 0], [width / 2, 0, 0], color=BLACK)
    y_axis = Line([-width / 2, 0, 0], [-width / 2, height, 0], color=BLACK)
    x_axis.set_z_index(2)
    y_axis.set_z_index(2)
    elements = VGroup(x_axis, y_axis)

    # ── x ticks + labels (every x_tick_step-th value of the domain) ───────────
    x_ticks = VGroup()
    for xv in x_values:
        if (xv - xmin) % x_tick_step != 0:
            continue
        x = x_of(xv)
        tick = Line([x, -0.1, 0], [x, 0, 0], color=BLACK)
        lab = crisp_text(str(xv), font=FONT, font_size=FONT_SIZE_SM, color=BLACK)
        lab.next_to(tick, DOWN, buff=0.12)
        x_ticks.add(VGroup(tick, lab))
    elements.add(x_ticks)

    # ── y ticks + labels (nice round steps) ───────────────────────────────────
    y_tick_grp = VGroup()
    for tv in ticks:
        if tv < y_min or tv > y_max:
            continue
        y = y_of(tv)
        tick = Line([-width / 2 - 0.1, y, 0], [-width / 2, y, 0], color=BLACK)
        lab = crisp_text(f"{tv:g}", font=FONT, font_size=FONT_SIZE_SM, color=BLACK)
        lab.next_to(tick, LEFT, buff=0.1)
        y_tick_grp.add(VGroup(tick, lab))
    elements.add(y_tick_grp)

    # ── the lines ─────────────────────────────────────────────────────────────
    lines = VGroup()
    dots = VGroup()
    for i, s in enumerate(series):
        color = s.get("color") or palette[i % len(palette)]
        stroke = s.get("stroke", line_stroke)
        pts = [np.array([x_of(xv), y_of(v), 0])
               for xv, v in zip(x_values, s["values"]) if v is not None]

        line = VMobject(stroke_color=color, stroke_width=stroke)
        if pts:
            line.set_points_as_corners(pts)
        if s.get("dashed"):
            line = DashedVMobject(line, num_dashes=max(6, len(pts) * 2),
                                  dashed_ratio=0.6)
        line.series_color = color
        line.series_label = s["label"]
        lines.add(line)

        dot_grp = VGroup()
        if show_dots:
            for p in pts:
                dot_grp.add(Dot(p, radius=dot_radius, color=color))
            dot_grp.set_z_index(1)
        dots.add(dot_grp)
    lines.set_z_index(1)
    elements.add(lines, dots)

    # ── axis labels + title ───────────────────────────────────────────────────
    x_axis_label_text = None
    if x_axis_label is not None:
        x_axis_label_text = crisp_text(x_axis_label, font=FONT,
                                       font_size=FONT_SIZE_SM, color=BLACK)
        x_axis_label_text.next_to(x_ticks, DOWN, buff=0.25)
        x_axis_label_text.set_x(0)
        elements.add(x_axis_label_text)

    y_axis_label_text = None
    if y_axis_label is not None:
        y_axis_label_text = crisp_text(y_axis_label, font=FONT,
                                       font_size=FONT_SIZE_SM, color=BLACK)
        y_axis_label_text.rotate(PI / 2)
        y_axis_label_text.next_to(y_tick_grp, LEFT, buff=0.2)
        y_axis_label_text.set_y(height / 2)
        elements.add(y_axis_label_text)

    title_text = None
    if title is not None:
        title_text = crisp_paragraph(title, alignment="center", font=FONT,
                                     font_size=FONT_SIZE_LG, color=BLACK)
        title_text.next_to(elements, UP, buff=0.4)
        title_text.set_x(0)
        elements.add(title_text)

    # ── shift so the plot BOX centers on ``center`` ───────────────────────────
    box_center = np.array([0, height / 2, 0])
    shift = np.array(center) - box_center
    elements.shift(shift)

    elements.lines = lines
    elements.dots = dots
    elements.x_axis = x_axis
    elements.y_axis = y_axis
    elements.x_ticks = x_ticks
    elements.y_ticks = y_tick_grp
    elements.x_axis_label_text = x_axis_label_text
    elements.y_axis_label_text = y_axis_label_text
    elements.title_text = title_text
    elements.plot_geom = {
        "x_values": list(x_values), "xmin": xmin, "xmax": xmax,
        "y_min": y_min, "y_max": y_max, "width": width, "height": height,
        "shift": shift,
    }
    return elements


def line_point(geom, x, y):
    """Absolute screen coords of data point (x, y) for a get_line_graph result —
    use it to anchor annotations (a label at a line's end, a callout, a marker)
    the same way histogram scenes use ``hist_geom``. ``geom`` is ``plot.plot_geom``."""
    width, height = geom["width"], geom["height"]
    x_span = (geom["xmax"] - geom["xmin"]) or 1
    y_span = (geom["y_max"] - geom["y_min"]) or 1
    px = -width / 2 + (x - geom["xmin"]) / x_span * width
    py = (y - geom["y_min"]) / y_span * height
    return np.array([px, py, 0]) + geom["shift"]


def make_line_legend(plot, entries=None, font_size=FONT_SIZE_SM, anchor=None,
                     swatch_len=0.34):
    """Legend (a short colour dash + label per series) for a get_line_graph result,
    anchored by its UPPER-LEFT corner so it never drifts as entries change. With
    ``entries=None`` it reads (colour, label) straight off the plot's lines.
    Defaults to the plot's upper-right interior."""
    if entries is None:
        entries = [(ln.series_color, ln.series_label) for ln in plot.lines]
    rows = VGroup()
    for col, text in entries:
        dash = Line([0, 0, 0], [swatch_len, 0, 0], color=col, stroke_width=4.0)
        txt = crisp_text(text, font=FONT, font_size=font_size, color=BLACK)
        txt.next_to(dash, RIGHT, buff=0.15)
        rows.add(VGroup(dash, txt))
    rows.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    g = plot.plot_geom
    if anchor is None:
        anchor = np.array([g["width"] * 0.10, g["height"] * 0.97, 0]) + g["shift"]
    rows.move_to(anchor, aligned_edge=UL)
    return rows
