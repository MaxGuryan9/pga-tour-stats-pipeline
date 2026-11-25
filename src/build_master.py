"""Step 3 of the pipeline: merge per-stat files into master datasets.

Writes data/processed/master_<year>.csv for each season and
data/processed/master_player_seasons.csv with every season combined.
Run with: python -m src.build_master
"""

from functools import reduce

import pandas as pd

from src import config


def load_stat_for_year(stat: config.Stat, year: int) -> pd.DataFrame | None:
    """Load one intermediate file. Returns None if it has no data rows."""
    path = config.INTER_DIR / f"{stat.key}_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing intermediate file: {path.name}")

    df = pd.read_csv(path)
    missing = {*config.ID_COLUMNS, stat.column} - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")

    df = df[df["player_name"].notna()]
    if df.empty:
        return None
    return df[config.ID_COLUMNS + [stat.column]]


def add_derived_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute each derived stat as the sum of its component columns."""
    for stat in config.DERIVED_STATS:
        if all(c in df.columns for c in stat.components):
            df[stat.column] = df[list(stat.components)].sum(axis=1, skipna=False)
        else:
            print(f"[WARN] Missing components for {stat.column}; leaving it empty.")
    return df


def build_for_year(year: int) -> pd.DataFrame:
    """Outer-join every stat for one season so no player is dropped."""
    frames, loaded, skipped, empty = [], [], [], []

    for stat in config.SOURCE_STATS:
        try:
            df_stat = load_stat_for_year(stat, year)
        except (FileNotFoundError, ValueError) as e:
            skipped.append(stat.key)
            print(f"[WARN] {e}; skipping.")
            continue
        if df_stat is None:
            empty.append(stat.key)
            print(f"[WARN] {stat.key}_{year}.csv has no data rows; skipping.")
            continue
        frames.append(df_stat)
        loaded.append(stat.key)

    if not frames:
        raise ValueError(f"No data for {year}. Skipped: {skipped}, empty: {empty}")

    print(f"    Loaded {len(loaded)} stats: {', '.join(loaded)}")

    merged = reduce(
        lambda left, right: pd.merge(left, right, on=config.ID_COLUMNS, how="outer"),
        frames,
    )
    merged = add_derived_stats(merged)

    # Same column order every season; stats that failed to load become empty columns.
    for col in config.MASTER_COLUMNS:
        if col not in merged.columns:
            print(f"[WARN] Column '{col}' missing for {year}; filling with NaN.")
            merged[col] = float("nan")

    return (
        merged[config.MASTER_COLUMNS]
        .sort_values(config.ID_COLUMNS)
        .reset_index(drop=True)
    )


def main() -> None:
    config.PROC_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building master dataset for seasons: {config.YEARS}")

    all_years = []
    for year in config.YEARS:
        print(f"  -> {year}")
        df_year = build_for_year(year)
        out_year = config.PROC_DIR / f"master_{year}.csv"
        df_year.to_csv(out_year, index=False)
        print(f"     Saved {out_year.name} ({len(df_year)} rows)")
        all_years.append(df_year)

    master = pd.concat(all_years, ignore_index=True)
    master.to_csv(config.MASTER_PATH, index=False)
    print(f"Wrote {config.MASTER_PATH.name} ({len(master)} rows)")


if __name__ == "__main__":
    main()
