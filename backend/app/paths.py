from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
ACTUALS_CSV = DATA_DIR / "actuals_wind.csv"
FORECASTS_CSV = DATA_DIR / "forecasts_wind.csv"
