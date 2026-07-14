"""Warn-only style linter for scene files (runs inside `render --check`).

Catches the CONVENTION VIOLATIONS that are mechanical enough to check statically —
the "reached for a raw value" class that prose CLAUDE.md rules rely on the agent
remembering (and that got missed while EDITING this-or-that scene):

  - a raw `Text(...)` / `Paragraph(...)` mobject         -> use crisp_text/crisp_paragraph
  - a hex colour literal ("#B01E43") inlined in a scene  -> name it in style.py / config.py
  - a raw manim palette colour (GREY, RED, …)            -> use a semantic style.py/config.py colour
  - a one-use `run_time` local (`rt = 1.2` … run_time=rt) -> inline the literal at the call site

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
_LOOPS = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp,
          ast.GeneratorExp)


class _Linter(ast.NodeVisitor):
    def __init__(self, local_names=()):
        self.warnings = []                       # list of (lineno, message)
        self.local = set(local_names)            # names ASSIGNED in this file (a
        #   local `GRAY = "#…"` constant is not manim's palette — its hex def is
        #   flagged where it's written, so don't also flag every use of the name)

    def _warn(self, lineno, msg):
        self.warnings.append((lineno, msg))

    # ── raw text mobjects ────────────────────────────────────────────────────
    def visit_Call(self, node):
        f = node.func
        name = (f.id if isinstance(f, ast.Name) else
                f.attr if isinstance(f, ast.Attribute) else None)
        if name in _RAW_TEXT:
            self._warn(node.lineno,
                       f"raw {name}(...) — use crisp_text/crisp_paragraph "
                       f"(bpkfigures.style), never a bare manim text mobject")
        self.generic_visit(node)

    # ── inline hex colours ───────────────────────────────────────────────────
    def visit_Constant(self, node):
        if isinstance(node.value, str) and _HEX_RE.match(node.value):
            self._warn(node.lineno,
                       f"hex colour {node.value!r} inlined — name it in style.py / "
                       f"the video's config.py, don't hardcode a hex in a scene")
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
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

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
