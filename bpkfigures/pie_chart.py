"""Pie chart — a ring of coloured Sectors summing to 360°, laid out CLOCKWISE from
the top (12 o'clock), with two fan-in animations.

`get_pie_chart(values, colors=…)` returns a `PieChart` (a VGroup) with handles:
    .sectors   VGroup of Sector wedges, in input order (clockwise from the top)
    .labels    VGroup of per-sector labels ("NAME  ##%"), or empty
and two animation methods (each takes the scene + a single `run_time`, both starting
at the vertical and sweeping CLOCKWISE):
    .fan_all(scene, run_time)         — ONE continuous sweep from the top, the whole
                                        pie drawing on over 360°.
    .fan_sequential(scene, run_time)  — each sector sweeps in ONE AT A TIME, the first
                                        starting at the top.
Colours (and optional labels) are the caller's — e.g. vowels red + consonants blue.
"""
from manim import *

from bpkfigures.style import FONT, FONT_SIZE_SM, crisp_text

_TOP = PI / 2   # 12 o'clock — where every sweep starts


class PieChart(VGroup):
    def __init__(self, values, *, colors, labels=None, radius=1.5, center=ORIGIN,
                 stroke_color=WHITE, stroke_width=2.0, label_color=None,
                 label_font_size=FONT_SIZE_SM, show_percent=True, label_buff=0.4,
                 **kwargs):
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
        if labels is not None:
            for i, name in enumerate(labels):
                mid = self.start[i] - self.arc[i] / 2          # sector mid-angle
                out = np.array([np.cos(mid), np.sin(mid), 0.0])
                txt = name + (f"  {round(100 * vals[i] / total)}%"
                              if show_percent else "")
                lab = crisp_text(txt, font=FONT, font_size=label_font_size,
                                 color=label_color or self.colors[i])
                # sit the label fully OUTSIDE the arc (edge nearest the pie at the
                # rim + buff), so a long label never bleeds over its sector
                lab.next_to(self.pie_center + out * radius, out, buff=label_buff)
                self.labels.add(lab)
            self.add(self.labels)

    def _sector(self, i, a):
        """Sector `i` drawn to arc `a` (0..arc[i]); invisible at a≈0 so a growing
        wedge starts from nothing rather than a stray radius line."""
        on = a > 1e-3
        return Sector(radius=self.radius, start_angle=self.start[i],
                      angle=-max(a, 1e-3), arc_center=self.pie_center,
                      fill_color=self.colors[i], fill_opacity=1.0 if on else 0.0,
                      stroke_color=self.stroke_color,
                      stroke_width=self.stroke_width if on else 0.0)

    def _redraw(self, i, a):
        self.sectors[i].become(self._sector(i, a))

    # ── animations (start at the top, sweep clockwise) ──────────────────────────
    def fan_all(self, scene, run_time):
        """One continuous clockwise sweep from the top over 360° — the whole pie
        draws on; each label fades in as the sweep reaches its sector."""
        if self not in scene.mobjects:
            scene.add(self)
        n = len(self.sectors)

        def func(_m, alpha):
            swept = alpha * TAU
            for i in range(n):
                self._redraw(i, min(max(swept - self.cum_before[i], 0.0), self.arc[i]))
            for i in range(len(self.labels)):
                mid = self.cum_before[i] + self.arc[i] / 2     # label appears at mid
                self.labels[i].set_opacity(1.0 if swept >= mid else 0.0)

        self.labels.set_opacity(0)
        scene.play(UpdateFromAlphaFunc(self, func), run_time=run_time,
                   rate_func=linear)
        for i in range(n):
            self._redraw(i, self.arc[i])
        self.labels.set_opacity(1)

    def fan_sequential(self, scene, run_time):
        """Each sector sweeps in one at a time (equal time each), the first starting
        at the top; each label fades in with its sector."""
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
            scene.play(UpdateFromAlphaFunc(self.sectors[i], func), run_time=rt,
                       rate_func=linear)
            self._redraw(i, self.arc[i])
        self.labels.set_opacity(1)


def get_pie_chart(values, **kwargs):
    """Factory (mirrors get_bar_chart / letter_grid): build a PieChart. See the class
    for the layout + `fan_all` / `fan_sequential` animations."""
    return PieChart(values, **kwargs)
