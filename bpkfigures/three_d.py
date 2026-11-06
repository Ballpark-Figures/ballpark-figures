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
    Surface or RevealSurface keeps the function it was built from. Call it on any ThreeDAxes
    or Surface stored on the scene, and on a RevealSurface after its last `fill_to`."""
    for m in mob.get_family():
        for k, v in list(vars(m).items()):
            qual = getattr(v, "__qualname__", "") if callable(v) else ""
            if "<locals>" in qual or "<lambda>" in qual:
                delattr(m, k)
        if isinstance(m, (Surface, RevealSurface)):
            m._func = None
    return mob


class RevealSurface(VGroup):
    """A surface z = func(u, v) on a fixed mesh that can be shown up to a moving straight
    edge in (u, v): `fill_to(a, b, level)` shows exactly the part where a*u + b*v <= level,
    cutting the tiles the edge crosses along it, so the fill is continuous and the mesh never
    moves or stretches. (a, b) = (1, 0) fills left to right; a fitted model's own linear
    predictor fills it from low to high, its edge a line of equal value.

    func(u, v) -> a scene point. Tiles are depth-sorted like a Surface's (shade_in_3d), and
    start hidden. Each tile is a flat polygon through func at its corners, as a Surface's."""

    def __init__(self, func, u_range, v_range, resolution, *, fill_color, stroke_color,
                 stroke_width=0.5, fill_opacity=1.0, **kwargs):
        super().__init__(**kwargs)
        self._func = func
        self.fill_opacity_full = fill_opacity
        us = np.linspace(*u_range, resolution[0] + 1)
        vs = np.linspace(*v_range, resolution[1] + 1)
        self.quads = []                 # each tile's corners in (u, v)
        for i in range(resolution[0]):
            for j in range(resolution[1]):
                quad = [(us[i], vs[j]), (us[i + 1], vs[j]), (us[i + 1], vs[j + 1]),
                        (us[i], vs[j + 1])]
                tile = VMobject(fill_color=fill_color, fill_opacity=0,
                                stroke_color=stroke_color, stroke_width=stroke_width,
                                stroke_opacity=0, shade_in_3d=True)
                tile.set_points_as_corners([func(*c) for c in quad + quad[:1]])
                self.quads.append(quad)
                self.add(tile)

    def fill_to(self, a, b, level):
        """Show the part of the surface where a*u + b*v <= level."""
        for tile, quad in zip(self, self.quads):
            inside = [a * u + b * v <= level for u, v in quad]
            if not any(inside):
                tile.set_fill(opacity=0).set_stroke(opacity=0)
                continue
            if all(inside):
                poly = quad
            else:                       # Sutherland-Hodgman against the one half-plane
                poly = []
                for (p, pin), (q, qin) in zip(zip(quad, inside),
                                              zip(quad[1:] + quad[:1], inside[1:] + inside[:1])):
                    if pin:
                        poly.append(p)
                    if pin != qin:
                        fp, fq = a * p[0] + b * p[1] - level, a * q[0] + b * q[1] - level
                        t = fp / (fp - fq)
                        poly.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
            tile.set_points_as_corners([self._func(*c) for c in poly + poly[:1]])
            tile.set_fill(opacity=self.fill_opacity_full).set_stroke(opacity=1)
        return self


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
