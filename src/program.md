# autotrade

Autonomous trading strategy research. The LLM iterates over strategies to optimize risk-adjusted returns.

## Setup

1. **Read the in-scope files**:
   - `src/prepare.py` — fixed: settings, data loading, evaluation. Do not modify.
   - `src/train.py` — the file you modify: `STRATEGY_FILE`, `TIMEFRAME`, `MAX_LEVERAGE`.
   - `src/strategies/base.py` — fixed: `BaseStrategy` base class. Do not modify.
   - `src/strategies/loader.py` — fixed: strategy loader. Do not modify.
2. **Verify data**: Run `uv run python -m src.train`. It will fail if `STRATEGY_FILE` is empty — that's expected before the first strategy is written.
3. **Initialize results.jsonl**: Create `./results.jsonl` as an empty file.
4. **Confirm and go**: Confirm setup looks good, then kick off the loop.

## Optimization Goals

The goal is **not just maximizing return** — a strategy must balance multiple objectives:

| Metric | Goal | Guideline |
|--------|------|-----------|
| **Return [%]** | Maximize | Primary profit metric |
| **Max. Drawdown [%]** | Minimize (less negative) | Aim to stay above `MAX_DRAWDOWN_LIMIT` (configured in `.env`) |
| **Profit Factor** | Maximize (>1.5 good, >2 excellent) | Strive to exceed `MIN_PROFIT_FACTOR` (configured in `.env`) |
| **Sharpe Ratio** | Maximize (>1 acceptable, >2 good) | No hard limit, but higher is better |

### Decision criteria

A strategy is a **keeper** if it improves on the current best in a balanced way:
- Higher `Return [%]` with similar or better drawdown
- Similar return but significantly lower `Max. Drawdown [%]`
- Better `Profit Factor` without sacrificing return

## Strategies

Each strategy lives in its own file under `src/strategies/generated/`. Discarded strategies are moved to `.trash/strategies/` to keep the working directory clean.

### Writing a strategy

Create a new file `src/strategies/generated/<name>.py`. Name it descriptively (e.g. `ema_crossover_rsi_4h.py`).

```python
# src/strategies/generated/ema_crossover_rsi_4h.py
import pandas as pd
import ta.trend
import ta.momentum

from src.strategies.base import BaseStrategy


class EmaCrossoverRsi(BaseStrategy):
    description = "EMA 50/200 crossover + RSI(14) filter, long-only, 4h"
    keep = False  # set to True after confirming it improves return_pct

    fast_window = 50
    slow_window = 200
    rsi_window = 14
    rsi_entry = 55

    def init(self) -> None:
        close = pd.Series(self.data.Close)
        self.fast_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.fast_window).ema_indicator().values
        )
        self.slow_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.slow_window).ema_indicator().values
        )
        self.rsi = self.I(
            lambda: ta.momentum.RSIIndicator(close, window=self.rsi_window).rsi().values
        )

    def next(self) -> None:
        if self.position:
            if self.fast_ema[-1] < self.slow_ema[-1]:
                self.position.close()
            return
        if self.fast_ema[-1] > self.slow_ema[-1] and self.rsi[-1] > self.rsi_entry:
            self.buy()
```

For swap markets, use leverage via position sizing: `self.buy(size=0.5)` for 50% of equity.

### Pointing train.py at the strategy

In `src/train.py`, set:
```python
STRATEGY_FILE = "ema_crossover_rsi_4h.py"
TIMEFRAME = "4h"
MAX_LEVERAGE = 1.0  # or e.g. 5.0 for 5x leverage on swap
```

## Output format

After each run, the script prints the strategy/timeframe/elapsed header followed by all backtesting metrics:

```
strategy:         ema_crossover_rsi_4h.py
timeframe:        4h
max_leverage:     1.0
elapsed_seconds:  2.0
Start                     2026-01-01 00:00:00+00:00
End                       2026-03-28 12:00:00+00:00
Duration                           86 days 12:00:00
Exposure Time [%]                         50.769231
Equity Final [$]                       117392.05579
Equity Peak [$]                        123947.04979
Commissions [$]                          1379.49421
Return [%]                                17.392056
Buy & Hold Return [%]                     -0.381128
Return (Ann.) [%]                         95.957728
Volatility (Ann.) [%]                      51.45616
CAGR [%]                                  96.721214
Sharpe Ratio                               1.864844
Sortino Ratio                              6.223883
Calmar Ratio                               6.826048
Alpha [%]                                  17.41927
Beta                                       0.071403
Max. Drawdown [%]                        -14.057581
Avg. Drawdown [%]                         -1.810152
Max. Drawdown Duration             52 days 20:00:00
Avg. Drawdown Duration              4 days 20:00:00
# Trades                                          7
Win Rate [%]                              57.142857
Best Trade [%]                            12.721248
Worst Trade [%]                           -5.938043
Avg. Trade [%]                             2.488295
Max. Trade Duration                11 days 08:00:00
Avg. Trade Duration                 6 days 03:00:00
Profit Factor                              2.952472
Expectancy [%]                             2.671982
SQN                                        1.013719
Kelly Criterion                            0.366353
```

