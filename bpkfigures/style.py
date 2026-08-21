import contextlib

from manim import *

BG_COLOR = ManimColor.from_rgb((2, 164, 211))
# ── ACCENT COLOUR HIERARCHY (pick in this order; don't hand-pick hex) ──────────
# 1. PRIMARY   — ACCENT_FILL (deep blue): the default single accent, for data /
#    bars / fills. A scene that needs only one colour uses this.
# 2. HIGHLIGHT — ACCENT_GOLD: the "notice this" accent — highlights, medians,
#    peaks, the emphasised element. Reserve it for that role; don't spend gold as a
#    generic categorical fill in a scene that also needs a highlight colour.
# 3. CATEGORICAL — when several colours must be told apart AT ONCE, pull from
#    CATEGORICAL_PALETTE in order (warm gold/orange/red, then cool green/purple/
#    pink). These carry NO fixed meaning; they only have to differ.
# NOT accents: semantic score/status colours (points = green, zeroed/loss = red)
# are a per-video concern, defined in that video's config.py (e.g. yahtzee
# SCORE_GREEN / SCORE_RED) and deliberately DARKER than the accents. Do NOT reuse
# ACCENT_GREEN / ACCENT_RED for "good/bad" — they're categorical only.
ACCENT_FILL = ManimColor.from_rgb((0, 0, 175))   # 1. primary (deep blue)

# Secondary "warm trio". ACCENT_GOLD is the highlight accent (tier 2 above); the
# three together are the first categorical set and read against the blue primary
# and the cyan background.
ACCENT_GOLD   = ManimColor("#E8A33D")            # 2. highlight / median / emphasis
ACCENT_ORANGE = ManimColor("#E87A2C")
ACCENT_RED    = ManimColor("#D6402C")
ACCENT_PALETTE = [ACCENT_GOLD, ACCENT_ORANGE, ACCENT_RED]

# Cool complements — extend the categorical set past three. Chosen to stay legible
# on the cyan background — a medium blue is deliberately avoided (it blends with the
# BG), so the deep-blue primary ACCENT_FILL stays reserved for bars/fills.
ACCENT_GREEN  = ManimColor("#2E9E4F")
ACCENT_PURPLE = ManimColor("#7A3FB0")
ACCENT_PINK   = ManimColor("#C43B86")

# 3. A 6-way categorical palette (warm trio + cool trio), none of which is the
# primary ACCENT_FILL. Use in order for lines/series that must all differ at once.
CATEGORICAL_PALETTE = [ACCENT_GOLD, ACCENT_ORANGE, ACCENT_RED,
                       ACCENT_GREEN, ACCENT_PURPLE, ACCENT_PINK]

# ── LIGHT RAINBOW — bright light-on-dark sequential/categorical fills ───────────
# Six bright hues (red→purple), saturated but high-value so they POP on a DARK
# background yet still read clearly as colours (not near-white pastels). For a
# rainbow ramp distinct from the ACCENT / CATEGORICAL sets — e.g. a per-count or
# per-step colour scale. Listed red→purple; index (or reverse-index) as the scale needs.
LIGHT_RED    = ManimColor("#FF6B6B")
LIGHT_ORANGE = ManimColor("#FF9E42")
LIGHT_YELLOW = ManimColor("#FFD93D")
LIGHT_GREEN  = ManimColor("#3FD97A")
LIGHT_BLUE   = ManimColor("#3FAEF5")
LIGHT_PURPLE = ManimColor("#B072EE")
LIGHT_PALETTE = [LIGHT_RED, LIGHT_ORANGE, LIGHT_YELLOW,
                 LIGHT_GREEN, LIGHT_BLUE, LIGHT_PURPLE]

# Default card surface (cream), shared by the card asset + scorecard.
CARD_FILL = "#F7F2E7"

# Cooler crimson — deliberately tuned to sit against the cyan BG without the orange
# cast of the warm-trio ACCENT_RED. Shared across videos: the scorecard header /
# Total bars (yahtzee CARD_ACCENT) and the semantic "miss / loss" red.
CRIMSON = ManimColor("#B01E43")

