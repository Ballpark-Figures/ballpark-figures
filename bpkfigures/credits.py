"""A CREDITS CARD -- the shared builder behind every video's reserved scene 98.

    card = credits_card([
        ("Created By", ["Name"]),
        ("Music and Sounds", ["@handle", "site.example"]),
    ])
    self.add(card)

Two columns that meet at a centre gutter: each LABEL right-aligned against the gutter,
its NAMES left-aligned after it, one name per line, the label on the line of its first
name. Every line sits on a shared TEXT BASELINE (`place_on_baseline`), so a label and
the name beside it line up whatever their ascenders and descenders.

Static construction only: the scene plays it (on from frame 0, a fade at the end).
The card is centred so its GUTTER is at x = 0 (not its bounding box), then
`fit_to_frame`d.

Role handles on the returned VGroup:
  ``.labels``   VGroup of the label texts, in order
  ``.names``    list of VGroups, the names of each section
  ``.sections`` list of VGroups, (label, *names) per section
"""
from manim import BOLD, WHITE, VGroup

from bpkfigures.style import ACCENT_GOLD, crisp_text, fit_to_frame, place_on_baseline


def credits_card(sections, *, label_size=30, name_size=30, label_color=ACCENT_GOLD,
                 name_color=WHITE, gutter=0.5, line_gap=0.62, group_gap=0.5):
    """`sections`: list of (label, [names...]). `line_gap` is baseline to baseline
    within a section; `group_gap` is the EXTRA space between sections."""
    card = VGroup()
    card.labels, card.names, card.sections = VGroup(), [], []
    y = 0.0
    for i, (label, names) in enumerate(sections):
        if i:
            y -= line_gap + group_gap
        lab = crisp_text(label, font_size=label_size, color=label_color, weight=BOLD,
                         baseline_at=(0, y))
        lab.shift([-gutter / 2 - lab.get_right()[0], 0, 0])
        group = VGroup()
        for j, name in enumerate(names):
            if j:
                y -= line_gap
            n = crisp_text(name, font_size=name_size, color=name_color, baseline_at=(0, y))
            n.shift([gutter / 2 - n.get_left()[0], 0, 0])
            group.add(n)
        card.labels.add(lab)
        card.names.append(group)
        section = VGroup(lab, *group)
        card.sections.append(section)
        card.add(section)
    card.shift([0, -card.get_center()[1], 0])     # vertically centred; gutter stays at x=0
    cx, w0 = card.get_center()[0], card.width
    fit_to_frame(card)                            # scales about the bbox centre, so...
    card.shift([-cx * (1 - card.width / w0), 0, 0])   # ...put the gutter back on x=0
    return card
