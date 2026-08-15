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


def _tail(hw, hh, side, length, spread, base=0.0, tip_off=-0.35, radius=0.0):
    """A triangle from one edge of the bubble out to a tip.

    ``hw``/``hh`` are the body half-extents; ``spread`` is the tail base
    half-width as a fraction of the half-extent it sits on; ``length`` is how
    far the tip juts past the edge. For a horizontal (``left``/``right``) tail,
    ``base`` shifts where the tail attaches ALONG the vertical edge (fraction of
    ``hh``; negative = lower) and ``tip_off`` is the tip's vertical offset from
    that base (fraction of ``hh``; negative = flicks down). Returns (Polygon,
    tip_point)."""
    horiz = {"left": -0.45, "": 0.0, "right": 0.45}
    if side.startswith("bottom") or side.startswith("top"):
        vert, sign = ("bottom", -1) if side.startswith("bottom") else ("top", 1)
        cx = hw * horiz[side[len(vert):].strip()]
        y = sign * hh
        b1 = np.array([cx - hw * spread, y - sign * 0.03, 0])
        b2 = np.array([cx + hw * spread, y - sign * 0.03, 0])
        tip = np.array([cx - hw * 0.15, y + sign * length, 0])
    elif side in ("left", "right"):
        # a horizontal tail — the speaker is off to that side; `base` slides the
        # attach point along the edge, `tip_off` sets which way the tip flicks.
        # Each base corner's x is SNAPPED onto the rounded-corner boundary at its
        # height (`radius`) so the tail stays flush on a round/pill cap at any y
        # (radius=0 → the old flat vertical edge, so existing callers are byte-same).
        sign = -1 if side == "left" else 1
        cy = hh * base

        def edge_x(y):
            straight = max(hh - radius, 0.0)          # the flat part of the edge
            if abs(y) <= straight:
                bx = hw                               # on the straight vertical edge
            else:                                     # on the corner arc
                d = min(abs(y) - straight, radius)
                bx = (hw - radius) + np.sqrt(max(radius * radius - d * d, 0.0))
            return sign * (bx - 0.03)                 # nudge 0.03 inward (flush, no sliver)

        y1, y2 = cy + hh * spread, cy - hh * spread
        b1 = np.array([edge_x(y1), y1, 0])
        b2 = np.array([edge_x(y2), y2, 0])
        tip = np.array([sign * (hw + length), cy + hh * tip_off, 0])
    else:
        raise ValueError(f"bad tail side: {side!r}")
    return Polygon(b1, tip, b2), tip


def speech_bubble(text, *, font_size=FONT_SIZE_MD, text_color=BLACK,
                  fill_color=WHITE, stroke_color=BLACK, stroke_width=3.0,
                  corner_radius=0.28, pad_w=0.5, pad_h=0.4, min_width=1.1,
                  tail="bottom left", tail_len=0.85, tail_spread=0.18,
                  tail_base=0.0, tail_tip=-0.35, pill=False):
    """A comic speech bubble sized to ``text`` (may contain ``\\n``).

    ``tail`` is a vertical tail ``top/bottom`` × ``left/''/right`` (e.g.
    ``"bottom left"``, ``"top"``) or a horizontal tail ``"left"``/``"right"``
    (the speaker is off to that side). ``pill=True`` gives fully-rounded
    (stadium) ends — the body's corner radius becomes half its height, so a
    short single-line label reads as a capsule. The bubble body is centred on
    ORIGIN before you ``move_to`` it."""
    label = crisp_paragraph(*text.split("\n"), font_size=font_size,
                            color=text_color, alignment="center")
    w = max(label.width + 2 * pad_w, min_width)
    h = label.height + 2 * pad_h
    radius = h / 2 if pill else min(corner_radius, h / 2 * 0.9)
    body = RoundedRectangle(width=w, height=h, corner_radius=radius)
    tail_poly, tip = _tail(w / 2, h / 2, tail, tail_len, tail_spread,
                           base=tail_base, tip_off=tail_tip, radius=radius)
    outline = Union(body, tail_poly)
    outline.set_fill(fill_color, opacity=1.0).set_stroke(stroke_color, stroke_width)
    label.move_to(ORIGIN)
    tip_dot = Dot(tip, radius=0.0).set_opacity(0.0)

    grp = VGroup(outline, label, tip_dot)
    grp.body = outline
    grp.label = label
    grp.tip_dot = tip_dot
    return grp
