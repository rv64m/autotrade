# Risk Control Reference

Safety floors that protect against dangerous strategy behavior. A strategy that breaches any floor must be logged as `status='discard'` (or `'crash'`) and **cannot** be marked `keep=True`.

## Metrics

| Metric | Type | Guideline |
|--------|------|-----------|
| **Max. Drawdown** | Soft floor | Must stay above `MAX_DRAWDOWN_LIMIT` — breach means unsafe |
| **Max. Leverage** | Hard limit | `train.py` raises `ValueError` if `MAX_LEVERAGE` exceeds `MAX_LEVERAGE_LIMIT` — fix before running |
| **Zero trades** | Auto-detected | Strategy produced no trades → treated as a crash |

## Configuration

```
# Risk control (.env)
MAX_DRAWDOWN_LIMIT=-20    # Safety floor: max drawdown must stay above this %
MAX_LEVERAGE_LIMIT=5.0    # Hard limit: MAX_LEVERAGE in train.py cannot exceed this
```

## Output

```
risk_passed:  True  | max_drawdown: -8.5% ✓
risk_passed:  False | max_drawdown: -35.2% ✗ (floor -20.0%)
risk_passed:  False | INVALID — strategy produced 0 trades (no signals fired or all metrics are NaN)
```

## Actions

| `risk_passed` | Action |
|---------------|--------|
| `True` | Proceed to profit check |
| `False` (drawdown) | Log `status='discard'`, record violation in `thoughts`, start next iteration |
| `False` (INVALID) | Log `status='crash'`, move file to `.trash/strategies/`, start next iteration |
