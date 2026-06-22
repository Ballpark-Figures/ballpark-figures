"""Channel logo (the donut) — OpenGL build, translucent body.

Render as a PNG with the OpenGL renderer:

    manim -s -qk --renderer=opengl logo_opengl.py Logo     # 4K
    manim -s -qh --renderer=opengl logo_opengl.py Logo     # 1080p

Why OpenGL: a translucent surface renders as one continuous skin, so there's no
polygon-seam grid like the default (Cairo) renderer shows on see-through fills.

Renderer-specific notes:
  * Background is set via config.background_color (OpenGL ignores camera.background_color).
  * Flat fills (asy `nolight`) come from set_shading(0,0,0) per surface.
  * Surfaces use stroke_width=0 so their own triangulation doesn't show.
  * OpenGL's camera convention differs from Cairo: THETA=180 puts the glaze on
    the right; VIEW is computed from PHI and THETA so the back-face cull matches.
  * The net is the original 20x10 wireframe, CULLED to the camera-facing half
    (so the donut reads as solid, no bright back lines), and clipped off the glaze.
"""
from manim import *
from manim.mobject.opengl.opengl_vectorized_mobject import OpenGLVMobject
import numpy as np

# --- Colors (matched to the Asymptote pens) ---

def lighten(rgb, amount=0.08):
    def to_hex(c):
        return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in c)
    return to_hex(rgb), to_hex(tuple(v + (255 - v) * amount for v in rgb))

def darken(rgb, amount=0.08):
    def to_hex(c):
        return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in c)
    return to_hex(rgb), to_hex(tuple(v * (1 - amount) for v in rgb))

#BG, SKIN = darken((2, 164, 211), 0.2)
BG, SKIN = lighten((18, 26, 51), 0.25)
YELLOW_PEN  = "#E6E600"   # rgb(0.9, 0.9, 0.0)
LIGHTYELLOW = "#E6E6B3"   # rgb(0.9, 0.9, 0.7)

config.background_color = BG

R_MAJOR, A_MINOR = 2.0, 1.0
PHI   = 36 * DEGREES                    # camera elevation off +z
THETA = 180 * DEGREES                   # OpenGL convention: glaze (u~180) -> right
NET_LIFT   = 1.004                      # net radius (raise slightly if it z-fights)
GLAZE_LIFT = 1.02                       # glaze sits clearly above the body

# net appearance — tune these to taste (front = near surface, back = far, dimmed)
NET_FRONT_WIDTH, NET_FRONT_OPACITY = 3.0, 0.95
NET_BACK_WIDTH,  NET_BACK_OPACITY  = 2.0, 0.28

# Camera view direction (origin -> eye). OpenGL's THETA=180 reproduces Cairo's
# theta=90 camera, whose eye sits in the y-z plane, so VIEW is (0, sinφ, cosφ).
# (Verified against the renderer's own inverse_rotation_matrix; the naive
# spherical formula with THETA=180 gives the wrong axis and breaks the cull.)
VIEW = np.array([0.0, np.sin(PHI), np.cos(PHI)])


def torus_pt(u, v, a=A_MINOR):
    return np.array([
        (R_MAJOR + a * np.cos(v)) * np.cos(u),
        (R_MAJOR + a * np.cos(v)) * np.sin(u),
        a * np.sin(v),
    ])


def normal(u, v):                       # outward unit normal of the torus
    return np.array([np.cos(v) * np.cos(u), np.cos(v) * np.sin(u), np.sin(v)])


def flat(mobj):
    try:
        mobj.set_shading(0.0, 0.0, 0.0)
    except Exception:
        pass
    try:
        mobj.set_stroke(width=0, opacity=0)
    except Exception:
        pass
    return mobj


class Logo(ThreeDScene):
    def construct(self):
        self.camera.background_color = BG
        self.set_camera_orientation(phi=PHI, theta=THETA)

        u_lo, u_hi = 123 * DEGREES, 234 * DEGREES     # the glaze arc

        # OpenGL's VGroup only accepts OpenGLVMobject; Cairo accepts VMobject.
        _rend = getattr(config.renderer, "value", config.renderer)
        PolyLine = OpenGLVMobject if _rend == "opengl" else VMobject

        # --- Translucent torus: one OpenGL mesh -> clean see-through, no seams ---
        navy = flat(Surface(
            lambda u, v: torus_pt(u, v),
            u_range=[0, TAU], v_range=[0, TAU],
            resolution=(80, 40), checkerboard_colors=False,
            fill_color=SKIN, fill_opacity=0.8, stroke_width=0,
        ))

        # --- Opaque glaze patch on top ---
        glaze = flat(Surface(
            lambda u, v: torus_pt(u, v, a=GLAZE_LIFT),
            u_range=[u_lo, u_hi], v_range=[0, TAU],
            resolution=(40, 30), checkerboard_colors=False,
            fill_color=YELLOW_PEN, fill_opacity=1.0, stroke_width=0,
        ))

        # --- 20x10 net: front half bright, back half dimmed (see-through depth) ---
        net_front = VGroup()
        net_back = VGroup()
        SAMP = 160

        def add_runs(target, samples):    # samples: list of (point, visible_bool)
            run = []
            for p, vis in samples:
                if vis:
                    run.append(p)
                elif len(run) >= 2:
                    target.add(PolyLine().set_points_as_corners(run)); run = []
                else:
                    run = []
            if len(run) >= 2:
                target.add(PolyLine().set_points_as_corners(run))

        def is_front(u, v):
            return np.dot(normal(u, v), VIEW) > 0.0

        def off_glaze(u):
            return not (u_lo < (u % TAU) < u_hi)

        for k in range(10):               # toroidal circles (constant v)
            v0 = TAU * k / 10
            pts = [(torus_pt(u, v0, a=NET_LIFT), u) for u in np.linspace(0, TAU, SAMP)]
            add_runs(net_front, [(p, is_front(u, v0) and off_glaze(u)) for p, u in pts])
            add_runs(net_back,  [(p, (not is_front(u, v0)) and off_glaze(u)) for p, u in pts])
        for k in range(20):               # poloidal circles (constant u)
            u0 = TAU * k / 20
            if not off_glaze(u0):
                continue
            pts = [(torus_pt(u0, v, a=NET_LIFT), v) for v in np.linspace(0, TAU, SAMP)]
            add_runs(net_front, [(p, is_front(u0, v)) for p, v in pts])
            add_runs(net_back,  [(p, not is_front(u0, v)) for p, v in pts])

        net_front.set_stroke(color=LIGHTYELLOW, width=NET_FRONT_WIDTH, opacity=NET_FRONT_OPACITY)
        net_back.set_stroke(color=LIGHTYELLOW, width=NET_BACK_WIDTH, opacity=NET_BACK_OPACITY)

        self.add(navy, glaze, net_back, net_front)
        self.wait(0.1)