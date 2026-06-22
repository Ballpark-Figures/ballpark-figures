"""Channel logo (the donut) — Cairo (default renderer).

    manim -s -qk logo.py Logo      # 4K PNG
    manim -s -qh logo.py Logo      # 1080p

The body is flat-colored, so it is NOT built from a 3D Surface -- a translucent
Surface forces Cairo to composite each polygon separately, which always leaves
the tessellation visible as a seam mesh (and no opacity/stroke trick removes
it). Instead the body, the near glaze, and the far glaze are each a single flat
filled shape traced from the torus silhouette. One fill over one fill composites
cleanly: the near navy over the far yellow gives a clean olive with no mesh, and
the opaque near yellow is never disturbed.

Silhouette: a torus point is on the outline where normal . VIEW = 0, i.e.
tan(v) = -sin(u) tan(PHI); the two v-branches trace the outer rim and hole rim.

Net lines are ordinary strokes (no fill compositing), drawn near-bright and
far-dim, the far set read through the translucent body.
"""
from manim import *
import numpy as np

def to_hex(c): return "#" + "".join(f"{max(0,min(255,round(v))):02X}" for v in c)

def lighten(rgb, amount=0.08):
    return to_hex(rgb), to_hex(tuple(v + (255 - v) * amount for v in rgb))

def darken(rgb, amount=0.08):
    return to_hex(rgb), to_hex(tuple(v * (1 - amount) for v in rgb))

#BG, SKIN = darken((2, 164, 211), 0.2)
#BG, SKIN = lighten((18, 26, 51), 0.25)

BG = to_hex((2, 164, 211))
SKIN = to_hex((18, 26, 51))

#YELLOW_PEN  = "#E6E600"
YELLOW_PEN = "#D0D000"
LIGHTYELLOW = "#E6E6B3"

R_MAJOR, A_MINOR = 2.0, 1.0
PHI = 40 * DEGREES
VIEW = np.array([0.0, np.sin(PHI), np.cos(PHI)])
u_lo, u_hi = 123*DEGREES, 237*DEGREES

BODY_OPACITY = 0.8
NET_FRONT_WIDTH, NET_FRONT_OPACITY = 3.0, 0.95
NET_BACK_WIDTH,  NET_BACK_OPACITY  = 2.0, 0.90   # further dimmed by the body it shows through


def torus_pt(u, v, a=A_MINOR):
    return np.array([(R_MAJOR + a*np.cos(v))*np.cos(u),
                     (R_MAJOR + a*np.cos(v))*np.sin(u),
                     a*np.sin(v)])

def normal(u, v):
    return np.array([np.cos(v)*np.cos(u), np.cos(v)*np.sin(u), np.sin(v)])

def v_sil(u):
    return np.arctan2(-np.sin(u)*np.sin(PHI), np.cos(PHI))

def is_front(u, v): return np.dot(normal(u, v), VIEW) > 0.0
def off_glaze(u):   return not (u_lo < (u % TAU) < u_hi)


def closed(pts):
    m = VMobject()
    m.start_new_path(pts[0]); m.add_points_as_corners(list(pts[1:]) + [pts[0]])
    return m

def glaze_region(front=True, m=0.0):
    """Flat outline of the glaze wedge on the near (front) or far shell.
    m insets the silhouette edges so the far shell stays inside the body."""
    us = np.linspace(u_lo, u_hi, 120)
    s = 0 if front else np.pi
    outer  = [torus_pt(u, v_sil(u) + s + m)          for u in us]
    inner  = [torus_pt(u, v_sil(u) + np.pi + s - m)  for u in us]
    cap_hi = [torus_pt(u_hi, v) for v in np.linspace(v_sil(u_hi)+s+m, v_sil(u_hi)+np.pi+s-m, 40)]
    cap_lo = [torus_pt(u_lo, v) for v in np.linspace(v_sil(u_lo)+np.pi+s-m, v_sil(u_lo)+s+m, 40)]
    return closed(outer + cap_hi + inner[::-1] + cap_lo)


class Logo(ThreeDScene):
    def construct(self):
        self.camera.background_color = BG
        self.camera.should_apply_shading = False
        self.set_camera_orientation(phi=PHI, theta=90*DEGREES)

        # body: single translucent fill of the donut outline (outer rim, hole)
        N = 240; us = np.linspace(0, TAU, N)
        outer = [torus_pt(u, v_sil(u))        for u in us]
        inner = [torus_pt(u, v_sil(u) + np.pi) for u in us]
        body = VMobject(fill_color=SKIN, fill_opacity=BODY_OPACITY, stroke_width=0)
        body.start_new_path(outer[0]); body.add_points_as_corners(outer[1:] + [outer[0]])
        body.start_new_path(inner[0]); body.add_points_as_corners(inner[1:][::-1] + [inner[0]])

        front_glaze = glaze_region(True ).set_fill(YELLOW_PEN, opacity=1.0).set_stroke(width=0)
        back_glaze  = glaze_region(False).set_fill(YELLOW_PEN, opacity=1.0).set_stroke(width=0)

        # 20x10 net. The full curves are drawn CONTINUOUSLY behind the body (so
        # they read dim/see-through and never break); the near-facing arcs are
        # layered on top at full brightness. None of it crosses the glaze.
        net_all = VGroup(); net_front = VGroup(); SAMP = 220
        def add_runs(target, samples):
            run = []
            for p, vis in samples:
                if vis: run.append(p)
                elif len(run) >= 2: target.add(VMobject().set_points_as_corners(run)); run = []
                else: run = []
            if len(run) >= 2: target.add(VMobject().set_points_as_corners(run))
        for k in range(10):                                   # toroidal (constant v)
            v0 = TAU*k/10
            uu = np.linspace(u_hi, u_lo + TAU, SAMP)           # one continuous off-glaze arc
            net_all.add(VMobject().set_points_as_corners([torus_pt(u, v0, a=1.004) for u in uu]))
            add_runs(net_front, [(torus_pt(u, v0, a=1.004), is_front(u % TAU, v0)) for u in uu])
        for k in range(20):                                   # poloidal (constant u)
            u0 = TAU*k/20
            if not off_glaze(u0): continue
            vv = np.linspace(0, TAU, SAMP)
            net_all.add(VMobject().set_points_as_corners([torus_pt(u0, v, a=1.004) for v in vv]))
            add_runs(net_front, [(torus_pt(u0, v, a=1.004), is_front(u0, v)) for v in vv])
        net_all.set_stroke(color=LIGHTYELLOW, width=NET_BACK_WIDTH, opacity=NET_BACK_OPACITY)
        net_front.set_stroke(color=LIGHTYELLOW, width=NET_FRONT_WIDTH, opacity=NET_FRONT_OPACITY)

        # mask: background color everywhere OUTSIDE the body outline, so any
        # far-glaze overhang past the silhouette is covered exactly at the edge
        big = [12*np.array([np.cos(t), np.sin(t), 0.0]) for t in np.linspace(0, TAU, 80)]
        mask = VMobject(fill_color=BG, fill_opacity=1.0, stroke_width=0)
        mask.start_new_path(big[0]);   mask.add_points_as_corners(big[1:] + [big[0]])
        mask.start_new_path(outer[0]); mask.add_points_as_corners(outer[1:][::-1] + [outer[0]])

        # far yellow -> mask overhang -> full net (dimmed by body) -> body -> near yellow -> near net
        self.add(back_glaze, mask, net_all, body, front_glaze, net_front)
        self.wait(0.1)