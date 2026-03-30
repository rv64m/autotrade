from __future__ import annotations

import time
from os import getenv

import ccxt
import pandas as pd
from dotenv import load_dotenv

from .exceptions import ExchangeNotSupportedError, FetchOHLCVError, MarketTypeNotSupportedError
from .types import MarketType, OHLCVRows, SUPPORTED_MARKET_TYPES, TimestampLike

load_dotenv()

DEFAULT_FETCH_LIMIT = 1000
DEFAULT_FETCH_MAX_RETRIES = 3


def build_exchange(
    exchange_id: str,
    market_type: MarketType = "spot",
    api_key: str | None = None,
    secret: str | None = None,
    password: str | None = None,
) -> ccxt.Exchange:
    _validate_market_type(market_type)

    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None:
        raise ExchangeNotSupportedError(f"Exchange '{exchange_id}' is not supported by ccxt.")

    config: dict[str, object] = {
        "enableRateLimit": True,
        "options": {"defaultType": market_type},
    }
    http_proxy = getenv("CRYPTO_HTTP_PROXY")
    if http_proxy:
        config["httpProxy"] = http_proxy
        config["httpsProxy"] = http_proxy

    resolved_api_key = api_key or getenv("CRYPTO_API_KEY")
    resolved_secret = secret or getenv("CRYPTO_API_SECRET")
    resolved_password = password or getenv("CRYPTO_API_PASSWORD")

    if resolved_api_key:
        config["apiKey"] = resolved_api_key
    if resolved_secret:
        config["secret"] = resolved_secret
    if resolved_password:
        config["password"] = resolved_password

    return exchange_class(config)


def fetch_ohlcv_raw(
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: TimestampLike,
    end: TimestampLike | None = None,
    market_type: MarketType = "spot",
    limit: int | None = None,
    max_retries: int | None = None,
    api_key: str | None = None,
    secret: str | None = None,
    password: str | None = None,
) -> OHLCVRows:
    exchange = build_exchange(
        exchange_id,
        market_type=market_type,
        api_key=api_key,
        secret=secret,
        password=password,
    )
    start_ts = _to_timestamp_ms(start)
    end_ts = _to_timestamp_ms(end) if end is not None else None
    page_limit = limit or DEFAULT_FETCH_LIMIT
    retries = max_retries if max_retries is not None else _get_max_retries()
    timeframe_delta_ms = _timeframe_to_milliseconds(timeframe)

    rows: OHLCVRows = []
    since = start_ts

    try:
        while True:
            batch = _fetch_ohlcv_page(
                exchange,
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=page_limit,
                max_retries=retries,
            )
            if not batch:
                break

            rows.extend(batch)
            last_timestamp = int(batch[-1][0])
            if end_ts is not None and last_timestamp >= end_ts:
                break

            next_since = last_timestamp + timeframe_delta_ms
            if next_since <= since:
                break
            since = next_since

        return rows
    except Exception as exc:
        if isinstance(exc, FetchOHLCVError):
            raise
        raise FetchOHLCVError(
            f"Failed to fetch OHLCV for {exchange_id} {symbol} {timeframe}."
        ) from exc
    finally:
        _close_exchange(exchange)


def _fetch_ohlcv_page(
    exchange: ccxt.Exchange,
    *,
    symbol: str,
    timeframe: str,
    since: int,
    limit: int,
    max_retries: int,
) -> OHLCVRows:
    for attempt in range(max_retries + 1):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        except (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeNotAvailable) as exc:
            if attempt >= max_retries:
                raise FetchOHLCVError(
                    f"Temporary fetch failure for {exchange.id} {symbol} {timeframe} after retries."
                ) from exc
            sleep_seconds = max(exchange.rateLimit / 1000, 0.2) * (attempt + 1)
            time.sleep(sleep_seconds)
        except ccxt.BaseError as exc:
            raise FetchOHLCVError(
                f"Exchange error while fetching {exchange.id} {symbol} {timeframe}."
            ) from exc

    raise FetchOHLCVError(f"Failed to fetch OHLCV page for {exchange.id} {symbol} {timeframe}.")


def _validate_market_type(market_type: str) -> None:
    if market_type not in SUPPORTED_MARKET_TYPES:
        raise MarketTypeNotSupportedError(
            f"Market type '{market_type}' is not supported. Use one of {SUPPORTED_MARKET_TYPES}."
        )


def _timeframe_to_milliseconds(timeframe: str) -> int:
    seconds = ccxt.Exchange.parse_timeframe(timeframe)
    return int(seconds * 1000)


def timeframe_to_timedelta(timeframe: str) -> pd.Timedelta:
    return pd.Timedelta(milliseconds=_timeframe_to_milliseconds(timeframe))


def _to_timestamp_ms(value: TimestampLike) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return int(timestamp.timestamp() * 1000)


def _get_max_retries() -> int:
    raw_value = getenv("CRYPTO_FETCH_MAX_RETRIES")
    if not raw_value:
        return DEFAULT_FETCH_MAX_RETRIES
    return int(raw_value)


def _close_exchange(exchange: ccxt.Exchange) -> None:
    close = getattr(exchange, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass
