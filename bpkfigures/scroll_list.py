"""Scrolling focus list — a picker-wheel / carousel where the centered item is
full size and full opacity, neighbours shrink and fade with distance, and items
past the visible radius drop off screen. Generic on purpose: each item is any
Mobject (used as-is) or a string (rendered with ``crisp_text``), so it works for
a plain list, a ranked table of caller-built rows, anything.

Design (why it's snapshot-safe):
  * ALL motion comes from one pure layout function, ``_apply_layout(pos)``: given
    a fractional focus position it sets every item's (scale, opacity, y). The
    ``pos`` is a float — integer p means item p is dead-centre; 2.5 is halfway
    between items 2 and 3.
  * At REST no updater is attached. The items are plain positioned mobjects, so a
    ScrollList pickles fine and carries across subscene snapshots like anything
    else (no ``setup_scene``-only restriction).
  * ``scroll_to()`` returns an ``UpdateFromAlphaFunc`` that drives
    ``_apply_layout`` from the ANIMATION's own alpha — no ValueTracker, no
    lingering updater. Drop it straight into
    ``self.play(self.wheel.scroll_to(target), run_time=t)``.

Geometry: the centre sits at ``_home``. Slot-distance ``d = i - pos``. A row's
offset along the axis is the cumulative integral of the scale falloff, which is a
concave, saturating curve — so spacing COMPRESSES toward the edges (the wheel
look) and far rows pile up just off-screen where they've already faded out.
"""
import math

import numpy as np
from manim import *

from bpkfigures.style import crisp_text, FONT_SIZE_MD


def _set_opacity(mob, o):
    """Set opacity, but let sub-mobjects that OVERRIDE set_opacity own their own
    subtree (e.g. a Die that keeps a fixed pool of pips and hides the inactive
    ones — manim's family propagation would bypass that override and reveal all
    the phantom pips). Anything using the standard Mobject/VMobject set_opacity is
    recursed normally."""
    st = getattr(type(mob), "set_opacity", None)
    if st is not None and st is not VMobject.set_opacity:
        mob.set_opacity(o)                 # custom handler owns its whole subtree
        return
    for sm in mob.submobjects:
        _set_opacity(sm, o)
    mob.set_opacity(o, family=False)       # this level's own points only


