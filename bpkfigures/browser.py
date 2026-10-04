"""Mock web browser — a window with one tab and an address bar, around a page.

STATIC and video-agnostic, like `youtube_card.py`, so it lives in bpkfigures. Every
string is passed in; nothing is computed.

    win = browser_window("britannica.com/games/octordle", "Octordle",
                         image="assets/web_media/octordle.png", width=13.6)
    win.chrome      # the frame, tab strip and toolbar (draws ON TOP of the page)
    win.page        # the page: an ImageMobject, a Mobject you passed, or a blank fill
    win.viewport    # the page's rectangle, for placing things inside it
    win.type_url(scene, "duotrigordle.com", run_time=1.0)   # caret + letters
    self.play(win.swipe_to("b.png", "site.org/b", "B"), run_time=1.0)  # next page
    self.play(win.scroll_by(1.0), run_time=1.5)            # down one screen
    self.play(win.fade_to("b_open.png"), run_time=0.2)     # same page, new state
    win.page_point(1560, 42)    # a screenshot pixel, as a scene point (cursor target)

THE PAGE FILLS THE VIEWPORT, AND THE VIEWPORT TAKES THE SCREENSHOT'S SHAPE (or
`aspect`, height over width; 16:9 when there is no image). So a 1920x1080 capture
makes a 16:9 window and a 1920x1490 one a taller window, with no cropping.

A SCROLLING PAGE is a screenshot TALLER than the viewport, e.g. a full-page
capture, with `aspect` given: the window shows its top, and `scroll_by` moves down
it.

DARK MODE IS CHROME'S, in the sizes of a 1920px-wide Chrome window: the tab strip and
toolbar together are ~4.5% of the window's width. Light mode exists for symmetry with
`youtube_card` and is untested beyond rendering.

TWO KNOWN SIMPLIFICATIONS. The window's bottom corners are rounded but the page image
inside is square, so at a large corner radius its corners would poke out; the radius
here is small enough that they sit under the window's stroke. And there is no real
clipping (manim has none), so nothing that moves the page moves a mobject:
`swipe_to` and `scroll_by` both work in PIXELS, showing a viewport-sized crop of
the screenshot(s) each frame.

SHARPNESS: the screenshot is pre-shrunk to the pixel width it is built at
(`youtube_card._image`). Building a window big and then scaling it down a lot brings
back the jagged look that avoids — so a window that will be shown small should be
BUILT small (or swapped for a small build at the end of the shrink).
"""
from manim import *

from bpkfigures.style import crisp_text
from PIL import Image

from bpkfigures.youtube_card import _image

_DARK = dict(frame="#202124", tab="#35363A", toolbar="#35363A", omnibox="#202124",
             text="#E8EAED", meta="#9AA0A6", page="#202124", stroke="#3C4043")
_LIGHT = dict(frame="#DEE1E6", tab="#FFFFFF", toolbar="#FFFFFF", omnibox="#F1F3F4",
              text="#202124", meta="#5F6368", page="#FFFFFF", stroke="#C4C7C5")
_LIGHTS = ("#FF5F57", "#FEBC2E", "#28C840")          # macOS close / minimise / zoom

# fractions of the window WIDTH, from a 1920px Chrome window
TAB_STRIP = 0.022
TOOLBAR = 0.024
RADIUS = 0.006


