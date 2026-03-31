# Profit Optimization Reference

Performance screening using the institutional two-layer approach. A strategy that fails any check must be logged as `status='discard'` and **cannot** be marked `keep=True`.

---

## Layer 1 — Statistical Validity

Checked first. If Layer 1 fails, Layer 2 metrics are extracted but not meaningful.

| Metric | Guideline |
|--------|-----------|
| **# Trades** | Must reach `MIN_NUM_TRADES` — too few trades means all statistics are unreliable |
| **Exposure Time [%]** | Must reach `MIN_EXPOSURE_PCT` — filters strategies that rarely enter the market |

### Configuration

```
MIN_NUM_TRADES=30       # Minimum trade count; below this, metrics cannot be trusted
MIN_EXPOSURE_PCT=5.0    # Minimum % of backtest period holding a position
```

---

## Layer 2 — Risk-Adjusted Return

Institutional-standard metrics. Both are normalised to annual scale, so they are **directly comparable across any backtest length** (3 months, 6 months, 1 year).

| Metric | Formula | Guideline |
|--------|---------|-----------|
| **Sharpe Ratio** | Ann. return / Ann. volatility | Must reach `MIN_SHARPE_RATIO` · >1.0 acceptable, >2.0 excellent |
| **Calmar Ratio** | Ann. return / \|Max Drawdown\| | Must reach `MIN_CALMAR_RATIO` · >1.0 acceptable, >3.0 excellent |

**Informational only** (shown in output, not a gate): Profit Factor, Return (Ann.) [%]

### Configuration

```
MIN_SHARPE_RATIO=1.0    # Annualised return / volatility — comparable across any period length
MIN_CALMAR_RATIO=1.0    # Annualised return / max drawdown — reward per unit of worst-case risk
```

---

## Output

```
# All passing:
profit_passed: True  | trades: 45 ✓  exposure: 23.5% ✓  |  sharpe: 2.23 ✓  calmar: 20.6 ✓  (pf: 7.31  ret_ann: 36.1%)

# Layer 1 failure — sample too small:
profit_passed: False | trades: 4 ✗ (min 30)  exposure: 0.5% ✗ (min 5.0%)  |  sharpe: 2.23 ✓  calmar: 20.6 ✓  (pf: 7.31  ret_ann: 36.1%)

# Layer 2 failure — weak risk-adjusted return:
profit_passed: False | trades: 52 ✓  exposure: 18.2% ✓  |  sharpe: 0.61 ✗ (min 1.0)  calmar: 0.8 ✗ (min 1.0)  (pf: 1.2  ret_ann: 8.3%)
```

---

## Actions

| `profit_passed` | Action |
|-----------------|--------|
| `True` | Strategy is `ELIGIBLE` — evaluate return quality and decide keep/discard |
| `False` (Layer 1) | Sample too small or strategy barely trades — `status='discard'`, note in `thoughts`, explore more active strategies |
| `False` (Layer 2) | Risk-adjusted return insufficient — `status='discard'`, note in `thoughts`, try improving signal quality |

---

## Rules for `keep=True`

A strategy can only be marked `keep=True` if:
1. `risk_passed: True` — safety floors met (see `src/reference/risk.md`)
2. `profit_passed: True` — all four profit checks pass (trades, exposure, Sharpe, Calmar)
3. Return quality (Ann. return or Sharpe) improves on the current best keeper

If any condition fails, the strategy **CANNOT** be marked `keep=True`.
