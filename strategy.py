from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(ABC):
    """交易策略抽象基底類別。"""

    def init(self, data: pd.DataFrame) -> None:
        """預計算指標，回測開始前呼叫一次。可選擇覆寫。"""
        pass

    @abstractmethod
    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        """根據歷史資料產生交易信號。只能參考 data.iloc[:current_index+1]。"""
        ...


class SmaCrossoverStrategy(Strategy):
    """SMA 交叉策略：短均線上穿長均線買入，下穿賣出。"""

    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    def init(self, data: pd.DataFrame) -> None:
        data["SMA_short"] = data["Close"].rolling(self.short_window).mean()
        data["SMA_long"] = data["Close"].rolling(self.long_window).mean()

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.long_window:
            return Signal.HOLD

        sma_short_today = data["SMA_short"].iloc[current_index]
        sma_long_today = data["SMA_long"].iloc[current_index]
        sma_short_yesterday = data["SMA_short"].iloc[current_index - 1]
        sma_long_yesterday = data["SMA_long"].iloc[current_index - 1]

        if pd.isna(sma_short_today) or pd.isna(sma_long_today):
            return Signal.HOLD

        # 黃金交叉：短均線由下往上穿越長均線
        if sma_short_today > sma_long_today and sma_short_yesterday <= sma_long_yesterday:
            return Signal.BUY

        # 死亡交叉：短均線由上往下穿越長均線
        if sma_short_today < sma_long_today and sma_short_yesterday >= sma_long_yesterday:
            return Signal.SELL

        return Signal.HOLD


class RsiStrategy(Strategy):
    """RSI 超買超賣策略：RSI 低於超賣門檻買入，高於超買門檻賣出。"""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def init(self, data: pd.DataFrame) -> None:
        delta = data["Close"].diff()
        gain = delta.clip(lower=0).rolling(self.period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.period).mean()
        rs = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.period:
            return Signal.HOLD
        rsi = data["RSI"].iloc[current_index]
        if pd.isna(rsi):
            return Signal.HOLD
        if rsi < self.oversold:
            return Signal.BUY
        if rsi > self.overbought:
            return Signal.SELL
        return Signal.HOLD


class BollingerStrategy(Strategy):
    """布林通道突破策略：價格跌破下軌買入，突破上軌賣出。"""

    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std

    def init(self, data: pd.DataFrame) -> None:
        sma = data["Close"].rolling(self.period).mean()
        std = data["Close"].rolling(self.period).std()
        data["BB_upper"] = sma + self.num_std * std
        data["BB_lower"] = sma - self.num_std * std

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.period:
            return Signal.HOLD
        close = data["Close"].iloc[current_index]
        lower = data["BB_lower"].iloc[current_index]
        upper = data["BB_upper"].iloc[current_index]
        if pd.isna(lower) or pd.isna(upper):
            return Signal.HOLD
        if close < lower:
            return Signal.BUY
        if close > upper:
            return Signal.SELL
        return Signal.HOLD


