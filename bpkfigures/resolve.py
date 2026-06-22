import ast
import glob
import os
import re
import sys

def _snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

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
                    is_sub = (isinstance(dec, ast.Name) and dec.id == "subscene") or \
                             (isinstance(dec, ast.Attribute) and dec.attr == "subscene")
                    if is_sub:
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
    idx = ord(letter) - ord("a")
    if not (0 <= idx < len(subs)):
        raise IndexError(f"Subscene '{letter}' out of range for {path}")
    return path, classname, f"{prefix}{letter}_{subs[idx]}", letter

def main():
    try:
        path, classname, output, letter = resolve(sys.argv[1])
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"{path}\t{classname}\t{output}\t{letter}")

if __name__ == "__main__":
    main()