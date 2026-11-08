# Milestone 2: Formula 1 Knowledge Graph

Deadline: Tue 17 Nov 2026, 23:59. Full plan, rules and checks: [team plan page](https://claude.ai/artifact/JtDrBXDNRd2nfR1At82KgX).

## Setup (once per person)

1. Pull the latest `main`.
2. Install the driver: `pip install -r milestone2/requirements.txt`.
3. Copy the 9 CSVs from your `data/raw/` folder into `milestone2/`: `drivers`, `constructors`, `circuits`, `seasons`, `status`, `races`, `results`, `qualifying`, `pit_stops`.
4. In Neo4j Desktop, create a local database on version 5.13 or later and start it.
5. Copy `config.example.txt` to `config.txt` and put in your local password.

`config.txt` and the CSVs are ignored by git. This repo is public, so never commit a real password.

## Who owns what

| Person | Helpers | Loaders | Queries | Reviews |
|---|---|---|---|---|
| P1 | `read_config` | `load_drivers`, `load_status`, `load_races` | Q3 | P2 |
| P2 | `to_int`, `to_float`, `to_date` | `load_results`, `load_constructors` | Q1, Q2 | P3 |
| P3 | `clean`, `run_batched` | `load_qualifying`, `load_circuits` | Q5 | P4 |
| P4 | `read_csv` | `load_pitstops`, `load_seasons`, `create_constraints`, `main` | Q4 | P1 |

## How to work

1. Create your branch from `main`: `git checkout -b ms2/p1` (use your own number).
2. Edit only your own sections of `Create_kg.py` and your own blocks in `queries.txt`.
3. Run the script from VS Code and check the graph in Neo4j Browser.
4. Open a pull request and get your assigned reviewer's approval before merging.

## Timeline

| Date (Nov) | Goal |
|---|---|
| Mon 9 | Helpers shared by night |
| Thu 12 | All loaders done |
| Fri 13 | Merge everything, test queries on the full graph |
| Sat 14 | Queries done |
| Sun 15 | Reviews done |
| Mon 16 | Clean run and submit |
| Tue 17 | Buffer, deadline 23:59 |

## Keep `queries.txt` in the grader's format

- Save as UTF-8, with queries in order 1 to 5.
- Keep each `//1. Query 1` header exactly as written.
- Start each query with `MATCH` and end with `RETURN` plus any `ORDER BY`.
- Use no comments or semicolons inside a query.

Submit `Create_kg.py`, `config.txt` and `queries.txt` through the course form.
