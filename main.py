import argparse

import pandas as pd

from backtest import fetch_data, Backtester, compute_metrics
from strategy import SmaCrossoverStrategy


def main():
    parser = argparse.ArgumentParser(description="美股回測系統")
    parser.add_argument("--ticker", default="AAPL", help="股票代碼（預設: AAPL）")
    parser.add_argument(
        "--start", default="2020-01-01", help="開始日期（預設: 2020-01-01）"
    )
    parser.add_argument(
        "--end", default="2023-12-31", help="結束日期（預設: 2023-12-31）"
    )
    parser.add_argument(
        "--cash", type=float, default=100_000, help="初始資金（預設: 100000）"
    )
    parser.add_argument(
        "--short-window", type=int, default=20, help="短期 SMA 天數（預設: 20）"
    )
    parser.add_argument(
        "--long-window", type=int, default=50, help="長期 SMA 天數（預設: 50）"
    )
    args = parser.parse_args()

    print(f"=== 美股回測系統 ===")
    print(f"股票: {args.ticker} | 期間: {args.start} ~ {args.end}")
    print(f"策略: SMA 交叉（短={args.short_window}, 長={args.long_window}）")
    print(f"初始資金: ${args.cash:,.0f}")
    print()

    # 取得資料
    print("正在取得歷史資料...")
    data = fetch_data(args.ticker, args.start, args.end)
    print(f"取得 {len(data)} 個交易日資料")
    print()

    # 執行回測
    strategy = SmaCrossoverStrategy(args.short_window, args.long_window)
    backtester = Backtester(data, strategy, args.cash)
    result = backtester.run()

    # 績效摘要
    metrics = compute_metrics(result)
    print("=== 績效摘要 ===")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print()

    # 交易明細
    if result.trade_log:
        print("=== 交易明細 ===")
        records = [
            {
                "日期": t.date,
                "動作": t.action,
                "價格": f"${t.price:.2f}",
                "股數": t.shares,
                "剩餘現金": f"${t.cash_after:,.2f}",
                "總權益": f"${t.equity_after:,.2f}",
            }
            for t in result.trade_log
        ]
        df = pd.DataFrame(records)
        print(df.to_string(index=False))
    else:
        print("無交易紀錄")


if __name__ == "__main__":
    main()
