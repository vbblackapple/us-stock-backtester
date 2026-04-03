from dataclasses import dataclass, field
from math import sqrt

import numpy as np
import pandas as pd
import yfinance as yf

from strategy import Strategy, Signal


def fetch_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """從 yfinance 取得歷史價格資料。"""
    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        raise ValueError(f"無法取得 {ticker} 從 {start} 到 {end} 的資料")
    # yfinance 可能回傳多層欄位，需 flatten
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    return data


@dataclass
class TradeRecord:
    date: str
    action: str
    price: float
    shares: int
    cash_after: float
    equity_after: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trade_log: list[TradeRecord] = field(default_factory=list)
    initial_cash: float = 100_000.0


class Backtester:
    """回測引擎：逐日迭代，執行策略信號，記錄交易與權益曲線。"""

    def __init__(self, data: pd.DataFrame, strategy: Strategy, initial_cash: float = 100_000.0):
        self.data = data
        self.strategy = strategy
        self.initial_cash = initial_cash

    def run(self) -> BacktestResult:
        self.strategy.init(self.data)

        cash = self.initial_cash
        shares = 0
        trade_log: list[TradeRecord] = []
        equity_values: list[float] = []
        dates: list = []

        for i in range(len(self.data)):
            row = self.data.iloc[i]
            close = float(row["Close"])
            date = str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"])

            signal = self.strategy.on_data(self.data, i)

            if signal == Signal.BUY and (shares == 0 or self.strategy.allow_partial_buy):
                buy_budget = self.strategy.buy_amount if self.strategy.buy_amount else cash
                buy_budget = min(buy_budget, cash)
                new_shares = int(buy_budget // close)
                if new_shares > 0:
                    shares += new_shares
                    cash -= new_shares * close
                    equity = cash + shares * close
                    trade_log.append(TradeRecord(
                        date=date, action="BUY", price=close,
                        shares=new_shares, cash_after=cash, equity_after=equity,
                    ))

            elif signal == Signal.SELL and shares > 0:
                cash += shares * close
                equity = cash
                trade_log.append(TradeRecord(
                    date=date, action="SELL", price=close,
                    shares=shares, cash_after=cash, equity_after=equity,
                ))
                shares = 0

            equity = cash + shares * close
            equity_values.append(equity)
            dates.append(date)

        equity_curve = pd.Series(equity_values, index=pd.to_datetime(dates))
        return BacktestResult(
            equity_curve=equity_curve,
            trade_log=trade_log,
            initial_cash=self.initial_cash,
        )


def compute_metrics(result: BacktestResult) -> dict:
    """從權益曲線計算回測績效指標。"""
    equity = result.equity_curve
    initial = result.initial_cash
    final = equity.iloc[-1]
    total_days = (equity.index[-1] - equity.index[0]).days

    # CAGR
    if total_days > 0 and final > 0:
        cagr = (final / initial) ** (365.25 / total_days) - 1
    else:
        cagr = 0.0

    # 日報酬率
    daily_returns = equity.pct_change().dropna()

    # 年化波動率
    volatility = daily_returns.std() * sqrt(252) if len(daily_returns) > 0 else 0.0

    # 夏普比率（無風險利率 = 0）
    if volatility > 0:
        annualized_return = daily_returns.mean() * 252
        sharpe = annualized_return / volatility
    else:
        sharpe = 0.0

    # 最大回撤
    cummax = equity.cummax()
    drawdown = (cummax - equity) / cummax
    max_drawdown = float(drawdown.max()) if len(drawdown) > 0 else 0.0

    return {
        "初始資金": initial,
        "最終權益": round(final, 2),
        "年化報酬率 (CAGR)": f"{cagr:.2%}",
        "年化波動率": f"{volatility:.2%}",
        "夏普比率 (Sharpe)": round(sharpe, 4),
        "最大回撤 (Max Drawdown)": f"{max_drawdown:.2%}",
        "總交易次數": len(result.trade_log),
    }
