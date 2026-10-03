"""f1_clean.py - shared cleaning pipeline for the CSEN903 F1 podium project.
Usage: from f1_clean import load_clean; clean = load_clean()   # DATA_DIR resolved automatically
Generated from the same code blocks as main.ipynb sections 1, 4, 5, 6 and 8. Do not edit by hand."""

import os, re, random, warnings
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
SENT = "\\N"          # the literal two-character sentinel used by the Ergast CSVs: backslash + N
KEYS = ["raceId", "driverId"]   # grain of the modeling table
TABLES = ["circuits", "constructors", "constructor_results", "constructor_standings",
          "drivers", "driver_standings", "races", "results", "qualifying", "lap_times",
          "pit_stops", "sprint_results", "seasons", "status"]


def set_all_seeds(seed: int = SEED) -> None:
    """Fix every RNG we might touch. Torch/TF are optional (P4 will use one of them)."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
    except Exception:
        pass


def _has_data(p: Path) -> bool:
    return p.is_dir() and all((p / f"{t}.csv").exists() for t in TABLES)


def resolve_data_dir() -> Path:
    """Find the folder holding the 14 CSVs, on Kaggle or locally, with no manual edits.
    Order: F1_DATA_DIR env var -> any /kaggle/input/**/races.csv -> common local folders."""
    candidates = []
    if os.environ.get("F1_DATA_DIR"):
        candidates.append(Path(os.environ["F1_DATA_DIR"]))
    kaggle_root = Path("/kaggle/input")
    if kaggle_root.exists():
        candidates += [p.parent for p in sorted(kaggle_root.rglob("races.csv"))]
    candidates += [Path(p) for p in ("data/raw", "../data/raw", "data", "../data", ".")]
    for p in candidates:
        if _has_data(p):
            return p.resolve()
    raise FileNotFoundError(
        "Could not find the 14 F1 CSVs. On Kaggle: attach the dataset "
        "'rohanrao/formula-1-world-championship-1950-2020' via 'Add Data'. "
        "Locally: put the CSVs in data/raw/ or set the F1_DATA_DIR environment variable.")


def _read_csv_raw(path: Path) -> pd.DataFrame:
    # dtype=str + keep_default_na=False: nothing is guessed, nothing is silently turned into NaN.
    # The raw file is therefore reproduced exactly, including every literal "\N".
    kw = dict(dtype=str, keep_default_na=False, na_values=[])
    try:
        return pd.read_csv(path, encoding="utf-8", **kw)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kw)


def read_raw_tables(data_dir) -> dict:
    return {t: _read_csv_raw(Path(data_dir) / f"{t}.csv") for t in TABLES}



# ---- Semantic typing specification (explicit > guessed) -------------------------------------
INT_COLS = {
    "races": ["year", "round"], "seasons": ["year"], "drivers": ["number"],
    "constructor_standings": ["position", "wins"], "driver_standings": ["position", "wins"],
    "results": ["number", "grid", "position", "positionOrder", "laps", "milliseconds", "fastestLap", "rank"],
    "qualifying": ["number", "position"],
    "lap_times": ["lap", "position", "milliseconds"],
    "pit_stops": ["stop", "lap", "milliseconds"],
    "sprint_results": ["number", "grid", "position", "positionOrder", "laps", "milliseconds", "fastestLap"],
}
FLOAT_COLS = {
    "circuits": ["lat", "lng", "alt"],
    "constructor_results": ["points"], "constructor_standings": ["points"], "driver_standings": ["points"],
    "results": ["points", "fastestLapSpeed"], "sprint_results": ["points", "fastestLapSpeed"],
}
DATE_COLS = {
    "races": ["date", "fp1_date", "fp2_date", "fp3_date", "quali_date", "sprint_date"],
    "drivers": ["dob"],
}
LAPTIME_COLS = {   # table -> {source string column: new numeric-seconds column}
    "results": {"fastestLapTime": "fastestLapTime_s"},
    "sprint_results": {"fastestLapTime": "fastestLapTime_s"},
    "qualifying": {"q1": "q1_s", "q2": "q2_s", "q3": "q3_s"},
    "lap_times": {"time": "time_s"},
    "pit_stops": {"duration": "duration_s"},
}

_LAP_RE = r"^(?:(?:(\d+):)?(\d+):)?(\d+(?:\.\d+)?)$"   # [h:][m:]s[.fff]


def laptime_to_seconds(s: pd.Series) -> pd.Series:
    """'1:27.452' -> 87.452 ; '59.3' -> 59.3 ; '1:02:03.5' -> 3723.5 ; NaN/garbage -> NaN."""
    parts = s.astype("string").str.extract(_LAP_RE)
    h = pd.to_numeric(parts[0]).fillna(0)
    m = pd.to_numeric(parts[1]).fillna(0)
    sec = pd.to_numeric(parts[2])
    return (h * 3600 + m * 60 + sec).astype("float64")


def to_int(s: pd.Series) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    if (n.notna() & (n % 1 != 0)).any():
        warnings.warn(f"non-integer values rounded in column {s.name}")
    return n.round().astype("Int64")      # nullable Int64 keeps NaN without turning ints into floats


def clean_table(name: str, df: pd.DataFrame):
    """Return (cleaned copy, log rows). The raw frame is never modified."""
    d = df.copy().replace(SENT, np.nan)
    log = []
    for c in d.columns:                                    # all *Id columns -> nullable ints
        if c.endswith("Id"):
            d[c] = to_int(d[c])
    for c in INT_COLS.get(name, []):
        if c in d: d[c] = to_int(d[c])
    for c in FLOAT_COLS.get(name, []):
        if c in d: d[c] = pd.to_numeric(d[c], errors="coerce").astype("float64")
    for c in DATE_COLS.get(name, []):
        if c in d:
            before = d[c].notna().sum()
            d[c] = pd.to_datetime(d[c], format="%Y-%m-%d", errors="coerce")
            log.append(dict(table=name, column=c, op="to_datetime", non_null_before=int(before),
                            non_null_after=int(d[c].notna().sum())))
    for src, dst in LAPTIME_COLS.get(name, {}).items():
        if src in d:
            before = d[src].notna().sum()
            d[dst] = laptime_to_seconds(d[src])
            log.append(dict(table=name, column=f"{src}->{dst}", op="laptime_to_seconds",
                            non_null_before=int(before), non_null_after=int(d[dst].notna().sum())))
            d = d.drop(columns=[src])           # keep one canonical column: numeric seconds
    if name == "races" and {"date", "time"} <= set(d.columns):   # scheduled start, known pre-race
        stamp = d["date"].dt.strftime("%Y-%m-%d") + " " + d["time"].astype("string")
        d["race_start_utc"] = pd.to_datetime(stamp, errors="coerce")
    return d, log


def clean_all(raw: dict):
    out, logs = {}, []
    for name, df in raw.items():
        out[name], lg = clean_table(name, df)
        logs += lg
    return out, pd.DataFrame(logs)



# ---- Population rules ------------------------------------------------------------------------
INDY_YEARS = (1950, 1960)
NONSTART_POSITION_TEXT = {"F", "W"}          # F = failed to qualify, W = withdrawn
NONSTART_STATUS_RE = r"did not (?:pre)?qualify|not qualified|withdrew|107%"


def flag_races(races: pd.DataFrame, circuits: pd.DataFrame) -> pd.DataFrame:
    """Add is_indy500: the 1950-1960 Indianapolis 500 rounds that counted for the F1 championship.
    NOTE: the same Indianapolis circuit hosted a real F1 US GP in 2000-2007 -> keep those (year filter)."""
    r = races.copy()
    indy_ids = circuits.loc[
        circuits["name"].str.contains("Indianapolis", case=False, na=False)
        | circuits["circuitRef"].str.contains("indianapolis", case=False, na=False), "circuitId"]
    by_name = r["name"].str.contains("Indianapolis 500", case=False, na=False)
    by_venue = r["circuitId"].isin(indy_ids) & r["year"].between(*INDY_YEARS)
    r["is_indy500"] = (by_name | by_venue).astype(bool)
    return r


def flag_non_starters(res: pd.DataFrame) -> pd.Series:
    """DNQ / DNPQ / withdrawn / 107%-rule rows. Uses only facts that are settled BEFORE lights-out
    (who failed to qualify or withdrew) - never laps or finishing status of drivers who did race."""
    by_text = res["positionText"].isin(NONSTART_POSITION_TEXT)
    by_status = res["status"].str.contains(NONSTART_STATUS_RE, case=False, regex=True, na=False)
    return (by_text | by_status).astype(bool)


def dedup_results(res: pd.DataFrame):
    """Enforce exactly one row per (raceId, driverId).
    KEEP-RULE (total order, first row wins):
      1. a row with grid > 0   -> the car the driver actually STARTED in (pre-race fact, so the choice
                                  itself cannot leak the outcome);
      2. lowest positionOrder  -> only to break remaining ties (no grid>0 row, or several);
      3. lowest resultId       -> deterministic final tie-break.
    Returns (kept rows with audit columns, dropped rows)."""
    d = res.reset_index(drop=True).copy()
    d["n_raw_rows"] = d.groupby(KEYS)["resultId"].transform("size").astype("int64")
    d["best_positionOrder_raw"] = d.groupby(KEYS)["positionOrder"].transform("min")
    d["_started"] = d["grid"].fillna(0).gt(0).astype(bool)
    d = d.sort_values(KEYS + ["_started", "positionOrder", "resultId"],
                      ascending=[True, True, False, True, True], kind="mergesort")
    kept = d.drop_duplicates(KEYS, keep="first")
    dropped = d.loc[~d.index.isin(kept.index)].drop(columns="_started")
    kept = kept.drop(columns="_started").assign(shared_drive=lambda x: x["n_raw_rows"] > 1)
    kept = kept.sort_values(["raceId", "positionOrder", "driverId"]).reset_index(drop=True)
    return kept, dropped



# ---- Column contracts: what is allowed to become a FEATURE vs. what is outcome-only ---------------
PRE_RACE_COLS = ["raceId", "driverId", "constructorId", "year", "round", "date", "circuitId", "number",
                 "grid", "pitlane_start", "has_qualifying", "qual_position", "q1_s", "q2_s", "q3_s"]
OUTCOME_COLS = ["raceId", "driverId", "resultId", "positionOrder", "podium", "positionText", "position",
                "points", "laps", "time", "milliseconds", "fastestLap", "rank", "fastestLapTime_s",
                "fastestLapSpeed", "statusId", "status", "n_raw_rows", "shared_drive", "best_positionOrder_raw"]
FORBIDDEN_IN_BASE = {"positionOrder", "positionText", "position", "points", "laps", "time", "milliseconds",
                     "fastestLap", "rank", "fastestLapTime", "fastestLapTime_s", "fastestLapSpeed",
                     "statusId", "status", "resultId", "n_raw_rows", "shared_drive", "best_positionOrder_raw"}


def prep_qualifying(q: pd.DataFrame):
    """Qualifying should be unique per (raceId, driverId); if not, keep the highest qualifyId."""
    q = q.sort_values("qualifyId")
    n_dup = int(q.duplicated(KEYS, keep="last").sum())
    q = q.drop_duplicates(KEYS, keep="last").rename(columns={"position": "qual_position"})
    return q[KEYS + ["qual_position", "q1_s", "q2_s", "q3_s"]], n_dup


def load_clean(data_dir=None, exclude_indy500: bool = True, drop_non_starters: bool = True) -> dict:
    """THE handoff function. Raw CSV -> typed -> Indy rule -> dedup -> non-starter rule -> split into
    a PRE-RACE base table and a POST-RACE outcomes table (never use outcomes columns as features).

    Returns dict with:
      model_base : one row per (raceId, driverId): pre-race columns + target `podium`
      outcomes   : same grain, post-race columns (status, points, positions...) for DE questions / audits
      non_starters, dup_dropped : rows removed, kept for audit
      tables     : every other typed table (races incl. is_indy500, circuits, drivers, constructors, status,
                   qualifying, *_standings (post-race! shift before use), lap_times, pit_stops, ...)
      meta       : row accounting for every filtering step
    """
    set_all_seeds(SEED)
    data_dir = Path(data_dir) if data_dir else resolve_data_dir()
    T, _ = clean_all(read_raw_tables(data_dir))
    T["races"] = flag_races(T["races"], T["circuits"])

    res = (T["results"]
           .merge(T["races"][["raceId", "year", "round", "date", "circuitId", "is_indy500"]],
                  on="raceId", how="inner", validate="m:1")
           .merge(T["status"], on="statusId", how="left", validate="m:1"))
    meta = {"raw_result_rows": len(T["results"]), "rows_after_race_join": len(res)}

    if exclude_indy500:
        meta["indy500_rows_removed"] = int(res["is_indy500"].sum())
        res = res[~res["is_indy500"]]
    res, dup_dropped = dedup_results(res)
    meta["duplicate_rows_removed"] = len(dup_dropped)
    res["is_non_starter"] = flag_non_starters(res)
    non_starters = res[res["is_non_starter"]].copy()
    meta["non_starter_rows_removed"] = len(non_starters) if drop_non_starters else 0
    if drop_non_starters:
        res = res[~res["is_non_starter"]]
    res = res.reset_index(drop=True)
    meta["final_rows"] = len(res)

    q, meta["qualifying_duplicate_rows_dropped"] = prep_qualifying(T["qualifying"])
    res["pitlane_start"] = res["grid"].eq(0).fillna(False).astype(bool)   # grid==0 among actual starters
    base = res.merge(q, on=KEYS, how="left", validate="1:1", indicator="_q")
    base["has_qualifying"] = base["_q"].eq("both")
    base = base.drop(columns="_q")
    outcomes = base[[c for c in OUTCOME_COLS if c != "podium" and c in base]].copy()
    outcomes["podium"] = (outcomes["positionOrder"] <= 3).astype("int8")
    outcomes = outcomes[OUTCOME_COLS]
    model_base = base[PRE_RACE_COLS].copy()
    model_base["podium"] = outcomes["podium"].values

    # ---- hard guarantees every teammate can rely on -----------------------------------------------
    assert not model_base.duplicated(KEYS).any(), "grain violated: duplicate (raceId, driverId)"
    assert model_base[KEYS].notna().all().all(), "null key in modeling table"
    assert not (FORBIDDEN_IN_BASE & set(model_base.columns)), "post-race column leaked into base table"
    assert len(model_base) == len(outcomes) == meta["final_rows"]
    return dict(model_base=model_base, outcomes=outcomes, non_starters=non_starters,
                dup_dropped=dup_dropped, tables=T, meta=meta)

