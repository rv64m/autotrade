"""
Autotrade experiment runner. The LLM modifies this file.
Usage: uv run python -m src.train

The LLM writes a new strategy to src/strategies/generated/<name>.py,
then sets STRATEGY_FILE below to point to it.
"""

import warnings

import pandas as pd
from backtesting import Backtest

# Suppress backtesting.py margin warnings (noisy but not critical)
warnings.filterwarnings("ignore", message=".*insufficient margin.*", module="backtesting")

from src.prepare import load_ohlcv_data, prepare_settings
from src.strategies.loader import load_strategy

# ---------------------------------------------------------------------------
# Hyperparameters (LLM modifies these)
# ---------------------------------------------------------------------------

STRATEGY_FILE = "paxg_donchian_fibo_regime_4h.py"   # filename inside src/strategies/generated/
TIMEFRAME = "4h"       # candle interval: "1m", "5m", "15m", "1h", "4h", "1d", etc.
MAX_LEVERAGE = 1.0     # 1.0 = no leverage (spot); >1 for swap, e.g. 5.0 = 5x


# ---------------------------------------------------------------------------
# Backtest runner (do not modify)
# ---------------------------------------------------------------------------

def run_backtest() -> tuple[pd.DataFrame, Backtest, pd.Series, any]:
    if not STRATEGY_FILE:
        raise ValueError("STRATEGY_FILE is not set. Point it to a file in src/strategies/generated/.")

    settings = prepare_settings()
    settings.timeframe = TIMEFRAME

    data = load_ohlcv_data(settings)
    strategy_cls = load_strategy(STRATEGY_FILE)

    # margin = 1/leverage: 1.0 = no leverage (spot), 0.1 = up to 10x (swap)
    margin = 1.0 / MAX_LEVERAGE

    backtest = Backtest(
        data,
        strategy_cls,
        cash=settings.cash,
        commission=0.001,
        exclusive_orders=True,
        margin=margin,
    )
    stats = backtest.run()
    return data, backtest, stats, settings


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Run backtest for a strategy")
    parser.add_argument("--plot", action="store_true", help="Show interactive plot after backtest")
    args = parser.parse_args()

    t0 = time.time()
    data, backtest, stats, settings = run_backtest()
    elapsed = time.time() - t0

    # Drop internal backtesting fields (prefixed with _)
    public_stats = stats[~stats.index.str.startswith("_")]
    print(f"strategy:         {STRATEGY_FILE}")
    print(f"symbol:           {settings.symbol}")
    print(f"timeframe:        {TIMEFRAME}")
    print(f"max_leverage:     {MAX_LEVERAGE}")
    print(f"elapsed_seconds:  {elapsed:.1f}")
    print(public_stats.to_string())

    if args.plot:
        backtest.plot()
