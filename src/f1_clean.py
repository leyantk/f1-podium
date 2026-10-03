"""f1_clean.py: shared cleaning code for the F1 podium project.
Usage: from f1_clean import load_clean; clean = load_clean()
Same code as the notebook (sections 1, 4, 5, 6, 8)."""

import os, random
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

SENT = "\\N"                    # the CSVs write a missing value as the text \N
KEYS = ["raceId", "driverId"]   # one row per driver per race
TABLES = ["circuits", "constructors", "constructor_results", "constructor_standings", "drivers",
          "driver_standings", "races", "results", "qualifying", "lap_times", "pit_stops",
          "sprint_results", "seasons", "status"]


def find_data_dir():
    """Works on Kaggle (/kaggle/input/...) and on a laptop (data/raw)."""
    folders = [Path("data/raw"), Path("../data/raw"), Path("data"), Path(".")]
    if Path("/kaggle/input").exists():
        folders = [p.parent for p in Path("/kaggle/input").rglob("races.csv")] + folders
    for folder in folders:
        if all((folder / f"{t}.csv").exists() for t in TABLES):
            return folder
    raise FileNotFoundError("F1 CSV files not found. Add the Kaggle dataset or put the CSVs in data/raw/")


def load_raw_tables(data_dir):
    """Read every CSV as plain text so nothing is guessed or silently changed."""
    raw = {}
    for t in TABLES:
        raw[t] = pd.read_csv(Path(data_dir) / f"{t}.csv", dtype=str, keep_default_na=False,
                             encoding_errors="replace")
    return raw



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
TIME_COLS = {   # text lap times -> seconds (old column: new column)
    "results": {"fastestLapTime": "fastestLapTime_s"},
    "sprint_results": {"fastestLapTime": "fastestLapTime_s"},
    "qualifying": {"q1": "q1_s", "q2": "q2_s", "q3": "q3_s"},
    "lap_times": {"time": "time_s"},
    "pit_stops": {"duration": "duration_s"},
}


def to_seconds(s):
    """'1:27.452' -> 87.452 (also handles '59.3' and '1:02:03.5'). Anything else -> NaN."""
    parts = s.astype("string").str.extract(r"^(?:(?:(\d+):)?(\d+):)?(\d+(?:\.\d+)?)$")
    hours = pd.to_numeric(parts[0]).fillna(0)
    minutes = pd.to_numeric(parts[1]).fillna(0)
    seconds = pd.to_numeric(parts[2])
    return (hours * 3600 + minutes * 60 + seconds).astype("float64")


def clean_tables(raw):
    """Return cleaned copies of all tables. The raw tables are not touched."""
    clean = {}
    for name, df in raw.items():
        d = df.replace(SENT, np.nan)                      # \N -> NaN
        d = d.replace(r"^\s*$", np.nan, regex=True)       # blank cells are missing too
        for c in d.columns:                               # ids and counts -> integers (can hold NaN)
            if c.endswith("Id") or c in INT_COLS.get(name, []):
                d[c] = pd.to_numeric(d[c], errors="coerce").round().astype("Int64")
        for c in FLOAT_COLS.get(name, []):
            if c in d.columns:
                d[c] = pd.to_numeric(d[c], errors="coerce")
        for c in DATE_COLS.get(name, []):                 # text -> real dates
            if c in d.columns:
                d[c] = pd.to_datetime(d[c], format="%Y-%m-%d", errors="coerce")
        for old, new in TIME_COLS.get(name, {}).items():  # text lap times -> seconds
            if old in d.columns:
                d[new] = to_seconds(d[old])
                d = d.drop(columns=[old])
        clean[name] = d
    return clean



def flag_indy500(races, circuits):
    """Mark the Indianapolis 500 rounds that counted for the championship (1950-1960).
    The same circuit hosted a real F1 US Grand Prix in 2000-2007, so we also check the year."""
    races = races.copy()
    indy_ids = circuits.loc[circuits["name"].str.contains("Indianapolis", na=False), "circuitId"]
    by_name = races["name"].str.contains("Indianapolis 500", na=False)
    by_place = races["circuitId"].isin(indy_ids) & races["year"].between(1950, 1960)
    races["is_indy500"] = (by_name | by_place).astype(bool)
    return races


def find_non_starters(res):
    """Drivers who did not qualify / withdrew. Only uses facts known before the race."""
    by_code = res["positionText"].isin(["F", "W"])      # F = failed to qualify, W = withdrew
    by_status = res["status"].str.contains("did not (?:pre)?qualify|not qualified|withdrew|107%",
                                           case=False, regex=True, na=False)
    return (by_code | by_status).astype(bool)


