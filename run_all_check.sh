#!/usr/bin/env bash
# Headless "Run All": fresh kernel, strict top-to-bottom order. Non-zero exit code on any error.
# Usage: bash tools/run_all_check.sh main.ipynb [data_dir]
set -euo pipefail
NB="${1:-main.ipynb}"
[ -n "${2:-}" ] && export F1_DATA_DIR="$2"
jupyter nbconvert --to notebook --execute "$NB" \
  --ExecutePreprocessor.timeout=3600 --ExecutePreprocessor.kernel_name=python3 \
  --output run_all_out.ipynb --output-dir outputs/
echo "RUN ALL PASSED: $NB"