class BrowserWindow(Group):
    def __init__(self, url, title, *, image=None, page=None, width=12.0, aspect=None,
                 dark=True):
        super().__init__()
        C = _DARK if dark else _LIGHT
        self.C, self.W = C, width
        self.image = image          # the page's file, for `swipe_to` / `scroll_by`
        self.scroll = 0.0           # how far down the page, in viewport heights
        tab_h, bar_h = TAB_STRIP * width, TOOLBAR * width
        if aspect is None:                 # height / width of the page area
            if image is not None:
                with Image.open(image) as im:
                    aspect = im.height / im.width
            else:
                aspect = 9 / 16
        self.aspect = aspect
        view_h = width * aspect
        total_h = tab_h + bar_h + view_h

        # ── the page ─────────────────────────────────────────────────────────
        top = total_h / 2                          # window built about the origin
        view_c = np.array([0.0, top - tab_h - bar_h - view_h / 2, 0.0])
        self.viewport = Rectangle(width=width, height=view_h, stroke_width=0,
                                  fill_color=C["page"], fill_opacity=1.0).move_to(view_c)
        if image is not None and _taller(image, aspect):
            self.page = ImageMobject(_view_pixels(image, width, aspect, 0.0)) \
                .set_width(width).move_to(view_c)
        elif image is not None:
            self.page = _image(image, width).move_to(view_c)
        elif page is not None:
            self.page = page.scale_to_fit_width(width).move_to(view_c)
        else:
            self.page = self.viewport.copy()

        # ── the chrome ───────────────────────────────────────────────────────
        frame = RoundedRectangle(width=width, height=total_h,
                                 corner_radius=RADIUS * width,
                                 fill_color=C["frame"], fill_opacity=1.0,
                                 stroke_color=C["stroke"], stroke_width=1.5)
        strip_c = top - tab_h / 2
        lights = VGroup(*[Circle(radius=tab_h * 0.16, stroke_width=0, fill_color=c,
                                 fill_opacity=1.0) for c in _LIGHTS])
        lights.arrange(RIGHT, buff=tab_h * 0.22)
        lights.move_to([-width / 2 + tab_h * 0.45 + lights.width / 2, strip_c, 0])

        tab_w = width * 0.13
        tab = RoundedRectangle(width=tab_w, height=tab_h * 0.78,
                               corner_radius=tab_h * 0.2,
                               fill_color=C["tab"], fill_opacity=1.0, stroke_width=0)
        tab.move_to([lights.get_right()[0] + tab_h * 0.8 + tab_w / 2,
                     top - tab_h + tab_h * 0.39, 0])
        # squares off the tab's bottom corners, so it joins the toolbar below it
        tab_foot = Rectangle(width=tab_w, height=tab_h * 0.2, stroke_width=0,
                             fill_color=C["tab"], fill_opacity=1.0)
        tab_foot.align_to(tab, DOWN).set_x(tab.get_x())
        self.tab = tab
        self.title = self._title(title)

        toolbar = Rectangle(width=width, height=bar_h, stroke_width=0,
                            fill_color=C["toolbar"], fill_opacity=1.0)
        toolbar.move_to([0, top - tab_h - bar_h / 2, 0])
        omni = RoundedRectangle(width=width * 0.78, height=bar_h * 0.72,
                                corner_radius=bar_h * 0.36,
                                fill_color=C["omnibox"], fill_opacity=1.0, stroke_width=0)
        omni.move_to(toolbar).set_x(-width * 0.02)
        self.omnibox = omni
        self.url = self._url(url)

        self.chrome = Group(frame, lights, tab, tab_foot, self.title, toolbar, omni, self.url)
        # page BELOW the chrome's text and fills, frame behind everything
        self.add(frame, self.viewport, self.page, toolbar, tab_foot, tab, lights,
                 self.title, omni, self.url)

    def _text(self, s, h, color):
        t = crisp_text(s, color=color, font_size=24)
        # size by a reference glyph so every label shares one cap height
        return t.scale(h / crisp_text("H", font_size=24).height)

    def _title(self, s):
        """The tab's label, left-aligned in the tab. A title too long for the tab is
        cut and ends in an ellipsis, as Chrome shows it (a short one is unchanged)."""
        tab_h = TAB_STRIP * self.W
        room = self.tab.width - tab_h * 0.9
        t = self._text(s, tab_h * 0.30, self.C["text"])
        n = len(s)
        while t.width > room and n > 1:
            n -= 1
            t = self._text(s[:n].rstrip() + "\u2026", tab_h * 0.30, self.C["text"])
        return t.move_to(self.tab).align_to(self.tab, LEFT).shift(RIGHT * tab_h * 0.45)

    def _url(self, s):
        bar_h = TOOLBAR * self.W
        t = self._text(s, bar_h * 0.27, self.C["text"]) if s else VGroup()
        if s:
            t.move_to(self.omnibox).align_to(self.omnibox, LEFT).shift(RIGHT * bar_h * 0.6)
        return t

    def type_url(self, scene, url, run_time):
        """Replace the address with `url`, typed in left to right (unused so far)."""
        new = self._url(url)
        old = self.url
        scene.play(FadeOut(old), run_time=run_time * 0.15)
        # letters fade in one at a time (house rule: never manim's Write /
        # AddTextLetterByLetter for text)
        scene.play(LaggedStart(*[FadeIn(ch) for ch in new], lag_ratio=1.0),
                   run_time=run_time * 0.85)
        self.remove(old)
        self.add(new)
        self.url = new

    def swipe_to(self, image, url, title):
        """An Animation: the page slides off to the LEFT and the next one (`image`)
        comes in from the right, INSIDE the viewport only -- the window stays put.
        The address and tab title cross-fade to `url` / `title` (old out over the
        first half, new in over the second). Play it with the caller's run_time:

            self.play(win.swipe_to("b.png", "site.org/b", "B"), run_time=1.0)

        manim has no clipping, so the slide is done in PIXELS: each frame shows a
        viewport-wide crop of the two screenshots side by side. That needs the two
        to be the same pixel size, i.e. the same capture size and a window that has
        not been rescaled since it was built (it raises otherwise)."""
        return _PageSwipe(self, image, url, title)

    def scroll_by(self, screens):
        """An Animation: the page scrolls DOWN `screens` viewport heights (negative
        scrolls up), stopping at the bottom of the screenshot. The window stays put;
        only the page inside it moves. Needs a screenshot taller than the viewport
        (a full-page capture and an `aspect`). Play it with the caller's run_time:

            self.play(win.scroll_by(1.0), run_time=1.5)"""
        return _PageScroll(self, screens)

    def fade_to(self, image):
        """An Animation: the page cross-fades to `image` where it is -- a new STATE
        of the same page (a panel opening, a switch flipping), so the address, the
        title and the scroll position all stay. Same pixel-size rule as
        `swipe_to`."""
        return _PageFade(self, image)

    def page_point(self, x, y):
        """The scene point showing pixel (x, y) of the current SCREENSHOT (in its
        own pixels, as a browser reports an element's box at that capture's zoom),
        wherever the window now is and however it is scaled, scroll included."""
        with Image.open(self.image) as im:
            w = im.width
        rows = w * self.aspect                     # screenshot rows the viewport shows
        y -= self.scroll * rows
        ul = self.viewport.get_corner(UL)
        return ul + np.array([x / w * self.viewport.width,
                              -y / rows * self.viewport.height, 0.0])


