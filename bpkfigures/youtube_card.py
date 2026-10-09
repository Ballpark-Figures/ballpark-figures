"""Mock YouTube UI — video card, full-screen watch page, and homepage grid.

STATIC, video-agnostic mocks (light or dark mode), so they live in bpkfigures. All
text is passed in (nothing is computed). Building blocks:

  youtube_card(...)   one grid card: 16:9 thumbnail + title / channel / meta
  youtube_watch(...)  full-screen watch page: big player + title + channel row
  youtube_home(cells) full-screen homepage: an N-column grid of cards, where each
                      cell is either a real card (a dict of kwargs) or None → a
                      greyed-out placeholder (skeleton)
  youtube_poll(...)   a community-tab poll post: avatar + channel + age, the
                      question, the vote count, and one bar per option filled to its
                      percentage (`page=True` sits it on a full-frame page)

The thumbnail is a grey play-button placeholder by default; pass `thumbnail=<path>`
for a real still (NOTE: a real ImageMobject keeps SQUARE corners — YouTube's ~12px
rounding needs a mask, a later refinement).

A PLAYING CLIP on the watch page: `play_clip(page, path, start)` returns an Animation
that plays the video file at `path` from `start` inside the page's player, at real
speed for whatever run_time the caller gives it:

    page = youtube_watch(...)
    self.play(play_clip(page, "hangman.mov", "13:30"), run_time=10)   # 13:30-13:40

Frames are STREAMED from ffmpeg as the animation runs (never held in memory or
written to disk — 10s at 60fps is ~2 GB of RGBA), pre-scaled to the player's pixel
size at this render's resolution, letterboxed like a real player. The video's
SOUND is NOT played. The player keeps the clip's last frame afterwards, so a later
fade starts from it. Like the thumbnail, the frame has square corners.
"""
import os
import subprocess
import textwrap

import numpy as np
from manim import *
from PIL import Image

from bpkfigures.style import crisp_text

_LIGHT = dict(surface="#FFFFFF", thumb="#E4E4E4", title="#0F0F0F",
              meta="#606060", avatar="#909090", skeleton="#E3E3E3",
              border="#E5E5E5", bar="#E5E5E5")
_DARK = dict(surface="#0F0F0F", thumb="#272727", title="#F1F1F1",
             meta="#AAAAAA", avatar="#717171", skeleton="#333333",
             border="#3F3F3F", bar="#3F3F3F")
_YT_RED = "#FF0000"


def _image(path, width):
    """An ImageMobject `width` units wide, PRE-SHRUNK with Lanczos to the exact pixel
    width it will occupy at this render's resolution. manim maps image pixels to the
    screen without averaging, so handing it a large image to show small (an 800- or
    1930-px avatar at ~96 px) breaks thin lines into dots and leaves jagged edges;
    resampling here first makes it come out smooth at any render quality."""
    img = Image.open(path).convert("RGBA")
    px = max(1, round(width / config.frame_width * config.pixel_width))
    if px < img.width:
        img = img.resize((px, max(1, round(img.height * px / img.width))),
                         Image.Resampling.LANCZOS)
    return ImageMobject(np.array(img)).set_width(width)


def _pal(dark):
    return _DARK if dark else _LIGHT


