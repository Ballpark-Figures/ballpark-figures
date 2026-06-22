import os
import pickle
import hashlib
import inspect

CACHE_DIR = "cache"

def _source_key(fn):
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        src = repr(fn)
    return hashlib.md5(src.encode()).hexdigest()

def load_or_compute(compute_fn, key=None, cache_dir=CACHE_DIR, recompute=None):
    if recompute is None:
        recompute = os.environ.get("RECOMPUTE", "0") == "1"
    os.makedirs(cache_dir, exist_ok=True)
    if key is None:
        key = _source_key(compute_fn)
    path = os.path.join(cache_dir, f"data_{key}.pkl")
    if not recompute and os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    result = compute_fn()
    with open(path, "wb") as f:
        pickle.dump(result, f)
    return result