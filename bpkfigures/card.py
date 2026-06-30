from manim import *

from bpkfigures.style import CARD_FILL


def get_card(width, height, center=ORIGIN, fill=CARD_FILL, corner_radius=0.22,
             stroke_color=BLACK, stroke_width=2.0):
    """A rounded panel — the standard surface to sit content on (matches the
    scorecard look). Returns a single RoundedRectangle."""
    return RoundedRectangle(
        width=width, height=height, corner_radius=corner_radius,
        fill_color=fill, fill_opacity=1.0,
        stroke_color=stroke_color, stroke_width=stroke_width,
    ).move_to(center)


def card_behind(mob, pad=0.45, **kwargs):
    """A card sized to wrap ``mob`` (with ``pad`` margin), placed one z-level
    behind it. Pass get_card kwargs (fill, corner_radius, …) through."""
    card = get_card(mob.width + 2 * pad, mob.height + 2 * pad,
                    center=mob.get_center(), **kwargs)
    card.set_z_index(mob.z_index - 1)
    return card
