import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility

from src.strategies.base import BaseStrategy


class BtcDonchianRegimeAsymmetric4h(BaseStrategy):
    description = "BTC 4-hour Two-way Donchian Breakout + Slow Moving Average Slope + ATR Expansion + Long-Short Asymmetric Filter"
    keep = True

    fast_window = 15
    slow_window = 55
    breakout_window = 20
    exit_window = 7
    atr_window = 14
    atr_regime_window = 20
    rsi_window = 14
    roc_window = 10
    long_rsi = 60
    short_rsi = 43
    long_roc = 1.0
    short_roc = -1.0
    long_stop_atr = 1.6
    short_stop_atr = 1.8
    long_size = 0.6
    short_size = 0.95

    def init(self) -> None:
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)

        self.fast_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.fast_window).ema_indicator().values
        )
        self.slow_ema = self.I(
            lambda: ta.trend.EMAIndicator(close, window=self.slow_window).ema_indicator().values
        )
        self.rsi = self.I(
            lambda: ta.momentum.RSIIndicator(close, window=self.rsi_window).rsi().values
        )
        self.roc = self.I(
            lambda: ta.momentum.ROCIndicator(close, window=self.roc_window).roc().values
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
        atr = self.atr[-1]
        atr_sma = self.atr_sma[-1]
        trend_up = self.fast_ema[-1] > self.slow_ema[-1] and self.slow_ema[-1] > self.slow_ema[-3]
        trend_down = self.fast_ema[-1] < self.slow_ema[-1] and self.slow_ema[-1] < self.slow_ema[-3]
        volatility_expanding = atr > atr_sma

        if self.position:
            entry_price = self.trades[-1].entry_price if self.trades else price
            if self.position.is_long:
                stop_price = entry_price - atr * self.long_stop_atr
                if (
                    price < stop_price
                    or price < self.exit_low[-1]
                    or self.fast_ema[-1] < self.slow_ema[-1]
                    or self.rsi[-1] < 50
                ):
                    self.position.close()
            else:
                stop_price = entry_price + atr * self.short_stop_atr
                if (
                    price > stop_price
                    or price > self.exit_high[-1]
                    or self.fast_ema[-1] > self.slow_ema[-1]
                    or self.rsi[-1] > 52
                ):
                    self.position.close()
            return

        if (
            trend_up
            and volatility_expanding
            and price > self.breakout_high[-1] + atr * 0.1
            and self.rsi[-1] > self.long_rsi
            and self.roc[-1] > self.long_roc
        ):
            self.buy(size=self.long_size)
            return

        if (
            trend_down
            and atr > atr_sma * 0.95
            and price < self.breakout_low[-1] - atr * 0.05
            and self.rsi[-1] < self.short_rsi
            and self.roc[-1] < self.short_roc
        ):
            self.sell(size=self.short_size)