# Neutral "no data yet / inactive" fill — a medium grey that reads clearly as
# placeholder against both WHITE (a real 0-value cell) and the accent fills, so an
# element can sit un-populated before its data animates in (e.g. a heatmap cell
# revealed only when its column is scaled in). Distinct from any accent/categorical.
MUTED_GREY = ManimColor("#888888")

FONT = "Inter"

FONT_SIZE_XS = 15.0
FONT_SIZE_SM = 24.0
FONT_SIZE_MD = 36.0
FONT_SIZE_LG = 48.0

TEXT_SS = 10
TEXT_SS_MAX_FONT = 240

def _supersample(font_size):
    return max(1.0, min(TEXT_SS, TEXT_SS_MAX_FONT / font_size))

@contextlib.contextmanager
def _no_pango_wrap():
    """Force an effectively-infinite Pango wrap width while a Text/Paragraph is built.

    manim wraps a ``Text`` at ``config["pixel_width"]`` — a RESOLUTION-dependent pixel
    count (144p=256, 480p=854, 1080p=1920) — and caches the resulting SVG by a hash that
    EXCLUDES it (``Text._text2hash``). Two consequences bit us repeatedly: crisp_text
    supersamples to up to 240pt (very wide in Pango's raster), so a long string wraps at
    low resolutions; and because the cache ignores the width, a low-res *preview* bakes a
    WRAPPED SVG that then persists into the final 1080p render. crisp_text and
    crisp_paragraph are single-line-per-string (real multi-line goes through explicit
    newlines, which Pango honours regardless of width), so width-wrapping is never wanted
    — pin it wide so output is one line at EVERY render resolution."""
    old = config["pixel_width"]
    config["pixel_width"] = max(old, 1 << 20)
    try:
        yield
    finally:
        config["pixel_width"] = old

def crisp_text(text, **kwargs):
    # Default to our brand FONT so callers can't accidentally render in manim's
    # built-in font by forgetting font=FONT (that was a real, repeated bug).
    kwargs.setdefault("font", FONT)
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    # baseline_at=(x, y): sit the result on its TEXT BASELINE at that point (instead of
    # bbox-centred) — for aligning several strings on one line (see place_on_baseline).
    baseline_at = kwargs.pop("baseline_at", None)
    ss = _supersample(fs)
    with _no_pango_wrap():
        mob = Text(text, font_size=fs * ss, **kwargs).scale(1 / ss)
    if baseline_at is not None:
        place_on_baseline(mob, baseline_at, string=text)
    return mob

def place_on_baseline(mob, point, *, string=None, factory=None):
    """Move ``mob`` so its TEXT BASELINE sits at ``point`` (x kept), instead of centring
    its bounding box. crisp_text (like manim Text) centres each label's bbox at the
    origin, so a row of mixed strings sits unevenly — ascender/descender words drift up
    and down. Baseline alignment fixes that (descenders hang below the shared line).

    The baseline is measured by appending 'x' (no descender, so its bbox bottom IS the
    baseline). Pass ``factory(str)->mob`` for non-crisp_text labels (e.g. chalk) so the
    probe matches their style; otherwise a crisp_text probe is used and the offset is
    applied scale-independently via ``mob.text``. ``string`` overrides the measured text.
    Returns ``mob``."""
    s = str(string if string is not None else getattr(mob, "text", "") or "")
    if not s:
        return mob.move_to([point[0], point[1], 0])
    if factory is not None:                       # same-style probe → offset is direct
        probe = factory(s + "x")
        off = (VGroup(*probe.submobjects[:-1]).get_center()[1]
               - probe.submobjects[-1].get_bottom()[1])
    else:                                         # crisp_text probe → scale-free ratio
        probe = crisp_text(s + "x", font_size=48)
        core = VGroup(*probe.submobjects[:-1])
        ratio = ((core.get_center()[1] - probe.submobjects[-1].get_bottom()[1])
                 / max(core.height, 1e-6))
        off = ratio * mob.height
    return mob.move_to([point[0], point[1] + off, 0])


def crisp_paragraph(*lines, **kwargs):
    kwargs.setdefault("font", FONT)
    fs = kwargs.pop("font_size", DEFAULT_FONT_SIZE)
    ss = _supersample(fs)
    with _no_pango_wrap():                     # each explicit line stays one line (see crisp_text)
        return Paragraph(*lines, font_size=fs * ss, **kwargs).scale(1 / ss)


