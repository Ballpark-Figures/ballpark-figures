"""Warn-only style linter for scene files (runs inside `render --check`).

Catches the CONVENTION VIOLATIONS that are mechanical enough to check statically —
the "reached for a raw value" class that prose CLAUDE.md rules rely on the agent
remembering (and that got missed while EDITING this-or-that scene):

  - a raw `Text(...)` / `Paragraph(...)` mobject         -> use crisp_text/crisp_paragraph
  - a hex colour literal ("#B01E43") inlined in a scene  -> name it in style.py / config.py
  - a raw manim palette colour (GREY, RED, …)            -> use a semantic style.py/config.py colour
  - a one-use `run_time` local (`rt = 1.2` … run_time=rt) -> inline the literal at the call site
  - a HELPER method that calls self.play but exposes NO run_time param -> a helper
      that plays takes a run_time the caller passes (@subscene beats are exempt —
      their timing lives inline in the body). Only "no timing knob AT ALL" is flagged;
      multi-knob helpers (rt_write/move_rt/…) satisfy it — the one-vs-many-knobs
      judgment is semantic and stays in CLAUDE.md, not here.
  - a recalled manim DEFAULT frame bound (7.11 / 14.22)  -> read config.frame_x_radius/​y_radius
  - `.scale(...)` chained on a get_scorecard()/get_two_scorecards() -> enters full-size via slide_in
  - a HAND-ROLLED BAR CHART (fill-only `Rectangle` bars with a data-driven
      height/width, built in a loop) -> use bpkfigures.histogram.get_histogram
      (ink_color=CHALK for dark/chalkboard scenes) / bar_graph.get_bar_graph

It is WARN-ONLY: it never changes the exit code and never blocks a render. The
judgment-based conventions still live in CLAUDE.md; this only mechanises the few
that a static check can catch with near-zero false positives. Lints SCENE files
only (assets/ legitimately define colours + use the text helpers).
"""
import ast
import re

# manim palette constants that should instead come from style.py / the video's
# config.py (a semantic name). BLACK and WHITE are universally fine, so excluded.
_RAW_COLOR_RE = re.compile(
    r"^(RED|GREEN|BLUE|YELLOW|GOLD|ORANGE|PURPLE|PINK|TEAL|MAROON|GREEN_SCREEN"
    r"|GREY|GRAY|GREY_BROWN|GRAY_BROWN|PURE_RED|PURE_GREEN|PURE_BLUE"
    r"|DARK_BLUE|DARK_BROWN|LIGHT_BROWN|LIGHT_PINK"
    r"|LIGHT_GREY|LIGHT_GRAY|DARK_GREY|DARK_GRAY|DARKER_GREY|DARKER_GRAY)"
    r"(_[A-E])?$")
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RAW_TEXT = {"Text", "Paragraph", "MarkupText"}
# manim's DEFAULT frame half-width (7.11) and full-width (14.22). This repo's
# frame is 16×9 (x-radius 8.0, y-radius 4.5), so these values are only ever a
# mis-recalled default — the exact scene-06 bug (a correct ruler at the wrong
# zero). Matched with a small tolerance to catch 7.1111…/14.2222…. NB the CORRECT
# bounds (8.0/4.5/4.0) are NOT flagged — far too common as ordinary positions to
# check without swamping the linter; the rule is "read them from config", but a
# static check can only catch the unambiguous wrong-default smell.
_FRAME_DEFAULT_BOUNDS = (7.11, 14.22)
# scorecard factories whose result must NOT be `.scale()`d — they enter full-size
# at canonical centres via slide_in / slide_two_in (a scaled card read tiny).
_SCORECARD_FACTORIES = {"get_scorecard", "get_two_scorecards"}
_LOOPS = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp,
          ast.GeneratorExp)
# decorators whose method's timing lives INLINE in the body by design (a @subscene
# is invoked with no args; @thumbnail/@still are static) — exempt from "needs a
# run_time param". A helper called BY a subscene is not exempt.
_EXEMPT_DECOS = {"subscene", "thumbnail", "still"}
# a parameter name that counts as a timing knob: the run_time family only. dur/
# fade/speed/t are deliberately NOT accepted — the convention calls those "the smell
# to fix" (rename to run_time), so a helper exposing only those SHOULD still flag.
_TIMING_PARAM_RE = re.compile(r"^(rt|run_time|.*_rt|rt_.*|.*_run_time)$")


