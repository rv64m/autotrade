"""
Fixed configuration and data loading for autotrade experiments.
Do not modify this file — it contains the fixed evaluation harness and settings.

Usage (from project root):
    uv run python -m src.train
"""

import os
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

from src.data.crypto.loader import load_ohlcv

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

TIME_BUDGET = 300  # seconds per experiment iteration (5 minutes)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass
class Settings:
    cash: float          # initial capital
    market: str          # "spot" or "swap"
    exchange_id: str
    symbol: str
    timeframe: str
    start: str
    end: str | None


def prepare_settings() -> Settings:
    load_dotenv(override=True)  # re-read .env on every call
    return Settings(
        cash=float(os.getenv("TOTAL_CASH", "100000")),
        market=os.getenv("MARKET_TYPE", "spot"),
        exchange_id=os.getenv("EXCHANGE_ID", "binance"),
        symbol=os.getenv("SYMBOL", "BTC/USDT"),
        timeframe=os.getenv("TIMEFRAME", "1h"),
        start=os.getenv("START_DATE", "2023-01-01"),
        end=os.getenv("END_DATE") or None,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ohlcv_data(settings: Settings) -> pd.DataFrame:
    return load_ohlcv(
        exchange_id=settings.exchange_id,
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        start=settings.start,
        end=settings.end,
        market_type=settings.market,
    )


# ---------------------------------------------------------------------------
# Evaluation (DO NOT CHANGE — this is the fixed metric)
# ---------------------------------------------------------------------------

def evaluate_strategy(stats: pd.Series) -> dict:
    """
    Extract key performance metrics from backtesting.py stats.
    return_pct is the primary metric — higher is better.
    """
    return {
        "return_pct": float(stats.get("Return [%]", 0.0)),
        "sharpe": float(stats.get("Sharpe Ratio", 0.0) or 0.0),
        "max_drawdown_pct": float(stats.get("Max. Drawdown [%]", 0.0)),
        "num_trades": int(stats.get("# Trades", 0)),
        "win_rate_pct": float(stats.get("Win Rate [%]", 0.0) or 0.0),
    }