"""Run AFTER tools/merge_notebooks.py. Makes the merged notebook self-contained so it also runs on Kaggle (no src/ folder).
Usage: python tools/finalize_merge.py main.ipynb
Fixes: (1) P3's `from f1_eval import ...` -> the code of src/f1_eval.py is pasted into that cell
       (2) '../reports' -> 'reports' (main.ipynb sits in the repo root, not in notebooks/)
Then checks that nothing local is left and that predict_podium is defined only once."""
import json, re, sys
from pathlib import Path

path = Path(sys.argv[1])
nb = json.load(open(path, encoding="utf-8"))
eval_code = Path("src/f1_eval.py").read_text(encoding="utf-8")
eval_code = eval_code[eval_code.index("import pandas"):].replace("\r\n", "\n")

for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    new = re.sub(r"^sys\.path\.append\([\"']\.\./src[\"']\)\s*\n", "", src, flags=re.M)
    new = re.sub(r"^from f1_eval import[^\n]*", "# copied from src/f1_eval.py\n" + eval_code, new, flags=re.M)
    new = new.replace("../reports", "reports")
    if new != src:
        cell["source"] = new.splitlines(keepends=True)

problems = []
n_def = 0
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    for bad in ["sys.path", "from f1_", "import f1_", "../reports", "../src", "%run"]:
        if bad in src:
            problems.append(f"cell {i}: still contains {bad!r}")
    n_def += len(re.findall(r"^def predict_podium\(", src, flags=re.M))
if n_def != 1:
    problems.append(f"'def predict_podium(' found {n_def} times (must be 1): rename P4's helper first")

json.dump(nb, open(path, "w", encoding="utf-8"), indent=1)
print("PROBLEMS:\n  " + "\n  ".join(problems) if problems else f"finalize OK: {path} ({len(nb['cells'])} cells)")
sys.exit(1 if problems else 0)
