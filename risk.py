"""Position-size calculator. Not a trade signal. Limits are never relaxed."""
import math


def size_position(capital, cash, entry, stop, max_risk_pct, max_alloc_pct,
                  fixed_costs_rs=0.0, target=None):
    cash = max(0.0, min(cash, capital))
    max_risk_rs = capital * max_risk_pct / 100.0
    res = {
        "shares": 0, "max_risk_rs": max_risk_rs, "by_risk": 0, "by_afford": 0,
        "position_value": 0.0, "gross_max_loss": 0.0, "total_max_loss": 0.0,
        "gross_reward": None, "net_reward": None, "reward_risk": None,
        "verdict": "",
    }
    if entry <= 0 or stop <= 0:
        res["verdict"] = "Entry and stop must be positive prices."
        return res
    loss_ps = entry - stop
    if loss_ps <= 0:
        res["verdict"] = "Stop must be below entry (long-only, cash segment)."
        return res
    budget = max_risk_rs - fixed_costs_rs
    if budget <= 0:
        res["verdict"] = "Your entered costs alone use up the whole risk budget."
        return res

    by_risk = math.floor(budget / loss_ps + 1e-9)
    alloc_cap = min(cash, capital * max_alloc_pct / 100.0)
    by_afford = math.floor(alloc_cap / entry + 1e-9)
    shares = max(0, min(by_risk, by_afford))
    res.update(by_risk=by_risk, by_afford=by_afford, shares=shares)

    if shares < 1:
        parts = []
        if by_risk < 1:
            parts.append("risk limit allows 0 shares at this stop distance")
        if by_afford < 1:
            parts.append("price exceeds cash/allocation cap")
        res["verdict"] = "NO POSITION POSSIBLE within your limits: " + "; ".join(parts) + "."
        return res

    res["position_value"] = shares * entry
    res["gross_max_loss"] = shares * loss_ps
    res["total_max_loss"] = shares * loss_ps + fixed_costs_rs
    if target and target > entry:
        gross = shares * (target - entry)
        res["gross_reward"] = gross
        res["net_reward"] = gross - fixed_costs_rs
        res["reward_risk"] = gross / res["gross_max_loss"]
    bound = "risk limit" if by_risk <= by_afford else "cash/allocation cap"
    res["verdict"] = f"{shares} share(s), limited by {bound}."
    return res
