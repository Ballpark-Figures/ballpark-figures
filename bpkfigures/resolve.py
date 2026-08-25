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
        subs, still = [], set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for dec in item.decorator_list:
                    # @still (independent static frame) and its @thumbnail
                    # specialization are subscenes too — they share the NNa/NNb
                    # addressing, so count them like @subscene. Track the @still ones
                    # separately: those render as a STILL IMAGE (a PNG), not a video.
                    name = dec.id if isinstance(dec, ast.Name) else \
                        dec.attr if isinstance(dec, ast.Attribute) else None
                    if name in ("subscene", "thumbnail", "still"):
                        subs.append(item.name)
                    if name in ("thumbnail", "still"):
                        still.add(item.name)
        inherits = any(
            (isinstance(b, ast.Name) and b.id == "BpkScene") or
            (isinstance(b, ast.Attribute) and b.attr == "BpkScene")
            for b in node.bases
        )
        if subs or inherits:
            return node.name, subs, still
    raise ValueError(f"No BpkScene subclass found in {path}")

def resolve(target):
    prefix, letter = target[:2], target[2:]
    path = _find_file(prefix)
    classname, subs, _still = _parse(path)
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
    _classname, subs, _still = _parse(path)
    return [index_to_label(i) for i in range(len(subs))]

def subscene_methods(prefix):
    """The @subscene METHOD NAMES (not letters) of the NN scene, in order — the STABLE
    identity part that render --stills / davinci match on across re-lettering (a split/
    merge/remove shifts letters but not method names). Used to spot orphaned timeline
    clips whose method no longer exists."""
    path = _find_file(prefix)
    _classname, subs, _still = _parse(path)
    return list(subs)

def is_still(target):
    """True if `target` should render as a STILL IMAGE (a PNG via manim -s) rather
    than a video, because it's decorated @still (incl. its @thumbnail specialization).
    A NN<letter> target is still iff that subscene is @still; a BARE NN (whole scene)
    is still iff EVERY subscene is @still — i.e. an image-only scene (99 thumbnails, a
    mock-UI walkthrough), which therefore has no meaningful combined full-scene render."""
    prefix, letter = target[:2], target[2:]
    path = _find_file(prefix)
    _classname, subs, still = _parse(path)
    if not letter:
        return bool(subs) and len(still) == len(subs)
    idx = label_to_index(letter)
    return 0 <= idx < len(subs) and subs[idx] in still

def clean_stale(classname, prefix, letter, keep_output, edit_dir=None):
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
    # ...and the flat edit_clips/ staging dir (render --stills) — a LETTER slot only.
    # Keeps the current subscene's anim AND its trailing still; drops a renamed beat's
    # leftovers (e.g. old 01b_all_outcomes.mp4 + _still.png when 01b is now 01b_pairs).
    # The leading still (NN_lead_still.png, no letter) never matches the slot glob.
    if edit_dir and letter:
        keep = {f"{keep_output}.mp4", f"{keep_output}_still.png"}
        for f in glob.glob(os.path.join(edit_dir, f"{slot}*")):
            if os.path.isfile(f) and os.path.basename(f) not in keep:
                try:
                    os.remove(f)
                    removed.append(f)
                except OSError:
                    pass
    return removed

def clean_orphans(prefix, edit_dir=None):
    """Remove rendered videos for subscene SLOTS PAST the current last subscene — the
    REMOVED-subscene case (e.g. a scene cut from 30 subscenes to 13 leaves 05n_*.mp4 ..
    05zb_*.mp4 orphaned). `clean_stale` only sweeps ONE slot's renamed files WHEN you
    render that letter, so a slot that no longer exists is never rendered again and would
    linger forever; this sweeps every slot whose label index is >= the current subscene
    count, so SHRINKING a scene self-cleans on its next render. The full-scene slot (NN_)
    and every in-range letter are kept, so it never touches a live render (the in-progress
    output is always in range). Scans media/videos AND media/padded_videos (mirrors
    clean_stale); image-only (@still/@thumbnail) scenes have no videos here, so it's a
    no-op for them. Returns the files removed."""
    path = _find_file(prefix)
    _classname, subs, _still = _parse(path)
    count = len(subs)
    stem = path[:-3]                                    # NNname.py -> NNname
    removed = []
    for tree in ("videos", "padded_videos"):
        base = os.path.join("media", tree, stem)
        for quality_dir in glob.glob(os.path.join(base, "*")):
            for mp4 in glob.glob(os.path.join(quality_dir, f"{prefix}*.mp4")):
                rest = os.path.basename(mp4)[len(prefix):-4]   # <label>_<method> | _<method>
                label = rest.split("_", 1)[0]           # "" for the full-scene NN_ slot
                if not label:
                    continue                            # full-scene render — keep
                try:
                    idx = label_to_index(label)
                except ValueError:
                    continue                            # unrecognized name — leave it alone
                if idx >= count:
                    try:
                        os.remove(mp4)
                        removed.append(mp4)
                    except OSError:
                        pass
    # ...and the flat edit_clips/ staging dir (render --stills): any letter slot past the
    # current subscene count (anim + its trailing still). The leading still (no letter) is
    # kept; a full-scene NN_ file isn't staged here so never appears.
    if edit_dir:
        for f in glob.glob(os.path.join(edit_dir, f"{prefix}*")):
            if not os.path.isfile(f):
                continue
            rest = os.path.splitext(os.path.basename(f))[0][len(prefix):]
            label = rest.split("_", 1)[0]
            if not label:
                continue
            try:
                idx = label_to_index(label)
            except ValueError:
                continue
            if idx >= count:
                try:
                    os.remove(f)
                    removed.append(f)
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