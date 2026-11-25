"""Smoke tests for the Flask dashboard."""

import pytest

from src import config


def test_homepage_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"PGA Stat Leaders" in resp.data


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json == {"status": "ok"}


@pytest.mark.parametrize("year", config.YEARS)
def test_homepage_for_each_season(client, year):
    resp = client.get(f"/?year={year}")
    assert resp.status_code == 200
    assert str(year).encode() in resp.data


def test_unknown_season_returns_404(client):
    resp = client.get(f"/?year={min(config.YEARS) - 1}")
    assert resp.status_code == 404


@pytest.mark.parametrize("stat", config.DASHBOARD_STATS, ids=lambda s: s.column)
def test_category_page_for_each_stat(client, stat):
    resp = client.get(f"/category/{stat.column}?year={max(config.YEARS)}")
    assert resp.status_code == 200
    assert stat.label.encode() in resp.data


def test_unknown_category_returns_404(client):
    resp = client.get("/category/not_a_stat")
    assert resp.status_code == 404


def test_stylesheet_is_served(client):
    resp = client.get("/static/css/style.css")
    assert resp.status_code == 200