def _thumbnail(w, h, C, thumbnail, duration):
    """16:9 thumbnail (grey play-button placeholder or a real image) with an
    optional duration badge at the bottom-right."""
    if thumbnail is not None:
        base = _image(thumbnail, w)                             # square corners
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

    av = (_image(avatar, 2 * avatar_r) if avatar is not None
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
    av = (_image(avatar, 2 * avatar_r) if avatar is not None
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
    watch = Group(page, stack)
    watch.player = player               # for play_clip
    return watch


def _seconds(t):
    """`t` in seconds: a number, or "M:SS" / "H:MM:SS"."""
    if isinstance(t, str):
        secs = 0.0
        for part in t.split(":"):
            secs = secs * 60 + float(part)
        return secs
    return float(t)


class _ClipPlayback(Animation):
    """See `play_clip`."""

    def __init__(self, watch, path, start, **kwargs):
        if not os.path.exists(path):
            raise FileNotFoundError(f"play_clip: no video file at {path}")
        self.watch, self.path, self.start = watch, path, _seconds(start)
        self.box = watch.player[0]                  # the thumbnail's 16:9 base
        self.px = max(2, round(self.box.width / config.frame_width * config.pixel_width))
        self.py = max(2, round(self.px * self.box.height / self.box.width))
        self.screen = getattr(watch, "screen", None)
        if self.screen is None:                     # first clip on this page
            # attached to the player NOW, not in begin(): Scene.play adds an
            # animation's mobject to the scene top-level unless it is already in
            # the family, and a top-level copy would survive a later FadeOut of
            # the page. Transparent until the clip starts.
            self.screen = ImageMobject(np.zeros((self.py, self.px, 4), dtype=np.uint8))
            self.screen.set_width(self.box.width).move_to(self.box)
            watch.player.add(self.screen)            # on top of thumbnail + badge
            watch.screen = self.screen
        kwargs.setdefault("rate_func", linear)      # real-speed playback
        super().__init__(self.screen, **kwargs)

    def begin(self):
        self.n = max(1, round(self.run_time * config.frame_rate))
        self.proc, self.shown = None, -1
        self.frame = np.zeros((self.py, self.px, 4), dtype=np.uint8)
        self.frame[:, :, 3] = 255
        self._show(self.frame)
        self.screen.set_width(self.box.width).move_to(self.box)
        # the clip covers the thumbnail and its badge; hide them, or they show
        # through the clip when the page later fades
        for m in self.watch.player.submobjects:
            if m is not self.screen:
                m.set_opacity(0.0)
        super().begin()

    def _open(self):
        vf = (f"fps={config.frame_rate},"
              f"scale={self.px}:{self.py}:force_original_aspect_ratio=decrease,"
              f"pad={self.px}:{self.py}:(ow-iw)/2:(oh-ih)/2:black")
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-ss", f"{self.start:.3f}", "-i", self.path,
             "-an", "-vf", vf, "-frames:v", str(self.n), "-f", "rawvideo",
             "-pix_fmt", "rgba", "-"],
            stdout=subprocess.PIPE)
        self.shown = -1

    def _read_to(self, idx):
        """Advance the stream to frame `idx` (frames come in order; a jump back,
        never needed by a normal render, reopens the stream)."""
        if self.proc is None or idx < self.shown:
            self._close()
            self._open()
        size = self.px * self.py * 4
        while self.shown < idx:
            buf = self.proc.stdout.read(size)
            if len(buf) < size:                     # clip ran out: hold the last frame
                break
            self.frame = np.frombuffer(buf, np.uint8).reshape(self.py, self.px, 4)
            self.shown += 1

    def _show(self, arr):
        self.screen.pixel_array = arr.copy()
        self.screen.orig_alpha_pixel_array = arr[:, :, 3].copy()

    def _close(self):
        if self.proc is not None:
            self.proc.stdout.close()
            self.proc.kill()
            self.proc.wait()
            self.proc = None

    def interpolate_mobject(self, alpha):
        self._read_to(min(self.n - 1, int(self.rate_func(alpha) * self.n)))
        self._show(self.frame)

    def finish(self):
        self._read_to(self.n - 1)
        super().finish()
        self._show(self.frame)
        self._close()


