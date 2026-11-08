r"""CSEN903 Milestone 2: build the Formula 1 Knowledge Graph in Neo4j.

SKELETON. Replace each NotImplementedError with your own code, and edit only
the sections you own (see README.md). Do not rename functions or change their
inputs and outputs without telling the team.

Rules that apply to every section:
- Use MERGE, never CREATE, so re-running the script makes no duplicates.
- Omit missing values (the literal \N and empty cells). Never store them.
- Convert ids before using them, or MATCH finds nothing and relationships go
  missing with no error.
"""

import csv
from datetime import date
from pathlib import Path

from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parent


# =============================================================================
# SHARED HELPERS (agree on these on day 1, share them by Mon 9 Nov night)
# =============================================================================

# ----- P1 -----------------------------------------------------------------


def read_config(path=BASE_DIR / "config.txt"):
    """Return a dict with the keys URI, USERNAME and PASSWORD.

    Read each value by its key, never by its line number. Split each line at
    the first "=". The grader's file also has a DATABASE line: ignore it, and
    never hardcode a database name.
    """
    raise NotImplementedError


# ----- P4 -----------------------------------------------------------------


def read_csv(name):
    """Return a list of dicts for the CSV called name, for example "drivers.csv".

    Read from BASE_DIR with encoding="utf-8" and csv.DictReader. Do not use
    pandas, which turns 44 into 44.0 in columns with gaps.
    """
    with open(BASE_DIR / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ----- P2 -----------------------------------------------------------------


def to_int(value):
    r"""Return value as an int, or None if it is \N or empty."""
    raise NotImplementedError


def to_float(value):
    r"""Return value as a float, or None if it is \N or empty."""
    raise NotImplementedError


def to_date(value):
    r"""Return a Python date for "YYYY-MM-DD", or None if it is \N or empty.

    The Neo4j driver stores a Python date as a Neo4j date.
    """
    raise NotImplementedError


# ----- P3 -----------------------------------------------------------------


def clean(props):
    """Return a copy of the dict props without the keys whose value is None."""
    raise NotImplementedError


def run_batched(session, cypher, rows, size=5000):
    """Run cypher in batches of size, passing each batch as $rows.

    Use session.execute_write for each batch. The agreed query pattern is:
    UNWIND $rows AS row MERGE (n:Label {id: row.id}) SET n += row.props
    Then MATCH the parents and MERGE the relationships.
    """
    raise NotImplementedError


# =============================================================================
# P1: Driver, Status, Race
# =============================================================================


def load_drivers(session):
    """drivers.csv -> (:Driver)

    Key: driverId (int)
    Int: number
    Date: dob
    String: driverRef, code, forename, surname, nationality
    """
    raise NotImplementedError


def load_status(session):
    """status.csv -> (:Status)

    Key: statusId (int)
    String: status
    """
    raise NotImplementedError


def load_races(session):
    """races.csv -> (:Race)

    Key: raceId (int)
    Int: year, round
    Date: date
    String: name, time
    Relationships: (Race)-[:AT_CIRCUIT]->(Circuit), (Race)-[:IN_SEASON]->(Season)
    Do not store circuitId, url, or the fp*, quali_* and sprint_* columns.
    """
    raise NotImplementedError


# =============================================================================
# P2: Result, Constructor
# =============================================================================


def load_results(session):
    """results.csv -> (:Result)

    Key: resultId (int)
    Int: number, grid, position, positionOrder, laps, milliseconds, fastestLap, rank
    Float: points, fastestLapSpeed
    String: positionText, time, fastestLapTime
    Relationships: (Result)-[:FOR_RACE]->(Race), (Result)-[:BY_DRIVER]->(Driver),
    (Result)-[:FOR_CONSTRUCTOR]->(Constructor), (Result)-[:HAS_STATUS]->(Status)
    """
    raise NotImplementedError


def load_constructors(session):
    """constructors.csv -> (:Constructor)

    Key: constructorId (int)
    String: constructorRef
    Renames: name -> constructor_name, nationality -> constructor_nationality
    Do not store url.
    """
    raise NotImplementedError


# =============================================================================
# P3: Qualifying, Circuit
# =============================================================================


def load_qualifying(session):
    r"""qualifying.csv -> (:Qualifying)

    Key: qualifyId (int)
    Int: number, position
    String: q1, q2, q3 (each can be \N or empty: omit the property)
    Relationships: (Qualifying)-[:FOR_RACE]->(Race),
    (Qualifying)-[:BY_DRIVER]->(Driver),
    (Qualifying)-[:FOR_CONSTRUCTOR]->(Constructor)
    """
    raise NotImplementedError


def load_circuits(session):
    """circuits.csv -> (:Circuit)

    Key: circuitId (int)
    Int: alt
    Float: lat, lng
    String: circuitRef
    Renames: name -> circuit_name, location -> circuit_loc, country -> circuit_country
    Do not store url.
    """
    raise NotImplementedError


# =============================================================================
# P4: PitStop, Season, constraints, main
# =============================================================================


def load_pitstops(session):
    """pit_stops.csv -> (:PitStop)

    Key: eventId (string, built as "raceId:driverId:stop")
    Int: stop, lap, milliseconds
    String: time, duration (values like 16:44.718 exist, never parse as float)
    Relationships: (PitStop)-[:FOR_RACE]->(Race), (PitStop)-[:BY_DRIVER]->(Driver)
    """
    raise NotImplementedError


def load_seasons(session):
    """seasons.csv -> (:Season)

    Key: year (int)
    Do not store url.
    """
    raise NotImplementedError


def create_constraints(session):
    """Create 9 unique constraints with IF NOT EXISTS, before any data loads.

    Driver.driverId, Constructor.constructorId, Circuit.circuitId, Season.year,
    Status.statusId, Race.raceId, Result.resultId, Qualifying.qualifyId,
    PitStop.eventId
    """
    raise NotImplementedError


def main():
    """Connect using read_config(), open driver.session() with no database name.

    Load order: create_constraints, load_seasons, load_status, load_drivers,
    load_constructors, load_circuits, load_races, load_results,
    load_qualifying, load_pitstops.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()