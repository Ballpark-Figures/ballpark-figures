import ast
import glob
import os
import re
import sys

def _snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

# ── subscene labels ───────────────────────────────────────────────────────────
# Index (0-based) <-> label. First 26 are a..z; past that we prepend another 'z'
# (the maximal letter) to a single trailing a..z: za..zz, then zza..zzz, etc.
# This keeps labels in LEXICOGRAPHIC order (a<b<...<z<za<...<zz<zza<...), so the
# rendered NN<label>_*.mp4 files sort into scene order in a file listing. (Plain
# a..z,aa,ab would put "aa" before "b".) 26 single + 26 z*+letter = 52 before a
# 3rd tier — see yahtzee scene 06 (38 subscenes: a..z, za..zl).
def index_to_label(i):
    return "z" * (i // 26) + chr(ord("a") + i % 26)

def label_to_index(label):
    if not label or not label.isalpha() or not label.islower() \
            or label[:-1] != "z" * (len(label) - 1):
        raise ValueError(f"bad subscene label {label!r} "
                         f"(want (tier) leading 'z's + one a-z, e.g. 'zl')")
    return 26 * (len(label) - 1) + (ord(label[-1]) - ord("a"))

def _find_file(prefix):
    matches = sorted(glob.glob(f"{prefix}*.py"))
    if not matches:
        raise FileNotFoundError(f"No file matching {prefix}*.py in {os.getcwd()}")
    return matches[0]

def _parse(path):
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        subs = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for dec in item.decorator_list:
                    # @thumbnail is a subscene too (independent static frame) — it
                    # shares the NNa/NNb addressing, so count it like @subscene.
                    name = dec.id if isinstance(dec, ast.Name) else \
                        dec.attr if isinstance(dec, ast.Attribute) else None
                    if name in ("subscene", "thumbnail"):
                        subs.append(item.name)
        inherits = any(
            (isinstance(b, ast.Name) and b.id == "BpkScene") or
            (isinstance(b, ast.Attribute) and b.attr == "BpkScene")
            for b in node.bases
        )
        if subs or inherits:
            return node.name, subs
    raise ValueError(f"No BpkScene subclass found in {path}")

def resolve(target):
    prefix, letter = target[:2], target[2:]
    path = _find_file(prefix)
    classname, subs = _parse(path)
    if not letter:
        return path, classname, f"{prefix}_{_snake(classname)}", ""
    idx = label_to_index(letter)
    if not (0 <= idx < len(subs)):
        raise IndexError(f"Subscene '{letter}' out of range for {path}")
    return path, classname, f"{prefix}{letter}_{subs[idx]}", letter

def subscene_letters(prefix):
    """The subscene labels (['a','b',...,'z','za',...]) defined in the
    NN-prefixed scene file, in order. Empty list if the scene has no @subscene
    methods."""
    path = _find_file(prefix)
    _classname, subs = _parse(path)
    return [index_to_label(i) for i in range(len(subs))]

def clean_stale(classname, prefix, letter, keep_output):
    """Remove stale rendered videos for this NN<letter> slot whose subscene was
    renamed/reordered (e.g. an old 01b_all_outcomes.mp4 left behind when 01b is
    now 01b_pairs). Keeps `keep_output`. Scans every quality dir under the
    scene's media/videos/<scene_module>/ folder AND the parallel
    media/padded_videos/<scene_module>/ tree (--padded copies). Returns the files
    removed."""
    # main renders live under media/videos/<stem>/<quality>/<output>.mp4; --padded
    # copies mirror them under media/padded_videos/<stem>/<quality>/ (see
    # render._pad_video). Sweep BOTH so a renamed beat's stale padded copy is
    # removed too — not just its videos/ one.
    stem = _find_file(prefix)[:-3]  # NNname.py -> NNname
    slot = f"{prefix}{letter}_" if letter else f"{prefix}_"
    removed = []
    for tree in ("videos", "padded_videos"):
        base = os.path.join("media", tree, stem)
        for quality_dir in glob.glob(os.path.join(base, "*")):
            for mp4 in glob.glob(os.path.join(quality_dir, f"{slot}*.mp4")):
                name = os.path.basename(mp4)[:-4]
                if name != keep_output:
                    try:
                        os.remove(mp4)
                        removed.append(mp4)
                    except OSError:
                        pass
    return removed

def main():
    args = sys.argv[1:]
    do_clean = "--clean" in args
    args = [a for a in args if a != "--clean"]
    try:
        path, classname, output, letter = resolve(args[0])
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if do_clean:
        prefix = args[0][:2]
        for f in clean_stale(classname, prefix, letter, output):
            print(f"[resolve] removed stale {f}", file=sys.stderr)
    print(f"{path}\t{classname}\t{output}\t{letter}")

if __name__ == "__main__":
    main()