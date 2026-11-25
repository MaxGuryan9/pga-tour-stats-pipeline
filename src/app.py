"""Flask dashboard for the PGA TOUR master dataset.

Routes:
    /                      Leader for each stat in a season
    /category/<column>     Full ranking for one stat in a season
    /health                Liveness check
"""

import pandas as pd
from flask import Flask, jsonify, render_template, request

from src import config

app = Flask(__name__, template_folder=str(config.PROJECT_ROOT / "templates"))

if not config.MASTER_PATH.exists():
    raise FileNotFoundError(
        f"Could not find {config.MASTER_PATH}. Run the pipeline (build_master) first."
    )

# The dataset is small (about 1,000 rows), so load it once at startup.
df = pd.read_csv(config.MASTER_PATH)
YEARS_AVAILABLE = sorted(int(y) for y in df["year"].unique())
LATEST_YEAR = YEARS_AVAILABLE[-1]


def format_value(stat: config.Stat, value) -> str:
    """Format a stat value for display."""
    if pd.isna(value):
        return "N/A"
    if stat.fmt == "money":
        return f"${value:,.0f}"
    return f"{value:.3f}"


def selected_year() -> int:
    return request.args.get("year", default=LATEST_YEAR, type=int)


@app.route("/")
def index():
    year = selected_year()
    season = df[df["year"] == year]
    if season.empty:
        return f"No data available for year {year}", 404

    leaders = []
    for stat in config.DASHBOARD_STATS:
        if stat.column not in season.columns:
            continue
        values = season[stat.column].dropna()
        if values.empty:
            continue

        idx = values.idxmax() if stat.higher_is_better else values.idxmin()
        leaders.append(
            {
                "stat_label": stat.label,
                "player_name": season.at[idx, "player_name"],
                "value": format_value(stat, values[idx]),
                "col": stat.column,
            }
        )

    return render_template("index.html", year=year, years=YEARS_AVAILABLE, leaders=leaders)


@app.route("/category/<string:category>")
def category_view(category: str):
    year = selected_year()

    stat = next((s for s in config.DASHBOARD_STATS if s.column == category), None)
    if stat is None:
        return f"Unknown category '{category}'", 404

    season = df[df["year"] == year]
    if season.empty or category not in season.columns:
        return f"No data available for {category} in {year}", 404

    ranked = season.dropna(subset=[category]).sort_values(
        by=category, ascending=not stat.higher_is_better
    )
    if ranked.empty:
        return f"No values for {category} in {year}", 404

    rows = [
        {"rank": rank, "player_name": name, "value": format_value(stat, value)}
        for rank, (name, value) in enumerate(
            zip(ranked["player_name"], ranked[category]), start=1
        )
    ]

    return render_template(
        "category.html",
        year=year,
        years=YEARS_AVAILABLE,
        stat_label=stat.label,
        category=category,
        rows=rows,
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Local development server. The Docker image serves the app with gunicorn.
    app.run(host=config.HOST, port=config.PORT, debug=False)