class ScrollList(VGroup):
    def __init__(self, items, *, focus=0, radius=3, gap=0.8, falloff=0.72,
                 fade_span=1.0, font_size=FONT_SIZE_MD, keys=None,
                 center=ORIGIN, axis=DOWN, **text_kwargs):
        """items    : list of Mobjects and/or strings (strings -> crisp_text).
        focus       : index centred initially.
        radius      : rows within this slot-distance are visible; beyond it,
                      opacity 0 (off screen).
        gap         : base centre-to-centre spacing at the middle (should be a
                      touch more than a row's height).
        falloff     : per-slot shrink factor (0.72 -> each step out is 72% the
                      size). Also sets how fast spacing compresses.
        fade_span   : over how many slots (ending at ``radius``) opacity ramps
                      1 -> 0.
        keys        : optional per-item lookup keys for scroll_to("label").
                      Defaults to the string itself for string items.
        center/axis : where the wheel sits and which way it scrolls (DOWN = list
                      flows downward, larger index lower)."""
        super().__init__()
        self.radius = radius
        self.gap = gap
        self.falloff = falloff
        self._logf = math.log(falloff)
        self.fade_span = fade_span
        self.axis = np.array(axis, dtype=float)
        self._home = np.array(center, dtype=float)
        self._pos_value = float(focus)

        self.rows = []
        self._keys = []
        for it in items:
            if isinstance(it, str):
                mob = crisp_text(it, font_size=font_size, **text_kwargs)
                key = it
            else:
                mob = it
                key = None
            mob._cur_scale = 1.0
            mob._cur_opacity = 1.0
            mob._parked = False
            self.rows.append(mob)
            self._keys.append(key)
        if keys is not None:
            self._keys = list(keys)
        self.add(*self.rows)
        self._apply_layout(self._pos_value)

    # ── geometry (pure functions of slot-distance d) ─────────────────────────
    def _y_of(self, d):
        # cumulative of falloff**|t| dt -> concave, saturating (compressed edges)
        mag = self.gap * (self.falloff ** abs(d) - 1.0) / self._logf
        return math.copysign(mag, d)

    def _scale_of(self, d):
        return self.falloff ** abs(d)

    def _opacity_of(self, d):
        r0 = self.radius - self.fade_span
        a = abs(d)
        if a <= r0:
            return 1.0
        if a >= self.radius:
            return 0.0
        t = (a - r0) / self.fade_span            # 0..1 across the ramp
        return 0.5 * (1.0 + math.cos(math.pi * t))  # smooth 1 -> 0

    def _apply_layout(self, pos):
        self._pos_value = pos
        for i, mob in enumerate(self.rows):
            d = i - pos
            # Off-screen buffer: don't bother positioning rows that are well past
            # the fade edge — just make sure they're parked invisible once.
            if abs(d) > self.radius + 1.5:
                if not mob._parked:
                    _set_opacity(mob, 0.0)
                    mob._cur_opacity = 0.0
                    mob._parked = True
                continue
            mob._parked = False
            s = self._scale_of(d)
            factor = s / mob._cur_scale          # set ABSOLUTE scale
            if abs(factor - 1.0) > 1e-6:
                mob.scale(factor)
                mob._cur_scale = s
            o = self._opacity_of(d)
            _set_opacity(mob, o)
            mob._cur_opacity = o
            mob.move_to(self._home + self._y_of(d) * self.axis)

    # ── public API ───────────────────────────────────────────────────────────
    def _resolve(self, target):
        if isinstance(target, (int, float)):
            return float(target)
        if isinstance(target, Mobject):
            return float(self.rows.index(target))
        if target in self._keys:
            return float(self._keys.index(target))
        raise ValueError(f"ScrollList: no item with key {target!r}")

    def set_focus(self, index):
        """Instantly centre ``index`` (int, label, or the item mobject). For the
        initial build / non-animated jumps."""
        self._apply_layout(self._resolve(index))
        return self

    def scroll_to(self, target):
        """Return a single animation that scrolls ``target`` (index, label, or
        item mobject) to the centre. Drive the pace with ``play(..., run_time=)``."""
        start = self._pos_value
        end = max(0.0, min(len(self.rows) - 1, self._resolve(target)))

        def _upd(mob, alpha):
            mob._apply_layout(interpolate(start, end, alpha))

        return UpdateFromAlphaFunc(self, _upd)

    def hide_all(self):
        """Instantly hide every row (dice-safe). Pair with fade_in() to reveal
        rows without a raw FadeIn/set_opacity (which would reveal a Die's hidden
        pips)."""
        for mob in self.rows:
            _set_opacity(mob, 0.0)
            mob._cur_opacity = 0.0
        return self

    def fade_in(self, indices=None):
        """Animation fading rows from their CURRENT opacity to their layout
        opacity — dice-safe (dice keep the right pips throughout). `indices`
        defaults to every currently-visible row (so it reveals whatever's hidden
        and leaves already-shown rows put)."""
        pos = self._pos_value
        if indices is None:
            indices = [i for i in range(len(self.rows))
                       if self._opacity_of(i - pos) > 0.01]
        starts = {i: self.rows[i]._cur_opacity for i in indices}
        targets = {i: self._opacity_of(i - pos) for i in indices}
        return self._fade_to(indices, starts, targets)

    def fade_out(self, indices=None):
        """Animation fading rows to 0 (dice-safe)."""
        if indices is None:
            indices = list(range(len(self.rows)))
        starts = {i: self.rows[i]._cur_opacity for i in indices}
        targets = {i: 0.0 for i in indices}
        return self._fade_to(indices, starts, targets)

    def _fade_to(self, indices, starts, targets):
        def _upd(mob, alpha):
            for i in indices:
                o = interpolate(starts[i], targets[i], alpha)
                _set_opacity(self.rows[i], o)
                self.rows[i]._cur_opacity = o
        return UpdateFromAlphaFunc(self, _upd)

    def enter(self):
        """Hide every row, then return a dice-safe fade-in of the visible ones."""
        self.hide_all()
        return self.fade_in()

    def exit(self):
        """Dice-safe fade-out of the whole wheel."""
        return self.fade_out()

    @property
    def focused(self):
        """The item mobject currently nearest the centre."""
        return self.rows[round(self._pos_value)]
