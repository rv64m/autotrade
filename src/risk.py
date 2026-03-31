"""
Risk control gate for autotrade experiments.

Responsibilities:
  - Hard leverage limit (pre-run): raises ValueError if MAX_LEVERAGE exceeds
    MAX_LEVERAGE_LIMIT, blocking the backtest entirely.
  - Soft drawdown target (post-run): checks whether Max. Drawdown breaches
    the safety floor. Failure means the strategy is unsafe — log as 'discard'
    and do NOT mark keep=True.
  - Invalid result detection: catches strategies that fired zero trades or
    produced NaN metrics (treated as a crash-level failure).

Configurable via .env:
    MAX_DRAWDOWN_LIMIT   e.g. -20  (soft safety floor, negative %)
    MAX_LEVERAGE_LIMIT   e.g. 5.0  (hard pre-run limit)

For profit optimization targets (MIN_PROFIT_FACTOR, MIN_RETURN_PCT) see
src/profit.py.
"""

from __future__ import annotations

import math
import pandas as pd

from src.prepare import Settings


# ---------------------------------------------------------------------------
# Hard check — runs BEFORE the backtest
# ---------------------------------------------------------------------------

def check_leverage_hard(leverage: float, settings: Settings) -> None:
    """
    Enforce the hard leverage ceiling.

    Raises ValueError if leverage exceeds settings.max_leverage_limit.
    The caller must NOT proceed to run the backtest; instead, lower
    MAX_LEVERAGE in train.py and re-run.
    """
    limit = settings.max_leverage_limit
    if leverage > limit:
        raise ValueError(
            f"[RISK] Hard limit violated: MAX_LEVERAGE={leverage}x exceeds "
            f"MAX_LEVERAGE_LIMIT={limit}x (set in .env). "
            f"Lower MAX_LEVERAGE in train.py to at most {limit}x and re-run."
        )


# ---------------------------------------------------------------------------
# Soft check — runs AFTER the backtest
# ---------------------------------------------------------------------------

def _is_invalid(value: float) -> bool:
    """Return True if a metric is nan or inf."""
    return math.isnan(value) or math.isinf(value)


def evaluate_risk(stats: pd.Series, settings: Settings) -> dict:
    """
    Evaluate backtest results against risk control thresholds.

    Checks (in order):
    1. Invalid result — zero trades or NaN key metrics → violations=['no_trades']
    2. Max drawdown safety floor — drawdown worse than MAX_DRAWDOWN_LIMIT

    A strategy that fails any check MUST be logged as status='discard' and
    CANNOT be marked keep=True.

    Returns:
        dict with keys:
            passed (bool):     True only if all risk checks pass.
            invalid (bool):    True if the strategy produced no usable result.
            violations (list): Human-readable failure descriptions.
            details (dict):    Per-metric breakdown.
    """
    num_trades        = int(stats.get("# Trades", 0) or 0)
    max_drawdown_pct  = float(stats.get("Max. Drawdown [%]", 0.0) or 0.0)
    profit_factor_raw = stats.get("Profit Factor", None)
    profit_factor     = float(profit_factor_raw) if profit_factor_raw is not None else float("nan")

    # --- Invalid / degenerate result ---
    if num_trades == 0 or _is_invalid(profit_factor):
        return {
            "passed":     False,
            "invalid":    True,
            "violations": [
                f"strategy produced {num_trades} trades — "
                f"no signals fired or entry conditions never met"
            ],
            "details": {
                "num_trades":         num_trades,
                "max_drawdown_pct":   max_drawdown_pct,
                "max_drawdown_limit": settings.max_drawdown_limit,
                "max_drawdown_ok":    False,
            },
        }

    # --- Drawdown safety floor ---
    drawdown_ok = max_drawdown_pct >= settings.max_drawdown_limit
    violations: list[str] = []
    if not drawdown_ok:
        violations.append(
            f"max drawdown {max_drawdown_pct:.1f}% breached safety floor "
            f"{settings.max_drawdown_limit}%"
        )

    return {
        "passed":     len(violations) == 0,
        "invalid":    False,
        "violations": violations,
        "details": {
            "num_trades":         num_trades,
            "max_drawdown_pct":   max_drawdown_pct,
            "max_drawdown_limit": settings.max_drawdown_limit,
            "max_drawdown_ok":    drawdown_ok,
        },
    }


def format_risk_summary(risk: dict) -> str:
    """
    One-line risk summary for printing after a run.

    Examples:
        risk_passed:  True  | max_drawdown: -8.5% ✓
        risk_passed:  False | max_drawdown: -35.2% ✗ (floor -20.0%)
        risk_passed:  False | INVALID — strategy produced 0 trades
    """
    if risk.get("invalid"):
        num = risk["details"].get("num_trades", 0)
        return (
            f"risk_passed:  False | INVALID — strategy produced {num} trades "
            f"(no signals fired or all metrics are NaN)"
        )

    d      = risk["details"]
    passed = risk["passed"]
    val    = d["max_drawdown_pct"]
    ok     = d["max_drawdown_ok"]
    mark   = "✓" if ok else f"✗ (floor {d['max_drawdown_limit']}%)"
    status = "True " if passed else "False"
    return f"risk_passed:  {status} | max_drawdown: {val:.1f}% {mark}"
