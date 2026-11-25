"""Step 2 of the pipeline: normalize raw stat CSVs into a common shape.

Each raw file in data/raw/<stat_key>_<year>.csv becomes
data/intermediate/<stat_key>_<year>.csv with columns:
    year, player_name, <stat column>
Run with: python -m src.parse_stats
"""

from pathlib import Path

import pandas as pd

from src import config

# Column-name keywords that rule a column out when guessing the value column.
NON_VALUE_KEYWORDS = ("rank", "this week", "last week", "event", "tournament", "round", "movement")


def normalize_col_name(col: str) -> str:
    """Lowercase, trim, and collapse internal whitespace for comparison."""
    return " ".join(col.strip().lower().split())


def to_numeric_clean(series: pd.Series) -> pd.Series:
    """Strip commas, dollar signs, and percent signs, then coerce to numbers."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def read_raw_csv(path: Path, stat: config.Stat) -> pd.DataFrame:
    """Read a raw CSV, tolerating the PGA API's occasional malformed rows."""
    kwargs = {}
    if stat.key == "fedex_rank":
        # 2023+ files have one more data column than header fields.
        kwargs = {"names": config.FEDEX_COLUMNS, "header": None, "skiprows": 1}

    try:
        return pd.read_csv(path, engine="python", **kwargs)
    except pd.errors.ParserError:
        print(f"[WARN] {path.name} has malformed rows; skipping them.")
        return pd.read_csv(path, engine="python", on_bad_lines="skip", **kwargs)


def find_player_name_column(df: pd.DataFrame) -> str:
    """Return the player-name column.

    Prefers a column containing 'player' (but not 'id'), then one containing
    'name', and falls back to the first column.
    """
    player_cols = []
    name_cols = []
    for col in df.columns:
        norm = normalize_col_name(col)
        if "player" in norm and "id" not in norm:
            player_cols.append(col)
        elif "name" in norm:
            name_cols.append(col)

    candidates = player_cols + name_cols
    return candidates[0] if candidates else df.columns[0]


def find_value_column(df: pd.DataFrame, stat: config.Stat) -> str:
    """Return the column holding the stat's value.

    Matches the stat's hints against column names first. If none match, picks
    the non-rank column with the most numeric values.
    """
    norm_map = {col: normalize_col_name(col) for col in df.columns}

    for col, norm in norm_map.items():
        if any(hint in norm for hint in stat.hints):
            return col

    player_col = find_player_name_column(df)
    numeric_counts = {
        col: to_numeric_clean(df[col]).notna().sum()
        for col in df.columns
        if col != player_col and not any(k in norm_map[col] for k in NON_VALUE_KEYWORDS)
    }
    numeric_counts = {col: n for col, n in numeric_counts.items() if n > 0}

    if not numeric_counts:
        raise ValueError(
            f"Could not identify a numeric value column for {stat.key!r}. "
            f"Columns: {list(df.columns)}"
        )

    best_col = max(numeric_counts, key=numeric_counts.get)
    print(f"[WARN] No hint matched for {stat.key!r}; using numeric column '{best_col}'.")
    return best_col


def parse_one_file(path: Path) -> pd.DataFrame:
    """Parse one raw CSV into a (year, player_name, <stat column>) DataFrame."""
    try:
        stat_key, year_str = path.stem.rsplit("_", 1)
        year = int(year_str)
    except ValueError:
        raise ValueError(f"Expected a filename like '<stat>_<year>.csv', got {path.name}")

    stat = config.STATS_BY_KEY.get(stat_key)
    if stat is None:
        raise ValueError(f"Unknown stat {stat_key!r}; add it to config.SOURCE_STATS.")

    df_raw = read_raw_csv(path, stat)
    player_col = find_player_name_column(df_raw)
    value_col = find_value_column(df_raw, stat)

    out = pd.DataFrame(
        {
            "year": year,
            "player_name": df_raw[player_col].astype(str).str.strip(),
            stat.column: to_numeric_clean(df_raw[value_col]),
        }
    )
    return out.dropna(subset=["player_name", stat.column])


def main() -> None:
    csv_paths = sorted(config.RAW_DIR.glob("*.csv"))
    if not csv_paths:
        print(f"No CSV files found in {config.RAW_DIR}. Run download_stats first.")
        return

    config.INTER_DIR.mkdir(parents=True, exist_ok=True)

    for path in csv_paths:
        try:
            df = parse_one_file(path)
        except Exception as e:
            print(f"[ERROR] Skipping {path.name}: {e}")
            continue

        out_path = config.INTER_DIR / path.name
        df.to_csv(out_path, index=False)
        if df.empty:
            print(f"[WARN] {out_path.name} has 0 rows; check the raw file.")
        else:
            print(f"Wrote {out_path.name} ({len(df)} rows)")

    print(f"Parsing complete. Output in {config.INTER_DIR.relative_to(config.PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
