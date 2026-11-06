"""3D charts: the pieces a ThreeDScene chart is built from.

A 3D scene subclasses the video's base scene AND manim's ThreeDScene, e.g.
`class WheelOfFortune3DScene(WheelOfFortuneScene, ThreeDScene)`. BpkScene saves the 3D
camera into each snapshot (angles, zoom, centre, the pinned-to-screen and face-the-camera
sets), so a subscene rendered alone starts from the previous one's camera.

Rendering is Cairo, which has no depth buffer: each FACE is sorted by its centre's depth and
drawn whole. Bars meeting a surface sort acceptably (checked in wheel-of-fortune 92); a
stroke-only mobject (a Line) is not depth-sorted and always draws on top.

Text: pin a title to the screen with `self.camera.add_fixed_in_frame_mobjects(m)`, and turn
a label placed in 3D toward the camera with `self.camera.add_fixed_orientation_mobjects(m)`.
Register with the CAMERA (not the scene's methods of the same name, which also add the
mobject, so it pops in) and then FadeIn as usual. crisp_text works in both.

Reference: wheel-of-fortune `scenes/92threed_test.py`, then scene 06.
"""
from manim import *
import numpy as np


def picklable(mob):
    """Drop, in place, what keeps a 3D mobject out of a snapshot, and return it. ThreeDAxes
    gives every axis piece instance-level lambdas (a sheen gradient and a unit normal), and a
    Surface keeps the function it was built from; neither is used after construction. Call it
    on any ThreeDAxes or Surface stored on the scene."""
    for m in mob.get_family():
        for k, v in list(vars(m).items()):
            qual = getattr(v, "__qualname__", "") if callable(v) else ""
            if "<locals>" in qual or "<lambda>" in qual:
                delattr(m, k)
        if isinstance(m, Surface):
            m._func = None
    return mob


def bar_grid(cells, to_point, side, z_len, *, color, stroke_color, stroke_width=0.5):
    """A grid of 3D bars, one Prism per cell, FLATTENED onto the floor ready to grow.

    cells     — (x, y, value) per bar: the cell's centre in data coordinates and its height
                as a fraction of `z_len` (0..1)
    to_point  — data (x, y, value) -> scene point
    side      — each bar's width and depth, scene units
    Each bar's full height is its saved state, so `grow_bar_grid` (or `Restore(bar)`)
    raises it. The result is a VGroup of the bars, in `cells` order."""
    bars = VGroup()
    for x, y, value in cells:
        bar = Prism(dimensions=[side, side, value * z_len], fill_color=color, fill_opacity=1,
                    stroke_color=stroke_color, stroke_width=stroke_width)
        bar.move_to(to_point(x, y, value / 2))
        bar.save_state()
        bar.stretch(0.01, 2, about_edge=IN)
        bars.add(bar)
    return bars


def grow_bar_grid(bars, lag_ratio=0.02):
    """The bars of `bar_grid` rising from the floor, one after another. Pass run_time to the
    play (or to move_camera's added_anims' play)."""
    return LaggedStart(*[Restore(b) for b in bars], lag_ratio=lag_ratio)
