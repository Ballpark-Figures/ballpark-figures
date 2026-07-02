"""Shared "notice this" emphasis — one place for the highlight move so scenes
don't each reinvent it.

`highlight()` fades a soft tinted overlay onto one or more targets, HOLDS it for
a beat or two, then fades it out. Holding is the default on purpose: a steady
highlight reads far better than a quick flash. Options:
  * pulse=True   — a single there-and-back flash instead of a hold (use with
                   lag_ratio to WALK the flash across targets one at a time).
  * persist=True — fade in and STOP; returns the overlay rects so the caller can
                   keep them up across later plays and remove them itself.

Targets are Mobjects (the overlay covers the bounding box + buff) or explicit
(center, width, height) regions — the latter for spans no single mobject covers
(e.g. a scorecard row across all three columns).

For emphasising one element WITHIN a group, prefer dimming the rest (see the
'emphasise by dimming' note in CLAUDE.md); use highlight() to spotlight specific
element(s) against an un-dimmed field.
"""
from manim import *

from bpkfigures.style import ACCENT_GOLD

__all__ = ["highlight", "overlay_rect"]


def overlay_rect(target, *, color=ACCENT_GOLD, opacity=0.5, buff=0.0,
                 corner_radius=0.0):
    """A stroke-less tinted rectangle covering `target`.

    `target` is a Mobject (its bounding box, grown by `buff`) or a
    (center, width, height) triple for an explicit region."""
    if isinstance(target, Mobject):
        center = target.get_center()
        width = target.width + 2 * buff
        height = target.height + 2 * buff
    else:
        center, width, height = target
    style = dict(width=width, height=height, stroke_width=0,
                 fill_color=color, fill_opacity=opacity)
    rect = (RoundedRectangle(corner_radius=corner_radius, **style)
            if corner_radius else Rectangle(**style))
    return rect.move_to(center)


def highlight(scene, targets, *, color=ACCENT_GOLD, opacity=0.5, buff=0.0,
              corner_radius=0.0, fade=0.25, hold=1.5, lag_ratio=0.0,
              pulse=False, persist=False):
    """Emphasise `targets` (Mobjects and/or (center, w, h) regions).

    Default: fade the overlays in (`fade` s), HOLD (`hold` s), fade out. See the
    module docstring for pulse=/persist=. Returns the overlay rects (which are
    still on screen only when persist=True; otherwise already cleaned up)."""
    rects = [overlay_rect(t, color=color, opacity=opacity, buff=buff,
                          corner_radius=corner_radius) for t in targets]

    if pulse:
        scene.play(
            LaggedStart(*[FadeIn(r, rate_func=there_and_back) for r in rects],
                        lag_ratio=lag_ratio),
            run_time=max(2 * fade, hold),
        )
        scene.remove(*rects)
        return []

    scene.play(LaggedStart(*[FadeIn(r) for r in rects], lag_ratio=lag_ratio),
               run_time=fade)
    if persist:
        return rects
    scene.wait(hold)
    scene.play(*[FadeOut(r) for r in rects], run_time=fade)
    scene.remove(*rects)
    return []
