import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility

from src.strategies.base import BaseStrategy


class PaxgDonchianFiboRegime4h(BaseStrategy):
    description = "PAXG 4h Donchian + Fibo EMA (8/21) + volume + ATR regime filter"
    keep = True

    fast_window = 8
    slow_window = 21
    breakout_window = 20
    exit_window = 6
    volume_window = 20
    atr_window = 14
    atr_regime_window = 20
    stop_atr = 1.8
    rsi_window = 14
    long_rsi = 54
    short_rsi = 46

    def init(self) -> None:
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)

        self.fast_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.fast_window).ema_indicator().values
        )
        self.slow_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.slow_window).ema_indicator().values
        )
        self.rsi = self.I(
            lambda: ta.momentum.RSIIndicator(close, window=self.rsi_window).rsi().values
        )
        self.atr = self.I(
            lambda: ta.volatility.AverageTrueRange(
                high, low, close, window=self.atr_window
            ).average_true_range().values
        )
        self.atr_sma = self.I(
            lambda: ta.trend.SMAIndicator(
                pd.Series(self.atr), window=self.atr_regime_window
            ).sma_indicator().values
        )
        self.volume_sma = self.I(
            lambda: ta.trend.SMAIndicator(volume, window=self.volume_window).sma_indicator().values
        )
        self.breakout_high = self.I(
            lambda: high.shift(1).rolling(self.breakout_window).max().values
        )
        self.breakout_low = self.I(
            lambda: low.shift(1).rolling(self.breakout_window).min().values
        )
        self.exit_high = self.I(
            lambda: high.shift(1).rolling(self.exit_window).max().values
        )
        self.exit_low = self.I(
            lambda: low.shift(1).rolling(self.exit_window).min().values
        )

    def next(self) -> None:
        if len(self.data.Close) < max(self.slow_window + 3, self.atr_regime_window):
            return

        price = self.data.Close[-1]
        volume = self.data.Volume[-1]
        atr = self.atr[-1]
        trend_up = self.fast_ema[-1] > self.slow_ema[-1] and self.slow_ema[-1] > self.slow_ema[-3]
        trend_down = self.fast_ema[-1] < self.slow_ema[-1] and self.slow_ema[-1] < self.slow_ema[-3]
        volatility_expanding = atr > self.atr_sma[-1]

        if self.position:
            entry_price = self.trades[-1].entry_price if self.trades else price
            if self.position.is_long:
                stop_price = entry_price - atr * self.stop_atr
                if (
                    price < stop_price
                    or price < self.exit_low[-1]
                    or self.fast_ema[-1] < self.slow_ema[-1]
                    or self.rsi[-1] < 50
                ):
                    self.position.close()
            else:
                stop_price = entry_price + atr * self.stop_atr
                if (
                    price > stop_price
                    or price > self.exit_high[-1]
                    or self.fast_ema[-1] > self.slow_ema[-1]
                    or self.rsi[-1] > 50
                ):
                    self.position.close()
            return

        if (
            trend_up
            and volatility_expanding
            and price > self.breakout_high[-1]
            and self.rsi[-1] > self.long_rsi
            and volume > self.volume_sma[-1]
        ):
            self.buy(size=0.95)
            return

        if (
            trend_down
            and volatility_expanding
            and price < self.breakout_low[-1]
            and self.rsi[-1] < self.short_rsi
            and volume > self.volume_sma[-1]
        ):
            self.sell(size=0.95)
