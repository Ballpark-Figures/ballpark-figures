"""Mock YouTube UI — video card, full-screen watch page, and homepage grid.

STATIC, video-agnostic mocks (light or dark mode), so they live in bpkfigures. All
text is passed in (nothing is computed). Building blocks:

  youtube_card(...)   one grid card: 16:9 thumbnail + title / channel / meta
  youtube_watch(...)  full-screen watch page: big player + title + channel row
  youtube_home(cells) full-screen homepage: an N-column grid of cards, where each
                      cell is either a real card (a dict of kwargs) or None → a
                      greyed-out placeholder (skeleton)

The thumbnail is a grey play-button placeholder by default; pass `thumbnail=<path>`
for a real still (NOTE: a real ImageMobject keeps SQUARE corners — YouTube's ~12px
rounding needs a mask, a later refinement). A real playing CLIP is a DaVinci overlay
dropped into the thumbnail rectangle in post, not manim.
"""
import textwrap

from manim import *

from bpkfigures.style import crisp_text

_LIGHT = dict(surface="#FFFFFF", thumb="#E4E4E4", title="#0F0F0F",
              meta="#606060", avatar="#909090", skeleton="#E3E3E3")
_DARK = dict(surface="#0F0F0F", thumb="#272727", title="#F1F1F1",
             meta="#AAAAAA", avatar="#717171", skeleton="#333333")
_YT_RED = "#FF0000"


def _pal(dark):
    return _DARK if dark else _LIGHT


def _thumbnail(w, h, C, thumbnail, duration):
    """16:9 thumbnail (grey play-button placeholder or a real image) with an
    optional duration badge at the bottom-right."""
    if thumbnail is not None:
        base = ImageMobject(thumbnail).set_width(w)             # square corners
    else:
        box = RoundedRectangle(width=w, height=h, corner_radius=0.14,
                               fill_color=ManimColor(C["thumb"]), fill_opacity=1.0,
                               stroke_width=0)
        pb = RoundedRectangle(width=h * 0.30, height=h * 0.21, corner_radius=0.055,
                              fill_color=ManimColor(_YT_RED), fill_opacity=1.0,
                              stroke_width=0)
        tri = Triangle(fill_color=WHITE, fill_opacity=1.0, stroke_width=0)
        tri.set_height(h * 0.10).rotate(-PI / 2).move_to(pb)   # point right
        base = VGroup(box, pb, tri)
    g = Group(base)
    if duration:
        dfs = min(20, max(12, h * 6))
        dtxt = crisp_text(duration, font_size=dfs, color=WHITE)
        dbg = RoundedRectangle(width=dtxt.width + 0.16, height=dtxt.height + 0.12,
                               corner_radius=0.05, fill_color=BLACK,
                               fill_opacity=0.85, stroke_width=0).move_to(dtxt)
        badge = VGroup(dbg, dtxt)
        badge.align_to(base, DOWN).align_to(base, RIGHT).shift(UP * 0.1 + LEFT * 0.1)
        g.add(badge)
    return g


def _avatar(channel, C, r):
    """A circular avatar placeholder with the channel's initial."""
    disc = Circle(radius=r, fill_color=ManimColor(C["avatar"]), fill_opacity=1.0,
                  stroke_width=0)
    initial = crisp_text(channel[:1].upper(), font_size=r * 74, color=WHITE).move_to(disc)
    return VGroup(disc, initial)


def _title_lines(title, size, color, wrap):
    """Bold title wrapped to (at most) 2 lines, left-aligned."""
    wrapped = textwrap.wrap(title, width=wrap) or [""]
    lines = wrapped[:2]
    if len(wrapped) > 2:
        lines[-1] = lines[-1].rstrip() + "…"
    return VGroup(*[crisp_text(ln, font_size=size, weight=BOLD, color=color)
                    for ln in lines]).arrange(DOWN, aligned_edge=LEFT, buff=size * 0.003)


def youtube_card(title, channel, meta, *, duration="12:34", thumbnail=None,
                 avatar=None, width=6.5, dark=False, surface=True):
    """One YouTube grid card, sized by `width` (the thumbnail width): a 16:9
    thumbnail (+ duration badge) over an avatar, 2-line title, channel, and a meta
    line ("1.2M views · 3 days ago"). `surface=False` drops the card background
    (for sitting on a page, e.g. the homepage grid). Returns a Group."""
    C = _pal(dark)
    thumb_h = width * 9 / 16
    title_size, meta_size = width * 4.0, width * 2.9
    wrap = max(12, int(width * 5.2))
    avatar_r = width * 0.04

    thumb = _thumbnail(width, thumb_h, C, thumbnail, duration).move_to(ORIGIN)

    av = (ImageMobject(avatar).set_width(2 * avatar_r) if avatar is not None
          else _avatar(channel, C, avatar_r))
    text_col = VGroup(
        _title_lines(title, title_size, ManimColor(C["title"]), wrap),
        crisp_text(channel, font_size=meta_size, color=ManimColor(C["meta"])),
        crisp_text(meta, font_size=meta_size, color=ManimColor(C["meta"])),
    ).arrange(DOWN, aligned_edge=LEFT, buff=width * 0.014)
    av.next_to(text_col, LEFT, buff=width * 0.025, aligned_edge=UP)
    row = Group(av, text_col).next_to(thumb, DOWN, buff=width * 0.034, aligned_edge=LEFT)

    if not surface:
        return Group(thumb, row)
    pad = width * 0.034
    inner = Group(thumb, row)
    surf = RoundedRectangle(width=inner.width + 2 * pad, height=inner.height + 2 * pad,
                            corner_radius=0.16, fill_color=ManimColor(C["surface"]),
                            fill_opacity=1.0, stroke_width=0).move_to(inner)
    return Group(surf, thumb, row)


