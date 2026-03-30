from __future__ import annotations

from pathlib import Path

import pandas as pd

from .exceptions import CacheIOError
from .normalize import finalize_ohlcv
from .types import OHLCV_COLUMNS, PathLike, TimestampLike


def build_cache_path(
    cache_dir: PathLike,
    *,
    exchange_id: str,
    market_type: str,
    symbol: str,
    timeframe: str,
) -> Path:
    safe_symbol = normalize_symbol(symbol)
    filename = f"{exchange_id}_{market_type}_{safe_symbol}_{timeframe}.parquet"
    return Path(cache_dir) / filename


def read_ohlcv_cache(
    path: PathLike,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
) -> pd.DataFrame | None:
    cache_path = Path(path)
    if not cache_path.exists():
        return None

    try:
        frame = pd.read_parquet(cache_path)
    except Exception as exc:
        raise CacheIOError(f"Failed to read OHLCV cache from {cache_path}.") from exc

    if "Date" in frame.columns:
        frame = frame.set_index("Date")

    return finalize_ohlcv(
        frame,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
    )


def write_ohlcv_cache(path: PathLike, frame: pd.DataFrame) -> None:
    cache_path = Path(path)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache_path)
    except Exception as exc:
        raise CacheIOError(f"Failed to write OHLCV cache to {cache_path}.") from exc


def merge_ohlcv_frames(
    current: pd.DataFrame | None,
    incoming: pd.DataFrame | None,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
) -> pd.DataFrame:
    frames = [frame for frame in (current, incoming) if frame is not None and not frame.empty]
    if not frames:
        empty = pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
        empty.index.name = "Date"
        return empty.astype(float)

    merged = pd.concat(frames, axis=0)
    return finalize_ohlcv(
        merged,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
    )


def clip_ohlcv_frame(
    frame: pd.DataFrame,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: TimestampLike,
    end: TimestampLike | None = None,
) -> pd.DataFrame:
    return finalize_ohlcv(
        frame,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "_").replace(":", "_")
