import os
import pickle
import hashlib
import inspect

def cached_setup(fn):
    def wrapper(self, *args, **kwargs):
        recompute = os.environ.get("RECOMPUTE", "0") == "1"
        
        source = inspect.getsource(fn)
        key = hashlib.md5(source.encode()).hexdigest()
        
        cache_dir = "cache"
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, f"{key}.pkl")
        
        if not recompute and os.path.exists(path):
            with open(path, "rb") as f:
                attrs = pickle.load(f)
            for k, v in attrs.items():
                setattr(self, k, v)
            print(f"Loaded setup from cache ({path})")
            return
        
        before = set(self.__dict__.keys())
        fn(self, *args, **kwargs)
        after = set(self.__dict__.keys())
        
        new_attrs = {k: self.__dict__[k] for k in after - before}
        with open(path, "wb") as f:
            pickle.dump(new_attrs, f)
        print(f"Saved setup to cache ({path})")
    
    return wrapper