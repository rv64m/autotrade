from __future__ import annotations

import argparse
from os import getenv
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .cache import build_cache_path, clip_ohlcv_frame, merge_ohlcv_frames, read_ohlcv_cache, write_ohlcv_cache
from .exceptions import CacheIOError
from .exchange import fetch_ohlcv_raw, timeframe_to_timedelta
from .normalize import normalize_ohlcv
from .types import MarketType, PathLike, TimestampLike

load_dotenv()

# Resolve project root relative to this file (src/data/crypto/loader.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_CACHE_DIR = _PROJECT_ROOT / ".data" / "crypto"


def load_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: TimestampLike,
    end: TimestampLike | None = None,
    market_type: MarketType = "spot",
    refresh: bool = True,
    cache_dir: PathLike | None = None,
    limit: int | None = None,
    max_retries: int | None = None,
    api_key: str | None = None,
    secret: str | None = None,
    password: str | None = None,
) -> pd.DataFrame:
    start_ts = _coerce_timestamp(start)
    end_ts = _coerce_timestamp(end) if end is not None else None
    step = timeframe_to_timedelta(timeframe)
    resolved_cache_dir = _resolve_cache_dir(cache_dir)
    cache_path = build_cache_path(
        resolved_cache_dir,
        exchange_id=exchange_id,
        market_type=market_type,
        symbol=symbol,
        timeframe=timeframe,
    )

    cached = read_ohlcv_cache(
        cache_path,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
    )

    if not refresh:
        if cached is None:
            raise CacheIOError(f"OHLCV cache does not exist at {cache_path}.")
        return clip_ohlcv_frame(
            cached,
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )

    if _cache_covers_request(cached, start=start_ts, end=end_ts):
        return clip_ohlcv_frame(
            cached,
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )

    merged = cached
    for missing_start, missing_end in _build_missing_ranges(cached, start=start_ts, end=end_ts, step=step):
        incoming = _fetch_segment(
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            market_type=market_type,
            start=missing_start,
            end=missing_end,
            limit=limit,
            max_retries=max_retries,
            api_key=api_key,
            secret=secret,
            password=password,
        )
        merged = merge_ohlcv_frames(
            merged,
            incoming,
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
        )

    if merged is not None:
        write_ohlcv_cache(cache_path, merged)

    return clip_ohlcv_frame(
        merged,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def _resolve_cache_dir(cache_dir: PathLike | None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)

    env_cache_dir = getenv("CRYPTO_CACHE_DIR")
    if env_cache_dir:
        return Path(env_cache_dir)

    return DEFAULT_CACHE_DIR


def _fetch_segment(
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    market_type: MarketType,
    start: pd.Timestamp,
    end: pd.Timestamp | None,
    limit: int | None,
    max_retries: int | None,
    api_key: str | None,
    secret: str | None,
    password: str | None,
) -> pd.DataFrame:
    incoming_rows = fetch_ohlcv_raw(
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        market_type=market_type,
        limit=limit,
        max_retries=max_retries,
        api_key=api_key,
        secret=secret,
        password=password,
    )
    return normalize_ohlcv(
        incoming_rows,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def _build_missing_ranges(
    cached: pd.DataFrame | None,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp | None,
    step: pd.Timedelta,
) -> list[tuple[pd.Timestamp, pd.Timestamp | None]]:
    if cached is None or cached.empty:
        return [(start, end)]

    ranges: list[tuple[pd.Timestamp, pd.Timestamp | None]] = []
    cache_start = cached.index[0]
    cache_end = cached.index[-1]

    if start < cache_start:
        left_end = min(end, cache_start - step) if end is not None else cache_start - step
        if start <= left_end:
            ranges.append((start, left_end))

    right_start = max(start, cache_end + step)
    if end is None:
        ranges.append((right_start, None))
    elif right_start <= end:
        ranges.append((right_start, end))

    return ranges


def _cache_covers_request(
    cached: pd.DataFrame | None,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp | None,
) -> bool:
    if cached is None or cached.empty:
        return False
    if cached.index[0] > start:
        return False
    if end is None:
        return False
    return cached.index[-1] >= end


def _coerce_timestamp(value: TimestampLike) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")

def main() -> None:
    # Example:
    # python3 -m src.data.crypto.loader \
    #   --exchange-id binance \
    #   --symbol BTC/USDT \
    #   --timeframe 1h \
    #   --start 2024-01-01 \
    #   --end 2024-01-31
    def _build_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Load crypto OHLCV data for manual testing.")
        parser.add_argument("--exchange-id", required=True, help="Exchange id supported by ccxt.")
        parser.add_argument("--symbol", required=True, help="Market symbol, for example BTC/USDT.")
        parser.add_argument("--timeframe", required=True, help="Timeframe, for example 1h.")
        parser.add_argument("--start", required=True, help="Start timestamp.")
        parser.add_argument("--end", help="End timestamp.")
        parser.add_argument(
            "--market-type",
            default="spot",
            choices=["spot", "swap"],
            help="Market type.",
        )
        parser.add_argument(
            "--refresh",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Fetch missing data when cache is not sufficient.",
        )
        parser.add_argument("--cache-dir", help="Override cache directory.")
        parser.add_argument("--limit", type=int, help="Page size for exchange.fetch_ohlcv.")
        parser.add_argument("--max-retries", type=int, help="Maximum retries for transient fetch failures.")
        parser.add_argument("--tail", type=int, default=5, help="Number of tail rows to print.")
        return parser

    args = _build_arg_parser().parse_args()
    frame = load_ohlcv(
        exchange_id=args.exchange_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        market_type=args.market_type,
        refresh=args.refresh,
        cache_dir=args.cache_dir,
        limit=args.limit,
        max_retries=args.max_retries,
    )

    print(f"rows={len(frame)}")
    if frame.empty:
        print("frame is empty")
        return

    print(f"start={frame.index[0].isoformat()}")
    print(f"end={frame.index[-1].isoformat()}")
    print("head:")
    print(frame.head(args.tail).to_string())
    print("tail:")
    print(frame.tail(args.tail).to_string())


if __name__ == "__main__":
    main()
