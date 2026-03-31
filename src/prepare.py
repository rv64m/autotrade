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
    # Risk control (safety floors)
    max_drawdown_limit: float  # soft: max drawdown must stay above this % (e.g. -20.0)
    max_leverage_limit: float  # hard: max allowed leverage (e.g. 5.0)
    # Profit optimization — Layer 1: statistical validity
    min_num_trades: int        # minimum trade count for statistical reliability (e.g. 30)
    min_exposure_pct: float    # minimum % of time in a position (e.g. 5.0)
    # Profit optimization — Layer 2: risk-adjusted return
    min_sharpe_ratio: float    # minimum Sharpe Ratio (e.g. 1.0)
    min_calmar_ratio: float    # minimum Calmar Ratio = Ann.Return / MaxDrawdown (e.g. 1.0)


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
        # Risk control
        max_drawdown_limit=float(os.getenv("MAX_DRAWDOWN_LIMIT", "-10")),
        max_leverage_limit=float(os.getenv("MAX_LEVERAGE_LIMIT", "3.0")),
        # Profit optimization — Layer 1: statistical validity
        min_num_trades=int(os.getenv("MIN_NUM_TRADES", "30")),
        min_exposure_pct=float(os.getenv("MIN_EXPOSURE_PCT", "5.0")),
        # Profit optimization — Layer 2: risk-adjusted return
        min_sharpe_ratio=float(os.getenv("MIN_SHARPE_RATIO", "1.0")),
        min_calmar_ratio=float(os.getenv("MIN_CALMAR_RATIO", "1.0")),
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
        "profit_factor": float(stats.get("Profit Factor", 0.0) or 0.0),
        "num_trades": int(stats.get("# Trades", 0)),
        "win_rate_pct": float(stats.get("Win Rate [%]", 0.0) or 0.0),
    }