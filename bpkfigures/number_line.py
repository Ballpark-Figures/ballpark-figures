"""A zoomable number line / timeline whose ticks re-choose themselves as you zoom.

    zl = ZoomLine(0, 4)                       # values 0..4 across x_range (-6..6)
    self.play(FadeIn(zl), run_time=1.0)
    m = zl.add_marker(3.42, ["Optimal", "(SALET)", "100% Win"])
    self.play(zl.marker_in(m), run_time=1.0)
    self.play(zl.zoom(0, 2500), run_time=3.0) # ticks and labels re-thin smoothly

THE WINDOW. ``(lo, hi)`` is the value range mapped onto ``x_range``; the drawn line
runs further, to ``ends`` (default: the frame edges less a buffer, with arrow tips),
so it reads as extending both ways. Ticks and labels fill the whole drawn line.

THE TICKS. Tick values come from a NESTED LADDER of steps, ``mantissas`` x 10^k
(default 1, 5 -> ..., 0.5, 1, 5, 10, 50, ...). Nested means every step divides the
next, so a value's LEVEL — the coarsest step it is a multiple of — is well defined,
and its opacity is a pure function of that level's ON-SCREEN spacing:

  tick opacity    ramps 0 -> 1 as the spacing goes tick_fade[0] -> tick_fade[1]
  label opacity   ramps 0 -> 1 as the spacing goes label_fade[0] -> label_fade[1]
  tick length     minor -> major with the label opacity

So a zoom is continuous: whole levels fade in and out together, never popping, and
the labelled set is always the multiples of one step. (1, 2, 5 is NOT nested — 5 is
not a multiple of 2 — and would show 0 2 4 5 6 8; it is refused.) ``min_label_step``
/ ``min_tick_step`` floor the ladder (a timeline wants whole years), and
``tick_min``/``tick_max`` clip where ticks exist at all.

MARKERS. ``add_marker(value, lines, side=UP|DOWN)`` hangs a dot, a stem and a
centred label at a value; it rides the window from then on. A DOWN marker's stem
starts below the tick labels.

ZOOMING. ``zoom(lo, hi)`` returns a ``ZoomLineTo`` animation: the width changes
GEOMETRICALLY about the one value that sits at the same screen x in both windows,
so a 0..4 -> 0..2500 zoom keeps 0 still and moves at a constant perceived speed.
Equal widths are a plain pan. ``set_window`` jumps.

PICKLING. No updaters or lambdas are stored, so a ZoomLine survives a snapshot.
A custom ``fmt`` must be a module-level function for the same reason.

HOW THE FRAME UPDATES: ticks are created and removed mid-animation. manim
re-extracts the family of the moving mobjects every frame, so new ones draw; a
removed one can stay in that frame's list, so it is set to opacity 0 first.
"""
import math

import numpy as np
from manim import (VGroup, Line, Dot, Animation, Mobject, AnimationGroup,
                   GrowFromCenter, Create, FadeIn, UP, DOWN, WHITE, config)

from bpkfigures.style import crisp_text, crisp_paragraph, FONT_SIZE_SM


def _ramp(x, lo, hi):
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def default_fmt(value, step):
    """The shortest fixed-point form that shows ``step``'s precision."""
    d = max(0, -math.floor(math.log10(step) + 1e-9))
    s = f"{value:.{d}f}"
    return "0" if float(s) == 0 else s


