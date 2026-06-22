from manim import *
import numpy as np

from bpkfigures.style import FONT, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, crisp_text, crisp_paragraph


def get_histogram_counts(data, min_val, max_val):
    values = list(range(min_val, max_val + 1))
    counts = {k: 0 for k in values}
    for x in data:
        counts[x] += 1
    return values, counts


def get_histogram(
    data,
    center=ORIGIN,
    title=None,
    min_val=None,
    max_val=None,
    width=8,
    height=4,
    bar_color=BLUE,
    is_vertical=False,
    x_axis_label=None,
    show_sim_count=False
):
    if min_val is None:
        min_val = min(data)
    if max_val is None:
        max_val = max(data)

    values, counts = get_histogram_counts(data, min_val=min_val, max_val=max_val)

    count_list = [counts[v] for v in values]
    max_count = max(count_list)
    n = max_val - min_val + 1
    bar_width = width / n

    bars = VGroup()

    for i, val in enumerate(values):
        c = counts[val]
        h = (c / max_count) * height

        if not is_vertical:
            bar = Rectangle(
                width=bar_width * 0.9,
                height=h,
                fill_color=bar_color,
                fill_opacity=1.0,
                stroke_width=0
            )
            x = (i - n / 2 + 0.5) * bar_width
            y = h / 2
        else:
            bar = Rectangle(
                width=h,
                height=bar_width * 0.9,
                fill_color=bar_color,
                fill_opacity=1.0,
                stroke_width=0
            )
            x = h / 2
            y = (i - n / 2 + 0.5) * bar_width
        bar.move_to(np.array([x, y, 0]))
        bars.add(bar)

    elements = VGroup(bars)

    if not is_vertical:
        axis = Line(
            start=np.array([-width / 2, 0, 0]),
            end=np.array([width / 2, 0, 0]),
            color=BLACK
        )
    else:
        axis = Line(
            start=np.array([0, -width / 2, 0]),
            end=np.array([0, width / 2, 0]),
            color=BLACK
        )
    elements.add(axis)

    labels = VGroup()
    for i, val in enumerate(values):
        if val % 10 != 0:
            continue
        if not is_vertical:
            x = (i - n / 2 + 0.5) * bar_width
            pos = np.array([x, -0.3, 0])
        else:
            y = (i - n / 2 + 0.5) * bar_width
            pos = np.array([-0.3, y, 0])
        label = crisp_text(str(val), font=FONT, font_size=FONT_SIZE_SM, color=BLACK)
        label.move_to(pos)
        labels.add(label)
    elements.add(labels)

    if x_axis_label is not None and not is_vertical:
        axis_label_text = crisp_text(
            x_axis_label,
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        axis_label_text.next_to(labels, DOWN, buff=0.3)
        elements.add(axis_label_text)

    if title is not None:
        title_text = crisp_paragraph(
            title,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_LG,
            color=BLACK
        )
        title_text.next_to(elements, UP, buff=0.5)
        elements.add(title_text)

    if show_sim_count:
        sim_label = crisp_text(
            f"{len(data):,} Simulations",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        sim_label.next_to(bars, UR, buff=0)
        sim_label.shift(LEFT * 1.0 + DOWN * 0.6)
        elements.add(sim_label)

    core = VGroup(bars, axis)
    elements.shift(np.array(center) - core.get_center())

    return elements


def get_dual_histogram(
    data_x,
    data_y,
    center=ORIGIN,
    min_val=None,
    max_val=None,
    square_size=5,
    marginal_size=1.25,
    x_label=None,
    y_label=None,
    above_color=BLUE,
    below_color=BLUE,
    title=None
):
    if min_val is None:
        min_val = min(min(data_x), min(data_y))
    if max_val is None:
        max_val = max(max(data_x), max(data_y))

    values_x, counts_x = get_histogram_counts(data_x, min_val=min_val, max_val=max_val)
    values_y, counts_y = get_histogram_counts(data_y, min_val=min_val, max_val=max_val)

    x_counts = np.array([counts_x[v] for v in values_x], dtype=float)
    y_counts = np.array([counts_y[v] for v in values_y], dtype=float)

    x_probs = x_counts / x_counts.sum()
    y_probs = y_counts / y_counts.sum()

    joint = np.outer(y_probs, x_probs)

    n = max_val - min_val + 1
    cell_size = square_size / n

    vmin = joint.min()
    vmax = joint.max()

    def get_color(val, coord_diff):
        alpha = (val - vmin) / (vmax - vmin) if vmax > vmin else 0
        if coord_diff > 0:
            dark_color = above_color
        elif coord_diff < 0:
            dark_color = below_color
        else:
            dark_color = (above_color + below_color) / 2
        return interpolate_color(0.2 * dark_color + 0.8 * WHITE, dark_color, alpha)

    heatmap = VGroup()
    for r in range(n):
        for c in range(n):
            square = Square(
                side_length=cell_size * 1.1,
                fill_color=get_color(joint[r, c], r - c),
                fill_opacity=1.0,
                stroke_width=0
            )
            x = -square_size / 2 + (c + 0.5) * cell_size
            y = -square_size / 2 + (r + 0.5) * cell_size
            square.move_to(np.array([x, y, 0]))
            heatmap.add(square)

    border = SurroundingRectangle(heatmap, color=BLACK, stroke_width=2, buff=0)
    heatmap_group = VGroup(heatmap, border)

    bottom_hist = get_histogram(
        data_x,
        center=ORIGIN,
        min_val=min_val,
        max_val=max_val,
        width=square_size,
        height=marginal_size,
        is_vertical=False,
        bar_color=above_color
    )

    left_hist = get_histogram(
        data_y,
        center=ORIGIN,
        min_val=min_val,
        max_val=max_val,
        width=square_size,
        height=marginal_size,
        is_vertical=True,
        bar_color=below_color
    )

    heatmap_group.shift(np.array([square_size / 2, square_size / 2, 0]))
    bottom_hist.shift(np.array([square_size / 2, -marginal_size, 0]))
    left_hist.shift(np.array([-marginal_size, square_size / 2, 0]))

    labels = VGroup()

    if x_label is not None:
        x_text = crisp_paragraph(
            x_label,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        x_text.next_to(bottom_hist, DOWN, buff=0.4)
        labels.add(x_text)

    if y_label is not None:
        y_text = crisp_paragraph(
            y_label,
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_SM,
            color=BLACK
        )
        y_text.rotate(PI / 2)
        y_text.next_to(left_hist, LEFT, buff=0.4)
        labels.add(y_text)

    if title is not None:
        title_text = crisp_paragraph(
            *title.split("\n"),
            alignment="center",
            font=FONT,
            font_size=FONT_SIZE_MD,
            color=BLACK
        )
        title_text.next_to(heatmap_group, RIGHT, buff=0.4)
        labels.add(title_text)

    elements = VGroup(left_hist, heatmap_group, bottom_hist, labels)
    elements.move_to(center)
    return elements, joint


def get_win_percents(arr, first_player=False):
    rows, cols = arr.shape
    below = 0.0
    above = 0.0
    diag = 0.0

    for r in range(rows):
        for c in range(cols):
            if r > c:
                below += arr[r, c]
            elif r < c:
                above += arr[r, c]
            else:
                diag += arr[r, c]

    total = arr.sum()

    if first_player:
        below_pct = (below + diag) / total
    else:
        below_pct = (below + diag / 2) / total
    above_pct = 1 - below_pct

    return below_pct, above_pct


def get_diagonal_line(border, color=BLACK, stroke_width=2):
    return Line(
        border.get_corner(DL),
        border.get_corner(UR),
        color=color,
        stroke_width=stroke_width
    )


def get_diagonal_labels(
    arr,
    border,
    font_size=FONT_SIZE_SM,
    decimals=1,
    above_color=BLACK,
    below_color=BLACK,
    first_player=False,
    opacity_diff=True,
):
    below_pct, above_pct = get_win_percents(arr, first_player=first_player)

    top_left = border.get_corner(UL)
    bottom_right = border.get_corner(DR)

    above_label = crisp_text(
        f"{100 * below_pct:.{decimals}f}%",
        font=FONT,
        font_size=font_size,
        color=(above_color + BLACK) / 2,
    )
    if opacity_diff:
        above_label.set_opacity(0.5)
    above_label.next_to(top_left, DR, buff=0.1)

    below_label = crisp_text(
        f"{100 * above_pct:.{decimals}f}%",
        font=FONT,
        font_size=font_size,
        color=(below_color + BLACK) / 2,
    )
    below_label.next_to(bottom_right, UL, buff=0.1)

    return VGroup(above_label, below_label)


def get_diagonal_annotation(
    dual_histogram,
    color=BLACK,
    stroke_width=2,
    font_size=FONT_SIZE_SM,
    decimals=1,
    above_color=BLACK,
    below_color=BLACK,
    first_player=False,
    opacity_diff=True,
):
    elements, arr = dual_histogram
    left_hist, heatmap_group, bottom_hist, labels = elements
    heatmap, border = heatmap_group

    line = get_diagonal_line(border, color=color, stroke_width=stroke_width)
    labels = get_diagonal_labels(arr, border, font_size=font_size, decimals=decimals, above_color=above_color, below_color=below_color, first_player=first_player, opacity_diff=opacity_diff)

    return VGroup(line, labels)