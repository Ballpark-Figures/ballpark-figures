"""Pie chart — a ring of coloured Sectors summing to 360°, laid out CLOCKWISE from
the top (12 o'clock), with two fan-in animations.

`get_pie_chart(values, colors=…)` returns a `PieChart` (a VGroup) with handles:
    .sectors   VGroup of Sector wedges, in input order (clockwise from the top)
    .labels    per-sector labels — `label_mode="outside"` (default): "NAME  ##%" on the
               rim ray; `label_mode="inside"`: just "##%" inside each wedge (no names);
               `label_mode="callout"`: "NAME  ##%" in a left/right column beside the pie,
               de-collided vertically with a leader line to the slice (crowded slices);
               `label_mode="legend"`: a column on ONE side (`legend_side`), a colour
               swatch per row in slice order, so labels never cross the pie or the far
               side (added for wheel-of-fortune 03). `label_factory(name, pct)` builds
               a legend row's label as any mobject (default "NAME  ##%" text)
and two animation methods (each takes the scene + a single `run_time`, both starting
at the vertical and sweeping CLOCKWISE):
    .fan_all(scene, run_time)         — ALL sectors grow SIMULTANEOUSLY from the top,
                                        the swept arc always split in the final
                                        proportions, expanding to the full pie over 360°.
    .fan_sequential(scene, run_time)  — each sector sweeps in ONE AT A TIME, the first
                                        starting at the top.
For an INCREMENTAL build across several beats (reveal some sectors now, more later):
    .hide_all()                       — set every sector invisible (the start state).
    .fan_sectors(scene, indices, run_time[, sequential=False])
                                      — grow just `indices` (each from its own edge),
                                        simultaneously by default or one at a time.
    .fan_group(scene, indices, run_time)
                                      — grow a contiguous `indices` as ONE arc from the
                                        first's edge (fan_all restricted to the group).
To CHANGE a pie already on screen (e.g. once a letter rules some answers out):
    .resize_sectors(scene, values, run_time[, anchor=None])
                                      — every arc moves to its share of the new `values`;
                                        a sector given 0 is EATEN by its neighbours. The
                                        first sector's start edge stays put (or, with
                                        anchor="gap", the point opposite the eaten ones);
                                        labels slide and cross-fade.
Sounds: `set_sounds(open=…, eat=…)` (once, e.g. in a video's config.py) puts an sfx under
every fan-in and every resize_sectors; each method's `sound=False` skips it for one call.
Both/all use manim's default easing. Colours (and optional labels) are the caller's —
e.g. vowels red + consonants blue.
"""
from manim import *

from bpkfigures.style import FONT, FONT_SIZE_SM, crisp_text

_TOP = PI / 2   # 12 o'clock — where every sweep starts

# Sound effects, off unless a video turns them on (set_sounds, e.g. in its config.py):
# "open" under every fan-in, "eat" under every resize_sectors. Each is None or
# (sfx name, gain dB or None), played with scene.sfx as the animation starts.
_SOUNDS = {"open": None, "eat": None}


def set_sounds(*, open=None, eat=None):
    """Turn on the pie's sounds for every pie from here on: `open` under each fan-in
    (fan_all, fan_sectors, fan_group, and each sector of fan_sequential), `eat` under
    each resize_sectors. Each is an sfx name, or (name, gain dB). None leaves it off."""
    for key, v in (("open", open), ("eat", eat)):
        _SOUNDS[key] = None if v is None else (v if isinstance(v, tuple) else (v, None))


def _cue(scene, key, sound):
    s = _SOUNDS[key]
    if sound and s is not None and hasattr(scene, "sfx"):
        scene.sfx(s[0], gain=s[1])


