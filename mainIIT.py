import sys
import random
from datetime import datetime

from alpha_research import BacktesterIIT , Side, Ticker


def my_broadcast_callback(state, ts):
    # print(f"\n[STATIC] Timestamp: {ts}")
    # for ticker, data in state.items():
    #     print(f"{ticker}: {len(data)} timestamp={data['Time']} PRICE={data['Price']}")
    # return
    

    tickers = [t for t, d in state.items() if d['Price'] != 0]
    buy_ticker = random.choice(tickers)
    sell_ticker = random.choice([t for t in tickers if t != buy_ticker])
    # place BUY
    trade_buy = backtest.place_order(
        ticker=buy_ticker,
        qty=1,
        side=Side.BUY
    )
    trade_sell = backtest.place_order(
        ticker=sell_ticker,
        qty=1,
        side=Side.SELL
    )


def on_timer(ts):
    print("On timer callback")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <config.json>")
        sys.exit(1)

    config_file = sys.argv[1]
    backtest = BacktesterIIT(config_file)
    print(datetime.now().strftime("%H:%M:%S"))  # only hh:mm:ss
    backtest.run(broadcast_callback=my_broadcast_callback, timer_callback=on_timer)
    print(datetime.now().strftime("%H:%M:%S"))  # only hh:mm:ss
