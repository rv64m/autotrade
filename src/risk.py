"""
Risk management gate for autotrade experiments.

Two levels of enforcement:

  Hard (pre-run):
    check_leverage_hard() — raises ValueError if MAX_LEVERAGE exceeds
    MAX_LEVERAGE_LIMIT. The Agent must fix train.py before re-running.

  Soft (post-run):
    evaluate_risk() — checks backtest results against target thresholds.
    Violations do NOT crash the run, but a strategy that fails soft targets
    MUST be marked status='discard'. It cannot be marked keep=True.

Configurable via .env:
    MAX_DRAWDOWN_LIMIT   e.g. -20  (soft target, negative %)
    MIN_PROFIT_FACTOR    e.g. 1.5  (soft target)
    MAX_LEVERAGE_LIMIT   e.g. 5.0  (hard limit)
"""

from __future__ import annotations

import pandas as pd

from src.prepare import Settings


# ---------------------------------------------------------------------------
# Hard check — runs BEFORE the backtest
# ---------------------------------------------------------------------------

def check_leverage_hard(leverage: float, settings: Settings) -> None:
    """
    Enforce the hard leverage ceiling.

    Raises ValueError if `leverage` exceeds `settings.max_leverage_limit`.
    The caller must NOT proceed to run the backtest; instead, lower
    MAX_LEVERAGE in train.py and re-run.

    Args:
        leverage: The MAX_LEVERAGE value set in train.py.
        settings: Loaded settings (contains max_leverage_limit from .env).

    Raises:
        ValueError: If leverage > max_leverage_limit.
    """
    limit = settings.max_leverage_limit
    if leverage > limit:
        raise ValueError(
            f"[RISK] Hard limit violated: MAX_LEVERAGE={leverage}x exceeds "
            f"MAX_LEVERAGE_LIMIT={limit}x (set in .env). "
            f"Lower MAX_LEVERAGE in train.py to at most {limit}x and re-run."
        )


# ---------------------------------------------------------------------------
# Soft evaluation — runs AFTER the backtest
# ---------------------------------------------------------------------------

def evaluate_risk(stats: pd.Series, settings: Settings) -> dict:
    """
    Evaluate backtest results against soft risk targets.

    Soft targets are guidelines, not hard walls. A strategy that fails one or
    more targets must be logged as status='discard' and CANNOT be marked
    keep=True in the strategy file.

    Args:
        stats:    The pd.Series returned by backtesting.py Backtest.run().
        settings: Loaded settings (contains soft target thresholds from .env).

    Returns:
        dict with keys:
            passed (bool):       True if ALL soft targets are met.
            violations (list):   Names of failed targets, empty if passed.
            details (dict):      Per-metric pass/fail breakdown with values.
    """
    max_drawdown_pct = float(stats.get("Max. Drawdown [%]", 0.0))
    profit_factor    = float(stats.get("Profit Factor", 0.0) or 0.0)
    sharpe           = float(stats.get("Sharpe Ratio", 0.0) or 0.0)

    drawdown_ok      = max_drawdown_pct >= settings.max_drawdown_limit
    profit_factor_ok = profit_factor >= settings.min_profit_factor

    violations: list[str] = []
    if not drawdown_ok:
        violations.append("max_drawdown")
    if not profit_factor_ok:
        violations.append("profit_factor")

    return {
        "passed":     len(violations) == 0,
        "violations": violations,
        "details": {
            "max_drawdown_pct":       max_drawdown_pct,
            "max_drawdown_limit":     settings.max_drawdown_limit,
            "max_drawdown_ok":        drawdown_ok,
            "profit_factor":          profit_factor,
            "min_profit_factor":      settings.min_profit_factor,
            "profit_factor_ok":       profit_factor_ok,
            # Sharpe is informational only — not a configurable target
            "sharpe":                 sharpe,
        },
    }


def format_risk_summary(risk: dict) -> str:
    """
    Return a human-readable one-line risk summary for printing after a run.

    Example output (passed):
        risk_passed:      True   | max_drawdown: -8.5% ✓  profit_factor: 2.95 ✓  sharpe: 1.86
    Example output (failed):
        risk_passed:      False  | max_drawdown: -35.2% ✗ (limit -20%)  profit_factor: 0.8 ✗ (min 1.5)  sharpe: 0.42
    """
    d = risk["details"]
    passed = risk["passed"]

    def dd_str() -> str:
        val = d["max_drawdown_pct"]
        ok  = d["max_drawdown_ok"]
        mark = "✓" if ok else f"✗ (limit {d['max_drawdown_limit']}%)"
        return f"max_drawdown: {val:.1f}% {mark}"

    def pf_str() -> str:
        val = d["profit_factor"]
        ok  = d["profit_factor_ok"]
        mark = "✓" if ok else f"✗ (min {d['min_profit_factor']})"
        return f"profit_factor: {val:.2f} {mark}"

    def sr_str() -> str:
        return f"sharpe: {d['sharpe']:.2f}"

    status = "True " if passed else "False"
    return f"risk_passed:      {status} | {dd_str()}  {pf_str()}  {sr_str()}"
