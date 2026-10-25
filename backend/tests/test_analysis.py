from datetime import date

import pandas as pd

from app import analysis as a


def test_cutoff_is_11am_uk_day_before_delivery():
    # 1 Jan delivery -> decision at 11:00 UK on 31 Dec (GMT, so 11:00 UTC)
    assert a.decision_cutoff(date(2026, 1, 1)) == pd.Timestamp("2025-12-31T11:00:00Z")

def test_selects_latest_forecast_published_before_cutoff():
    raw_f = pd.DataFrame({
        "publishTime": ["2025-12-30T12:00:00Z",   # before cutoff -> should be used
                        "2025-12-31T12:00:00Z"],  # after 11:00 cutoff -> must be ignored
        "startTime": ["2026-01-01T00:00:00Z"] * 2,
        "generation": [100, 200],
    })
    raw_a = pd.DataFrame({
        "fuelType": ["WIND"],
        "startTime": ["2026-01-01T00:00:00Z"],
        "generation": [90],
    })

    df = a.build_comparison(a.prepare_actuals(raw_a), a.prepare_forecasts(raw_f))
    row = df[df["startTime"] == pd.Timestamp("2026-01-01T00:00:00Z")].iloc[0]

    assert row["forecast_mw"] == 100
    assert row["publishTime"] == pd.Timestamp("2025-12-30T12:00:00Z")
    assert row["error_mw"] == 10

def test_grid_has_744_january_hours():
    df = a.build_comparison(
        a.prepare_actuals(pd.DataFrame(columns=["fuelType", "startTime", "generation"])),
        a.prepare_forecasts(pd.DataFrame(columns=["publishTime", "startTime", "generation"])),
    )
    assert len(df) == 31 * 24


def test_metrics_use_only_evaluated_periods():
    raw_f = pd.DataFrame({
        "publishTime": ["2025-12-30T12:00:00Z"],
        "startTime": ["2026-01-01T00:00:00Z"],
        "generation": [100],
    })
    raw_a = pd.DataFrame({
        "fuelType": ["WIND"],
        "startTime": ["2026-01-01T00:00:00Z"],
        "generation": [90],
    })
    df = a.build_comparison(a.prepare_actuals(raw_a), a.prepare_forecasts(raw_f))
    m = a.compute_metrics(df)

    assert m["periods_evaluated"] == 1
    assert m["mae_mw"] == 10
    assert m["bias_mw"] == 10