class _Linter(ast.NodeVisitor):
    def __init__(self, local_names=()):
        self.warnings = []                       # list of (lineno, message)
        self.local = set(local_names)            # names ASSIGNED in this file (a
        #   local `GRAY = "#…"` constant is not manim's palette — its hex def is
        #   flagged where it's written, so don't also flag every use of the name)
        self._loop_depth = 0                     # >0 while visiting inside a loop
        #   (so a `Rectangle(...)` bar built per-iteration can be recognised)
        self._class_stack = []                   # enclosing class names (for the
        #   ClassName.attr snapshot-digest footgun check)

    def _warn(self, lineno, msg):
        self.warnings.append((lineno, msg))

    # ── raw text mobjects  +  scaled scorecard factory ───────────────────────
    def visit_Call(self, node):
        f = node.func
        name = (f.id if isinstance(f, ast.Name) else
                f.attr if isinstance(f, ast.Attribute) else None)
        if name in _RAW_TEXT:
            self._warn(node.lineno,
                       f"raw {name}(...) — use crisp_text/crisp_paragraph "
                       f"(bpkfigures.style), never a bare manim text mobject")
        # a fill-only Rectangle with a DATA-DRIVEN height/width, built in a loop =
        # a hand-rolled bar chart -> the shared histogram/bar-graph asset
        if name == "Rectangle" and self._loop_depth > 0:
            self._check_hand_rolled_bar(node)
        # `.scale(...)` chained DIRECTLY on a scorecard factory call
        if (name == "scale" and isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Call)):
            inner = f.value.func
            inner_name = (inner.id if isinstance(inner, ast.Name) else
                          inner.attr if isinstance(inner, ast.Attribute) else None)
            if inner_name in _SCORECARD_FACTORIES:
                self._warn(node.lineno,
                           f"{inner_name}(...).scale(...) — a scorecard enters "
                           f"FULL size at its canonical centre via slide_in / "
                           f"slide_two_in; don't .scale() it (it reads tiny)")
        self.generic_visit(node)

    # ── loop tracking (so a per-iteration Rectangle bar is recognisable) ──────
    def _visit_loop(self, node):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    visit_For = _visit_loop
    visit_While = _visit_loop
    visit_ListComp = _visit_loop
    visit_SetComp = _visit_loop
    visit_DictComp = _visit_loop
    visit_GeneratorExp = _visit_loop

    def _check_hand_rolled_bar(self, node):
        """`node` is a `Rectangle(...)` call inside a loop. Flag it as a hand-rolled
        bar iff it's fill-only (`stroke_width=0`) AND at least one of its height/
        width is DATA-DRIVEN (not a numeric literal) — the bar idiom. A fixed-size
        rectangle grid (both dims literal) is left alone."""
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        sw = kw.get("stroke_width")
        if not (isinstance(sw, ast.Constant) and sw.value == 0):
            return
        def data_driven(v):
            return v is not None and not (isinstance(v, ast.Constant)
                                          and isinstance(v.value, (int, float))
                                          and not isinstance(v.value, bool))
        if data_driven(kw.get("height")) or data_driven(kw.get("width")):
            self._warn(node.lineno,
                       "hand-rolled bar chart (fill-only Rectangle bars in a loop) — "
                       "use bpkfigures.histogram.get_histogram (ink_color=CHALK for "
                       "dark/chalkboard scenes) or bar_graph.get_bar_graph; if the "
                       "shared helper lacks a knob, ADD the param, don't rebuild")

    # ── inline hex colours  +  recalled default frame bounds ──────────────────
    def visit_Constant(self, node):
        if isinstance(node.value, str) and _HEX_RE.match(node.value):
            self._warn(node.lineno,
                       f"hex colour {node.value!r} inlined — name it in style.py / "
                       f"the video's config.py, don't hardcode a hex in a scene")
        elif (isinstance(node.value, float)
              and any(abs(node.value - b) < 0.01 for b in _FRAME_DEFAULT_BOUNDS)):
            self._warn(node.lineno,
                       f"{node.value} looks like manim's DEFAULT frame bound — this "
                       f"repo's frame is 16×9 (x-radius 8.0, y-radius 4.5). Read "
                       f"config.frame_x_radius / frame_y_radius, never a recalled default")
        self.generic_visit(node)

    # ── snapshot-digest footgun: referencing the scene class BY NAME ──────────
    def visit_ClassDef(self, node):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Attribute(self, node):
        """Flag ``ClassName.attr`` inside ClassName's own body. Naming the class makes the
        snapshot digest hash ``inspect.getsource`` of the WHOLE class, so editing ANY method
        re-keys every subscene reaching this one (looks like random mass-invalidation). Read
        a class attr via ``self.attr``; keep TUNABLE constants at MODULE level (captured by
        value). See CLAUDE.md 'CLASS attributes are the blind spot'."""
        if isinstance(node.value, ast.Name) and node.value.id in self._class_stack:
            self._warn(node.lineno,
                       f"{node.value.id}.{node.attr} — referencing the scene class by NAME "
                       f"inside its own body poisons the snapshot digest (hashes the WHOLE "
                       f"class source, so editing any beat re-renders every subscene). Read "
                       f"it via self.{node.attr}; keep tunable constants at MODULE level")
        self.generic_visit(node)

    # ── raw manim palette colours ────────────────────────────────────────────
    def visit_Name(self, node):
        if (isinstance(node.ctx, ast.Load) and node.id not in self.local
                and _RAW_COLOR_RE.match(node.id)):
            self._warn(node.lineno,
                       f"raw manim colour {node.id} — pull a semantic colour from "
                       f"style.py / config.py (ACCENT_*, SCORE_*, …), not the palette")
        self.generic_visit(node)

    # ── one-use run_time locals ──────────────────────────────────────────────
    def visit_FunctionDef(self, node):
        self._check_run_time_locals(node)
        self._check_play_run_time(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    # ── a helper that plays but takes no run_time ─────────────────────────────
    def _check_play_run_time(self, fn):
        """Flag a method that calls self.play in its OWN body but exposes no run_time-
        family parameter. @subscene/@thumbnail/@still (and setup_scene) are exempt —
        their timing is inline literals by design. A nested closure that plays is its
        own FunctionDef (checked on its own visit), so only DIRECT plays count here."""
        decos = set()
        for d in fn.decorator_list:
            if isinstance(d, ast.Name):
                decos.add(d.id)
            elif isinstance(d, ast.Attribute):
                decos.add(d.attr)
            elif isinstance(d, ast.Call):
                g = d.func
                decos.add(g.id if isinstance(g, ast.Name)
                          else g.attr if isinstance(g, ast.Attribute) else None)
        if decos & _EXEMPT_DECOS or fn.name == "setup_scene":
            return
        if not self._plays_directly(fn):
            return
        a = fn.args
        params = [p.arg for p in (a.posonlyargs + a.args + a.kwonlyargs)]
        if any(_TIMING_PARAM_RE.match(p) for p in params):
            return
        self._warn(fn.lineno,
                   f"helper `{fn.name}` calls self.play but exposes no run_time "
                   f"parameter — a helper that plays takes a run_time the caller "
                   f"passes (scale each sub-play by it); @subscene beats are exempt")

    def _plays_directly(self, fn):
        """True iff `fn`'s OWN body calls self.play / scene.play, NOT counting plays
        inside a nested def/lambda (those are separate scopes, checked separately)."""
        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    continue
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "play"
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id in ("self", "scene")):
                    return True
                if walk(child):
                    return True
            return False
        return walk(fn)

    def _check_run_time_locals(self, fn):
        """Flag `name = <number>` where `name` is used EXACTLY once and that use is a
        `run_time=` kwarg NOT inside a loop (a loop is the sanctioned lockstep case —
        one local driving many same-length plays; several textual uses likewise)."""
        assigned = {}                            # name -> lineno of its assignment
        for n in ast.walk(fn):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, (int, float))
                    and not isinstance(n.value.value, bool)):
                assigned[n.targets[0].id] = n.lineno
        if not assigned:
            return
        loads = {}                               # name -> total Load occurrences
        rt_names = {}                            # name -> any run_time= use in a loop?
        for child, in_loop in self._descend(fn):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                loads[child.id] = loads.get(child.id, 0) + 1
            if (isinstance(child, ast.keyword) and child.arg == "run_time"
                    and isinstance(child.value, ast.Name)):
                rt_names[child.value.id] = rt_names.get(child.value.id, False) or in_loop
        for name, lineno in assigned.items():
            if name in rt_names and not rt_names[name] and loads.get(name, 0) == 1:
                self._warn(lineno,
                           f"one-use run_time local `{name}` — inline the literal at "
                           f"the run_time= call site (a named local is only for a "
                           f"lockstep loop)")

    def _descend(self, node, in_loop=False):
        """Yield (descendant, is-inside-a-loop) for every node under `node`."""
        for child in ast.iter_child_nodes(node):
            yield child, in_loop
            yield from self._descend(child, in_loop or isinstance(child, _LOOPS))


def _assigned_names(tree):
    """Every name ASSIGNED anywhere in the module (so a scene-local colour constant
    named like a manim palette entry isn't mistaken for the palette itself)."""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
    return names


def lint_file(path):
    """Return sorted, de-duplicated (lineno, message) style warnings for one scene
    file. Returns [] on a syntax error (the caller's parse reports those)."""
    with open(path) as f:
        src = f.read()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError:
        return []
    linter = _Linter(_assigned_names(tree))
    linter.visit(tree)
    return sorted(set(linter.warnings))
