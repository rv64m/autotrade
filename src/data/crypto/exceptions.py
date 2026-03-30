class CryptoDataError(Exception):
    """Base exception for crypto data errors."""


class ExchangeNotSupportedError(CryptoDataError):
    """Raised when the exchange id is not available in ccxt."""


class MarketTypeNotSupportedError(CryptoDataError):
    """Raised when the market type is not supported."""


class FetchOHLCVError(CryptoDataError):
    """Raised when OHLCV fetching fails."""


class NormalizeOHLCVError(CryptoDataError):
    """Raised when OHLCV normalization fails."""


class DataValidationError(CryptoDataError):
    """Raised when normalized OHLCV data is invalid."""


class CacheIOError(CryptoDataError):
    """Raised when cache read or write fails."""
