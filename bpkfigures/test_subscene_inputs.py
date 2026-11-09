"""Tests for bpkfigures.subscene_inputs: what the recorder counts as a subscene's input,
and the two things render.py reads from the records. Run with the video's venv:

    python -m bpkfigures.test_subscene_inputs
"""
import json
import os
import tempfile

from bpkfigures import subscene_inputs as SI


def _tree():
    """A throwaway project, <root>/animations/{scenes,assets,cache,media}, cwd = scenes/."""
    root = tempfile.mkdtemp()
    anim = os.path.join(root, "animations")
    for d in ("scenes", "assets", "cache", "media"):
        os.makedirs(os.path.join(anim, d))
    os.chdir(os.path.join(anim, "scenes"))
    return anim, root


def _write(path, text):
    with open(path, "w") as f:
        f.write(text)


def test_records_only_asset_reads():
    anim, root = _tree()
    data = os.path.join(anim, "assets", "x_cache.json")
    others = [os.path.join(anim, "assets", "x_data.py"), os.path.join(anim, "cache", "s.pkl"),
              os.path.join(anim, "media", "clip.txt"), os.path.join(root, "elsewhere.txt")]
    for p in [data] + others:
        _write(p, "1")
    rec = SI._Recorder()
    rec.stack.append(("beat", set()))
    for p in [data] + others:
        rec.audit("open", (p, "r", 0))
    rec.audit("open", (data, "w", 0))                       # a write is not a read
    assert rec.stack[-1][1] == {os.path.realpath(data)}, rec.stack[-1][1]
    rec.stack.clear()                                       # nothing running: nothing kept
    rec.audit("open", (data, "r", 0))
    assert rec.stack == []


def test_hash_and_staleness_follow_only_recorded_files():
    anim, _root = _tree()
    a, b = (os.path.realpath(os.path.join(anim, "assets", n)) for n in ("a.json", "b.json"))
    _write(a, "1")
    _write(b, "1")
    os.makedirs(SI.SNAPSHOT_DIR)
    with open(SI.records_path("T"), "w") as f:
        json.dump({"setup_scene": {}, "one": {}, "two": {a: SI.file_md5(a)}}, f)
    names = ["one", "two", "three"]
    assert SI.inputs_hash("T", ["setup_scene", "one", "two", "three"]) is None, \
        "a subscene with no record must not get a per-clip hash"
    h1 = SI.inputs_hash("T", ["setup_scene", "one"])
    h2 = SI.inputs_hash("T", ["setup_scene", "one", "two"])
    assert SI.stale_from("T", names) is None
    _write(b, "2")                                          # a file nobody read
    assert SI.inputs_hash("T", ["setup_scene", "one", "two"]) == h2
    assert SI.stale_from("T", names) is None
    _write(a, "2")                                          # the file `two` read
    assert SI.inputs_hash("T", ["setup_scene", "one"]) == h1
    assert SI.inputs_hash("T", ["setup_scene", "one", "two"]) != h2
    assert SI.stale_from("T", names) == 1, SI.stale_from("T", names)   # `two`, index 1


if __name__ == "__main__":
    cwd = os.getcwd()
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                fn()
                print(f"ok  {name}")
    finally:
        os.chdir(cwd)
