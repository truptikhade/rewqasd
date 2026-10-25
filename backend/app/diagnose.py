import pandas as pd
from app import analysis as a
from app.paths import FORECASTS_CSV

f = a.prepare_forecasts(pd.read_csv(FORECASTS_CSV))
f = f[a._in_delivery_month(f["startTime"])].copy()
f["delivery_date"] = f["startTime"].dt.tz_convert(a.UK).dt.date
f["cutoff"] = pd.to_datetime(f["delivery_date"].map(a.decision_cutoff), utc=True)

usable = f[f["publishTime"] <= f["cutoff"]]
summary = pd.DataFrame({
    "forecast_rows_total": f.groupby("delivery_date").size(),
    "forecast_rows_before_cutoff": usable.groupby("delivery_date").size(),
    "latest_publish_before_cutoff": usable.groupby("delivery_date")["publishTime"].max(),
}).fillna(0)

print(summary.to_string())

# NEW: distinct half-hours covered per day
covered = usable.groupby("delivery_date")["startTime"].nunique()
print(covered.to_string())
print("Total periods covered:", usable["startTime"].nunique(), "of 744")

one_day = usable[usable["delivery_date"] == pd.Timestamp("2026-01-01").date()]
print(one_day.groupby("publishTime")["startTime"]
      .agg(["min", "max", "count"]).tail(10).to_string())