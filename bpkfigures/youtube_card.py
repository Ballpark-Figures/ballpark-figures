"""Mock YouTube video card — a 16:9 thumbnail with title / channel / views below.

A STATIC, reusable "watch this video" snippet (light or dark mode). Video-agnostic,
so it lives in bpkfigures. All text is passed in (nothing is computed).

The thumbnail region is a grey placeholder (with a play button) by default; pass
`thumbnail=<image path>` for a real still. NOTE: a real ImageMobject gets SQUARE
corners here — YouTube's ~12px rounding needs a mask, a later refinement. And a
real playing CLIP is a DaVinci overlay in post, not manim — drop the clip into the
thumbnail rectangle at the finishing step.
"""
import textwrap

from manim import *

from bpkfigures.style import crisp_text

_LIGHT = dict(surface="#FFFFFF", thumb="#E4E4E4", title="#0F0F0F",
              meta="#606060", avatar="#909090")
_DARK = dict(surface="#0F0F0F", thumb="#272727", title="#F1F1F1",
             meta="#AAAAAA", avatar="#717171")
_YT_RED = "#FF0000"


def _placeholder_thumb(w, h, fill):
    """A grey thumbnail box with a centred YouTube play button."""
    box = RoundedRectangle(width=w, height=h, corner_radius=0.14,
                           fill_color=ManimColor(fill), fill_opacity=1.0,
                           stroke_width=0)
    pb = RoundedRectangle(width=h * 0.30, height=h * 0.21, corner_radius=0.055,
                          fill_color=ManimColor(_YT_RED), fill_opacity=1.0,
                          stroke_width=0)
    tri = Triangle(fill_color=WHITE, fill_opacity=1.0, stroke_width=0)
    tri.set_height(h * 0.10).rotate(-PI / 2).move_to(pb)      # point right
    return VGroup(box, pb, tri)


def youtube_card(title, channel, meta, *, duration="12:34", thumbnail=None,
                 avatar=None, width=6.5, dark=False, title_size=26, meta_size=19,
                 wrap=34):
    """A YouTube-style video card: 16:9 thumbnail (+ duration badge) above an
    avatar, a 2-line `title`, the `channel`, and a `meta` line (e.g.
    "1.2M views · 3 days ago"). Returns a Group; caller positions/scales it.
    `wrap` is the title's per-line character budget (title truncates to 2 lines)."""
    C = _DARK if dark else _LIGHT
    pad = 0.22
    thumb_w = width - 2 * pad
    thumb_h = thumb_w * 9 / 16

    # ── thumbnail (+ duration badge) ──────────────────────────────────────────
    if thumbnail is not None:
        thumb = ImageMobject(thumbnail).set_width(thumb_w)
    else:
        thumb = _placeholder_thumb(thumb_w, thumb_h, C["thumb"])
    thumb.move_to(ORIGIN)

    badge = Group()
    if duration:
        dtxt = crisp_text(duration, font_size=15, color=WHITE)
        dbg = RoundedRectangle(width=dtxt.width + 0.16, height=dtxt.height + 0.12,
                               corner_radius=0.05, fill_color=BLACK,
                               fill_opacity=0.85, stroke_width=0).move_to(dtxt)
        badge = VGroup(dbg, dtxt)
        badge.align_to(thumb, DOWN).align_to(thumb, RIGHT).shift(UP * 0.13 + LEFT * 0.13)

    # ── text row below: avatar | title / channel / meta ──────────────────────
    avatar_r = 0.26
    if avatar is not None:
        av = ImageMobject(avatar).set_width(2 * avatar_r)
    else:
        disc = Circle(radius=avatar_r, fill_color=ManimColor(C["avatar"]),
                      fill_opacity=1.0, stroke_width=0)
        initial = crisp_text(channel[:1].upper(), font_size=20, color=WHITE).move_to(disc)
        av = VGroup(disc, initial)

    wrapped = textwrap.wrap(title, width=wrap) or [""]
    lines = wrapped[:2]
    if len(wrapped) > 2:
        lines[-1] = lines[-1].rstrip() + "…"
    title_mob = VGroup(*[crisp_text(ln, font_size=title_size, weight=BOLD,
                                    color=ManimColor(C["title"])) for ln in lines]
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
    channel_mob = crisp_text(channel, font_size=meta_size, color=ManimColor(C["meta"]))
    meta_mob = crisp_text(meta, font_size=meta_size, color=ManimColor(C["meta"]))
    text_col = VGroup(title_mob, channel_mob, meta_mob).arrange(
        DOWN, aligned_edge=LEFT, buff=0.09)
    av.next_to(text_col, LEFT, buff=0.16, aligned_edge=UP)

    row = Group(av, text_col)
    row.next_to(thumb, DOWN, buff=0.22, aligned_edge=LEFT)

    inner = Group(thumb, badge, row)
    surface = RoundedRectangle(width=inner.width + 2 * pad,
                               height=inner.height + 2 * pad, corner_radius=0.16,
                               fill_color=ManimColor(C["surface"]), fill_opacity=1.0,
                               stroke_width=0).move_to(inner)

    return Group(surface, thumb, badge, row)