class ZoomLine(VGroup):
    def __init__(self, lo, hi, *, x_range=(-6.0, 6.0), y=0.0, ends=None,
                 ends_buff=0.35, tips=True, tip_length=0.22, color=WHITE,
                 stroke_width=3.0, mantissas=(1, 5),
                 tick_fade=(0.2, 0.35), label_fade=(0.8, 1.1),
                 major_len=0.24, minor_len=0.12, tick_stroke=2.5,
                 font_size=FONT_SIZE_SM, label_buff=0.14, fmt=default_fmt,
                 min_tick_step=None, min_label_step=None,
                 tick_min=None, tick_max=None, **kwargs):
        super().__init__(**kwargs)
        for a, b in zip(mantissas, list(mantissas[1:]) + [10 * mantissas[0]]):
            if b % a:
                raise ValueError(f"mantissas {mantissas} are not nested: "
                                 f"{b} is not a multiple of {a}")
        if ends is None:
            ends = (-config.frame_x_radius + ends_buff,
                    config.frame_x_radius - ends_buff)
        self.x_range, self.y, self.ends = tuple(x_range), float(y), tuple(ends)
        self.color, self.mantissas = color, tuple(mantissas)
        self.tick_fade, self.label_fade = tuple(tick_fade), tuple(label_fade)
        self.major_len, self.minor_len = major_len, minor_len
        self.tick_stroke, self.font_size = tick_stroke, font_size
        self.label_buff, self.fmt = label_buff, fmt
        self.min_tick_step, self.min_label_step = min_tick_step, min_label_step
        self.tick_min, self.tick_max = tick_min, tick_max
        self.tips, self.tip_length = tips, tip_length

        self.line = Line([ends[0], y, 0], [ends[1], y, 0], color=color,
                         stroke_width=stroke_width)
        if tips:
            self.line.add_tip(tip_length=tip_length, tip_width=tip_length)
            self.line.add_tip(tip_length=tip_length, tip_width=tip_length,
                              at_start=True)
        self.ticks = VGroup()          # contents change with the window
        self.labels = VGroup()
        self.markers = VGroup()
        self.add(self.line, self.ticks, self.labels, self.markers)
        self._tick_mobs = {}           # n (multiple of the finest step) -> Line
        self._label_cache = {}         # label text -> crisp_text
        self._finest = None
        self.set_window(lo, hi)

    # ── mapping ───────────────────────────────────────────────────────────────
    @property
    def scale_factor(self):
        """Screen units per value unit."""
        return (self.x_range[1] - self.x_range[0]) / (self.hi - self.lo)

    def x_of(self, v):
        return self.x_range[0] + (v - self.lo) * self.scale_factor

    def v_of(self, x):
        return self.lo + (x - self.x_range[0]) / self.scale_factor

    def point_of(self, v):
        return np.array([self.x_of(v), self.y, 0.0])

    def label_band_bottom(self):
        """The lowest y the tick labels reach (for placing things under them)."""
        probe = self._label("0")
        return self.y - self.major_len / 2 - self.label_buff - probe.height

    # ── the ladder ────────────────────────────────────────────────────────────
    def _steps_from(self, smallest):
        """Ladder steps, ascending, starting at the first one >= ``smallest``."""
        e = math.floor(math.log10(smallest)) - 1
        while True:
            for m in self.mantissas:
                s = m * 10.0 ** e
                if s >= smallest * (1 - 1e-9):
                    yield s
            e += 1

    def _label(self, text):
        lab = self._label_cache.get(text)
        if lab is None:
            lab = crisp_text(text, color=self.color, font_size=self.font_size)
            if len(self._label_cache) > 200:          # keep a snapshot small
                shown = set(self.labels.submobjects)
                for k in [k for k, m in self._label_cache.items() if m not in shown]:
                    del self._label_cache[k]
            self._label_cache[text] = lab
        return lab

    # ── the window ────────────────────────────────────────────────────────────
    def set_window(self, lo, hi):
        """Show values ``lo..hi`` across ``x_range``; re-thin ticks, move markers."""
        self.lo, self.hi = float(lo), float(hi)
        sf = self.scale_factor
        inner = self.tip_length if self.tips else 0.0
        x0, x1 = self.ends[0] + inner, self.ends[1] - inner
        vmin, vmax = self.v_of(x0), self.v_of(x1)
        if self.tick_min is not None:
            vmin = max(vmin, self.tick_min)
        if self.tick_max is not None:
            vmax = min(vmax, self.tick_max)

        smallest = self.tick_fade[0] / sf
        if self.min_tick_step is not None:
            smallest = max(smallest, self.min_tick_step)
        steps = []                      # every ladder step whose ticks can show
        for s in self._steps_from(smallest):
            steps.append(s)
            if s * sf > max(self.tick_fade[1], self.label_fade[1]) and s > vmax - vmin:
                break
        f = steps[0]
        ratios = [round(s / f) for s in steps]
        if self._finest is None or not math.isclose(f, self._finest):
            # the finest step changed: every key means something else now
            for m in self._tick_mobs.values():
                m.set_stroke(opacity=0)
            self._tick_mobs = {}
            self._finest = f

        live_ticks, live_labels = {}, []
        label_top = self.y - self.major_len / 2 - self.label_buff
        lab_lo = self.min_label_step or 0.0
        if vmax >= vmin:
            for n in range(math.ceil(vmin / f - 1e-9), math.floor(vmax / f + 1e-9) + 1):
                level = f
                for s, r in zip(steps, ratios):
                    if n % r == 0:
                        level = s
                spacing = level * sf
                t_op = _ramp(spacing, *self.tick_fade)
                l_op = _ramp(spacing, *self.label_fade) if level >= lab_lo * (1 - 1e-9) else 0.0
                if t_op <= 0 and l_op <= 0:
                    continue
                v, x = n * f, self.x_of(n * f)
                half = (self.minor_len + (self.major_len - self.minor_len) * l_op) / 2
                tick = self._tick_mobs.get(n)
                if tick is None:
                    tick = Line(ORIGIN_, UP_, color=self.color,
                                stroke_width=self.tick_stroke)
                tick.put_start_and_end_on([x, self.y - half, 0], [x, self.y + half, 0])
                tick.set_stroke(opacity=max(t_op, l_op))
                live_ticks[n] = tick
                if l_op > 0:
                    lab = self._label(self.fmt(v + 0.0, level))
                    lab.move_to([x, label_top - lab.height / 2, 0])
                    if x0 + lab.width / 2 <= x <= x1 - lab.width / 2:
                        lab.set_opacity(l_op)
                        live_labels.append(lab)

        for n, m in self._tick_mobs.items():
            if n not in live_ticks:
                m.set_stroke(opacity=0)
        for m in self.labels.submobjects:
            if m not in live_labels:
                m.set_opacity(0)
        self._tick_mobs = live_ticks
        self.ticks.submobjects = list(live_ticks.values())
        self.labels.submobjects = live_labels
        for mk in self.markers:
            self._place_marker(mk)
        return self

    def zoom(self, lo, hi, **kwargs):
        """An animation to the window ``lo..hi`` (pass run_time to self.play)."""
        return ZoomLineTo(self, lo, hi, **kwargs)

    # ── markers ───────────────────────────────────────────────────────────────
    def add_marker(self, value, lines, *, side=UP, stem=0.45, gap=0.12,
                   dot_radius=0.08, font_size=30, color=None, stem_stroke=2.5):
        """A dot at ``value``, a stem, and ``lines`` (one string per line) centred
        at the stem's end, on ``side`` (UP or DOWN) of the line. Added to the line
        (so a later FadeIn/marker_in finds it on screen) and moved with every
        window change. Returns it, with handles .dot .stem .label .value."""
        color = color or self.color
        if isinstance(lines, str):
            lines = [lines]
        mk = VGroup()
        mk.value, mk.side = float(value), np.array(side, dtype=float)
        mk.stem_len, mk.gap = stem, gap
        mk.dot = Dot(radius=dot_radius, color=color)
        mk.stem = Line(ORIGIN_, UP_, color=color, stroke_width=stem_stroke)
        mk.label = crisp_paragraph(*lines, alignment="center", color=color,
                                   font_size=font_size)
        mk.add(mk.dot, mk.stem, mk.label)
        self._place_marker(mk)
        self.markers.add(mk)
        return mk

    def _place_marker(self, mk):
        x = self.x_of(mk.value)
        mk.dot.move_to([x, self.y, 0])
        if mk.side[1] >= 0:
            y0 = self.y + mk.gap
            y1 = y0 + mk.stem_len
            mk.label.move_to([x, y1 + mk.gap + mk.label.height / 2, 0])
        else:
            y0 = self.label_band_bottom() - mk.gap
            y1 = y0 - mk.stem_len
            mk.label.move_to([x, y1 - mk.gap - mk.label.height / 2, 0])
        mk.stem.put_start_and_end_on([x, y0, 0], [x, y1, 0])

    def marker_in(self, mk, shift=0.2):
        """The marker's entrance: dot grows, stem draws, label rises into place
        (pass run_time to self.play)."""
        return AnimationGroup(GrowFromCenter(mk.dot), Create(mk.stem),
                              FadeIn(mk.label, shift=mk.side * shift),
                              lag_ratio=0.35)


