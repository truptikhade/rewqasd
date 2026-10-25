# UK Wind Generation: Forecast vs Actual Portal

Compares Elexon WINDFOR wind forecasts with FUELHH wind actuals for January 2026. For each delivery hour, it selects the latest forecast published by the day-ahead decision cutoff and compares it with the average of the two half-hourly actuals in that hour. The API reports MAE, RMSE, and bias over hours with both values available.

## Layout

- `backend/app/paths.py`: data file locations
- `backend/app/elexon_client.py`: Elexon API client (windowed requests, 429 retry)
- `backend/app/ingest.py`: downloads and caches raw data to `backend/data/` (run once)
- `backend/app/analysis.py`: pure analysis logic (cutoffs, latest-forecast selection, metrics)
- `backend/app/main.py`: FastAPI endpoints
- `backend/tests/test_analysis.py`: unit tests
- `frontend/src/App.jsx`: React dashboard (chart, metrics, decision-day selector)
- `docker-compose.yml`: runs both services locally

## Analysis

- The delivery period is January 2026 in UK local time, from 1 January inclusive to 1 February exclusive: 744 hourly periods.
- Elexon actuals are supplied at half-hourly resolution. The two actual values in each hour are averaged to match the hourly WINDFOR forecast.
- The forecast for each delivery hour is the latest forecast with a `publishTime` at or before the decision cutoff. A forecast published exactly at the cutoff is eligible.
- The decision cutoff is 11:00 UK time on the day before delivery (D-1).
- Error is forecast minus actual. Positive bias means the forecast was higher than actual generation.
- MAE, RMSE, and bias include only hours with both a forecast and an actual. Missing-period counts are reported separately.

## API

- `GET /api/health`: service status and number of hourly rows.
- `GET /api/metrics`: January-wide error metrics and missing-data counts.
- `GET /api/series`: hourly forecast and actual values for the month.
- `GET /api/series?day=YYYY-MM-DD`: hourly values for one UK delivery date.
- `GET /api/decision?day=YYYY-MM-DD`: decision cutoff and forecast coverage for one delivery date.

## Running locally

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
python -m app.ingest        # downloads data; check the printed row counts
pytest
uvicorn app.main:app --reload
```

Frontend (new terminal):

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

With Docker: `docker compose up --build`, then open http://localhost:8080.

## Live links

- https://rewqasd-n64s.vercel.app

## AI tool disclosure

GitHub Copilot in VS Code was used to assist with frontend refactoring, chart styling, and README updates. The changes were reviewed, and the frontend production build was run.