Extract key metrics:
```
grep "^strategy:\|^Return\|^Sharpe\|^Max. Drawdown\|^Profit Factor\|^# Trades" run.log
```

## Logging results

Log every experiment to `src/results.jsonl` (JSON Lines — one JSON object per line).

```json
{
  "strategy_file": "ema_crossover_rsi_4h.py",
  "timeframe": "4h",
  "max_leverage": 1.0,
  "return_pct": 15.32,
  "sharpe": 1.24,
  "max_drawdown_pct": -8.5,
  "profit_factor": 2.95,
  "num_trades": 45,
  "win_rate_pct": 55.6,
  "status": "keep",
  "thoughts": "Hypothesis: EMA crossover with RSI filter reduces false signals in trending markets. Better return with acceptable drawdown (-8.5%) and strong profit factor (2.95).",
  "description": "EMA 50/200 crossover + RSI(14) filter, long-only, 4h"
}
```

- `status`: `keep`, `discard`, or `crash`
- `thoughts`: your reasoning — hypothesis, what you expected, what surprised you, why you discarded
- For crashes: `return_pct: 0.0`, document the error in `thoughts`

## Optimization approach

**DO NOT** get stuck iterating on a single strategy. Explore broadly first, then optimize the best performers.

### 1. Try different strategy types

Create a **new strategy file** for each fundamentally different approach. Don't just tweak parameters on one idea.

### 2. Adjust parameters and timeframes

Once a strategy type shows promise, tune it:
- Window lengths (e.g., EMA 20/50 vs 50/200)
- Entry/exit thresholds (e.g., RSI 30/70 vs 20/80)
- Timeframes (e.g., 1h vs 4h vs 1d)
- Create variants as separate files: `ema_cross_4h_v1.py`, `ema_cross_4h_v2.py`

### 3. Position scaling (pyramiding)

Build positions gradually instead of all-in. Use `self.buy(size=X)` where X is fraction of equity:

```python
def next(self) -> None:
    # Track how many scale-in levels we've entered
    if not hasattr(self, 'scale_level'):
        self.scale_level = 0

    # Entry signal
    if self.should_enter():
        if self.scale_level == 0:
            self.buy(size=0.3)  # first entry: 30%
            self.scale_level = 1
        elif self.scale_level == 1 and self.is_stronger_signal():
            self.buy(size=0.3)  # add 30% on confirmation
            self.scale_level = 2
        elif self.scale_level == 2 and self.is_even_stronger():
            self.buy(size=0.3)  # final 30%
            self.scale_level = 3

    # Exit: close all and reset
    if self.should_exit():
        self.position.close()
        self.scale_level = 0
```

Benefits of scaling:
- Lower average entry price if scaling into winners
- Reduces risk if first entry is wrong (only 30% exposed)
- Can improve Profit Factor by cutting losers early

## The experiment loop

LOOP FOREVER:

1. Write a new strategy file to `src/strategies/generated/<name>.py`.
2. Set `STRATEGY_FILE`, `TIMEFRAME`, and `MAX_LEVERAGE` in `src/train.py`.
3. Run: `uv run python -m src.train > run.log 2>&1`
4. Read results: `grep "^strategy:\|^Return\|^Sharpe\|^Max. Drawdown\|^Profit Factor\|^# Trades" run.log`
5. If grep is empty → crashed. Run `tail -n 50 run.log` to read the error. Fix simple bugs and re-run. If the idea is broken, log as `crash` and move the file to `.trash/strategies/`.
6. Log the result to `src/results.jsonl`.
7. **Evaluate against goals** (guidelines in `.env`):
   - Prefer strategies where `Max. Drawdown [%]` ≥ `MAX_DRAWDOWN_LIMIT` and `Profit Factor` ≥ `MIN_PROFIT_FACTOR`
   - Keep if: improves `Return [%]` without worsening drawdown, OR reduces drawdown significantly, OR improves `Profit Factor` meaningfully
8. If keeper: set `keep = True` in the strategy file.
9. If discard: move the strategy file to `.trash/strategies/`.

To move a discarded strategy:
```bash
mkdir -p .trash/strategies && mv src/strategies/generated/<name>.py .trash/strategies/
```

**NEVER STOP**: Once the loop begins, do NOT pause to ask the human if you should continue. The human may be away. You are autonomous. If you run out of ideas, think harder. The loop runs until the human interrupts you.

## Long/short for swap markets

When `MARKET_TYPE=swap`, the strategy can go both long and short. Use `self.sell()` to open a short position and `self.buy()` to close it (or vice versa). Example:

```python
def next(self) -> None:
    if self.fast_ema[-1] > self.slow_ema[-1]:
        if self.position.is_short:
            self.position.close()
        if not self.position.is_long:
            self.buy()
    elif self.fast_ema[-1] < self.slow_ema[-1]:
        if self.position.is_long:
            self.position.close()
        if not self.position.is_short:
            self.sell()
```