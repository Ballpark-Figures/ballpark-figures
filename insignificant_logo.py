"""Insignificant Figures logo — the Ballpark Figures donut, flattened (Cairo).

    manim -s -qk insignificant_logo.py Logo LogoNavy LogoBlackNet

Logo is the original's colouring; LogoNavy swaps the light blue and the navy (navy
background, light-blue ring); LogoBlackNet draws the mesh in black. The PNGs live WITH THE CURRENT LOGO'S render, in media/images/logo/ (gitignored),
as insignificant_logo.png, insignificant_logo_navy.png and
insignificant_logo_blacknet.png.

The original torus (logo.py) seen from directly above: a ring with the hole in the
middle, the yellow glaze as a wedge on the right, and the net crossing only the navy.
Every colour, opacity, stroke and dimension is IMPORTED from logo.py, so the two logos
cannot drift apart:

    ring       inner radius R_MAJOR - A_MINOR, outer R_MAJOR + A_MINOR  (1 : 3)
    navy       SKIN at BODY_OPACITY over BG, as the original's body
    wedge      YELLOW_PEN, the glaze's own angular span (u_lo..u_hi, 114 degrees)
    spokes     the original's 20 poloidal lines, every 18 degrees, navy part only
    circles    EVENLY spaced (the user's call, 2026-10-12), rims included, NET_RINGS
               of them — the flat counterpart of the original's 10 toroidal lines
"""
from manim import *

import logo as bpk

# Square canvas. The ring's outer edge sits at RING_FILL of the way from the centre to
# the edge, i.e. of YouTube's circular avatar crop. 0.75 filled the circle too much
# (the user, 2026-10-12).
RING_FILL = 0.6
config.pixel_width = config.pixel_height = 2160

R_IN = bpk.R_MAJOR - bpk.A_MINOR
R_OUT = bpk.R_MAJOR + bpk.A_MINOR
HALF = (bpk.u_hi - bpk.u_lo) / 2          # the glaze's half-width, centred on the right
NET_RINGS = 6                              # circles, rims included -> 4 inside
SPOKES = 20
config.frame_width = config.frame_height = 2 * R_OUT / RING_FILL
# manim draws stroke widths relative to the FRAME, so zooming out thins the net against
# the ring. Scale it back so the lines keep the weight they had at the first render's
# 8-unit frame, which the user approved.
NET_WIDTH = bpk.NET_FRONT_WIDTH * config.frame_width / 8.0


class Logo(Scene):
    BACKGROUND, RING, NET = bpk.BG, bpk.SKIN, bpk.LIGHTYELLOW

    def construct(self):
        self.camera.background_color = self.BACKGROUND

        body = Annulus(inner_radius=R_IN, outer_radius=R_OUT,
                       fill_color=self.RING, fill_opacity=bpk.BODY_OPACITY, stroke_width=0)
        wedge = AnnularSector(inner_radius=R_IN, outer_radius=R_OUT,
                              start_angle=-HALF, angle=2 * HALF,
                              fill_color=bpk.YELLOW_PEN, fill_opacity=1.0, stroke_width=0)

        net = VGroup()
        for k in range(SPOKES):
            a = TAU * k / SPOKES
            if abs((a + PI) % TAU - PI) <= HALF:           # inside the wedge
                continue
            d = np.array([np.cos(a), np.sin(a), 0.0])
            net.add(Line(R_IN * d, R_OUT * d))
        for i in range(NET_RINGS):
            r = R_IN + (R_OUT - R_IN) * i / (NET_RINGS - 1)
            net.add(Arc(radius=r, start_angle=HALF, angle=TAU - 2 * HALF))
        net.set_stroke(color=self.NET, width=NET_WIDTH,
                       opacity=bpk.NET_FRONT_OPACITY)

        self.add(body, wedge, net)


class LogoNavy(Logo):
    """The light blue and the navy swapped (the user's request, 2026-10-12)."""
    BACKGROUND, RING = bpk.SKIN, bpk.BG


class LogoBlackNet(Logo):
    """The original colouring with BLACK mesh lines (the user's request, 2026-10-12)."""
    NET = BLACK