def fit_to_frame(mob, *, buff=0.3, width=None, height=None):
    """Scale ``mob`` DOWN (never up) so it fits inside the frame minus ``buff`` on each
    side — the shared fix for the recurring "a label / tree / grid spills off-frame" redo
    (scene 05 hand-rolled width-clamps repeatedly). Pass ``width``/``height`` to fit a
    REGION instead of the whole frame. Reads the real frame bounds from ``config`` (never
    a recalled 7.11/4.0). Returns ``mob`` (scaled in place)."""
    max_w = (width if width is not None else 2 * config.frame_x_radius) - 2 * buff
    max_h = (height if height is not None else 2 * config.frame_y_radius) - 2 * buff
    f = min(max_w / max(mob.width, 1e-6), max_h / max(mob.height, 1e-6), 1.0)
    if f < 1.0:
        mob.scale(f)
    return mob


class CrispCounter:
    """A label+value as ONE ``crisp_text`` driven by a ValueTracker, positioned by a
    FIXED LEFT EDGE (never recentred) so counting never shifts or resizes it — the shared
    fix for the recurring "rolling counter jitter / resize / wrap" redo (scenes 05 & 18
    each hand-rolled this; see CLAUDE.md "A COUNTING number WITH a label"). The value is
    ``fmt``-formatted and appended to ``prefix``; while counting, only the trailing NUMBER
    glyphs flash (green up / crimson down, easing back to ``color``), the prefix stays put::

        tr = ValueTracker(3.88)
        c = CrispCounter("Average Misses: ", tr, left=x, y=y, font_size=30)
        scene.add(c.mob)
        c.count(scene, 4.22, run_time=1.5)                 # counts up, number flashes green
        c.count(scene, 4.10, run_time=1.0, flash="none")   # an UNDO: count, no flash

    The whole string is rebuilt via ``.become()`` each frame, so a bare ValueTracker (which
    pickles fine) can live in ``setup_scene`` and only the updater is attached in the body."""

    def __init__(self, prefix, tracker, *, left, y, font_size, color=BLACK,
                 weight=NORMAL, fmt=None, up_color=None, down_color=None):
        self.prefix, self.tracker = prefix, tracker
        self.left, self.y, self.font_size = left, y, font_size
        self.color, self.weight = color, weight
        self.fmt = fmt or (lambda v: f"{v:.2f}")
        self.up_color = ACCENT_GREEN if up_color is None else up_color
        self.down_color = CRIMSON if down_color is None else down_color
        self.mob = self._build(tracker.get_value(), color)

    def _build(self, value, num_color):
        numstr = self.fmt(value)
        m = crisp_text(self.prefix + numstr, font_size=self.font_size,
                       color=self.color, weight=self.weight)
        m.move_to([self.left, self.y, 0], aligned_edge=LEFT)     # FIXED left edge — no recentre
        if num_color != self.color and numstr:
            m[-len(numstr):].set_color(num_color)                # recolour only the number glyphs
        return m

    def _updater(self, v0, v1, flash):
        col = None if flash == "none" else (
            self.up_color if v1 > v0 + 1e-9 else self.down_color if v1 < v0 - 1e-9 else None)

        def upd(m):
            v = self.tracker.get_value()
            c = self.color
            if col is not None and abs(v1 - v0) > 1e-9:
                a = (v - v0) / (v1 - v0)                          # 0..1 count progress
                t = 0.0 if a < 0.72 else (a - 0.72) / 0.28        # hold flash, then ease to base
                c = interpolate_color(col, self.color, t)
            m.become(self._build(v, c))
        return upd

    def count(self, scene, value, run_time, *, flash="auto"):
        """Animate the tracker to ``value`` (the readout follows via a become() updater);
        the number flashes by direction unless ``flash="none"`` (an undo/reset)."""
        v0 = self.tracker.get_value()
        self.mob.add_updater(self._updater(v0, value, flash))
        scene.play(self.tracker.animate.set_value(value), run_time=run_time)
        self.mob.clear_updaters()