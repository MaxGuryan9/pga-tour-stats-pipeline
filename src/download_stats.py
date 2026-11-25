"""Step 1 of the pipeline: download raw stat CSVs from the PGA TOUR stats API.

Writes one file per stat per season to data/raw/<stat_key>_<year>.csv.
Run with: python -m src.download_stats
"""

import time

import requests

from src import config


def download_stat_csv(session: requests.Session, stat: config.Stat, year: int) -> None:
    """Download one stat for one season and save it to RAW_DIR."""
    params = {**config.STATS_PARAMS, "statsId": stat.stat_id, "year": year}
    out_path = config.RAW_DIR / f"{stat.key}_{year}.csv"

    print(f"Downloading {stat.key} ({stat.stat_id}) for {year}")
    resp = session.get(config.STATS_URL, params=params, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()

    out_path.write_bytes(resp.content)
    print(f"  Saved {out_path.relative_to(config.PROJECT_ROOT)}")


def main() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        for year in config.YEARS:
            for stat in config.SOURCE_STATS:
                download_stat_csv(session, stat, year)
                time.sleep(config.REQUEST_DELAY)

    print(f"Downloaded {len(config.SOURCE_STATS)} stats for seasons {config.YEARS}.")


if __name__ == "__main__":
    main()