class MacdStrategy(Strategy):
    """MACD 交叉策略：MACD 線上穿信號線買入，下穿賣出。"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def init(self, data: pd.DataFrame) -> None:
        ema_fast = data["Close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = data["Close"].ewm(span=self.slow, adjust=False).mean()
        data["MACD_line"] = ema_fast - ema_slow
        data["MACD_signal"] = data["MACD_line"].ewm(span=self.signal_period, adjust=False).mean()

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.slow + self.signal_period:
            return Signal.HOLD
        macd_today = data["MACD_line"].iloc[current_index]
        sig_today = data["MACD_signal"].iloc[current_index]
        macd_yesterday = data["MACD_line"].iloc[current_index - 1]
        sig_yesterday = data["MACD_signal"].iloc[current_index - 1]
        if pd.isna(macd_today) or pd.isna(sig_today):
            return Signal.HOLD
        if macd_today > sig_today and macd_yesterday <= sig_yesterday:
            return Signal.BUY
        if macd_today < sig_today and macd_yesterday >= sig_yesterday:
            return Signal.SELL
        return Signal.HOLD


class MomentumStrategy(Strategy):
    """動量策略：過去 N 天漲幅超過門檻買入，跌幅超過門檻賣出。"""

    def __init__(self, lookback: int = 20, threshold: float = 5.0):
        self.lookback = lookback
        self.threshold = threshold

    def init(self, data: pd.DataFrame) -> None:
        data["Momentum_pct"] = data["Close"].pct_change(self.lookback) * 100

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.lookback:
            return Signal.HOLD
        momentum = data["Momentum_pct"].iloc[current_index]
        if pd.isna(momentum):
            return Signal.HOLD
        if momentum > self.threshold:
            return Signal.BUY
        if momentum < -self.threshold:
            return Signal.SELL
        return Signal.HOLD


class MeanReversionStrategy(Strategy):
    """均值回歸策略：價格偏離均線過多時反向操作。"""

    def __init__(self, period: int = 20, threshold: float = 2.0):
        self.period = period
        self.threshold = threshold

    def init(self, data: pd.DataFrame) -> None:
        data["MR_sma"] = data["Close"].rolling(self.period).mean()
        data["MR_std"] = data["Close"].rolling(self.period).std()
        data["MR_zscore"] = (data["Close"] - data["MR_sma"]) / data["MR_std"]

    def on_data(self, data: pd.DataFrame, current_index: int) -> Signal:
        if current_index < self.period:
            return Signal.HOLD
        z = data["MR_zscore"].iloc[current_index]
        if pd.isna(z):
            return Signal.HOLD
        if z < -self.threshold:
            return Signal.BUY
        if z > self.threshold:
            return Signal.SELL
        return Signal.HOLD


STRATEGY_REGISTRY = {
    "sma_crossover": {
        "class": SmaCrossoverStrategy,
        "name": "SMA 交叉",
        "params": [
            {"key": "short_window", "label": "短期 SMA (天)", "type": "int", "default": 20, "min": 2},
            {"key": "long_window", "label": "長期 SMA (天)", "type": "int", "default": 50, "min": 3},
        ],
    },
    "rsi": {
        "class": RsiStrategy,
        "name": "RSI 超買超賣",
        "params": [
            {"key": "period", "label": "RSI 週期", "type": "int", "default": 14, "min": 2},
            {"key": "oversold", "label": "超賣門檻", "type": "int", "default": 30, "min": 1},
            {"key": "overbought", "label": "超買門檻", "type": "int", "default": 70, "min": 1},
        ],
    },
    "bollinger": {
        "class": BollingerStrategy,
        "name": "布林通道突破",
        "params": [
            {"key": "period", "label": "均線週期", "type": "int", "default": 20, "min": 2},
            {"key": "num_std", "label": "標準差倍數", "type": "float", "default": 2.0, "min": 0.1, "step": 0.1},
        ],
    },
    "macd": {
        "class": MacdStrategy,
        "name": "MACD 交叉",
        "params": [
            {"key": "fast", "label": "快線週期", "type": "int", "default": 12, "min": 2},
            {"key": "slow", "label": "慢線週期", "type": "int", "default": 26, "min": 2},
            {"key": "signal", "label": "信號線週期", "type": "int", "default": 9, "min": 2},
        ],
    },
    "momentum": {
        "class": MomentumStrategy,
        "name": "動量策略",
        "params": [
            {"key": "lookback", "label": "回顧天數", "type": "int", "default": 20, "min": 1},
            {"key": "threshold", "label": "漲幅門檻 (%)", "type": "float", "default": 5.0, "min": 0.1, "step": 0.1},
        ],
    },
    "mean_reversion": {
        "class": MeanReversionStrategy,
        "name": "均值回歸",
        "params": [
            {"key": "period", "label": "均線週期", "type": "int", "default": 20, "min": 2},
            {"key": "threshold", "label": "偏離門檻 (標準差)", "type": "float", "default": 2.0, "min": 0.1, "step": 0.1},
        ],
    },
}
