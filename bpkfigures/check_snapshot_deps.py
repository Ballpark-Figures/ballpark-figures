"""GATE for the snapshot source hash: the static import closure must cover what a
scene REALLY imports.

    cd <video>/animations/scenes
    python -m bpkfigures.check_snapshot_deps            # every scene file here
    python -m bpkfigures.check_snapshot_deps 12 07      # just these

The snapshot key hashes only `scene._import_closure` of the scene file — the
project files it can import, found by reading import statements. If that walk
MISSED a file the scene really loads, editing that file would leave a stale
snapshot valid: a wrong render, silently. So each scene is imported for real in a
fresh interpreter (module top level only — nothing renders), and every project
file then in sys.modules must be in the closure. The closure may be LARGER (a lazy
import not yet run, a branch not taken); only a file missing from it is a failure.

Exits nonzero on any miss. Run it after touching `_import_closure`, and on a
video whose scenes do unusual imports (importlib, exec, sys.path tricks).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))

PROBE = r"""
import importlib.util, json, os, sys
scene = os.path.realpath(sys.argv[1])
sys.path.insert(0, os.path.dirname(scene))
spec = importlib.util.spec_from_file_location("_probe_scene", scene)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
files = sorted({os.path.realpath(m.__file__) for m in list(sys.modules.values())
                if getattr(m, "__file__", None)})
print(json.dumps(files))
"""


def main(argv):
    sys.path.insert(0, os.path.dirname(HERE))
    from bpkfigures import scene as S
    scenes_dir = os.getcwd()
    animations = os.path.dirname(scenes_dir)
    roots = [S._BPK_DIR, animations]
    search = [animations, os.path.dirname(S._BPK_DIR)]
    under = lambda p: any(p.startswith(os.path.realpath(r) + os.sep) for r in roots)
    names = sorted(f for f in os.listdir(scenes_dir)
                   if f.endswith(".py") and f[:2].isdigit()
                   and (not argv or f[:2] in argv))
    siblings = {os.path.realpath(os.path.join(scenes_dir, f))
                for f in os.listdir(scenes_dir) if f.endswith(".py")}
    bad = checked = 0
    for name in names:
        path = os.path.join(scenes_dir, name)
        p = subprocess.run([sys.executable, "-c", PROBE, path], cwd=scenes_dir,
                           capture_output=True, text=True)
        if p.returncode:
            print(f"  SKIP {name}: does not import cleanly\n{p.stderr[-400:]}")
            continue
        loaded = {f for f in json.loads(p.stdout.strip().splitlines()[-1])
                  if under(f)} - siblings
        closure = S._import_closure(path, roots, search)
        missing = loaded - closure
        checked += 1
        if missing:
            bad += 1
            print(f"  FAIL {name}: loaded but not in the closure:")
            for f in sorted(missing):
                print(f"         {f}")
        else:
            print(f"  ok   {name}: {len(loaded)} project files loaded, "
                  f"closure {len(closure)}")
    if not checked:
        print("no scene was checked")
        return 1
    print(f"\n{checked} scenes checked, {bad} with a missed dependency")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
