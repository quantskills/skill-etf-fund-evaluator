"""Pure ETF performance, tracking, liquidity, and cash-flow metrics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _annualized_return(nav: pd.Series, periods_per_year: int = 252) -> float | None:
    values = nav.dropna()
    if len(values) < 2 or values.iloc[0] <= 0 or values.iloc[-1] <= 0:
        return None
    years = (len(values) - 1) / periods_per_year
    return float((values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1) if years > 0 else None


def max_drawdown(nav: pd.Series) -> dict[str, Any]:
    values = nav.dropna()
    if values.empty:
        return {"max_drawdown": None, "peak_date": None, "trough_date": None, "recovery_days": None}
    peaks = values.cummax()
    dd = values / peaks - 1
    trough = dd.idxmin()
    peak = values.loc[:trough].idxmax()
    recovery = None
    post = values.loc[trough:]
    recovered = post[post >= values.loc[peak]]
    if not recovered.empty:
        recovery = int((pd.Timestamp(recovered.index[0]) - pd.Timestamp(peak)).days)
    return {
        "max_drawdown": float(dd.min()),
        "peak_date": str(peak),
        "trough_date": str(trough),
        "recovery_days": recovery,
    }


def risk_return_metrics(frame: pd.DataFrame, risk_free_rate: float = 0.0) -> dict[str, Any]:
    if frame.empty or "date" not in frame.columns or "close" not in frame.columns:
        return {}
    df = frame.sort_values("date").copy()
    close = _series(df, "close")
    returns = close.pct_change().dropna()
    if returns.empty:
        return {}
    annual = _annualized_return(close)
    vol = float(returns.std(ddof=1) * math.sqrt(252)) if len(returns) > 1 else None
    downside = returns[returns < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(252)) if len(downside) > 1 else None
    excess = (annual - risk_free_rate) if annual is not None else None
    sharpe = excess / vol if excess is not None and vol else None
    sortino = excess / downside_vol if excess is not None and downside_vol else None
    dd = max_drawdown(pd.Series(close.to_numpy(), index=pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")))
    var95 = float(returns.quantile(0.05)) if len(returns) >= 20 else None
    calmar = annual / abs(dd["max_drawdown"]) if annual is not None and dd["max_drawdown"] else None
    return {
        "observations": int(len(returns)),
        "total_return": float(close.iloc[-1] / close.iloc[0] - 1),
        "annual_return": annual,
        "annual_volatility": vol,
        "downside_volatility": downside_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "var_95_daily": var95,
        **dd,
    }


def capture_metrics(etf: pd.Series, benchmark: pd.Series) -> dict[str, float | None]:
    data = pd.concat([etf.rename("etf"), benchmark.rename("benchmark")], axis=1).dropna()
    if len(data) < 12:
        return {"up_capture": None, "down_capture": None, "up_capture_ratio": None, "down_capture_ratio": None}
    er, br = data["etf"], data["benchmark"]
    up = br > 0
    down = br < 0
    up_capture = float(er[up].sum()) if up.any() else None
    down_capture = float(er[down].sum()) if down.any() else None
    up_bench = float(br[up].sum()) if up.any() else None
    down_bench = float(br[down].sum()) if down.any() else None
    return {
        "up_capture": up_capture,
        "down_capture": down_capture,
        "up_capture_ratio": up_capture / up_bench if up_bench else None,
        "down_capture_ratio": down_capture / down_bench if down_bench else None,
    }


def tracking_metrics(etf: pd.Series, benchmark: pd.Series) -> dict[str, float | None]:
    data = pd.concat([etf.rename("etf"), benchmark.rename("benchmark")], axis=1).dropna()
    if len(data) < 20:
        return {"observations": len(data), "tracking_error": None, "tracking_difference": None, "r_squared": None, "beta": None, "max_cumulative_deviation": None}
    diff = data["etf"] - data["benchmark"]
    cov = np.cov(data["etf"], data["benchmark"], ddof=1)[0, 1]
    var = float(data["benchmark"].var(ddof=1))
    beta = float(cov / var) if var else None
    corr = data["etf"].corr(data["benchmark"])
    cumulative = (1 + diff).cumprod() - 1
    return {
        "observations": int(len(data)),
        "tracking_error": float(diff.std(ddof=1) * math.sqrt(252)),
        "tracking_difference": float(diff.mean() * 252),
        "r_squared": float(corr**2) if pd.notna(corr) else None,
        "beta": beta,
        "max_cumulative_deviation": float(cumulative.abs().max()),
    }


def liquidity_metrics(frame: pd.DataFrame, flow_frame: pd.DataFrame | None = None) -> dict[str, Any]:
    if frame.empty:
        return {}
    amount = _series(frame, "amount").dropna()
    volume = _series(frame, "volume").dropna()
    result: dict[str, Any] = {
        "amount_mean_20": float(amount.tail(20).mean()) if len(amount) else None,
        "amount_median_20": float(amount.tail(20).median()) if len(amount) else None,
        "amount_mean_60": float(amount.tail(60).mean()) if len(amount) else None,
        "zero_amount_pct_60": float((amount.tail(60) <= 0).mean() * 100) if len(amount) else None,
        "volume_mean_20": float(volume.tail(20).mean()) if len(volume) else None,
    }
    if flow_frame is not None and not flow_frame.empty:
        f = flow_frame.sort_values("date")
        for window in (20, 60):
            net = _series(f, "net_inflow").tail(window)
            size = _series(f, "size").tail(window)
            shares_change = _series(f, "shares_change").tail(window)
            result[f"net_inflow_{window}"] = float(net.sum()) if len(net) else None
            result[f"net_inflow_pct_size_{window}"] = float(net.sum() / size.iloc[-1]) if len(net) and len(size) and size.iloc[-1] else None
            result[f"shares_change_{window}"] = float(shares_change.sum()) if len(shares_change) else None
            result[f"positive_inflow_days_{window}"] = int((net > 0).sum()) if len(net) else None
    return result


def premium_discount(nav_frame: pd.DataFrame, daily_frame: pd.DataFrame) -> dict[str, float | None]:
    if nav_frame.empty or daily_frame.empty or "date" not in nav_frame or "date" not in daily_frame:
        return {"premium_discount_mean": None, "premium_discount_abs_mean": None, "premium_discount_abs_max": None}
    left = nav_frame[[c for c in ("date", "reference_net", "unit_nav") if c in nav_frame]].copy()
    right = daily_frame[[c for c in ("date", "close") if c in daily_frame]].copy()
    merged = left.merge(right, on="date", how="inner")
    base = _series(merged, "reference_net").where(_series(merged, "reference_net") > 0, _series(merged, "unit_nav"))
    premium = _series(merged, "close") / base - 1
    premium = premium.replace([np.inf, -np.inf], np.nan).dropna()
    if premium.empty:
        return {"premium_discount_mean": None, "premium_discount_abs_mean": None, "premium_discount_abs_max": None}
    return {"premium_discount_mean": float(premium.mean()), "premium_discount_abs_mean": float(premium.abs().mean()), "premium_discount_abs_max": float(premium.abs().max())}
