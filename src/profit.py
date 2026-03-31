"""
Profit optimization evaluator for autotrade experiments.

Implements a two-layer institutional-grade screening process:

  Layer 1 — Statistical validity (checked first):
    MIN_NUM_TRADES     Minimum trade count; fewer trades = unreliable statistics.
    MIN_EXPOSURE_PCT   Minimum % of time holding a position; filters out strategies
                       that almost never trade.

  Layer 2 — Risk-adjusted return:
    MIN_SHARPE_RATIO   Annualised excess return / volatility. Comparable across any
                       backtest period length (3 months vs 12 months).
    MIN_CALMAR_RATIO   Annualised return / max drawdown. Rewards strategies that
                       earn well relative to their worst loss.

Informational (shown in output, not a gate):
    Profit Factor, Return (Ann.) [%]

Configurable via .env:
    MIN_NUM_TRADES      e.g. 30
    MIN_EXPOSURE_PCT    e.g. 5.0
    MIN_SHARPE_RATIO    e.g. 1.0
    MIN_CALMAR_RATIO    e.g. 1.0

Note: Zero-trade detection is handled upstream in src/risk.py (evaluate_risk).
      This module assumes at least one trade exists.
"""

from __future__ import annotations

import math
import pandas as pd

from src.prepare import Settings


def _safe_float(value, fallback: float = 0.0) -> float:
    """Convert a stat value to float, returning fallback for None/nan/inf."""
    if value is None:
        return fallback
    f = float(value)
    return fallback if (math.isnan(f) or math.isinf(f)) else f


def evaluate_profit(stats: pd.Series, settings: Settings) -> dict:
    """
    Evaluate backtest results using a two-layer profit screening process.

    Should be called AFTER evaluate_risk() passes (including the zero-trade
    check). If risk failed or result is invalid, skip this — it won't be
    meaningful.

    Layer 1 (statistical validity) is checked first. If it fails, Layer 2
    metrics are extracted but all violations are reported together so the
    Agent has the full picture.

    Returns:
        dict with keys:
            passed (bool):            True if ALL checks pass.
            layer1_passed (bool):     True if statistical validity checks pass.
            violations (list):        Human-readable failure descriptions.
            details (dict):           Per-metric breakdown with values and targets.
    """
    # --- Extract metrics ---
    num_trades    = int(stats.get("# Trades", 0) or 0)
    exposure_pct  = _safe_float(stats.get("Exposure Time [%]"))
    sharpe        = _safe_float(stats.get("Sharpe Ratio"))
    calmar        = _safe_float(stats.get("Calmar Ratio"))
    # Informational only
    profit_factor = _safe_float(stats.get("Profit Factor"))
    ann_return    = _safe_float(stats.get("Return (Ann.) [%]"))

    # --- Layer 1: Statistical validity ---
    trades_ok   = num_trades  >= settings.min_num_trades
    exposure_ok = exposure_pct >= settings.min_exposure_pct

    # --- Layer 2: Risk-adjusted return ---
    sharpe_ok = sharpe >= settings.min_sharpe_ratio
    calmar_ok = calmar >= settings.min_calmar_ratio

    violations: list[str] = []

    # Layer 1 violations (always checked)
    if not trades_ok:
        violations.append(
            f"{num_trades} trades is below minimum {settings.min_num_trades} "
            f"— sample too small, metrics unreliable"
        )
    if not exposure_ok:
        violations.append(
            f"exposure time {exposure_pct:.1f}% is below minimum {settings.min_exposure_pct}% "
            f"— strategy rarely in market"
        )

    # Layer 2 violations (always checked, but less meaningful if Layer 1 fails)
    if not sharpe_ok:
        violations.append(
            f"Sharpe Ratio {sharpe:.2f} is below target {settings.min_sharpe_ratio}"
        )
    if not calmar_ok:
        violations.append(
            f"Calmar Ratio {calmar:.2f} is below target {settings.min_calmar_ratio}"
        )

    return {
        "passed":        len(violations) == 0,
        "layer1_passed": trades_ok and exposure_ok,
        "violations":    violations,
        "details": {
            # Layer 1
            "num_trades":        num_trades,
            "min_num_trades":    settings.min_num_trades,
            "trades_ok":         trades_ok,
            "exposure_pct":      exposure_pct,
            "min_exposure_pct":  settings.min_exposure_pct,
            "exposure_ok":       exposure_ok,
            # Layer 2
            "sharpe":            sharpe,
            "min_sharpe_ratio":  settings.min_sharpe_ratio,
            "sharpe_ok":         sharpe_ok,
            "calmar":            calmar,
            "min_calmar_ratio":  settings.min_calmar_ratio,
            "calmar_ok":         calmar_ok,
            # Informational
            "profit_factor":     profit_factor,
            "ann_return_pct":    ann_return,
        },
    }


def format_profit_summary(profit: dict) -> str:
    """
    Two-line profit summary for printing after a run.

    Examples (passed):
        profit_passed: True  | trades: 45 ✓  exposure: 23.5% ✓  |  sharpe: 2.23 ✓  calmar: 20.6 ✓  (pf: 7.31  ret_ann: 36.1%)

    Examples (failed):
        profit_passed: False | trades: 4 ✗ (min 30)  exposure: 0.5% ✗ (min 5.0%)  |  sharpe: 2.23 ✓  calmar: 20.6 ✓  (pf: 7.31  ret_ann: 36.1%)
    """
    d      = profit["details"]
    passed = profit["passed"]
    status = "True " if passed else "False"

    def trades_str() -> str:
        val, ok = d["num_trades"], d["trades_ok"]
        mark = "✓" if ok else f"✗ (min {d['min_num_trades']})"
        return f"trades: {val} {mark}"

    def exposure_str() -> str:
        val, ok = d["exposure_pct"], d["exposure_ok"]
        mark = "✓" if ok else f"✗ (min {d['min_exposure_pct']}%)"
        return f"exposure: {val:.1f}% {mark}"

    def sharpe_str() -> str:
        val, ok = d["sharpe"], d["sharpe_ok"]
        mark = "✓" if ok else f"✗ (min {d['min_sharpe_ratio']})"
        return f"sharpe: {val:.2f} {mark}"

    def calmar_str() -> str:
        val, ok = d["calmar"], d["calmar_ok"]
        mark = "✓" if ok else f"✗ (min {d['min_calmar_ratio']})"
        return f"calmar: {val:.2f} {mark}"

    info = f"(pf: {d['profit_factor']:.2f}  ret_ann: {d['ann_return_pct']:.1f}%)"

    return (
        f"profit_passed: {status} | "
        f"{trades_str()}  {exposure_str()}  |  "
        f"{sharpe_str()}  {calmar_str()}  {info}"
    )
