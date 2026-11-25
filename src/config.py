"""Central configuration for the pipeline, dashboard, and tests.

Paths, seasons, network settings, and the stat catalog live here so every
module reads from one source. Seasons and port can be overridden with the
environment variables PGA_YEARS and PORT.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (resolved from this file, so scripts work from any working directory)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTER_DIR = DATA_DIR / "intermediate"
PROC_DIR = DATA_DIR / "processed"
MASTER_PATH = PROC_DIR / "master_player_seasons.csv"


# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------
DEFAULT_YEARS = "2022-2025"


def parse_years(spec: str) -> list[int]:
    """Parse a season spec such as '2022-2025' or '2021,2023,2025'."""
    years: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(p) for p in part.split("-", 1))
            years.update(range(start, end + 1))
        else:
            years.add(int(part))
    if not years:
        raise ValueError(f"No seasons found in PGA_YEARS={spec!r}")
    return sorted(years)


YEARS = parse_years(os.environ.get("PGA_YEARS", DEFAULT_YEARS))


# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
STATS_URL = "https://www.pgatour.com/api/stats-download"
STATS_PARAMS = {"timePeriod": "THROUGH_EVENT", "tourCode": "R"}
REQUEST_TIMEOUT = 20   # seconds per request
REQUEST_DELAY = 1.0    # seconds between requests, to avoid hammering the API


# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


# ---------------------------------------------------------------------------
# Stat catalog
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Stat:
    key: str                     # file stem used in data/raw and data/intermediate
    column: str                  # column name in the master dataset
    label: str                   # display name on the dashboard
    higher_is_better: bool = True
    fmt: str = "decimal"         # "decimal" or "money"
    stat_id: str | None = None   # PGA TOUR stat ID; None for derived stats
    hints: tuple[str, ...] = ()  # substrings that identify the value column in raw CSVs
    components: tuple[str, ...] = field(default=())  # columns summed for derived stats


# Downloaded stats, in master-dataset column order.
SOURCE_STATS = [
    Stat("sg_total", "sg_total", "Strokes Gained: Total",
         stat_id="02675", hints=("mean", "avg", "average", "sg:total")),
    Stat("sg_ott", "sg_off_the_tee", "Strokes Gained: Off the Tee",
         stat_id="02567", hints=("mean", "avg", "average")),
    Stat("sg_app", "sg_approach", "Strokes Gained: Approach",
         stat_id="02568", hints=("mean", "avg", "average")),
    Stat("sg_arg", "sg_around_green", "Strokes Gained: Around the Green",
         stat_id="02569", hints=("mean", "avg", "average")),
    Stat("sg_putt", "sg_putting", "Strokes Gained: Putting",
         stat_id="02564", hints=("mean", "avg", "average")),
    Stat("driving_distance", "driving_distance", "Driving Distance (yards)",
         stat_id="101", hints=("avg", "average", "distance")),
    Stat("driving_accuracy", "driving_accuracy", "Driving Accuracy (%)",
         stat_id="102", hints=("%", "pct", "accuracy")),
    Stat("greens_in_regulation", "greens_in_regulation", "Greens in Regulation (%)",
         stat_id="103", hints=("%", "pct", "greens in reg")),
    Stat("scoring_average", "scoring_average", "Scoring Average (lower is better)",
         higher_is_better=False,
         stat_id="120", hints=("avg", "average", "mean")),
    Stat("money_earned", "money_earned", "Money Earned", fmt="money",
         stat_id="109", hints=("money", "earnings", "$", "amount")),
    Stat("fedex_rank", "final_season_rank", "Season Rank (1 is best)",
         higher_is_better=False,
         stat_id="02671", hints=("rank", "points", "fedexcup", "strokes", "finish position")),
]

# Stats computed from other columns during the master build.
DERIVED_STATS = [
    Stat("sg_tee_to_green", "sg_tee_to_green", "Strokes Gained: Tee to Green",
         components=("sg_off_the_tee", "sg_approach", "sg_around_green")),
]

ALL_STATS = SOURCE_STATS + DERIVED_STATS
STATS_BY_KEY = {s.key: s for s in SOURCE_STATS}
STATS_BY_COLUMN = {s.column: s for s in ALL_STATS}

ID_COLUMNS = ["year", "player_name"]
MASTER_COLUMNS = ID_COLUMNS + [s.column for s in ALL_STATS]

# Stats shown on the dashboard, in display order.
DASHBOARD_COLUMNS = [
    "money_earned",
    "sg_total",
    "sg_off_the_tee",
    "sg_tee_to_green",
    "sg_putting",
    "driving_accuracy",
    "driving_distance",
    "greens_in_regulation",
    "scoring_average",
    "final_season_rank",
]
DASHBOARD_STATS = [STATS_BY_COLUMN[c] for c in DASHBOARD_COLUMNS]

# The 2023+ FedEx ranking files have 8 data columns but only 7 header fields,
# so they are read with this explicit column list.
FEDEX_COLUMNS = [
    "RANK", "MOVEMENT", "PLAYER_ID", "PLAYER", "FINISH POSITION",
    "# OF WINS", "# OF TOP-10S", "FEDEXCUP STROKES",
]
