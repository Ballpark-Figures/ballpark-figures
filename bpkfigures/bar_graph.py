from manim import *
import numpy as np

from bpkfigures.style import FONT, FONT_SIZE_SM, FONT_SIZE_MD, ACCENT_FILL, crisp_text


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
):
    """Horizontal double-bar table. ``rows`` is a list of dicts:
        {label, max_value, expected_value, pct, fade=False, color=None}
    Per row: a long bar (length ∝ max_value, light) with an overlapping short bar
    (length ∝ expected_value, saturated) and a "{pct}%" readout to the right.
    All rows share one value→length scale. Returns a VGroup whose ``[i]`` is row
    ``i`` — each row VGroup is (label, long_bar, short_bar, pct)."""
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

        table.add(VGroup(label, long_bar, short_bar, pct))

    table.move_to(center)
    return table
