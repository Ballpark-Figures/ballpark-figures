"""Quick structural dump of one or more ``.npz`` files — a FIXED, safe
alternative to ad-hoc ``python -c`` / throwaway probe scripts for peeking at
solver data (which are arbitrary code execution and so always prompt).

For each archive it prints, per array: name, dtype, shape, and — for numeric
arrays — min / max / mean / sum plus a short flat sample.

``np.load`` is called with ``allow_pickle=False`` so loading an archive can
never execute embedded objects; that's what makes this safe to allowlist as a
fixed ``python -m bpkfigures.inspect_npz`` invocation.

Usage:
    python -m bpkfigures.inspect_npz <path.npz> [<path2.npz> ...] [--sample N]
"""
import sys
import numpy as np


def inspect(path, sample=8):
    print(f"=== {path} ===")
    try:
        with np.load(path, allow_pickle=False) as z:
            for k in z.files:
                a = z[k]
                line = f"  {k}: dtype={a.dtype} shape={a.shape}"
                if a.size and np.issubdtype(a.dtype, np.number):
                    line += (f"  min={a.min():.6g} max={a.max():.6g}"
                             f" mean={a.mean():.6g} sum={a.sum():.6g}")
                print(line)
                if a.size and sample:
                    print(f"     sample: {a.ravel()[:sample]}")
    except Exception as e:
        print(f"  <error: {type(e).__name__}: {e}>")


def main(argv):
    paths, sample = [], 8
    it = iter(argv)
    for arg in it:
        if arg == "--sample":
            sample = int(next(it, 8))
        else:
            paths.append(arg)
    if not paths:
        print("usage: python -m bpkfigures.inspect_npz <path.npz> ... [--sample N]")
        return 1
    for p in paths:
        inspect(p, sample=sample)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