ORIGIN_ = np.array([0.0, 0.0, 0.0])
UP_ = np.array([0.0, 1.0, 0.0])


class ZoomLineTo(Animation):
    """Move a ZoomLine's window to ``lo..hi``: geometric in width, about the value
    that holds its screen position (a pan when the widths match)."""

    def __init__(self, line, lo, hi, **kwargs):
        self.target = (float(lo), float(hi))
        super().__init__(line, **kwargs)

    def begin(self):
        self.start = (self.mobject.lo, self.mobject.hi)
        super().begin()

    def create_starting_mobject(self):
        return Mobject()                # nothing is interpolated submobject-wise

    def window_at(self, t):
        (l0, h0), (l1, h1) = self.start, self.target
        w0, w1 = h0 - l0, h1 - l1
        if math.isclose(w0, w1, rel_tol=1e-9):
            return l0 + (l1 - l0) * t, h0 + (h1 - h0) * t
        p = (l1 * w0 - l0 * w1) / (w0 - w1)        # same screen x in both windows
        u = (p - l0) / w0
        w = w0 * (w1 / w0) ** t
        return p - u * w, p - u * w + w

    def interpolate_mobject(self, alpha):
        self.mobject.set_window(*self.window_at(self.rate_func(alpha)))

    def finish(self):
        super().finish()
        self.mobject.set_window(*self.target)       # land exactly
