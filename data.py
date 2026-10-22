"""Market-data layer. Phase 2: yfinance (unofficial) plus a clearly labelled sample fallback."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

COLS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass
class DataResult:
    symbol: str
    df: pd.DataFrame
    source: str
    is_sample: bool
    fetched_at_utc: str
    note: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def fetch_yfinance(symbol: str, period: str) -> pd.DataFrame:
    import yfinance as yf  # imported here so the app still starts if it is missing

    raw = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
    if raw is None or raw.empty:
        raise ValueError("provider returned no rows")
    df = raw[COLS].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def make_sample(symbol: str, n: int = 500) -> pd.DataFrame:
    """Deterministic synthetic random walk. NOT real market data."""
    rng = np.random.default_rng(sum(ord(c) for c in symbol))
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n)))
    open_ = close * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    vol = rng.integers(500_000, 5_000_000, n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=dates,
    )


def load(symbol: str, period: str = "2y", force_sample: bool = False) -> DataResult:
    if force_sample:
        reason = "sample data forced by user"
    else:
        try:
            df = fetch_yfinance(symbol, period)
            return DataResult(
                symbol, df, "Yahoo Finance via yfinance (unofficial)", False, _now(),
                "Daily bars, end-of-day/delayed. NOT live.",
            )
        except Exception as exc:  # network error, rate limit, bad symbol, schema change
            reason = f"{type(exc).__name__}: {exc}"
    return DataResult(
        symbol, make_sample(symbol), "SAMPLE (synthetic, not real market data)",
        True, _now(), f"Sample shown because: {reason}",
    )
