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
