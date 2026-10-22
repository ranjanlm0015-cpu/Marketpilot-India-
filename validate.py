"""Data-quality checks. Returns rows the dashboard shows in a table."""
import pandas as pd

from data import COLS

PRICE = ["Open", "High", "Low", "Close"]


def _row(check, status, detail):
    return {"Check": check, "Status": status, "Detail": detail}


def run_checks(df: pd.DataFrame, is_sample: bool, stale_after_days: int = 4) -> list[dict]:
    rows = []

    if is_sample:
        rows.append(_row("Data origin", "FAIL", "SAMPLE data: synthetic, never use for decisions"))

    n = len(df)
    rows.append(_row("History length", "PASS" if n >= 200 else "WARN",
                     f"{n} daily bars" + ("" if n >= 200 else " (<200: SMA200 unavailable)")))

    dups = int(df.index.duplicated().sum())
    rows.append(_row("Duplicate dates", "PASS" if dups == 0 else "FAIL", f"{dups} found"))

    missing = int(df[COLS].isna().sum().sum())
    rows.append(_row("Missing values", "PASS" if missing == 0 else "FAIL", f"{missing} cells"))

    p = df[PRICE]
    bad = int(((p <= 0).any(axis=1) | (df["High"] < df["Low"])
               | (df["Close"] > df["High"]) | (df["Close"] < df["Low"])).sum())
    rows.append(_row("Invalid prices", "PASS" if bad == 0 else "FAIL", f"{bad} bad bars"))

    zero_vol = int((df["Volume"] == 0).sum())
    rows.append(_row("Zero-volume days", "PASS" if zero_vol == 0 else "WARN", f"{zero_vol} days"))

    idx = df.index.unique().sort_values()
    gaps = int((idx.to_series().diff().dt.days > 4).sum()) if len(idx) > 1 else 0
    rows.append(_row("Date gaps >4 days", "PASS" if gaps == 0 else "WARN",
                     f"{gaps} gaps (some may be exchange holidays; no holiday calendar yet)"))

    jumps = int((df["Close"].pct_change().abs() > 0.15).sum())
    rows.append(_row("Moves >15% in a day", "PASS" if jumps == 0 else "WARN",
                     f"{jumps} days (could be news or an unadjusted split/bonus; not verified)"))

    if len(idx):
        last = idx[-1]
        age = (pd.Timestamp.today().normalize() - last).days
        rows.append(_row("Freshness", "PASS" if age <= stale_after_days else "FAIL",
                         f"last bar {last.date()} ({age} days old)"))
    return rows


def has_blocking_failure(rows: list[dict]) -> bool:
    """Later phases: any FAIL means no signals."""
    return any(r["Status"] == "FAIL" for r in rows)
