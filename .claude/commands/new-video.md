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
  "python.analysis.indexing": false
}
```

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

## Then initialize git
Run `git init` inside `<root>/<name>/`, then `git add -A` and an initial
commit `Scaffold <name> video` (the .gitignore is in place first, so no
artifacts get staged). Do NOT touch the umbrella repo's git or the
bpkfigures repo.

## Finally
Report what was created as a short tree, and remind the user that the
`.venv/` for the new video still needs to be created/linked separately
(it's intentionally not scaffolded). Then open `<name>.code-workspace` is
the user's manual step.
