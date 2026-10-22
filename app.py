"""MarketPilot India, Phase 2: historical-data dashboard. Analysis only. No signals, no orders."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from data import load
from indicators import ema, sma
from risk import size_position
from validate import run_checks

st.set_page_config(page_title="MarketPilot India", layout="centered")

ICON = {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}


@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def cached_load(symbol, period, force_sample):
    return load(symbol, period, force_sample)


def norm(sym: str) -> str:
    s = sym.strip().upper()
    if not s or s.startswith("^") or s.endswith(".NS") or s.endswith(".BO"):
        return s
    return s + ".NS"


def last_info(res):
    c = res.df["Close"].dropna()
    last = float(c.iloc[-1])
    prev = float(c.iloc[-2]) if len(c) > 1 else last
    return last, (last / prev - 1) * 100, c.index[-1].date()


def show_source(res):
    if res.is_sample:
        st.error(f"⚠️ SAMPLE DATA for {res.symbol}: synthetic, not real. {res.note}")
    else:
        st.caption(f"Source: {res.source} · fetched {res.fetched_at_utc} "
                   f"(cached up to {config.CACHE_TTL_SECONDS // 60} min) · {res.note}")


# ---------------- Sidebar ----------------
st.sidebar.header("Settings")
st.sidebar.metric("Capital (set in config.py)", f"₹{config.CAPITAL_RS:,.0f}")
st.sidebar.caption(
    f"Max risk/trade: {config.MAX_RISK_PCT}% = ₹{config.CAPITAL_RS * config.MAX_RISK_PCT / 100:,.2f}\n\n"
    f"Max allocation/position: {config.MAX_ALLOCATION_PCT}%\n\n"
    f"Max hold: {config.MAX_HOLD_DAYS} trading days (used from Phase 4)"
)
force_sample = st.sidebar.checkbox("Force SAMPLE data (testing)", value=False)
wl_text = st.sidebar.text_area("Watchlist (NSE symbols, comma-separated)",
                               value=", ".join(config.DEFAULT_WATCHLIST))
symbols = list(dict.fromkeys(s for s in (norm(x) for x in wl_text.split(",")) if s))[:15]
st.sidebar.caption("Up to 15 symbols. '.NS' is added automatically.")

# ---------------- Header ----------------
st.title("MarketPilot India")
st.warning("Historical end-of-day data only. This is NOT live and NOT delayed-live. "
           "Analysis tool: no buy/sell signals and no orders. Not investment advice.")

if not symbols:
    st.info("Add at least one symbol in the sidebar.")
    st.stop()

with st.spinner("Loading data..."):
    bench = {n: cached_load(t, config.HISTORY_PERIOD, force_sample)
             for n, t in config.BENCHMARKS.items()}
    stocks = {s: cached_load(s, config.HISTORY_PERIOD, force_sample) for s in symbols}

sample_names = [r.symbol for r in [*bench.values(), *stocks.values()] if r.is_sample]
if sample_names:
    st.error("⚠️ SAMPLE DATA IN USE for: " + ", ".join(sample_names) +
             ". These are synthetic numbers, not real prices. Do not use them for decisions.")

tab_over, tab_chart, tab_dq, tab_risk, tab_about = st.tabs(
    ["Overview", "Chart", "Data quality", "Risk calc", "About"])

# ---------------- Overview ----------------
with tab_over:
    for name, res in bench.items():
        last, chg, d = last_info(res)
        kind = "SAMPLE" if res.is_sample else "end-of-day"
        st.metric(f"{name} ({kind})", f"{last:,.2f}", f"{chg:+.2f}%")
        st.caption(f"Last bar {d} · {res.source} · fetched {res.fetched_at_utc}")

    st.subheader("Watchlist")
    cap = config.CAPITAL_RS * config.MAX_ALLOCATION_PCT / 100
    rows = []
    for s, res in stocks.items():
        last, chg, d = last_info(res)
        statuses = [r["Status"] for r in run_checks(res.df, res.is_sample, config.STALE_AFTER_DAYS)]
        worst = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
        rows.append({
            "Symbol": s, "Last close ₹": round(last, 2), "Day %": round(chg, 2),
            "Last bar": str(d), "Data": "SAMPLE" if res.is_sample else "Yahoo EOD",
            "1 share ≤ cap?": "Yes" if last <= cap else "No",
            "Checks": ICON[worst],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(f"Cap = ₹{cap:,.0f} (capital × max allocation). 'Yes' means one share fits, "
               "not that it is a good trade.")

# ---------------- Chart ----------------
with tab_chart:
    sym = st.selectbox("Stock", symbols, key="chart_sym")
    bars = st.slider("Bars to show", 60, 500, 180)
    overlays = st.multiselect("Overlays", ["SMA 20", "SMA 50", "SMA 200", "EMA 20"],
                              default=["SMA 50", "EMA 20"])
    res = stocks[sym]
    show_source(res)
    df = res.df
    fig = go.Figure(go.Candlestick(x=df.index[-bars:], open=df["Open"].iloc[-bars:],
                                   high=df["High"].iloc[-bars:], low=df["Low"].iloc[-bars:],
                                   close=df["Close"].iloc[-bars:], name=sym))
    for o in overlays:
        kind, n = o.split()
        line = sma(df["Close"], int(n)) if kind == "SMA" else ema(df["Close"], int(n))
        fig.add_trace(go.Scatter(x=df.index[-bars:], y=line.iloc[-bars:], name=o, mode="lines"))
        if line.dropna().empty:
            st.caption(f"{o} unavailable: not enough history.")
    fig.update_layout(height=420, xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Data quality ----------------
with tab_dq:
    sym_q = st.selectbox("Stock", symbols, key="dq_sym")
    resq = stocks[sym_q]
    show_source(resq)
    checks = pd.DataFrame(run_checks(resq.df, resq.is_sample, config.STALE_AFTER_DAYS))
    checks["Status"] = checks["Status"].map(ICON)
    st.dataframe(checks, hide_index=True, use_container_width=True)

# ---------------- Risk calculator ----------------
with tab_risk:
    st.caption("Position-size calculator. Not a trade signal. Defaults below are placeholders; enter your own.")
    sym_r = st.selectbox("Stock", symbols, key="risk_sym")
    resr = stocks[sym_r]
    show_source(resr)
    last, _, _ = last_info(resr)
    entry = st.number_input("Planned entry ₹", min_value=0.01, value=round(last, 2),
                            step=0.05, format="%.2f", key=f"entry_{sym_r}")
    stop = st.number_input("Stop-loss ₹ (placeholder, set your own)", min_value=0.01,
                           value=round(last * 0.97, 2), step=0.05, format="%.2f",
                           key=f"stop_{sym_r}")
    target = st.number_input("Target ₹ (0 = none)", min_value=0.0, value=0.0,
                             step=0.05, format="%.2f", key=f"target_{sym_r}")
    cash = st.number_input("Available cash ₹", min_value=0.0, max_value=float(config.CAPITAL_RS),
                           value=float(config.CAPITAL_RS), step=50.0)
    costs = st.number_input("Total round-trip costs ₹ (YOU enter; unverified, default 0)",
                            min_value=0.0, value=0.0, step=1.0)
    if resr.is_sample:
        st.error("Entry is based on SAMPLE data. Do not use these numbers.")
    r = size_position(config.CAPITAL_RS, cash, entry, stop, config.MAX_RISK_PCT,
                      config.MAX_ALLOCATION_PCT, costs, target or None)
    if r["shares"] < 1:
        st.warning(r["verdict"])
    else:
        st.success(r["verdict"])
        c1, c2 = st.columns(2)
        c1.metric("Shares", r["shares"])
        c2.metric("Position value", f"₹{r['position_value']:,.2f}")
        c1.metric("Max loss, price only", f"₹{r['gross_max_loss']:,.2f}")
        c2.metric("Max loss incl. your costs", f"₹{r['total_max_loss']:,.2f}")
        if r["gross_reward"] is not None:
            c1.metric("Gross reward", f"₹{r['gross_reward']:,.2f}")
            c2.metric("Reward after your costs", f"₹{r['net_reward']:,.2f}")
            st.caption(f"Gross reward/risk: {r['reward_risk']:.2f}. Net figures are only as "
                       "accurate as the cost you typed in.")
    st.caption(f"Risk budget ₹{r['max_risk_rs']:,.2f}. Shares by risk: {r['by_risk']}, "
               f"by cash/allocation: {r['by_afford']}. A stop can fill worse than its price "
               "(gaps), so a real loss can exceed the plan.")

# ---------------- About ----------------
with tab_about:
    st.markdown(
        "- **Phase 2 build:** historical daily data only, no signals, no orders.\n"
        "- **Source:** Yahoo Finance via yfinance (unofficial). Treat as end-of-day.\n"
        "- **Sample fallback:** shown only with red warnings. Never real prices.\n"
        "- **Costs:** not modelled. Broker tariff needed (Phase 4).\n"
        "- **Hosting:** free Streamlit hosting may sleep when idle, so no background alerts.\n"
        "- **Not advice.** Results are never guaranteed."
    )
