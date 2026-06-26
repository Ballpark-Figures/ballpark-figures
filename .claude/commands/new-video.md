---
description: Scaffold a new Ballpark-Figures video directory (git repo + math/ + animations/)
argument-hint: <video-name>
---

Scaffold a new video sub-project in the Ballpark-Figures umbrella repo.

The video name is: **$1**

If `$1` is empty, ask the user for the video name (a short lowercase
kebab-case directory name, e.g. `chess` or `connect-four`) before doing
anything. Derive a PascalCase form for the Scene class (e.g. `chess` →
`Chess`, `connect-four` → `ConnectFour`).

The umbrella repo root is the directory CONTAINING `bpkfigures/` (the same
level as `yahtzee/`). Resolve it; create everything relative to it. Below,
`<name>` is `$1` and `<Name>` is the PascalCase class prefix.

## Refuse-and-stop guards
- If `<name>/` already exists, STOP and tell the user — do not overwrite.
- If `bpkfigures/` is not found at the resolved root, STOP and ask where the
  umbrella root is.

## Create this exact structure
```
<root>/<name>/
  .gitignore
  CLAUDE.md
  .vscode/settings.json
  math/data/.gitkeep
  math/notebooks/.gitkeep
  animations/config.py
  animations/manim.cfg
  animations/assets/__init__.py
  animations/scenes/__init__.py
  animations/scenes/manim.cfg
<root>/<name>.code-workspace
```

`.gitkeep` files exist only so the empty `data/`/`notebooks/` dirs are
tracked; create them empty.

### `<name>/CLAUDE.md`
```markdown
# <name> video — specifics

<name>-only conventions. The shared cross-video rules live in
`bpkfigures/CLAUDE.md` (auto-loaded since bpkfigures is always in the workspace).

## Script
- `animations/Script.md` is the video script. Scenes become
  `scenes/NN<name>.py`. (Fill in this video's script/scene conventions.)

## Gameplay layout
- (Describe this video's on-screen layout and the assets in `animations/assets/`.)

## Style
- Uses `bpkfigures` style + the local `config.py` for colors/fonts.
```

### `<name>/.gitignore`
Generic — ignores build artifacts, keeps ALL of `math/data/` tracked (no
game-specific keep-rules; the user adds those per video as needed):
```gitignore
# Python/cache files
**/__pycache__/
*.pyc

# Virtual environments
.venv/
venv/

# Manim / generated media (never commit renders)
media/
**/media/
*.mp4
*.mov
*.wav
*.mp3

# Manim snapshot cache (build artifact, 50+ MB pickles). Scoped to the
# animations tree so it does NOT touch tracked solver .pkl files in math/data/.
animations/**/cache/

# OS / editor junk
.DS_Store

# Ignore notebook checkpoints
**/.ipynb_checkpoints/
```

### `<name>/.vscode/settings.json`
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python3.14",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/animations"
  ],
  "files.watcherExclude": {
    "**/.venv/**": true,
    "**/__pycache__/**": true,
    "**/media/**": true,
    "**/cache/**": true
  },
  "search.exclude": {
    "**/.venv/**": true,
    "**/__pycache__/**": true,
    "**/media/**": true,
    "**/cache/**": true
  },
  "python.analysis.exclude": [
    "**/.venv",
    "**/__pycache__",
    "**/media",
    "**/cache"
  ],
  "python.analysis.diagnosticMode": "openFilesOnly",
  "python.analysis.indexing": false,
  "python.terminal.activateEnvironment": true
}
```
A single shared `.venv` at the project root serves BOTH animations and math.
`python.terminal.activateEnvironment` auto-activates it in VS Code terminals
opened anywhere in the project (including `math/`).

### `<name>/animations/config.py`
```python
from bpkfigures.scene import *


class <Name>Scene(BpkScene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        super().construct()
```

### `<name>/animations/manim.cfg` AND `<name>/animations/scenes/manim.cfg`
(identical — create both):
```ini
[CLI]
frame_rate = 30
pixel_height = 1080
pixel_width = 1920
frame_height = 9
frame_width = 16
background_color = BLACK
background_opacity = 1
scene_names = Default
max_files_cached = 1000
```

### `<name>/animations/assets/__init__.py` and `<name>/animations/scenes/__init__.py`
Empty files.

### `<root>/<name>.code-workspace`
```json
{
  "folders": [
    { "path": "<name>", "name": "<name>" },
    { "path": "bpkfigures", "name": "bpkfigures (shared)" }
  ],
  "settings": {
    "files.exclude": {
      "**/__pycache__": true,
      "**/*.pyc": true,
      "**/.venv": true,
      "**/media": true,
      "**/cache": true
    },
    "search.exclude": {
      "**/.venv": true,
      "**/media": true,
      "**/cache": true
    }
  }
}
```

## Create the shared venv and install packages
ONE shared `.venv` at `<root>/<name>/.venv` serves both animations and math.
From inside `<root>/<name>/`:
1. `python3.14 -m venv .venv` (fall back to `python3` if `python3.14` is
   missing; report which Python was used).
2. `.venv/bin/python -m pip install --upgrade pip`
3. `.venv/bin/pip install --upgrade manim scipy` — NEWEST STABLE versions
   (no pins; `numpy` arrives as a manim dependency).
4. `.venv/bin/pip install -e <root>` — editable install of the shared
   `bpkfigures` package so edits to shared code take effect live.

This downloads ~500 MB and takes a few minutes. Run installs in the
background if possible and surface the final versions of `manim`/`scipy`/
`numpy` (`.venv/bin/pip show`) in the completion report. If an install
step fails (e.g. no network), do NOT abort the whole scaffold — report the
failure and print the exact commands so the user can finish it later.

## Then initialize git
Run `git init` inside `<root>/<name>/`, then `git add -A` and an initial
commit `Scaffold <name> video`. The `.gitignore` (which excludes `.venv/`)
is in place first, so neither the venv nor any artifact gets staged. Do NOT
touch the umbrella repo's git or the bpkfigures repo.

## Create the PRIVATE GitHub remote
All videos live under the `Ballpark-Figures` GitHub org and start PRIVATE
(made public manually on release). After the initial commit, from inside
`<root>/<name>/`:
```
gh repo create Ballpark-Figures/<name> --private --source=. --remote=origin --push
```
This creates the private repo, links it as `origin` (HTTPS, matching the
other repos), and pushes. Guards:
- If `gh` is NOT installed or NOT authenticated (`gh auth status` fails), do
  NOT abort — skip this step and print the exact command above so the user
  can run it later.
- If the repo already exists on GitHub or creation fails for any reason,
  report it and print the manual command; leave the local repo intact.

## Finally
Report what was created as a short tree, plus the installed
`manim`/`scipy`/`numpy` versions and the GitHub repo URL (or the skip
notice). Note that:
- Opening `<name>.code-workspace` is the user's manual step.
- The shared `.venv` auto-activates in VS Code terminals (and is found
  automatically by the `render` script) — no manual activation needed.
- On RELEASE, flip the repo public with:
  `gh repo visibility public --repo Ballpark-Figures/<name>`
