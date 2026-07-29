"""Generic heatmap — an array of values rendered as a grid of colour-mapped cells.

Generalized from the battleship board heatmap (which is 10×10 and board-coupled)
into a plain, reusable primitive: give it a 1-D or 2-D array and it returns a
VGroup of unit squares coloured `low_color`→`high_color` by value. Pass an
explicit `vmin`/`vmax` to share ONE colour scale across several heatmaps (e.g.
white = 0, red = a global max); omit them to auto-scale to this array's range.

Cells are laid out row-major, row 0 at TOP, centered on the group's origin.
`.cells` is a list-of-rows for `[r][c]` access; `.values` holds any labels.
"""
from manim import *

from bpkfigures.style import crisp_text


def get_heatmap(arr, *, cell_size=0.6, vmin=None, vmax=None,
                low_color=WHITE, high_color=PURE_RED,
                stroke_color=BLACK, stroke_width=1.0,
                show_values=False, decimals=0, value_font_size=14,
                value_color=BLACK):
    """Grid of colour-mapped cells from a 1-D or 2-D array (see module docstring).

    vmin/vmax default to the array's own min/max; pass them to fix the scale.
    show_values overlays each cell's value as a percentage (`decimals` places).
    Returns a VGroup(cells, values) with `.cells` (rows of squares) and `.values`.
    """
    a = np.atleast_2d(np.asarray(arr, dtype=float))
    rows, cols = a.shape
    lo = float(a.min()) if vmin is None else float(vmin)
    hi = float(a.max()) if vmax is None else float(vmax)

    def color(v):
        alpha = (v - lo) / (hi - lo) if hi > lo else 0.0
        return interpolate_color(low_color, high_color, min(max(alpha, 0.0), 1.0))

    cells = VGroup()
    values = VGroup()
    grid = []
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            sq = Square(side_length=cell_size, fill_color=color(a[r, c]),
                        fill_opacity=1.0, stroke_color=stroke_color,
                        stroke_width=stroke_width)
            sq.move_to([(c - (cols - 1) / 2) * cell_size,
                        ((rows - 1) / 2 - r) * cell_size, 0])
            cells.add(sq)
            row_cells.append(sq)
            if show_values:
                txt = crisp_text(f"{100 * a[r, c]:.{decimals}f}%",
                                 font_size=value_font_size, color=value_color)
                txt.move_to(sq)
                values.add(txt)
        grid.append(row_cells)

    hm = VGroup(cells, values)
    hm.cells = grid
    hm.values = values
    return hm
