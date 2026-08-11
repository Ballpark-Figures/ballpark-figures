"""Pie chart — a ring of coloured Sectors summing to 360°, laid out CLOCKWISE from
the top (12 o'clock), with two fan-in animations.

`get_pie_chart(values, colors=…)` returns a `PieChart` (a VGroup) with handles:
    .sectors   VGroup of Sector wedges, in input order (clockwise from the top)
    .labels    per-sector labels — `label_mode="outside"` (default): "NAME  ##%" at the
               rim; `label_mode="inside"`: just "##%" inside each wedge (no names)
and two animation methods (each takes the scene + a single `run_time`, both starting
at the vertical and sweeping CLOCKWISE):
    .fan_all(scene, run_time)         — ALL sectors grow SIMULTANEOUSLY from the top,
                                        the swept arc always split in the final
                                        proportions, expanding to the full pie over 360°.
    .fan_sequential(scene, run_time)  — each sector sweeps in ONE AT A TIME, the first
                                        starting at the top.
Both use manim's default easing. Colours (and optional labels) are the caller's — e.g.
vowels red + consonants blue.
"""
from manim import *

from bpkfigures.style import FONT, FONT_SIZE_SM, crisp_text

_TOP = PI / 2   # 12 o'clock — where every sweep starts


class PieChart(VGroup):
    def __init__(self, values, *, colors, labels=None, radius=1.5, center=ORIGIN,
                 stroke_color=WHITE, stroke_width=2.0, label_color=None,
                 label_font_size=FONT_SIZE_SM, show_percent=True, label_buff=0.4,
                 label_mode="outside", inner_label_color=WHITE, inner_frac=0.62,
                 inner_frac_spread=0.0, **kwargs):
        super().__init__(**kwargs)
        vals = [float(v) for v in values]
        total = sum(vals) or 1.0
        self.pie_center = np.array(center, dtype=float)
        self.radius = radius
        self.colors = list(colors)
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        # each sector's arc (radians), the cumulative arc before it, and its start edge
        # (measured CLOCKWISE from the top). angle is drawn NEGATIVE = clockwise.
        self.arc = [v / total * TAU for v in vals]
        self.cum_before, c = [], 0.0
        for a in self.arc:
            self.cum_before.append(c)
            c += a
        self.start = [_TOP - cb for cb in self.cum_before]

        self.sectors = VGroup(*[self._sector(i, self.arc[i])
                                for i in range(len(vals))])
        self.add(self.sectors)

        self.labels = VGroup()
        if label_mode == "inside":
            # each slice's percentage drawn INSIDE the wedge, at its centroid — no
            # names (there's no room), no `labels`. Colour via `inner_label_color`.
            for i in range(len(vals)):
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
        elif labels is not None:
            for i, name in enumerate(labels):
                mid = self.start[i] - self.arc[i] / 2          # sector mid-angle
                out = np.array([np.cos(mid), np.sin(mid), 0.0])
                pct = f"{round(100 * vals[i] / total)}%"
                txt = (f"{name}  {pct}" if name and show_percent
                       else pct if show_percent else name)
                lab = crisp_text(txt, font=FONT, font_size=label_font_size,
                                 color=label_color or self.colors[i])
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
    def fan_all(self, scene, run_time):
        """ALL sectors grow SIMULTANEOUSLY from the top: the arc drawn so far is always
        split in the final proportions (a 39% sector is 39% of the swept arc throughout),
        expanding clockwise to the full pie. Each sector's start scales with the sweep so
        the wedges stay contiguous. Labels fade in over the last third."""
        if self not in scene.mobjects:
            scene.add(self)
        n = len(self.sectors)

        def func(_m, alpha):
            for i in range(n):
                self._redraw(i, self.arc[i] * alpha,
                             start=_TOP - self.cum_before[i] * alpha)
            self.labels.set_opacity(max(0.0, (alpha - 0.7) / 0.3))

        self.labels.set_opacity(0)
        scene.play(UpdateFromAlphaFunc(self, func), run_time=run_time)
        for i in range(n):
            self._redraw(i, self.arc[i])
        self.labels.set_opacity(1)

    def fan_sequential(self, scene, run_time):
        """Each sector sweeps in one at a time (equal time each), the first starting at
        the top; each label fades in with its sector. Default manim easing per sector."""
        if self not in scene.mobjects:
            scene.add(self)
        n = len(self.sectors)
        for i in range(n):
            self._redraw(i, 0.0)
        self.labels.set_opacity(0)
        rt = run_time / max(n, 1)
        for i in range(n):
            def func(_m, alpha, i=i):
                self._redraw(i, self.arc[i] * alpha)
                if i < len(self.labels):
                    self.labels[i].set_opacity(alpha)
            scene.play(UpdateFromAlphaFunc(self.sectors[i], func), run_time=rt)
            self._redraw(i, self.arc[i])
        self.labels.set_opacity(1)


def get_pie_chart(values, **kwargs):
    """Factory (mirrors get_bar_chart / letter_grid): build a PieChart. See the class
    for the layout + `fan_all` / `fan_sequential` animations."""
    return PieChart(values, **kwargs)
