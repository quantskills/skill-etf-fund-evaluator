"""Peer-relative five-dimension ETF scoring."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

DIMENSION_WEIGHTS = {"tracking": 30.0, "risk_return": 25.0, "liquidity": 20.0, "scale_flow": 15.0, "robustness": 10.0}


def percentile_score(value: float | None, peers: list[float | None], higher_is_better: bool = True) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    values = [float(x) for x in peers if x is not None and math.isfinite(float(x))]
    if len(values) < 2:
        return None
    rank = sum(x <= value for x in values) / len(values) if higher_is_better else sum(x >= value for x in values) / len(values)
    return round(rank * 100, 1)


def weighted_available(items: list[tuple[str, float | None, float]]) -> tuple[float | None, float, list[dict[str, Any]]]:
    available = [(name, value, weight) for name, value, weight in items if value is not None and math.isfinite(float(value))]
    details = [{"name": name, "score": value, "weight": weight, "available": value is not None} for name, value, weight in items]
    if not available:
        return None, 0.0, details
    total = sum(weight for _, _, weight in available)
    score = sum(float(value) * weight for _, value, weight in available) / total
    return round(score, 1), round(total / sum(weight for _, _, weight in items) * 100, 1), details


def star_from_peer_rank(score: float | None, peer_scores: list[float | None], min_sample: int = 5) -> int | None:
    values = [float(x) for x in peer_scores if x is not None and math.isfinite(float(x))]
    if score is None or len(values) < min_sample:
        return None
    percentile = percentile_score(score, values, higher_is_better=True)
    if percentile is None:
        return None
    if percentile >= 90: return 5
    if percentile >= 75: return 4
    if percentile >= 25: return 3
    if percentile >= 10: return 2
    return 1


def score_dimension(metrics: dict[str, Any], peer_metrics: list[dict[str, Any]], specs: list[tuple[str, str, bool, float]]) -> dict[str, Any]:
    items = []
    details = []
    for label, key, higher, weight in specs:
        value = metrics.get(key)
        peers = [m.get(key) for m in peer_metrics]
        score = percentile_score(value, peers, higher)
        items.append((label, score, weight))
        details.append({"metric": key, "value": value, "score": score, "higher_is_better": higher, "weight": weight})
    score, coverage, _ = weighted_available(items)
    return {"score": score, "coverage_pct": coverage, "metrics": details}


def score_product(metrics: dict[str, Any], peer_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {
        "tracking": score_dimension(metrics, peer_metrics, [
            ("年化跟踪误差", "tracking_error", False, 30),
            ("跟踪偏离绝对值", "tracking_difference_abs", False, 20),
            ("R²", "r_squared", True, 20),
            ("Beta接近1", "beta_distance", False, 15),
            ("最大累计偏离", "max_cumulative_deviation", False, 15),
        ]),
        "risk_return": score_dimension(metrics, peer_metrics, [
            ("Sharpe", "sharpe", True, 25),
            ("Sortino", "sortino", True, 15),
            ("Calmar", "calmar", True, 15),
            ("年化收益", "annual_return", True, 15),
            ("最大回撤", "max_drawdown", True, 20),
            ("VaR", "var_95_daily", True, 10),
        ]),
        "liquidity": score_dimension(metrics, peer_metrics, [
            ("20日成交额", "amount_mean_20", True, 30),
            ("60日成交额", "amount_mean_60", True, 25),
            ("成交额稳定性", "zero_amount_pct_60", False, 15),
            ("折溢价稳定性", "premium_discount_abs_mean", False, 20),
            ("折溢价极值", "premium_discount_abs_max", False, 10),
        ]),
        "scale_flow": score_dimension(metrics, peer_metrics, [
            ("规模", "latest_size", True, 30),
            ("20日净流入", "net_inflow_20", True, 25),
            ("60日净流入", "net_inflow_60", True, 25),
            ("净流入持续性", "positive_inflow_days_60", True, 20),
        ]),
        "robustness": score_dimension(metrics, peer_metrics, [
            ("上市年限", "listed_years", True, 25),
            ("行情完整率", "data_completeness", True, 30),
            ("申赎开放率", "creation_redemption_rate", True, 20),
            ("申赎篮子可用率", "basket_availability", True, 15),
            ("存续状态", "active_status", True, 10),
        ]),
    }
    total_items = [(name, item["score"], DIMENSION_WEIGHTS[name]) for name, item in dimensions.items()]
    total, coverage, _ = weighted_available(total_items)
    return {"total_score": total, "coverage_pct": coverage, "dimensions": dimensions}
