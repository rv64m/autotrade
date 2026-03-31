# Risk Management Reference

## Metrics overview

| Metric | Type | Goal | Guideline |
|--------|------|------|-----------|
| **Return** | — | Maximize | Primary profit metric |
| **Max. Drawdown** | Soft target | Minimize (less negative) | Must stay above `MAX_DRAWDOWN_LIMIT` (from `.env`) to be eligible for `keep` |
| **Profit Factor** | Soft target | Maximize (>1.5 good, >2 excellent) | Must exceed `MIN_PROFIT_FACTOR` (from `.env`) to be eligible for `keep` |
| **Sharpe Ratio** | Informational | Maximize (>1 acceptable, >2 good) | Printed for reference only; not a configurable gate |
| **Max. Leverage** | Hard limit | Must not exceed `MAX_LEVERAGE_LIMIT` | `train.py` raises `ValueError` before running if violated — fix and re-run |

### Configuration (`.env` / `.env.example`)

```
# Soft targets — failing these means the strategy cannot be marked keep=True
MAX_DRAWDOWN_LIMIT=-20    # target: max drawdown must stay above this % (e.g. -20%)
MIN_PROFIT_FACTOR=1.5     # target: profit factor must be at least this value

# Hard limit — train.py raises ValueError if MAX_LEVERAGE exceeds this
MAX_LEVERAGE_LIMIT=5.0    # maximum allowed leverage multiplier
```

---

## Rules when `risk_passed: False`

1. Log `status='discard'` in `results.jsonl`.
2. Record the violated targets in `thoughts` (e.g. "drawdown hit -35%, exceeded -20% limit").
3. **You CANNOT set `keep = True`** in the strategy file — even if return looks impressive.
4. Move the file to `.trash/strategies/`.

---

## Decision criteria for `keep`

A strategy is a **keeper** if it **passes the risk gate** AND improves on the current best in a balanced way:

- Higher `Return` with similar or better drawdown
- Similar return but significantly lower `Max. Drawdown`
- Better `Profit Factor` without sacrificing return