def keep_one_row_per_driver(res):
    """One row per (raceId, driverId).
    WHICH row we keep uses only facts known before the race (never the finishing position):
      1) a car that really started (grid > 0), 2) the lowest grid slot, 3) constructorId, car number,
      4) resultId only as a last resort (rows that look identical before the race).
    The LABEL is different: podium = the driver's best finish over all his rows <= 3."""
    res = res.reset_index(drop=True).copy()
    res["n_raw_rows"] = res.groupby(KEYS)["resultId"].transform("size")
    res["best_positionOrder"] = res.groupby(KEYS)["positionOrder"].transform("min")
    res["started"] = res["grid"].fillna(0) > 0
    res["grid_for_sort"] = res["grid"].where(res["started"])
    res = res.sort_values(KEYS + ["started", "grid_for_sort", "constructorId", "number", "resultId"],
                          ascending=[True, True, False, True, True, True, True], kind="mergesort")
    kept = res.drop_duplicates(KEYS, keep="first")
    dropped = res.drop(kept.index).drop(columns=["started", "grid_for_sort"])
    kept = kept.drop(columns=["started", "grid_for_sort"]).copy()
    kept["shared_drive"] = kept["n_raw_rows"] > 1
    kept["podium"] = (kept["best_positionOrder"] <= 3).astype("int8")
    return kept.reset_index(drop=True), dropped



PRE_RACE_COLS = ["raceId", "driverId", "constructorId", "year", "round", "date", "circuitId", "number",
                 "grid", "pitlane_start", "has_qualifying", "qual_position", "q1_s", "q2_s", "q3_s"]
OUTCOME_COLS = ["raceId", "driverId", "resultId", "positionOrder", "podium", "positionText", "position",
                "points", "laps", "time", "milliseconds", "fastestLap", "rank", "fastestLapTime_s",
                "fastestLapSpeed", "statusId", "status", "n_raw_rows", "shared_drive", "best_positionOrder"]
POST_RACE_COLS = {"positionOrder", "positionText", "position", "points", "laps", "time", "milliseconds",
                  "fastestLap", "rank", "fastestLapTime_s", "fastestLapSpeed", "statusId", "status",
                  "resultId", "n_raw_rows", "shared_drive", "best_positionOrder"}


def load_clean(data_dir=None, exclude_indy500=True, drop_non_starters=True, exclude_shared_drives=False):
    """Raw CSVs -> clean tables. Everybody on the team should start from this function.
    model_base = pre-race columns + target `podium` (one row per driver per race)
    outcomes   = post-race columns (status, points, ...) - never use these as features."""
    random.seed(SEED)
    np.random.seed(SEED)
    tables = clean_tables(load_raw_tables(data_dir or find_data_dir()))
    tables["races"] = flag_indy500(tables["races"], tables["circuits"])

    res = tables["results"].merge(tables["races"][["raceId", "year", "round", "date", "circuitId", "is_indy500"]],
                                  on="raceId", how="inner")
    res = res.merge(tables["status"], on="statusId", how="left")
    meta = {"raw_result_rows": len(tables["results"]), "after_race_join": len(res)}

    if exclude_indy500:
        meta["indy500_rows_removed"] = int(res["is_indy500"].sum())
        res = res[~res["is_indy500"]]
    res, dropped = keep_one_row_per_driver(res)
    meta["duplicate_rows_removed"] = len(dropped)
    res["is_non_starter"] = find_non_starters(res)
    if drop_non_starters:
        meta["non_starter_rows_removed"] = int(res["is_non_starter"].sum())
        res = res[~res["is_non_starter"]]
    if exclude_shared_drives:
        meta["shared_drive_rows_removed"] = int(res["shared_drive"].sum())
        res = res[~res["shared_drive"]]
    res = res.reset_index(drop=True)
    meta["final_rows"] = len(res)

    quali = tables["qualifying"].sort_values("qualifyId")
    meta["qualifying_duplicates_dropped"] = int(quali.duplicated(KEYS, keep="last").sum())
    quali = quali.drop_duplicates(KEYS, keep="last").rename(columns={"position": "qual_position"})
    quali = quali[KEYS + ["qual_position", "q1_s", "q2_s", "q3_s"]]

    res["pitlane_start"] = (res["grid"] == 0).fillna(False).astype(bool)
    base = res.merge(quali, on=KEYS, how="left", indicator=True)
    base["has_qualifying"] = base["_merge"] == "both"

    model_base = base[PRE_RACE_COLS].copy()
    model_base["podium"] = base["podium"].values
    outcomes = base[OUTCOME_COLS].copy()

    # safety checks
    assert not model_base.duplicated(KEYS).any(), "more than one row for a driver in a race"
    assert model_base[KEYS].notna().all().all(), "missing key"
    assert not (POST_RACE_COLS & set(model_base.columns)), "post-race column in the base table"
    return {"model_base": model_base, "outcomes": outcomes, "tables": tables, "meta": meta}

