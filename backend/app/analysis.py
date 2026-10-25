"""Core analysis logic. No network or file I/O, so it can be unit tested.

Definitions used throughout:
- A delivery hour is identified by its startTime (UTC), and each hour's actual is the mean of its two half-hourly values.
- Its delivery date is the UK local calendar date of that startTime.
- The day-ahead decision for a delivery date is made at DECISION_TIME_LOCAL
  on the day DECISION_LEAD_DAYS before delivery (UK local time).
- The forecast used for a half-hour is the latest one whose publishTime is
  at or before that decision cutoff.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

UK = ZoneInfo("Europe/London")

DELIVERY_START = datetime(2026, 1, 1, tzinfo=UK)   # inclusive
DELIVERY_END = datetime(2026, 2, 1, tzinfo=UK)     # exclusive

DECISION_LEAD_DAYS = 1              # decision is made 1 day before delivery
DECISION_TIME_LOCAL = time(11, 0)    # 11:00 UK time. Change to match the client's gate closure.


def decision_cutoff(delivery_day: date) -> pd.Timestamp:
    """Latest moment (UTC) a forecast can be published and still be used."""
    decision_day = delivery_day - timedelta(days=DECISION_LEAD_DAYS)
    local = datetime.combine(decision_day, DECISION_TIME_LOCAL, tzinfo=UK)
    return pd.Timestamp(local).tz_convert("UTC")


def _in_delivery_month(ts: pd.Series) -> pd.Series:
    local = ts.dt.tz_convert(UK)
    return (local >= DELIVERY_START) & (local < DELIVERY_END)


def prepare_actuals(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep WIND actuals for January, one row per half-hour."""
    df = raw.copy()
    if "fuelType" in df.columns:
        df = df[df["fuelType"] == "WIND"]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.drop_duplicates("startTime")
    df = df.rename(columns={"generation": "actual_mw"})[["startTime", "actual_mw"]]
    return df[_in_delivery_month(df["startTime"])].reset_index(drop=True)


def prepare_forecasts(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse forecast rows. One row per (startTime, publishTime)."""
    df = raw.copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.drop_duplicates(["startTime", "publishTime"])
    df = df.rename(columns={"generation": "forecast_mw"})
    return df[["startTime", "publishTime", "forecast_mw"]].reset_index(drop=True)


def select_latest_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """For each January half-hour, pick the latest forecast published before its cutoff."""
    f = forecasts[_in_delivery_month(forecasts["startTime"])].copy()
    f["delivery_date"] = f["startTime"].dt.tz_convert(UK).dt.date

    cutoffs = {d: decision_cutoff(d) for d in f["delivery_date"].unique()}
    f["cutoff"] = pd.to_datetime(f["delivery_date"].map(cutoffs), utc=True)

    f = f[f["publishTime"] <= f["cutoff"]]
    latest = f.loc[f.groupby("startTime")["publishTime"].idxmax()].copy()
    latest["lead_hours"] = (
        (latest["startTime"] - latest["publishTime"]).dt.total_seconds() / 3600
    )
    return latest.reset_index(drop=True)


def hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Average the half-hourly actuals within each hour, to match hourly forecasts."""
    df = actuals.copy()
    df["startTime"] = df["startTime"].dt.floor("h")
    return df.groupby("startTime", as_index=False)["actual_mw"].mean()


def build_comparison(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    """One row per January hour (744 rows), with forecast, actual and error."""
    latest = select_latest_forecasts(forecasts)
    hourly = hourly_actuals(actuals)

    grid_index = pd.date_range(DELIVERY_START, DELIVERY_END,
                               freq="h", inclusive="left")
    grid = pd.DataFrame({"startTime": grid_index.tz_convert("UTC")})

    df = (grid
          .merge(latest[["startTime", "publishTime", "cutoff",
                         "forecast_mw", "lead_hours"]],
                 on="startTime", how="left")
          .merge(hourly, on="startTime", how="left"))

    df["delivery_date"] = df["startTime"].dt.tz_convert(UK).dt.date
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df

def compute_metrics(df: pd.DataFrame) -> dict:
    """Error metrics over half-hours where both forecast and actual exist."""
    valid = df.dropna(subset=["forecast_mw", "actual_mw"])
    e = valid["error_mw"]
    return {
        "periods_total": int(len(df)),
        "periods_evaluated": int(len(valid)),
        "periods_missing_forecast": int(df["forecast_mw"].isna().sum()),
        "periods_missing_actual": int(df["actual_mw"].isna().sum()),
        "mae_mw": float(e.abs().mean()) if len(e) else None,
        "rmse_mw": float(np.sqrt((e ** 2).mean())) if len(e) else None,
        "bias_mw": float(e.mean()) if len(e) else None,
    }
