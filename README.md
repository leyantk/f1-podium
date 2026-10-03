# F1 Podium Prediction (CSEN903 M1)
1. Download the Kaggle dataset `rohanrao/formula-1-world-championship-1950-2020` into `data/raw/` (or set `F1_DATA_DIR`).
2. `pip install -r requirements.txt && nbstripout --install --attributes .gitattributes`  (once per clone)
3. `from f1_clean import load_clean; clean = load_clean()`
Branch per person, PR + 1 reviewer, never commit notebook outputs or raw CSVs.
