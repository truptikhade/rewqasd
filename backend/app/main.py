import json
import os
from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import analysis
from .paths import ACTUALS_CSV, FORECASTS_CSV


def load_comparison() -> pd.DataFrame:
    if not (ACTUALS_CSV.exists() and FORECASTS_CSV.exists()):
        raise RuntimeError("Data files missing. Run: python -m app.ingest")
    actuals = analysis.prepare_actuals(pd.read_csv(ACTUALS_CSV))
    forecasts = analysis.prepare_forecasts(pd.read_csv(FORECASTS_CSV))
    return analysis.build_comparison(actuals, forecasts)


DF = load_comparison()

app = FastAPI(title="UK Wind Forecast Portal")
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_methods=["GET"], allow_headers=["*"])


def _records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    out["delivery_date"] = out["delivery_date"].astype(str)
    return json.loads(out.to_json(orient="records", date_format="iso"))


def _filter_day(day: str | None) -> pd.DataFrame:
    if day is None:
        return DF
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="day must be YYYY-MM-DD")
    result = DF[DF["delivery_date"] == d]
    if result.empty:
        raise HTTPException(status_code=404, detail="no January 2026 data for that day")
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "rows": len(DF)}


@app.get("/api/metrics")
def metrics():
    return analysis.compute_metrics(DF)


@app.get("/api/series")
def series(day: str | None = Query(None, description="UK delivery date, YYYY-MM-DD")):
    cols = ["startTime", "delivery_date", "cutoff", "publishTime",
            "lead_hours", "forecast_mw", "actual_mw", "error_mw"]
    return _records(_filter_day(day)[cols])


@app.get("/api/decision")
def decision(day: str = Query(..., description="UK delivery date, YYYY-MM-DD")):
    subset = _filter_day(day)
    d = date.fromisoformat(day)
    return {
        "delivery_date": day,
        "decision_cutoff_utc": analysis.decision_cutoff(d).isoformat(),
        "periods": int(len(subset)),
        "periods_with_forecast": int(subset["forecast_mw"].notna().sum()),
    }
