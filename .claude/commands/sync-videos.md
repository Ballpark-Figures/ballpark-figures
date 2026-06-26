---
description: Clone any Ballpark-Figures video repos missing locally and build their .venv (for a second machine, e.g. the desktop)
---

> **⚠️ UNTESTED ON THE DESKTOP / WSL.** This command was authored on the Mac
> laptop and has NOT yet been run on Patrick's WSL desktop. The FIRST time it
> runs successfully on the desktop, DELETE this blockquote note (edit this file
> to remove these lines) and report that it's now been verified on WSL.

Bring a second machine up to date with the `Ballpark-Figures` GitHub org by
cloning any video repos that exist remotely but not locally, then building a
`.venv` for each freshly-cloned repo. Existing local repos are left UNTOUCHED
(no pulls) — clone-missing-only.

The umbrella repo root is the directory containing `bpkfigures/` (and this
`.claude/`). All clones go directly under it, as siblings of `bpkfigures/`.

## Steps

1. **Preflight.** Verify `gh auth status` succeeds. If not, STOP and tell the
   user to run `gh auth login` first. Verify `bpkfigures/` exists at the
   resolved root; if not, STOP and ask where the umbrella root is.

2. **List remote repos.** `gh repo list Ballpark-Figures --limit 100 --json name`
   Skip these NON-video repos: `ballpark-figures` (the umbrella itself) and
   `.github` (org profile). Everything else is a video repo.

3. **Find what's missing.** For each video repo name, check whether
   `<root>/<name>/` already exists locally. Build the list of MISSING ones.
   If none are missing, report "already in sync" and stop.

4. **Clone each missing repo** into `<root>/`:
   `gh repo clone Ballpark-Figures/<name> <root>/<name>`
   (Cloned repos already contain `.vscode/settings.json`, `.gitignore`,
   `animations/`, `math/`, etc. — those were committed, so nothing needs
   re-scaffolding. Only the gitignored `.venv` is absent.)

5. **Build the shared `.venv` for each freshly-cloned repo.** From inside
   `<root>/<name>/`:
   - `python3.14 -m venv .venv` — FALL BACK to `python3` if `python3.14` is
     missing (likely on WSL). REPORT which Python/version each venv used.
   - `.venv/bin/python -m pip install --upgrade pip`
   - `.venv/bin/pip install --upgrade manim scipy` (newest stable; numpy
     arrives via manim)
   - `.venv/bin/pip install -e <root>` (editable shared `bpkfigures`)
   Run installs in the background where possible. If an install fails (e.g. no
   network), do NOT abort the whole sync — report it and print the commands so
   the user can finish that repo later.

6. **Interpreter-path sanity check (WSL).** The committed
   `.vscode/settings.json` points `python.defaultInterpreterPath` at
   `${workspaceFolder}/.venv/bin/python` (unversioned), which exists for any
   Python version — so it should work on WSL as-is. If for some reason a repo's
   settings still reference a versioned `python3.14` that does NOT exist in its
   `.venv/bin/`, flag it so the user can fix the path.

## Finally
Report a short summary: which repos were cloned, which Python/version each
venv used, the installed `manim`/`scipy`/`numpy` versions, and any repos whose
venv install failed (with the manual commands). Remind the user that `.venv`
auto-activates in VS Code terminals and `render` finds it automatically.

If this run was on the desktop/WSL and succeeded, remove the UNTESTED note at
the top of this file.
