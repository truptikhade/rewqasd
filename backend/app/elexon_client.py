"""Thin client for the Elexon BMRS datasets API.

Requests are split into time windows so responses stay small and
429 (rate limit) responses are retried with backoff.
"""
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _windows(start: datetime, end: datetime, chunk_days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        yield cur, nxt
        cur = nxt


def fetch_dataset(dataset: str, start: datetime, end: datetime,
                  chunk_days: int = 3, max_retries: int = 5) -> pd.DataFrame:
    """Fetch a dataset filtered by publishTime between start and end (UTC)."""
    frames = []
    for w_from, w_to in _windows(start, end, chunk_days):
        params = {
            "publishDateTimeFrom": _fmt(w_from),
            "publishDateTimeTo": _fmt(w_to),
        }
        for attempt in range(max_retries):
            resp = requests.get(f"{BASE_URL}/{dataset}/stream",
                                params=params, timeout=120)
            if resp.status_code == 429:
                time.sleep(5 * 2 ** attempt)
                continue
            resp.raise_for_status()
            break
        else:
            raise RuntimeError(f"{dataset}: still rate limited after {max_retries} tries")

        data = resp.json()
        if data:
            frames.append(pd.DataFrame(data))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()
