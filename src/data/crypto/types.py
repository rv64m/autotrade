from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeAlias

import ccxt
import pandas as pd

MarketType: TypeAlias = Literal["spot", "swap"]
OHLCVRow: TypeAlias = list[int | float | None]
OHLCVRows: TypeAlias = list[OHLCVRow]
TimestampLike: TypeAlias = pd.Timestamp | str
PathLike: TypeAlias = str | Path
ExchangeFactory: TypeAlias = Callable[[str], ccxt.Exchange]

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
SUPPORTED_MARKET_TYPES: tuple[MarketType, ...] = ("spot", "swap")