def _grey_card(width, dark):
    """A greyed-out placeholder card (skeleton): grey thumbnail + grey bars where
    the avatar / title / channel / meta would be. Sits on the page (no surface)."""
    C = _pal(dark)
    bar = ManimColor(C["skeleton"])
    thumb_h = width * 9 / 16
    thumb = RoundedRectangle(width=width, height=thumb_h, corner_radius=0.14,
                             fill_color=bar, fill_opacity=1.0, stroke_width=0)

    def sk(w, h):
        return RoundedRectangle(width=w, height=h, corner_radius=h / 2,
                                fill_color=bar, fill_opacity=1.0, stroke_width=0)

    avatar_r = width * 0.04
    av = Circle(radius=avatar_r, fill_color=bar, fill_opacity=1.0, stroke_width=0)
    text_col = VGroup(sk(width * 0.82, width * 0.033), sk(width * 0.6, width * 0.033),
                      sk(width * 0.42, width * 0.026), sk(width * 0.5, width * 0.026)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=width * 0.022)
    av.next_to(text_col, LEFT, buff=width * 0.025, aligned_edge=UP)
    row = Group(av, text_col).next_to(thumb, DOWN, buff=width * 0.034, aligned_edge=LEFT)
    return Group(thumb, row)


def youtube_home(cells, *, cols=3, dark=False, frame_w=16.0, frame_h=9.0,
                 margin_x=0.5, margin_y=0.5, gap=0.55):
    """Full-screen homepage: an `cols`-column grid of cards on a page background.
    Each item of `cells` is either a dict of `youtube_card` kwargs (a real video)
    or None (a greyed-out placeholder). Cards align by their top edge per row."""
    C = _pal(dark)
    page = Rectangle(width=frame_w, height=frame_h, fill_color=ManimColor(C["surface"]),
                     fill_opacity=1.0, stroke_width=0)
    card_w = (frame_w - 2 * margin_x - (cols - 1) * gap) / cols

    built = [(_grey_card(card_w, dark) if spec is None
              else youtube_card(width=card_w, dark=dark, surface=False, **spec))
             for spec in cells]
    row_pitch = max(c.height for c in built) + gap

    left0 = -frame_w / 2 + margin_x + card_w / 2      # centre-x of column 0
    top0 = frame_h / 2 - margin_y                     # top edge of row 0
    for i, card in enumerate(built):
        r, c = divmod(i, cols)
        card.set_x(left0 + c * (card_w + gap))
        card.align_to(np.array([0.0, top0 - r * row_pitch, 0.0]), UP)
    return Group(page, *built)


def youtube_watch(title, channel, meta, *, subscribe=True, duration=None,
                  thumbnail=None, avatar=None, dark=True, width=11.6,
                  frame_w=16.0, frame_h=9.0):
    """Full-screen watch page: a big 16:9 player, then the title, a channel row
    (avatar + name + Subscribe), and a grey meta line, on a page background."""
    C = _pal(dark)
    page = Rectangle(width=frame_w, height=frame_h, fill_color=ManimColor(C["surface"]),
                     fill_opacity=1.0, stroke_width=0)
    player = _thumbnail(width, width * 9 / 16, C, thumbnail, duration)

    title_mob = _title_lines(title, 34, ManimColor(C["title"]), int(width * 4.2))

    avatar_r = 0.4
    av = (ImageMobject(avatar).set_width(2 * avatar_r) if avatar is not None
          else _avatar(channel, C, avatar_r))
    cname = crisp_text(channel, font_size=25, weight=BOLD, color=ManimColor(C["title"]))
    av.next_to(cname, LEFT, buff=0.22)
    chan = Group(av, cname)
    if subscribe:
        stxt = crisp_text("Subscribe", font_size=22, color=(BLACK if dark else WHITE))
        sbg = RoundedRectangle(width=stxt.width + 0.5, height=stxt.height + 0.42,
                               corner_radius=(stxt.height + 0.42) / 2,
                               fill_color=(WHITE if dark else BLACK), fill_opacity=1.0,
                               stroke_width=0).move_to(stxt)
        btn = VGroup(sbg, stxt).next_to(chan, RIGHT, buff=0.55)
        chan = Group(av, cname, btn)

    meta_mob = crisp_text(meta, font_size=20, color=ManimColor(C["meta"]))

    below = Group(title_mob, chan, meta_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    below.next_to(player, DOWN, buff=0.32, aligned_edge=LEFT)
    stack = Group(player, below)
    stack.move_to(ORIGIN)
    if stack.height > frame_h - 0.6:
        stack.scale((frame_h - 0.6) / stack.height)
    return Group(page, stack)
