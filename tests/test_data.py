"""Validation tests for the master dataset produced by the pipeline."""

import numpy as np
import pandas as pd
import pytest

from src import config


@pytest.fixture(scope="module")
def master() -> pd.DataFrame:
    assert config.MASTER_PATH.exists(), f"Missing {config.MASTER_PATH}"
    return pd.read_csv(config.MASTER_PATH)


def test_master_not_empty(master):
    assert len(master) > 0


def test_master_has_expected_columns(master):
    assert list(master.columns) == config.MASTER_COLUMNS


def test_all_configured_seasons_present(master):
    missing = set(config.YEARS) - set(master["year"].unique())
    assert not missing, f"Seasons missing from master dataset: {sorted(missing)}"


def test_no_duplicate_player_seasons(master):
    dupes = master.duplicated(subset=config.ID_COLUMNS)
    assert not dupes.any(), f"{dupes.sum()} duplicate (year, player_name) rows"


@pytest.mark.parametrize("stat", config.DERIVED_STATS, ids=lambda s: s.column)
def test_derived_stat_equals_sum_of_components(master, stat):
    cols = [*stat.components, stat.column]
    complete = master.dropna(subset=cols)
    assert len(complete) > 0, f"No complete rows to check {stat.column}"

    expected = complete[list(stat.components)].sum(axis=1)
    max_diff = (complete[stat.column] - expected).abs().max()
    assert np.isfinite(max_diff)
    assert max_diff < 1e-6, f"{stat.column} differs from its components by {max_diff}"
