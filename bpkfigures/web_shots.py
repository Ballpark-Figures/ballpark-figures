"""Screenshot web pages for browser mocks (`browser.py`): the engine, shared by videos.

Promoted 2026-11-15 from wordle's `animations/assets/web_shots.py` for its second user,
wheel-of-fortune. Wordle is shipped and keeps its own copy (promotions are forward-only).
A video keeps only its RECIPES, in its own `animations/assets/web_shots.py`:

    from bpkfigures.web_shots import main
    OUT = Path(__file__).resolve().parent / "web_media"
    RECIPES = {"name": ("https://...", [steps], {options})}
    if __name__ == "__main__":
        main(RECIPES, OUT)

    .venv/bin/python animations/assets/web_shots.py            # every recipe
    .venv/bin/python animations/assets/web_shots.py name       # just one
    .venv/bin/python animations/assets/web_shots.py --list     # the recipes

Drives the Google Chrome already installed on this machine through Playwright
(`channel="chrome"`), so no browser is downloaded. A recipe is a URL plus the clicks
that get to the state to capture.

Output: `<out>/<name>.png`, 1920x1080 unless `--size` says otherwise, dark colour scheme
requested (a site with no dark mode stays light) unless a recipe names its own (the
recipe's options dict, which can also set a page zoom and a full-page capture).

A recipe with `shot` steps saves THOSE, as `<name>_<shot>.png`, and no final
screenshot -- several states of one page from one session. `box` steps write
`<name>_boxes.json`: each named element's box in SCREENSHOT PIXELS (zoom applied),
`[left, top, right, bottom]`, so a scene can aim at it without eyeballing.

Steps (a Playwright locator description each):
  ("text", "Play")        click the first visible element whose text is exactly that
  ("frame", url_part)     switch into the iframe whose url contains url_part
  ("click", css)          click the first visible element matching a CSS selector
  ("key", "Escape")       press a key
  ("hide", css)           hide every element matching a CSS selector (display: none)
  ("shot", name)          save a screenshot now, as <recipe>_<name>.png
  ("box", css, name)      record that element's box, into <recipe>_boxes.json
Options (all optional): scheme ("dark"), zoom (1.0), full_page (False).

Requests to known ad hosts are dropped, so no ad lands in a screenshot (a real ad
would put a third party's creative in the video).

A screenshot is a POINT-IN-TIME capture of a live site, so re-running replaces it;
nothing here is computed. A recipe that stops finding its click target FAILS LOUDLY
rather than saving the wrong state under the recipe's name.

macOS only in practice (it needs Chrome.app); `playwright` is the one dependency, in
the video's own venv.
"""
import argparse
import json
import sys
from pathlib import Path

VIEW = {"width": 1920, "height": 1080}
SETTLE_MS = 4000

# Substring match on the request's host.
AD_HOSTS = ("doubleclick", "googlesyndication", "googleadservices", "adservice",
            "amazon-adsystem", "adnxs", "rubiconproject", "pubmatic", "openx",
            "criteo", "taboola", "outbrain", "moatads", "teads", "casalemedia",
            "33across", "sharethrough", "indexww", "adsrvr", "smartadserver",
            "gumgum", "media.net", "yieldmo", "triplelift", "lijit", "sovrn",
            "adform", "springserve", "pubnation", "kargo", "connatix", "freestar",
            "googletagservices", "securepubads", "ad-delivery", "adsafeprotected")


def _block_ads(route):
    host = route.request.url.split("/")[2] if "://" in route.request.url else ""
    if any(a in host for a in AD_HOSTS):
        return route.abort()
    return route.continue_()