class PieChart(VGroup):
    def __init__(self, values, *, colors, labels=None, radius=1.5, center=ORIGIN,
                 stroke_color=WHITE, stroke_width=2.0, label_color=None,
                 label_font_size=FONT_SIZE_SM, show_percent=True, label_buff=0.4,
                 label_mode="outside", inner_label_color=WHITE, inner_frac=0.62,
                 inner_frac_spread=0.0, min_label_frac=0.0, leader_color=GREY,
                 rotation=0.0, legend_side="right", legend_buff=0.5, legend_gap=0.5,
                 swatch_size=0.28, label_factory=None, **kwargs):
        super().__init__(**kwargs)
        vals = [float(v) for v in values]
        total = sum(vals) or 1.0
        self.pie_center = np.array(center, dtype=float)
        self.radius = radius
        self.colors = list(colors)
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        # what resize_sectors needs to rebuild the labels for new values
        self._label_args = dict(
            colors=colors, labels=labels, radius=radius, center=center,
            stroke_color=stroke_color, stroke_width=stroke_width, label_color=label_color,
            label_font_size=label_font_size, show_percent=show_percent,
            label_buff=label_buff, label_mode=label_mode,
            inner_label_color=inner_label_color, inner_frac=inner_frac,
            inner_frac_spread=inner_frac_spread, min_label_frac=min_label_frac,
            leader_color=leader_color, legend_side=legend_side, legend_buff=legend_buff,
            legend_gap=legend_gap, swatch_size=swatch_size, label_factory=label_factory)
        # each sector's arc (radians), the cumulative arc before it, and its start edge
        # (measured CLOCKWISE from the top, less `rotation`: how far clockwise the first
        # sector starts, nonzero only after a resize). angle is drawn NEGATIVE = clockwise.
        self.rotation = rotation
        self.arc = [v / total * TAU for v in vals]
        self.cum_before, c = [], 0.0
        for a in self.arc:
            self.cum_before.append(c)
            c += a
        self.start = [_TOP - rotation - cb for cb in self.cum_before]

        self.sectors = VGroup(*[self._sector(i, self.arc[i])
                                for i in range(len(vals))])
        self.add(self.sectors)

        self.labels = VGroup()
        if label_mode == "inside":
            # each slice's percentage drawn INSIDE the wedge, at its centroid — no
            # names (there's no room), no `labels`. Colour via `inner_label_color`.
            # A slice below `min_label_frac` gets an EMPTY placeholder label (keeps
            # self.labels index-aligned with self.sectors for the reveal animations)
            # so a spray of tiny slivers isn't an unreadable pile of overlapping %.
            for i in range(len(vals)):
                if vals[i] <= 0 or vals[i] / total < min_label_frac:
                    self.labels.add(VGroup())
                    continue
                mid = self.start[i] - self.arc[i] / 2
                out = np.array([np.cos(mid), np.sin(mid), 0.0])
                pct = f"{round(100 * vals[i] / total)}%"
                lab = crisp_text(pct, font=FONT, font_size=label_font_size,
                                 color=inner_label_color, weight=BOLD)
                # bigger slices sit a bit further IN, thinner slices further OUT
                f = inner_frac + inner_frac_spread * (0.5 - vals[i] / total)
                lab.move_to(self.pie_center + out * (radius * f))
                self.labels.add(lab)
            self.add(self.labels)
        elif label_mode == "callout" and labels is not None:
            # LEADER-LINE callouts: each label sits in a LEFT/RIGHT column beside the
            # pie at its slice's rim height (de-collided so crowded small slices don't
            # overlap), with a thin leader line from the rim to the label. Each label
            # is VGroup(leader, text) so the reveal animations fade both together.
            col_gap = label_buff + 0.55                    # column offset beyond the rim
            min_gap = 0.55                                 # min vertical spacing per column
            built, sides = {}, {1.0: [], -1.0: []}
            for i, name in enumerate(labels):
                if vals[i] <= 0 or vals[i] / total < min_label_frac:
                    continue
                mid = self.start[i] - self.arc[i] / 2
                d = np.array([np.cos(mid), np.sin(mid), 0.0])
                side = 1.0 if d[0] >= 0 else -1.0
                pct = f"{round(100 * vals[i] / total)}%"
                txt = (f"{name}  {pct}" if name and show_percent
                       else pct if show_percent else name)
                lab = crisp_text(txt, font=FONT, font_size=label_font_size,
                                 color=label_color or self.colors[i], weight=BOLD)
                sides[side].append({"i": i, "rim": self.pie_center + d * radius,
                                    "y": (self.pie_center + d * radius)[1], "lab": lab})
            for side, items in sides.items():
                items.sort(key=lambda e: -e["y"])          # top → bottom
                col_x = self.pie_center[0] + side * (radius + col_gap)
                ys = [e["y"] for e in items]
                for k in range(1, len(ys)):                # push apart to keep min_gap
                    if ys[k] > ys[k - 1] - min_gap:
                        ys[k] = ys[k - 1] - min_gap
                for e, y in zip(items, ys):
                    lab = e["lab"]
                    lab.move_to([col_x + side * lab.width / 2, y, 0])
                    inner = (lab.get_left() if side > 0 else lab.get_right())
                    leader = Line(e["rim"], inner - np.array([side * 0.08, 0, 0]),
                                  stroke_width=1.5, color=leader_color)
                    built[e["i"]] = VGroup(leader, lab)
            for i in range(len(vals)):
                self.labels.add(built.get(i, VGroup()))
            self.add(self.labels)
        elif label_mode == "legend" and labels is not None:
            # one column beside the pie, rows top to bottom in slice order, each a
            # swatch of the slice's colour then its label; centred on the pie's height
            rows, shown = [], []
            for i, name in enumerate(labels):
                if vals[i] <= 0:            # no row for an empty slice (e.g. one eaten
                    continue                # by resize_sectors)
                shown.append(i)
                pct = f"{round(100 * vals[i] / total)}%"
                lab = (label_factory(name, pct) if label_factory is not None
                       else crisp_text(f"{name}  {pct}" if show_percent else name,
                                       font=FONT, font_size=label_font_size,
                                       color=label_color or WHITE))
                sw = Square(side_length=swatch_size, fill_color=self.colors[i],
                            fill_opacity=1, stroke_width=0)
                rows.append(VGroup(sw, lab.next_to(sw, RIGHT, buff=0.2)))
            top = self.pie_center[1] + (len(rows) - 1) / 2 * legend_gap
            col = VGroup()
            for k, row in enumerate(rows):
                row.set_y(top - k * legend_gap)
                col.add(row)
            for row in rows:
                row.align_to(col, LEFT)
            if legend_side == "right":
                col.shift(RIGHT * (self.pie_center[0] + radius + legend_buff - col.get_left()[0]))
            else:
                col.shift(RIGHT * (self.pie_center[0] - radius - legend_buff - col.get_right()[0]))
            by_slice = dict(zip(shown, rows))
            for i in range(len(vals)):
                self.labels.add(by_slice.get(i, VGroup()))
            self.add(self.labels)
        elif labels is not None:
            for i, name in enumerate(labels):
                if vals[i] <= 0 or vals[i] / total < min_label_frac:
                    self.labels.add(VGroup())                  # placeholder: keep alignment
                    continue
                mid = self.start[i] - self.arc[i] / 2          # sector mid-angle
                out = np.array([np.cos(mid), np.sin(mid), 0.0])
                pct = f"{round(100 * vals[i] / total)}%"
                txt = (f"{name}  {pct}" if name and show_percent
                       else pct if show_percent else name)
                lab = crisp_text(txt, font=FONT, font_size=label_font_size,
                                 color=label_color or self.colors[i], weight=BOLD)
                # CENTRE the label on the sector's radial ray, pushed out so its inner
                # edge clears the rim by `label_buff`. Clear by the dimension ALIGNED
                # with the ray (width when mostly horizontal, height when mostly
                # vertical) — using the full corner projection would shove a wide label
                # far out on a near-vertical ray. (next_to would anchor by a corner and
                # sit askew; this keeps every label centred on its own ray.)
                extent = lab.width / 2 if abs(out[0]) >= abs(out[1]) else lab.height / 2
                lab.move_to(self.pie_center + out * (radius + label_buff + extent))
                self.labels.add(lab)
            self.add(self.labels)

    def _sector(self, i, a, start=None):
        """Sector `i` drawn to arc `a` (0..arc[i]) from `start` (default = its final
        start edge); invisible at a≈0 so a growing wedge starts from nothing rather
        than a stray radius line."""
        on = a > 1e-3
        return Sector(radius=self.radius,
                      start_angle=self.start[i] if start is None else start,
                      angle=-max(a, 1e-3), arc_center=self.pie_center,
                      fill_color=self.colors[i], fill_opacity=1.0 if on else 0.0,
                      stroke_color=self.stroke_color,
                      stroke_width=self.stroke_width if on else 0.0)

    def _redraw(self, i, a, start=None):
        self.sectors[i].become(self._sector(i, a, start))

    # ── animations (start at the top, sweep clockwise; default manim easing) ────
    def fan_all(self, scene, run_time, extra=(), sound=True):
        """ALL sectors grow SIMULTANEOUSLY from the top: the arc drawn so far is always
        split in the final proportions (a 39% sector is 39% of the swept arc throughout),
        expanding clockwise to the full pie. Each sector's start scales with the sweep so
        the wedges stay contiguous. Labels fade in over the last third. `extra` plays
        alongside (e.g. the chart's title fading in with it)."""
        if self not in scene.mobjects:
            scene.add(self)
        n = len(self.sectors)

        def func(_m, alpha):
            for i in range(n):
                self._redraw(i, self.arc[i] * alpha,
                             start=_TOP - self.cum_before[i] * alpha)
            self.labels.set_opacity(max(0.0, (alpha - 0.7) / 0.3))

        self.labels.set_opacity(0)
        _cue(scene, "open", sound)
        scene.play(UpdateFromAlphaFunc(self, func), *extra, run_time=run_time)
        for i in range(n):
            self._redraw(i, self.arc[i])
        self.labels.set_opacity(1)

    def hide_all(self):
        """Set every sector invisible (arc 0) and hide all labels — the start state
        for an INCREMENTAL build via fan_sectors / fan_sequential."""
        for i in range(len(self.sectors)):
            self._redraw(i, 0.0)
        self.labels.set_opacity(0)

    def _fan_one(self, scene, i, run_time, sound=True):
        """Grow sector ``i`` from nothing to its full arc (from its own start edge),
        its label fading in with it."""
        def func(_m, alpha):
            self._redraw(i, self.arc[i] * alpha)
            if i < len(self.labels):
                self.labels[i].set_opacity(alpha)
        _cue(scene, "open", sound)
        scene.play(UpdateFromAlphaFunc(self.sectors[i], func), run_time=run_time)
        self._redraw(i, self.arc[i])
        if i < len(self.labels):
            self.labels[i].set_opacity(1)

    def fan_sequential(self, scene, run_time, sound=True):
        """Each sector sweeps in one at a time (equal time each), the first starting at
        the top; each label fades in with its sector. Default manim easing per sector."""
        if self not in scene.mobjects:
            scene.add(self)
        self.hide_all()
        n = len(self.sectors)
        rt = run_time / max(n, 1)
        for i in range(n):
            self._fan_one(scene, i, rt, sound)

    def fan_sectors(self, scene, indices, run_time, *, sequential=False, extra=(), sound=True):
        """Grow just the sectors in ``indices`` (each from its OWN start edge) over one
        ``run_time`` — SIMULTANEOUSLY by default (the "all at once" tail), or one at a
        time if ``sequential=True``. Un-named sectors are left as they are, so calling
        this repeatedly across beats builds the pie incrementally (pair with an initial
        ``hide_all``). Labels for the named sectors fade in with them. `extra` plays
        alongside (simultaneous mode only), as in fan_all."""
        if self not in scene.mobjects:
            scene.add(self)
        indices = [int(i) for i in indices]
        if sequential:
            rt = run_time / max(len(indices), 1)
            for i in indices:
                self._fan_one(scene, i, rt, sound)
            return

        def func(_m, alpha):
            for i in indices:
                self._redraw(i, self.arc[i] * alpha)
                if i < len(self.labels):
                    self.labels[i].set_opacity(alpha)
        _cue(scene, "open", sound)
        scene.play(UpdateFromAlphaFunc(self.sectors, func), *extra, run_time=run_time)
        for i in indices:
            self._redraw(i, self.arc[i])
            if i < len(self.labels):
                self.labels[i].set_opacity(1)

    def fan_group(self, scene, indices, run_time, extra=(), sound=True):
        """Grow a CONTIGUOUS group of sectors as ONE arc sweeping clockwise from the
        FIRST sector's start edge (a shared origin) — the swept arc always split in the
        group's final proportions (fan_all, restricted to `indices`), so the group fans
        out from one place rather than each sector growing in place from its own edge.
        Labels fade in over the last third. `extra` plays alongside, as in fan_all."""
        if self not in scene.mobjects:
            scene.add(self)
        idx = sorted(int(i) for i in indices)
        base = self.start[idx[0]]                      # shared start edge (group's top)
        cums, c = [], 0.0
        for i in idx:
            cums.append(c)
            c += self.arc[i]

        def func(_m, alpha):
            for j, i in enumerate(idx):
                self._redraw(i, self.arc[i] * alpha, start=base - cums[j] * alpha)
                if i < len(self.labels):
                    self.labels[i].set_opacity(max(0.0, (alpha - 0.7) / 0.3))
        for i in idx:
            self._redraw(i, 0.0)
            if i < len(self.labels):
                self.labels[i].set_opacity(0)
        _cue(scene, "open", sound)
        scene.play(UpdateFromAlphaFunc(self.sectors, func), *extra, run_time=run_time)
        for i in idx:
            self._redraw(i, self.arc[i])
            if i < len(self.labels):
                self.labels[i].set_opacity(1)

    def resize_sectors(self, scene, values, run_time, *, anchor=None, extra=(), sound=True):
        """Re-split the pie to new `values` (one per sector, in the same order): every
        arc moves from its old share to its new one at once, and a sector given 0 is
        EATEN by its neighbours, which grow into it from both sides until it is gone.
        The values are the caller's (sourced, like the first ones); nothing here
        renormalises a removal for you.

        One point of the ring stays still, so the pie never spins: `anchor` (radians
        clockwise from the top). By default it is the first sector's start edge, so a
        pie that starts at the top still does and the sectors after an eaten one
        close up behind it. `anchor="gap"` keeps the point opposite the eaten sectors
        (their arc-weighted mean direction) instead, so the gap closes on itself from
        both sides. A label in both layouts
        slides to its new place as old and new cross-fade (its % changing in place);
        an eaten sector's label fades out over the first 40%. `extra` plays alongside."""
        vals = [float(v) for v in values]
        n = len(self.sectors)
        if len(vals) != n:
            raise ValueError(f"resize_sectors: {len(vals)} values for {n} sectors")
        total = sum(vals)
        if total <= 0:
            raise ValueError("resize_sectors: the new values sum to 0")
        old = list(self.arc)
        new = [v / total * TAU for v in vals]
        rot0 = self.rotation

        def cums(arcs):
            out, c = [], 0.0
            for a in arcs:
                out.append(c)
                c += a
            return out

        old_cum = cums(old)
        if anchor is None:
            anchor = rot0                       # the first sector's start edge stays put
        elif anchor == "gap":
            gone = [i for i in range(n) if new[i] <= 0 < old[i]]
            if gone:
                # the eaten sectors' mean direction (clockwise from the top), then opposite
                mids = [rot0 + old_cum[i] + old[i] / 2 for i in gone]
                w = [old[i] for i in gone]
                x = sum(wi * np.cos(m) for wi, m in zip(w, mids))
                y = sum(wi * np.sin(m) for wi, m in zip(w, mids))
                anchor = np.arctan2(y, x) + PI
            else:
                anchor = rot0
        # the anchor's place in the OLD layout: sector j, fraction f of its arc. It is
        # kept at the same angle as every arc changes, which fixes the rotation.
        rel = (anchor - rot0) % TAU
        j = next((k for k in range(n) if old[k] > 0 and old_cum[k] + old[k] >= rel), n - 1)
        f = (rel - old_cum[j]) / old[j] if old[j] > 0 else 0.0
        f = min(max(f, 0.0), 1.0)

        def layout(alpha):
            arcs = [(1 - alpha) * o + alpha * w for o, w in zip(old, new)]
            cum = cums(arcs)
            rot = anchor - cum[j] - f * arcs[j]
            return arcs, cum, rot

        _, _, rot1 = layout(1.0)
        target = PieChart(vals, rotation=rot1, **self._label_args)
        new_labels = target.labels
        new_labels.set_opacity(0)
        old_labels = self.labels
        scene.add(new_labels)
        # a label kept by both layouts slides from its old place to its new one as the
        # two cross-fade (a legend row whose % changes reads as one row moving); an eaten
        # sector's label fades out early, a newly shown one fades in late
        pairs = []
        for i in range(min(len(old_labels), len(new_labels))):
            o, w = old_labels[i], new_labels[i]
            if len(o.get_family()) > 1 and len(w.get_family()) > 1:
                pairs.append((o, w, o.get_center(), w.get_center()))
        paired = {id(o) for o, *_ in pairs} | {id(w) for _, w, *_ in pairs}

        def func(_m, alpha):
            arcs, cum, rot = layout(alpha)
            for i in range(n):
                self._redraw(i, arcs[i], start=_TOP - rot - cum[i])
            s = smooth(alpha)
            for o, w, oc, wc in pairs:
                o.move_to(oc + (wc - oc) * s)
                w.move_to(wc + (oc - wc) * (1 - s))
                o.set_opacity(1 - s)
                w.set_opacity(s)
            for lab in old_labels:
                if id(lab) not in paired:
                    lab.set_opacity(max(0.0, 1 - alpha / 0.4))
            for lab in new_labels:
                if id(lab) not in paired:
                    lab.set_opacity(max(0.0, (alpha - 0.6) / 0.4))

        _cue(scene, "eat", sound)
        scene.play(UpdateFromAlphaFunc(self.sectors, func), *extra, run_time=run_time)
        # adopt the new layout, so later calls (another resize) start from it
        self.rotation, self.arc, self.cum_before = rot1, new, cums(new)
        self.start = [_TOP - rot1 - cb for cb in self.cum_before]
        for i in range(n):
            self._redraw(i, self.arc[i])
        scene.remove(new_labels)
        self.remove(old_labels)
        for o, w, oc, wc in pairs:
            w.move_to(wc)
        new_labels.set_opacity(1)
        self.labels = new_labels
        self.add(new_labels)


def get_pie_chart(values, **kwargs):
    """Factory (mirrors get_bar_chart / letter_grid): build a PieChart. See the class
    for the layout + `fan_all` / `fan_sequential` animations."""
    return PieChart(values, **kwargs)
