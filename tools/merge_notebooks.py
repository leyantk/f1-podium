#!/usr/bin/env python3
"""Merge per-person notebooks into one run-all notebook.
Usage: python tools/merge_notebooks.py p1.ipynb p2.ipynb p3.ipynb p4.ipynb p1_inference.ipynb -o main.ipynb
Rules enforced (exit code 1 on violation):
  * only the FIRST notebook may define SEED / DATA_DIR / set_all_seeds (single setup cell)
  * no '!pip', absolute local paths (C:\\, /Users/, /home/), or hard-coded '/kaggle/input' outside the resolver
  * outputs and execution counts are stripped
  * a code cell starting with '# LOCAL SETUP' is dropped from every notebook except the first
"""
import argparse, json, re, sys

FORBIDDEN_LATER = [r"^\s*SEED\s*=", r"^\s*DATA_DIR\s*=", r"def\s+set_all_seeds", r"def\s+resolve_data_dir"]
FORBIDDEN_EVERYWHERE = [r"^\s*!pip", r"[A-Za-z]:\\\\", r"/Users/", r"/home/\w+"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("notebooks", nargs="+"); ap.add_argument("-o", "--output", default="main.ipynb")
    a = ap.parse_args(); merged, errors = None, []
    for i, path in enumerate(a.notebooks):
        nb = json.load(open(path, encoding="utf-8"))
        if merged is None:
            merged = {k: v for k, v in nb.items() if k != "cells"}; merged["cells"] = []
        merged["cells"].append({"cell_type": "markdown", "metadata": {}, "source": [f"---\n# >>> Section from `{path}`\n"]})
        for n, c in enumerate(nb["cells"]):
            src = "".join(c["source"])
            if i > 0 and c["cell_type"] == "code" and src.lstrip().startswith("# LOCAL SETUP"):
                continue                      # local-only imports (sys.path / f1_clean); main.ipynb already has load_clean
            if c["cell_type"] == "code":
                pats = FORBIDDEN_EVERYWHERE + (FORBIDDEN_LATER if i > 0 else [])
                for p in pats:
                    if re.search(p, src, flags=re.M):
                        errors.append(f"{path} cell {n}: matches forbidden pattern {p!r}")
                c = dict(c, outputs=[], execution_count=None)
            merged["cells"].append(c)
    if errors:
        print("\n".join(errors)); sys.exit(1)
    json.dump(merged, open(a.output, "w", encoding="utf-8"), indent=1)
    print(f"merged {len(a.notebooks)} notebooks -> {a.output} ({len(merged['cells'])} cells)")

if __name__ == "__main__":
    main()