def _run(name, url, steps, browser, out, full_page=False, view=VIEW, scheme="dark",
         zoom=1.0):
    # zoom: lay the page out in a window 1/zoom the size, at zoom x the pixel
    # density, so the capture keeps `view`'s pixel size with everything bigger
    css = {"width": round(view["width"] / zoom), "height": round(view["height"] / zoom)}
    ctx = browser.new_context(viewport=css, device_scale_factor=zoom,
                              color_scheme=scheme)
    ctx.route("**/*", _block_ads)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(SETTLE_MS)
        scope = page
        shots, boxes = [], {}
        for kind, arg, *more in steps:
            if kind == "frame":
                frames = [f for f in page.frames if arg in f.url]
                if not frames:
                    raise RuntimeError(f"no iframe matching {arg!r}")
                scope = frames[0]
            elif kind == "text":
                loc = scope.get_by_text(arg, exact=True).locator("visible=true").first
                loc.click(timeout=15000)
                page.wait_for_timeout(SETTLE_MS)
            elif kind == "click":
                scope.locator(arg).locator("visible=true").first.click(timeout=15000)
                page.wait_for_timeout(SETTLE_MS)
            elif kind == "key":
                page.keyboard.press(arg)
                page.wait_for_timeout(SETTLE_MS)
            elif kind == "hide":
                if scope.locator(arg).count() == 0:
                    raise RuntimeError(f"nothing to hide matching {arg!r}")
                scope.add_style_tag(content=f"{arg} {{ display: none !important; }}")
                page.wait_for_timeout(1000)
            elif kind == "shot":
                out.mkdir(exist_ok=True)
                path = out / f"{name}_{arg}.png"
                page.screenshot(path=str(path), full_page=full_page)
                shots.append(path)
            elif kind == "box":
                r = scope.locator(arg).locator("visible=true").first.bounding_box(timeout=15000)
                if r is None:
                    raise RuntimeError(f"no box for {arg!r}")
                boxes[more[0]] = [round(v * zoom, 1) for v in
                                  (r["x"], r["y"], r["x"] + r["width"], r["y"] + r["height"])]
            else:
                raise ValueError(kind)
        out.mkdir(exist_ok=True)
        if not shots:
            path = out / f"{name}.png"
            page.screenshot(path=str(path), full_page=full_page)
            shots.append(path)
        if boxes:
            path = out / f"{name}_boxes.json"
            path.write_text(json.dumps(boxes, indent=2) + "\n")
            shots.append(path)
        for path in shots:
            print(f"  ok   {name:13s} {path.relative_to(out.parent.parent)}")
        # the address and tab title a browser mock shows, read off the live page
        print(f"       {'':13s} url {page.url}   title {page.title()!r}")
        return True
    except Exception as e:
        print(f"  FAIL {name:13s} {type(e).__name__}: {str(e).splitlines()[0]}")
        return False
    finally:
        ctx.close()


def main(recipes, out, argv=None):
    """Capture `recipes` (name -> (url, steps[, options])) into the folder `out`."""
    from playwright.sync_api import sync_playwright

    out = Path(out)
    ap = argparse.ArgumentParser(description="Screenshot the pages shown in browser mocks.")
    ap.add_argument("names", nargs="*", help=f"subset of: {' '.join(recipes)}")
    ap.add_argument("--size", default="1920x1080",
                    help="browser viewport WxH in px (default 1920x1080)")
    ap.add_argument("--full-page", action="store_true",
                    help="capture the whole scrolling page, not just the window")
    ap.add_argument("--list", action="store_true", help="print the recipes and stop")
    a = ap.parse_args(argv)
    if a.list:
        for g, (u, s, *opts) in recipes.items():
            print(f"{g:13s} {u}  {s}  {opts[0] if opts else ''}")
        return
    bad = [g for g in a.names if g not in recipes]
    if bad:
        sys.exit(f"unknown recipe(s): {bad}; known: {list(recipes)}")
    todo = a.names or list(recipes)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        w, h = (int(x) for x in a.size.lower().split("x"))
        ok = []
        for g in todo:
            url, steps, *opts = recipes[g]
            opts = dict(opts[0]) if opts else {}
            full = a.full_page or opts.pop("full_page", False)
            ok.append(_run(g, url, steps, browser, out, full,
                           {"width": w, "height": h}, **opts))
        browser.close()
    if not all(ok):
        sys.exit(1)