def _taller(path, aspect):
    """Whether the screenshot at `path` is taller than a viewport of `aspect`."""
    with Image.open(path) as im:
        return im.height / im.width > aspect + 1e-3


def _view_pixels(path, width, aspect, scroll):
    """The viewport's pixels: the screenshot pre-shrunk for `width` (`_image`), cut
    to a viewport of `aspect`, `scroll` viewport heights down (clamped to the
    bottom). A screenshot no taller than the viewport is returned whole."""
    full = _image(path, width).pixel_array
    rows = round(full.shape[1] * aspect)
    if full.shape[0] <= rows:
        return full
    off = min(round(scroll * rows), full.shape[0] - rows)
    return np.ascontiguousarray(full[off:off + rows])


def _set_page(page, arr):
    """Show `arr` in the page ImageMobject, as its resting pixels (so a later fade
    starts from them)."""
    page.pixel_array = arr.copy()
    page.orig_alpha_pixel_array = arr[:, :, 3].copy()


class _PageScroll(Animation):
    """See `BrowserWindow.scroll_by`."""

    def __init__(self, win, screens, **kwargs):
        if win.image is None or not _taller(win.image, win.aspect):
            raise ValueError("scroll_by needs a screenshot taller than the viewport "
                             "(a full-page capture, and the window's `aspect`)")
        self.win = win
        self.full = _image(win.image, win.W).pixel_array
        self.rows = round(self.full.shape[1] * win.aspect)
        bottom = self.full.shape[0] - self.rows
        self.y0 = min(round(win.scroll * self.rows), bottom)
        self.y1 = max(0, min(round((win.scroll + screens) * self.rows), bottom))
        super().__init__(win.page, **kwargs)

    def _crop(self, y):
        return np.ascontiguousarray(self.full[y:y + self.rows])

    def interpolate_mobject(self, alpha):
        a = self.rate_func(alpha)
        self.mobject.pixel_array = self._crop(round(self.y0 + a * (self.y1 - self.y0)))

    def finish(self):
        super().finish()
        _set_page(self.mobject, self._crop(self.y1))
        self.win.scroll = self.y1 / self.rows