def show_clip_frame(watch, path, start=0):
    """Put the frame of `path` at `start` into `watch`'s player, in place of the
    thumbnail — so the page shows where a `play_clip` from `start` will begin (09c:
    the watch page swipes back already on the clip's first frame). Same sizing and
    letterboxing as play_clip; a later play_clip on this page reuses the screen."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"show_clip_frame: no video file at {path}")
    box = watch.player[0]
    px = max(2, round(box.width / config.frame_width * config.pixel_width))
    py = max(2, round(px * box.height / box.width))
    vf = (f"scale={px}:{py}:force_original_aspect_ratio=decrease,"
          f"pad={px}:{py}:(ow-iw)/2:(oh-ih)/2:black")
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{_seconds(start):.3f}",
                          "-i", path, "-an", "-vf", vf, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE, check=True).stdout
    frame = np.frombuffer(out, np.uint8).reshape(py, px, 4)
    screen = getattr(watch, "screen", None)
    if screen is None:
        screen = ImageMobject(frame.copy())
        watch.player.add(screen)
        watch.screen = screen
    screen.pixel_array = frame.copy()
    screen.orig_alpha_pixel_array = frame[:, :, 3].copy()
    # WHICH frame this is, as text, so manim's animation cache can see it. Its hash of
    # an ndarray over 1000 elements keeps only the first 10,000 values -- the top rows
    # of the picture -- so two frames with the same top rows (a blue border) hashed
    # alike and a cached swipe showing the OLD frame was reused (wordle 09c,
    # 2026-10-09: 13:30 moved to 2:18 and the swipe kept showing 13:30).
    screen.clip_key = f"{os.path.abspath(path)}@{_seconds(start):.3f}"
    screen.set_width(box.width).move_to(box)
    for m in watch.player.submobjects:      # the thumbnail and its badge go under it
        if m is not screen:
            m.set_opacity(0.0)
    return watch


def play_clip(watch, path, start=0, **kwargs):
    """Play the video file at `path` from `start` (seconds, or "M:SS") inside the
    player of `watch`, a `youtube_watch` page, at real speed for the run_time the
    caller passes (so `run_time=10` shows 10 seconds of video). See the module
    docstring."""
    return _ClipPlayback(watch, path, start, **kwargs)


def youtube_poll(channel, age, question, votes, options, *, avatar=None, likes=None,
                 width=9.0, dark=True, page=False, frame_w=16.0, frame_h=9.0):
    """A community-tab poll post, sized by `width` (the card width). `options` is a
    list of (label, percent) pairs; each option is a bordered bar whose left part is
    filled to `percent`, label at the left and "N%" at the right. All text is passed
    in (nothing is computed). `likes` is accepted for completeness but NOT drawn —
    the reaction row needs icons this module does not have yet.

    Proportions are taken from YouTube's desktop layout, in "px" of a 742-px-wide
    card, so every size scales with `width`. `page=True` returns the card centred
    on a full-frame page background (scaled down if it would not fit). Returns a
    Group with role handles `.surface`, `.header`, `.question`, `.votes`, `.options`
    (one Group per option: `.box`, `.fill`, `.label`, `.pct`)."""
    C = _pal(dark)
    u = width / 742.0                  # one layout px in manim units
    fs = 71.2 * u                      # font_size for a 1-px em (crisp_text metrics)
    inset = 83 * u                     # text column's left edge from the card's
    bar_w = 593 * u
    bar_h, bar_gap = 46 * u, 14 * u
    col_x = -width / 2 + inset         # left edge of the text column (card at origin)

    def text(s, px, color, **kw):
        return crisp_text(s, font_size=px * fs, color=ManimColor(C[color]), **kw)

    # header: avatar at the far left, channel name (bold) + age on one line
    avatar_r = 23 * u
    av = (_image(avatar, 2 * avatar_r) if avatar is not None
          else _avatar(channel, C, avatar_r))
    name = text(channel, 14, "title", weight=BOLD)
    when = text(age, 14, "meta")
    head_line = VGroup(name, when).arrange(RIGHT, buff=10 * u, aligned_edge=DOWN)
    head_line.align_to(np.array([col_x, 0, 0]), LEFT)

    # question: wrapped by MEASURED width to the bar width, 18-px text on a 25-px
    # line pitch (a character-count wrap breaks early, since glyph widths vary)
    lines, cur = [], ""
    for word in question.split(" "):
        trial = f"{cur} {word}" if cur else word
        if cur and text(trial, 18, "title").width > bar_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    q_lines = VGroup(*[text(ln, 18, "title") for ln in lines])
    q_lines.arrange(DOWN, aligned_edge=LEFT, buff=25 * u - q_lines[0].height)
    q_lines.align_to(head_line, LEFT)

    votes_mob = text(votes, 13, "meta").align_to(head_line, LEFT)

    rows = []
    for label, pct in options:
        box = RoundedRectangle(width=bar_w, height=bar_h, corner_radius=4 * u,
                               fill_color=ManimColor(C["surface"]), fill_opacity=1.0,
                               stroke_color=ManimColor(C["border"]), stroke_width=1.5)
        fill = RoundedRectangle(width=max(bar_w * pct / 100.0, 8 * u), height=bar_h,
                                corner_radius=4 * u, fill_color=ManimColor(C["bar"]),
                                fill_opacity=1.0 if pct > 0 else 0.0, stroke_width=0)
        fill.align_to(box, LEFT)
        lab = text(label, 18, "title")
        lab.move_to(box).align_to(box, LEFT).shift(RIGHT * 11 * u)
        pc = text(f"{pct}%", 18, "title")
        pc.move_to(box).align_to(box, RIGHT).shift(LEFT * 11 * u)
        row = Group(box, fill, lab, pc)
        row.box, row.fill, row.label, row.pct = box, fill, lab, pc
        rows.append(row)
    opts = Group(*rows).arrange(DOWN, buff=bar_gap)
    opts.align_to(np.array([col_x, 0, 0]), LEFT)

    # vertical rhythm from the reference layout (px from the card top):
    # name line ~262, question 290 / 315, votes 343, first option 368
    head_line.set_y(0.0)
    q_lines.next_to(head_line, DOWN, buff=13 * u).align_to(head_line, LEFT)
    votes_mob.next_to(q_lines, DOWN, buff=14 * u).align_to(head_line, LEFT)
    opts.next_to(votes_mob, DOWN, buff=18 * u).align_to(head_line, LEFT)
    av.move_to(np.array([-width / 2 + 42 * u, head_line.get_top()[1] - 14 * u, 0]))

    content = Group(av, head_line, q_lines, votes_mob, opts)
    card_top = head_line.get_top()[1] + 20 * u
    card_bot = opts.get_bottom()[1] - 26 * u
    surf = RoundedRectangle(width=width, height=card_top - card_bot, corner_radius=12 * u,
                            fill_color=ManimColor(C["surface"]), fill_opacity=1.0,
                            stroke_color=ManimColor(C["border"]), stroke_width=1.5)
    surf.move_to(np.array([0, (card_top + card_bot) / 2, 0]))
    post = Group(surf, content)
    post.move_to(ORIGIN)
    post.surface, post.header, post.question = surf, Group(av, head_line), q_lines
    post.votes, post.options = votes_mob, opts
    if not page:
        return post
    if post.height > frame_h - 0.6:
        post.scale((frame_h - 0.6) / post.height)
    bg = Rectangle(width=frame_w, height=frame_h, fill_color=ManimColor(C["surface"]),
                   fill_opacity=1.0, stroke_width=0)
    out = Group(bg, post)
    out.post = post
    return out
