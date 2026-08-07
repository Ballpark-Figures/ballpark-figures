"""Speech bubble — a rounded comic bubble that auto-sizes to its text, with a tail
pointing toward the speaker.

The outline is ONE continuous path: a rounded-rectangle perimeter with the tail
spliced straight into whichever edge it sits on (no boolean ``Union`` — that left a
seam and an uneven stroke). Because the perimeter is traced parametrically from the
text-derived ``w``/``h``, it reshapes cleanly for ANY amount of text — the tail slides
along its edge and the corners re-fit automatically.

    bub = speech_bubble("L", font_size=54, tail="bottom left")
    bub.move_to([2, 3, 0])
    self.play(GrowFromPoint(bub, bub.tip_dot.get_center()))

Handles on the returned VGroup:
    .body     the unioned-free single-path outline, filled + stroked
    .label    the text
    .tip_dot  an invisible Dot at the tail's tip — read ``.get_center()`` AFTER
              any move/scale to aim a GrowFromPoint / arrow at the speaker.
"""
import numpy as np
from manim import *

from bpkfigures.style import crisp_paragraph, FONT_SIZE_MD

# tail base offset along its edge for a left/''/right sub-position (fraction of the
# half-extent), and the tip's sideways lean (fraction of the half-width).
_HORIZ = {"left": -0.45, "": 0.0, "right": 0.45}
_LEAN = 0.15
_CORNER_PTS = 10          # points approximating each 90° corner arc (smooth enough)


def _tip_point(w, h, side, length, spread):
    """World position of the tail tip for a given side/length (the speaker anchor)."""
    hw, hh = w / 2, h / 2
    if side.startswith("bottom"):
        cx = hw * _HORIZ.get(side[len("bottom"):].strip(), 0.0)
        return np.array([cx - hw * _LEAN, -hh - length, 0.0])
    if side.startswith("top"):
        cx = hw * _HORIZ.get(side[len("top"):].strip(), 0.0)
        return np.array([cx - hw * _LEAN, hh + length, 0.0])
    if side == "left":
        return np.array([-hw - length, -hh * 0.35, 0.0])
    if side == "right":
        return np.array([hw + length, -hh * 0.35, 0.0])
    raise ValueError(f"bad tail side: {side!r}")


def _outline_points(w, h, r, side, length, spread):
    """Perimeter points (clockwise) of a rounded rect ``w``×``h`` (corner radius ``r``)
    with a triangular tail spliced into one edge. Returned as a closed corner list to
    feed ``set_points_as_corners`` — one continuous path, uniform stroke."""
    r = min(r, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    tip = _tip_point(w, h, side, length, spread)
    P = []

    def add(x, y):
        P.append(np.array([x, y, 0.0]))

    def corner(cx, cy, a0, a1):
        for a in np.linspace(a0, a1, _CORNER_PTS):
            P.append(np.array([cx + r * np.cos(a), cy + r * np.sin(a), 0.0]))

    # top edge (left → right)
    add(-hw + r, hh)
    if side.startswith("top"):
        cx = hw * _HORIZ.get(side[len("top"):].strip(), 0.0)
        b = hw * spread
        add(cx - b, hh); add(tip[0], tip[1]); add(cx + b, hh)
    add(hw - r, hh)
    corner(hw - r, hh - r, np.pi / 2, 0.0)              # TR
    # right edge (top → bottom)
    if side == "right":
        b = hh * spread
        add(hw, b); add(tip[0], tip[1]); add(hw, -b)
    add(hw, -hh + r)
    corner(hw - r, -hh + r, 0.0, -np.pi / 2)            # BR
    # bottom edge (right → left)
    add(hw - r, -hh)
    if side.startswith("bottom"):
        cx = hw * _HORIZ.get(side[len("bottom"):].strip(), 0.0)
        b = hw * spread
        add(cx + b, -hh); add(tip[0], tip[1]); add(cx - b, -hh)
    add(-hw + r, -hh)
    corner(-hw + r, -hh + r, -np.pi / 2, -np.pi)        # BL
    # left edge (bottom → top)
    if side == "left":
        b = hh * spread
        add(-hw, -b); add(tip[0], tip[1]); add(-hw, b)
    add(-hw, hh - r)
    corner(-hw + r, hh - r, np.pi, np.pi / 2)           # TL
    add(-hw + r, hh)                                     # close back to start

    # drop consecutive duplicates (an edge endpoint that coincides with a corner start)
    out = [P[0]]
    for p in P[1:]:
        if np.linalg.norm(p - out[-1]) > 1e-9:
            out.append(p)
    return out


def speech_bubble(text, *, font_size=FONT_SIZE_MD, text_color=BLACK,
                  fill_color=WHITE, stroke_color=BLACK, stroke_width=3.0,
                  corner_radius=0.28, pad_w=0.5, pad_h=0.4, min_width=1.1,
                  tail="bottom left", tail_len=0.85, tail_spread=0.18):
    """A comic speech bubble sized to ``text`` (may contain ``\\n``).

    ``tail`` is a vertical tail ``top/bottom`` × ``left/''/right`` (e.g.
    ``"bottom left"``, ``"top"``) or a horizontal tail ``"left"``/``"right"``
    (the speaker is off to that side). The bubble body is centred on ORIGIN
    before you ``move_to`` it."""
    label = crisp_paragraph(*text.split("\n"), font_size=font_size,
                            color=text_color, alignment="center")
    w = max(label.width + 2 * pad_w, min_width)
    h = label.height + 2 * pad_h
    r = min(corner_radius, h / 2 * 0.9)

    outline = VMobject()
    outline.set_points_as_corners(_outline_points(w, h, r, tail, tail_len, tail_spread))
    outline.set_fill(fill_color, opacity=1.0).set_stroke(stroke_color, stroke_width)
    label.move_to(ORIGIN)
    tip_dot = Dot(_tip_point(w, h, tail, tail_len, tail_spread),
                  radius=0.0).set_opacity(0.0)

    grp = VGroup(outline, label, tip_dot)
    grp.body = outline
    grp.label = label
    grp.tip_dot = tip_dot
    return grp
