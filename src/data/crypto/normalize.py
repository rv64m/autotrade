from __future__ import annotations

import pandas as pd

from .exceptions import DataValidationError, NormalizeOHLCVError
from .types import OHLCV_COLUMNS, OHLCVRows, TimestampLike


def normalize_ohlcv(
    rows: OHLCVRows,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: TimestampLike | None = None,
    end: TimestampLike | None = None,
) -> pd.DataFrame:
    try:
        frame = pd.DataFrame(
            rows,
            columns=["timestamp", *OHLCV_COLUMNS],
        )
    except Exception as exc:
        raise NormalizeOHLCVError(
            f"Failed to build OHLCV DataFrame for {exchange_id} {symbol} {timeframe}."
        ) from exc

    return finalize_ohlcv(
        frame,
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def finalize_ohlcv(
    frame: pd.DataFrame,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: TimestampLike | None = None,
    end: TimestampLike | None = None,
) -> pd.DataFrame:
    if frame.empty:
        empty = pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
        empty.index.name = "Date"
        return empty.astype(float)

    try:
        normalized = frame.copy()

        if "timestamp" in normalized.columns:
            timestamp_index = pd.to_datetime(normalized.pop("timestamp"), unit="ms", utc=True)
        else:
            timestamp_index = pd.to_datetime(normalized.index, utc=True)

        normalized.index = pd.DatetimeIndex(timestamp_index, name="Date")
        normalized = normalized.loc[:, OHLCV_COLUMNS]
        normalized = normalized.apply(pd.to_numeric, errors="coerce").astype(float)
        normalized = normalized[~normalized.index.duplicated(keep="last")]
        normalized = normalized.sort_index()

        start_ts = _coerce_timestamp(start) if start is not None else None
        end_ts = _coerce_timestamp(end) if end is not None else None

        if start_ts is not None:
            normalized = normalized.loc[normalized.index >= start_ts]
        if end_ts is not None:
            normalized = normalized.loc[normalized.index <= end_ts]

        validate_ohlcv(
            normalized,
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
        )
        return normalized
    except DataValidationError:
        raise
    except Exception as exc:
        raise NormalizeOHLCVError(
            f"Failed to normalize OHLCV data for {exchange_id} {symbol} {timeframe}."
        ) from exc


def validate_ohlcv(
    frame: pd.DataFrame,
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
) -> None:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise DataValidationError(
            f"OHLCV index must be a DatetimeIndex for {exchange_id} {symbol} {timeframe}."
        )
    if frame.index.tz is None or str(frame.index.tz) != "UTC":
        raise DataValidationError(
            f"OHLCV index must be timezone-aware UTC for {exchange_id} {symbol} {timeframe}."
        )
    if not frame.index.is_monotonic_increasing:
        raise DataValidationError(
            f"OHLCV index must be sorted for {exchange_id} {symbol} {timeframe}."
        )
    if frame.index.has_duplicates:
        raise DataValidationError(
            f"OHLCV index contains duplicates for {exchange_id} {symbol} {timeframe}."
        )
    if list(frame.columns) != OHLCV_COLUMNS:
        raise DataValidationError(
            f"OHLCV columns must be {OHLCV_COLUMNS} for {exchange_id} {symbol} {timeframe}."
        )
    if frame.empty:
        return

    if frame[["Open", "High", "Low", "Close"]].isna().all().all():
        raise DataValidationError(
            f"OHLCV price columns are fully empty for {exchange_id} {symbol} {timeframe}."
        )

    invalid_high = frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1, skipna=True)
    if invalid_high.any():
        raise DataValidationError(
            f"High price invariant failed for {exchange_id} {symbol} {timeframe}."
        )

    invalid_low = frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1, skipna=True)
    if invalid_low.any():
        raise DataValidationError(
            f"Low price invariant failed for {exchange_id} {symbol} {timeframe}."
        )


def _coerce_timestamp(value: TimestampLike) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")
