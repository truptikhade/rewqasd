"""Download WIND actuals and WINDFOR forecasts and cache them as CSV.

Run once from the backend folder:
    python -m app.ingest
"""
from datetime import datetime, timezone

from .elexon_client import fetch_dataset
from .paths import ACTUALS_CSV, DATA_DIR, FORECASTS_CSV


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Forecasts published from 29 Dec so that the latest forecast before the
    # 31 Dec 00:00 UK cutoff (for 1 Jan deliveries) is included.
    fc = fetch_dataset("WINDFOR", utc(2025, 12, 29), utc(2026, 1, 31))
    fc[["publishTime", "startTime", "generation"]].to_csv(FORECASTS_CSV, index=False)

    # Actuals are published with a delay,so the window extends past the end of January.
    act = fetch_dataset("FUELHH", utc(2025, 12, 31), utc(2026, 2, 5))
    act = act[act["fuelType"] == "WIND"]
    act[["startTime", "generation"]].to_csv(ACTUALS_CSV, index=False)

    print(f"Forecast rows cached: {len(fc)}")
    print(f"Actual WIND rows cached: {len(act)}")


if __name__ == "__main__":
    main()
