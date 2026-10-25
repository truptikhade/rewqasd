import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const JAN_DAYS = Array.from(
  { length: 31 },
  (_, i) => `2026-01-${String(i + 1).padStart(2, "0")}`,
);

const fmt = (x, d = 0) => (x == null ? "n/a" : Number(x).toFixed(d));
const ukTime = (iso) =>
  new Date(iso).toLocaleString("en-GB", {
    timeZone: "Europe/London",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

function MetricCard({ label, value, unit }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 12,
        minWidth: 150,
      }}
    >
      <div style={{ fontSize: 12, color: "#666" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600 }}>
        {value} {unit && <span style={{ fontSize: 13 }}>{unit}</span>}
      </div>
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [series, setSeries] = useState([]);
  const [day, setDay] = useState(""); // "" means the whole month
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/metrics`)
      .then((r) => r.json())
      .then(setMetrics)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    const url = day ? `${API}/api/series?day=${day}` : `${API}/api/series`;
    fetch(url)
      .then((r) => r.json())
      .then(setSeries)
      .catch((e) => setError(String(e)));
  }, [day]);

  const chartData = series.map((r) => ({
    ...r,
    label: ukTime(r.startTime),
  }));

  const publishTimes = series
    .map((r) => r.publishTime)
    .filter(Boolean)
    .sort();
  const cutoff = series[0]?.cutoff;

  return (
    <div
      style={{
        padding: 24,
        fontFamily: "sans-serif",
        maxWidth: 1100,
        margin: "0 auto",
      }}
    >
      <h1>UK Wind Generation: Forecast vs Actual (January 2026)</h1>
      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      <h2>Accuracy, whole month</h2>
      {metrics && (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <MetricCard label="MAE" value={fmt(metrics.mae_mw)} unit="MW" />
          <MetricCard label="RMSE" value={fmt(metrics.rmse_mw)} unit="MW" />
          <MetricCard
            label="Mean bias"
            value={fmt(metrics.bias_mw)}
            unit="MW"
          />
          <MetricCard
            label="Hours evaluated"
            value={`${metrics.periods_evaluated} / ${metrics.periods_total}`}
          />
        </div>
      )}
      {metrics &&
        (metrics.periods_missing_forecast > 0 ||
          metrics.periods_missing_actual > 0) && (
          <p style={{ fontSize: 13, color: "#8a5a00" }}>
            Missing data: {metrics.periods_missing_forecast} hours without a
            forecast, {metrics.periods_missing_actual} without an actual.
          </p>
        )}

      <h2>Forecast vs actual</h2>
      <label>
        Decision day:{" "}
        <select value={day} onChange={(e) => setDay(e.target.value)}>
          <option value="">Whole month</option>
          {JAN_DAYS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </label>

      {day && cutoff && (
        <p style={{ fontSize: 14 }}>
          Deliveries on {day} were decided at <b>{ukTime(cutoff)}</b> (UK). The
          forecasts used were published between <b>{ukTime(publishTimes[0])}</b>{" "}
          and <b>{ukTime(publishTimes[publishTimes.length - 1])}</b>.
        </p>
      )}

      <ResponsiveContainer width="100%" height={420}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" minTickGap={60} />
          <YAxis label={{ value: "MW", angle: -90, position: "insideLeft" }} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="actual_mw"
            name="Actual"
            dot={{ r: 1.5 }}
            connectNulls
            stroke="#1f77b4"
          />
          <Line
            type="monotone"
            dataKey="forecast_mw"
            name="Forecast (latest before decision)"
            stroke="#ff7f0e"
            dot={{ r: 1.5 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
