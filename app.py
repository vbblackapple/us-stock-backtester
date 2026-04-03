from dataclasses import asdict

from flask import Flask, render_template, request, jsonify

from backtest import fetch_data, Backtester, compute_metrics
from strategy import STRATEGY_REGISTRY

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/backtest", methods=["POST"])
def run_backtest():
    body = request.get_json(force=True)

    ticker = body.get("ticker", "").strip().upper()
    start = body.get("start", "")
    end = body.get("end", "")
    cash = body.get("cash", 100_000)
    strategy_key = body.get("strategy", "sma_crossover")

    # 驗證
    if not ticker:
        return jsonify(error="請輸入股票代碼"), 400
    if not start or not end:
        return jsonify(error="請輸入完整的日期範圍"), 400
    if strategy_key not in STRATEGY_REGISTRY:
        return jsonify(error=f"未知的策略: {strategy_key}"), 400

    try:
        cash = float(cash)
    except (TypeError, ValueError):
        return jsonify(error="參數格式不正確"), 400
    if cash <= 0:
        return jsonify(error="初始資金必須大於 0"), 400

    # 動態提取策略參數
    reg = STRATEGY_REGISTRY[strategy_key]
    strategy_params = {}
    try:
        for p in reg["params"]:
            raw = body.get(p["key"], p["default"])
            if p["type"] == "int":
                strategy_params[p["key"]] = int(raw)
            elif p["type"] == "float":
                strategy_params[p["key"]] = float(raw)
    except (TypeError, ValueError):
        return jsonify(error="策略參數格式不正確"), 400

    try:
        data = fetch_data(ticker, start, end)
        strategy = reg["class"](**strategy_params)
        backtester = Backtester(data, strategy, cash)
        result = backtester.run()
        metrics = compute_metrics(result)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"回測執行失敗: {e}"), 500

    # 序列化
    equity_curve = result.equity_curve
    dates = [d.strftime("%Y-%m-%d") for d in equity_curve.index]
    values = [round(float(v), 2) for v in equity_curve.values]

    trades = [asdict(t) for t in result.trade_log]
    for t in trades:
        t["price"] = round(t["price"], 2)
        t["cash_after"] = round(t["cash_after"], 2)
        t["equity_after"] = round(t["equity_after"], 2)

    return jsonify(
        metrics=metrics,
        trades=trades,
        equity_curve={"dates": dates, "values": values},
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
