"""Speech bubble — a rounded comic bubble that auto-sizes to its text, with a
tail pointing toward the speaker. Shared across videos; supersedes battleship's
ellipse-based ``assets.speech_bubbles`` (cleaner outline, content-sized, a tip
handle so a scene can grow it out of the speaker).

    bub = speech_bubble("L", font_size=54, tail="bottom left")
    bub.move_to([2, 3, 0])
    self.play(GrowFromPoint(bub, bub.tip_dot.get_center()))

Handles on the returned VGroup:
    .body     the unioned outline (bubble + tail), filled + stroked
    .label    the text
    .tip_dot  an invisible Dot at the tail's tip — read ``.get_center()`` AFTER
              any move/scale to aim a GrowFromPoint / arrow at the speaker.
"""
from manim import *

from bpkfigures.style import crisp_paragraph, FONT_SIZE_MD


def _tail(hw, hh, side, length, spread):
    """A triangle from one edge of the bubble out to a tip.

    ``hw``/``hh`` are the body half-extents; ``spread`` is the tail base
    half-width as a fraction of the half-extent it sits on; ``length`` is how
    far the tip juts past the edge. Returns (Polygon, tip_point)."""
    horiz = {"left": -0.45, "": 0.0, "right": 0.45}
    if side.startswith("bottom") or side.startswith("top"):
        vert, sign = ("bottom", -1) if side.startswith("bottom") else ("top", 1)
        cx = hw * horiz[side[len(vert):].strip()]
        y = sign * hh
        b1 = np.array([cx - hw * spread, y - sign * 0.03, 0])
        b2 = np.array([cx + hw * spread, y - sign * 0.03, 0])
        tip = np.array([cx - hw * 0.15, y + sign * length, 0])
    else:
        raise ValueError(f"bad tail side: {side!r}")
    return Polygon(b1, tip, b2), tip


def speech_bubble(text, *, font_size=FONT_SIZE_MD, text_color=BLACK,
                  fill_color=WHITE, stroke_color=BLACK, stroke_width=3.0,
                  corner_radius=0.28, pad_w=0.5, pad_h=0.4, min_width=1.1,
                  tail="bottom left", tail_len=0.85, tail_spread=0.18):
    """A comic speech bubble sized to ``text`` (may contain ``\\n``).

    ``tail`` is one of ``top/bottom`` × ``left/''/right`` (e.g. ``"bottom
    left"``, ``"top"``). The bubble body is centred on ORIGIN before you
    ``move_to`` it."""
    label = crisp_paragraph(*text.split("\n"), font_size=font_size,
                            color=text_color, alignment="center")
    w = max(label.width + 2 * pad_w, min_width)
    h = label.height + 2 * pad_h
    body = RoundedRectangle(width=w, height=h,
                            corner_radius=min(corner_radius, h / 2 * 0.9))
    tail_poly, tip = _tail(w / 2, h / 2, tail, tail_len, tail_spread)
    outline = Union(body, tail_poly)
    outline.set_fill(fill_color, opacity=1.0).set_stroke(stroke_color, stroke_width)
    label.move_to(ORIGIN)
    tip_dot = Dot(tip, radius=0.0).set_opacity(0.0)

    grp = VGroup(outline, label, tip_dot)
    grp.body = outline
    grp.label = label
    grp.tip_dot = tip_dot
    return grp
