# US Stock Backtester

A minimal viable backtesting system for US stock trading strategies with a web UI and CLI interface.

## How to Run

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web server
python app.py
# Visit http://localhost:5000

# Or use the CLI (SMA Crossover only)
python main.py --ticker AAPL --start 2020-01-01 --end 2023-12-31
```

### Deploy to Vercel

The project includes a `vercel.json` config and deploys as a serverless Python app.

### Verify

1. Open the web UI, select a strategy (e.g. SMA Crossover), enter a ticker (e.g. AAPL), and click Run.
2. Confirm the results panel shows metrics (CAGR, Sharpe Ratio, Max Drawdown), an equity curve chart, and a trade log table.
3. Test edge cases: invalid tickers, reversed date ranges, different strategies.

## Key Assumptions

- **No transaction costs or slippage** — trades execute at exact daily close prices.
- **Full position sizing** — BUY signals invest all available cash (except DCA, which uses a fixed dollar amount).
- **SELL signals liquidate all shares** at once.
- **Sharpe Ratio assumes 0% risk-free rate.**
- **RSI uses simple moving average** (not Wilder's exponential smoothing).
- **Data sourced from Yahoo Finance** via `yfinance` — subject to availability and accuracy of that API.

## Strategies

| Strategy | Description |
|---|---|
| Buy & Hold | Buy on day 1, hold until end |
| DCA | Invest a fixed amount every N days |
| SMA Crossover | Golden cross / death cross signals |
| RSI | Buy oversold, sell overbought |
| Bollinger Bands | Buy at lower band, sell at upper band |
| MACD | Buy on MACD/signal line crossover |
| Momentum | Buy/sell based on % price change |
| Mean Reversion | Buy/sell based on z-score thresholds |

## Tech Stack

- **Backend:** Flask, pandas, NumPy, yfinance
- **Frontend:** Vanilla HTML/JS, Chart.js
- **Deployment:** Vercel (serverless Python)

## AI / Agent Workflow

This project was developed with the assistance of **Claude Code** (Anthropic's AI coding agent). The AI-assisted workflow included:

- **Architecture design** — Claude helped design the strategy registry pattern, making it easy to add new strategies by implementing a class and registering it in a dictionary.
- **Strategy implementation** — The 8 trading strategies (SMA Crossover, RSI, Bollinger Bands, MACD, Momentum, Mean Reversion, Buy & Hold, DCA) were implemented with Claude generating the indicator logic and signal generation code.
- **Backtesting engine** — Claude built the core simulation loop that iterates through daily prices, executes trades based on strategy signals, and computes performance metrics.
- **Frontend UI** — The single-page HTML/JS interface with Chart.js visualizations was developed iteratively with Claude, including responsive layout, dynamic parameter forms per strategy, and equity curve charting with trade markers.
- **Iterative refinement** — Features like partial buy support for DCA, inline CSS for Vercel compatibility, and UI polish were added through conversational back-and-forth with the AI agent.
