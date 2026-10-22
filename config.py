"""Central settings. No secrets live in this project."""

CAPITAL_RS = 2000.0          # strict cap; the app never exceeds this
MAX_RISK_PCT = 1.0           # default max planned loss per trade (Rs 20)
MAX_ALLOCATION_PCT = 50.0    # my assumption: max share of capital in one position
MAX_HOLD_DAYS = 5            # used from Phase 4 onward
STALE_AFTER_DAYS = 4         # calendar days before a daily bar is "stale"
CACHE_TTL_SECONDS = 900      # data cached for up to 15 minutes
HISTORY_PERIOD = "2y"

BENCHMARKS = {"Nifty 50": "^NSEI", "Sensex": "^BSESN"}

# UNVERIFIED starting list. Nifty 50 membership and prices change, so check both.
DEFAULT_WATCHLIST = [
    "ITC", "ONGC", "COALINDIA", "NTPC",
    "POWERGRID", "TATASTEEL", "WIPRO", "SBIN",
]
