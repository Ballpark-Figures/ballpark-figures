import hashlib
import inspect
import os
import pickle

from manim import Scene

SNAPSHOT_DIR = os.path.join("cache", "snapshots")


def subscene(fn):
    fn._is_subscene = True
    return fn


def _ordered_subscenes(cls):
    found = []
    for name, fn in inspect.getmembers(cls, predicate=inspect.isfunction):
        if getattr(fn, "_is_subscene", False):
            found.append((fn.__code__.co_firstlineno, name))
    found.sort()
    return [name for _, name in found]


def _letter(i):
    return chr(ord("a") + i)


class BpkScene(Scene):
    def setup_scene(self):
        pass

    def _prefix_key(self, idx, names):
        # hash of setup_scene + subscenes up to and including idx.
        # editing a LATER subscene leaves earlier snapshots valid.
        cls = type(self)
        srcs = [inspect.getsource(cls.setup_scene)]
        for name in names[: idx + 1]:
            srcs.append(inspect.getsource(getattr(cls, name)))
        return hashlib.md5("".join(srcs).encode()).hexdigest()

    def _snapshot_path(self, idx):
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        return os.path.join(SNAPSHOT_DIR, f"{type(self).__name__}_{_letter(idx)}.pkl")

    def _save_snapshot(self, idx, names):
        user_keys = set(self.__dict__) - self._baseline_keys
        bundle = {
            "key": self._prefix_key(idx, names),
            "attrs": {k: self.__dict__[k] for k in user_keys},
            "mobjects": list(self.mobjects),  # same dump -> identity preserved
        }
        path = self._snapshot_path(idx)
        try:
            with open(path, "wb") as f:
                pickle.dump(bundle, f)
        except Exception as e:
            if os.path.exists(path):
                os.remove(path)
            print(f"[bpk] snapshot skipped at {_letter(idx)}: {type(e).__name__}")

    def _load_snapshot(self, idx, names):
        if os.environ.get("RECOMPUTE", "0") == "1":
            return False
        path = self._snapshot_path(idx)
        if not os.path.exists(path):
            return False
        try:
            with open(path, "rb") as f:
                bundle = pickle.load(f)
        except Exception:
            return False
        if bundle.get("key") != self._prefix_key(idx, names):
            return False
        for k, v in bundle["attrs"].items():
            setattr(self, k, v)
        for m in bundle["mobjects"]:
            self.add(m)
        return True

    def construct(self):
        self._baseline_keys = set(self.__dict__.keys())
        names = _ordered_subscenes(type(self))
        target = os.environ.get("SUBSCENE", "")

        if not target:
            self.setup_scene()
            for i, name in enumerate(names):
                getattr(self, name)()
                self._save_snapshot(i, names)
            return

        idx = ord(target) - ord("a")
        if not (0 <= idx < len(names)):
            raise IndexError(f"Subscene '{target}' out of range (have {len(names)})")

        loaded = self._load_snapshot(idx - 1, names) if idx > 0 else False
        if not loaded:
            self.setup_scene()
            if idx > 0:
                self.renderer.skip_animations = True
                for i, name in enumerate(names[:idx]):
                    getattr(self, name)()
                    self._save_snapshot(i, names)
                self.renderer.skip_animations = False

        getattr(self, names[idx])()
        self._save_snapshot(idx, names)