"""Mouse cursor — an arrow pointer that glides to a point and clicks.

Video-agnostic, like `browser.py`. Positions are in terms of the arrow's TIP (its
hot spot, the pixel a real click lands on), never its centre:

    cur = Cursor().point_to(start)              # tip at `start`
    self.play(FadeIn(cur), run_time=0.3)
    self.play(cur.glide_to(toggle.get_center()), run_time=0.8)
    self.sfx("click")                           # the press is the click's first frame
    self.play(cur.click(), run_time=0.35)

or the whole gesture in one play, with the sound placed on the press:

    self.sfx("click", at=0.8)                   # = the glide's share of the run_time
    self.play(Succession(cur.glide_to(p), cur.click(), lag_ratio=1.0),
              run_time=1.15)

THE CLICK is a press (the arrow dips to 85% about its tip and back) plus a ripple
ring spreading from the tip and fading, which is what reads as "clicked" in a video
where no real UI responds. `ripple=False` drops the ring. Whatever the click turns
on (a toggle flipping, a menu opening) is the caller's own animation, played after
or alongside.

THE GLIDE follows a slight arc (`arc`, radians; 0 = straight), as a hand moving a
mouse does, with manim's default smooth easing.

The arrow is the classic one: black with a white outline, so it reads on any
background. `height` is the arrow's height in scene units.
"""
from manim import *

from bpkfigures.style import ACCENT_GOLD

# the arrow, in units of its own height, tip at the origin (y down is negative):
# down the left edge, in to the notch, out along the tail, back to the notch, and
# across to the right shoulder
_ARROW = [(0.0, 0.0), (0.0, -0.80), (0.20, -0.62), (0.34, -0.95), (0.46, -0.90),
          (0.32, -0.57), (0.58, -0.57)]

PRESS = 0.85            # the arrow's scale at the bottom of a click
RIPPLE_R = 1.0          # the ring's final radius, in arrow heights


class Cursor(VMobject):
    def __init__(self, height=0.45, fill=BLACK, outline=WHITE, outline_width=2.5,
                 **kwargs):
        super().__init__(fill_color=fill, fill_opacity=1.0, stroke_color=outline,
                         stroke_width=outline_width, **kwargs)
        self.set_points_as_corners([[x * height, y * height, 0]
                                    for x, y in _ARROW + _ARROW[:1]])
        self.arrow_h = height

    def tip(self):
        """The hot spot: the arrow's top-left vertex."""
        return self.points[0].copy()

    def point_to(self, point):
        """Move the arrow (no animation) so its tip sits on `point`."""
        return self.shift(np.asarray(point, dtype=float) - self.tip())

    def glide_to(self, point, arc=0.25):
        """An Animation: the tip travels to `point` along a slight arc."""
        return _Glide(self, point, arc)

    def click(self, ripple=True, ripple_color=ACCENT_GOLD):
        """An Animation: one click at the tip -- a press and, unless `ripple` is
        False, a ring spreading from the tip. Put the click's sound on its first
        frame (`self.sfx(...)` just before the play)."""
        press = _Press(self)
        if not ripple:
            return press
        return AnimationGroup(press, _ripple(self.tip(), self.arrow_h, ripple_color))


class _Glide(Animation):
    def __init__(self, cursor, point, arc, **kwargs):
        self.end = np.asarray(point, dtype=float)
        self.arc = arc
        super().__init__(cursor, **kwargs)

    def begin(self):
        self.start = self.mobject.tip()
        self.path = path_along_arc(self.arc)
        super().begin()

    def interpolate_mobject(self, alpha):
        a = self.rate_func(alpha)
        p = self.path(self.start[None], self.end[None], a)[0]
        self.mobject.point_to(p)


class _Press(Animation):
    """The arrow dips to PRESS about its tip and back."""

    def __init__(self, cursor, **kwargs):
        super().__init__(cursor, **kwargs)

    def interpolate_mobject(self, alpha):
        s = 1 - (1 - PRESS) * there_and_back(alpha)
        self.mobject.become(self.starting_mobject)
        self.mobject.scale(s, about_point=self.starting_mobject.tip())


def _ripple(point, arrow_h, color):
    ring = Circle(radius=0.01, stroke_color=color, stroke_width=4).move_to(point)

    def grow(m, alpha):
        # the ring grows fast and settles (ease out), but fades evenly over the
        # whole click -- on the same easing it is all but gone by mid-click
        a = rate_functions.ease_out_cubic(alpha)
        m.become(Circle(radius=max(0.01, RIPPLE_R * arrow_h * a), stroke_color=color,
                        stroke_width=4, stroke_opacity=1 - alpha).move_to(point))

    # introducer: the ring is not on screen before the click, and a plain animation
    # inside an AnimationGroup is never added for it; remover: gone afterwards
    return UpdateFromAlphaFunc(ring, grow, introducer=True, remover=True)