class _PageSwipe(Animation):
    """See `BrowserWindow.swipe_to`."""

    def __init__(self, win, image, url, title, **kwargs):
        self.win = win
        if win.image is None:
            raise ValueError("swipe_to needs a window whose page is a screenshot")
        # the shown page REBUILT from its file at this render's resolution, not its
        # current pixels: a snapshot made at another quality carries those. Both
        # pages are cut to the viewport: the old one where it is scrolled to, the
        # new one at its top.
        old = _view_pixels(win.image, win.W, win.aspect, win.scroll)
        new = _view_pixels(image, win.W, win.aspect, 0.0)
        if new.shape != old.shape:
            raise ValueError(f"swipe_to needs a page the same pixel size as the one "
                             f"shown: {new.shape} vs {old.shape} (same screenshot "
                             f"size, and a window not rescaled since built)")
        self.image = image
        self.new_array = new
        self.strip = np.concatenate([old, new], axis=1)
        self.px = old.shape[1]
        self.old_text = (win.url, win.title)
        self.new_text = (win._url(url), win._title(title))
        super().__init__(win.page, **kwargs)

    def begin(self):
        for t in self.new_text:
            t.set_opacity(0.0)
        self.win.add(*self.new_text)
        super().begin()

    def interpolate_mobject(self, alpha):
        a = self.rate_func(alpha)
        off = round(a * self.px)
        self.mobject.pixel_array = np.ascontiguousarray(self.strip[:, off:off + self.px])
        # the old address and tab title fade out over the first half, the new ones
        # in over the second
        for t in self.old_text:
            t.set_opacity(max(0.0, 1 - 2 * a))
        for t in self.new_text:
            t.set_opacity(max(0.0, 2 * a - 1))

    def finish(self):
        super().finish()
        _set_page(self.mobject, self.new_array)
        self.win.remove(*self.old_text)
        for t in self.new_text:
            t.set_opacity(1.0)
        self.win.url, self.win.title = self.new_text
        self.win.image = self.image
        self.win.scroll = 0.0


class _PageFade(Animation):
    """See `BrowserWindow.fade_to`."""

    def __init__(self, win, image, **kwargs):
        if win.image is None:
            raise ValueError("fade_to needs a window whose page is a screenshot")
        self.win, self.image = win, image
        self.old = _view_pixels(win.image, win.W, win.aspect, win.scroll).astype(np.float32)
        new = _view_pixels(image, win.W, win.aspect, win.scroll)
        if new.shape != self.old.shape:
            raise ValueError(f"fade_to needs a page the same pixel size as the one "
                             f"shown: {new.shape} vs {self.old.shape}")
        self.new = new
        super().__init__(win.page, **kwargs)

    def interpolate_mobject(self, alpha):
        a = self.rate_func(alpha)
        mix = self.old + (self.new.astype(np.float32) - self.old) * a
        self.mobject.pixel_array = mix.round().astype(np.uint8)

    def finish(self):
        super().finish()
        _set_page(self.mobject, self.new)
        self.win.image = self.image


def browser_window(url, title, **kwargs):
    return BrowserWindow(url, title, **kwargs)
