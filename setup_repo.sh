#!/usr/bin/env bash
# Usage: bash setup_repo.sh [project-dir]     (run once by P1; teammates only need the nbstripout step after cloning)
set -euo pipefail
ROOT="${1:-f1-podium}"
mkdir -p "$ROOT"/{data/raw,notebooks,src,tools,reports,outputs}
cd "$ROOT"
git init -q 2>/dev/null || true

cat > .gitignore << 'GI'
# raw data + local checkpoints (raw CSVs stay immutable and out of git)
data/raw/
data/**/*.csv
outputs/
*.parquet
*.pkl
*.h5
*.pt
.ipynb_checkpoints/
__pycache__/
.venv/
.DS_Store
GI

cat > requirements.txt << 'RQ'
pandas>=2.2
numpy
matplotlib
seaborn
scikit-learn
nbstripout
nbformat
nbconvert
ipykernel
RQ

cat > README.md << 'RD'
# F1 Podium Prediction (CSEN903 M1)
1. Download the Kaggle dataset `rohanrao/formula-1-world-championship-1950-2020` into `data/raw/` (or set `F1_DATA_DIR`).
2. `pip install -r requirements.txt && nbstripout --install --attributes .gitattributes`  (once per clone)
3. `from f1_clean import load_clean; clean = load_clean()`
Branch per person, PR + 1 reviewer, never commit notebook outputs or raw CSVs.
RD

pip install -q nbstripout
nbstripout --install --attributes .gitattributes
echo "Repo skeleton ready in $ROOT. Copy f1_clean.py -> src/, merge_notebooks.py + run_all_check.sh -> tools/."
