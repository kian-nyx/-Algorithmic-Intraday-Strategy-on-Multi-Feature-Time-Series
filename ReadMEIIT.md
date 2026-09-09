# Inter IIT Backtesting Framework README
## Files Provided
- mainIIT.py
- configIIT.json
- dist/alpha_research-0.1.0-<tag>.whl

## Requirements
- Python 3.9.23

## Installation 
`pip install alpha_research-0.1.0-<tag>.whl`

## Re-installation
`pip install --force-reinstall alpha_research-0.1.0-cp39-cp39-linux_x86_64.whl`

## Run Your Strategy
`python mainIIT.py configIIT.json`


## Config Details
```
{
    "data_path": "/path/to/data",
    "start_date": 0, 
    "end_date": 100,
    "timer": 600, // on timer callback every x seconds to display ticker wise positon and pnl at this interval
    "tcost": 0.02 // in percentage
    "broadcast": [   
        "EBY",
        "EBX"
    ] // Will run for both EBY and EBX
}
```



## Statistics
After completion of the program you will get a cumulative report across all days which includes:
- Final_Equity
- PnL_Rs
- PnL_%
- Sharpe
- Sortino
- Calmar
- Max_Drawdown_%
- Positive_Trades
- Negative_Trades
- Total_Trades
- WinRate_% (same as hit_rate)


You will get a pandas dataframe which include day wise statistics for each ticker which includes:
- day
- pnl
- pnl_with_tc
- pnl_pct
- pnl_cumsum
- max_drawdown_pct
- pos_trades
- neg_trades
- total_trades
- hit_rate_%

## Other information
If the program does not square off positions by EOD, it will be squared off automatically, but it will incur penalty.

Only placing market order is allowed

```
trade_buy = backtest.place_order(
        ticker=buy_ticker,
        qty=1,
        side=Side.BUY
    )
    # if trade_buy:
    #     print(f"Placed BUY trade: {trade_buy}")

    # place SELL
trade_sell = backtest.place_order(
    ticker=sell_ticker,
    qty=1,
    side=Side.SELL
)
```

`trade_buy` and `trade_sell` includes :

`trade = Trade(ticker=ticker,side=side,price=exec_price,quantity=qty,timestamp=self.timestamp)`

## Functions

DON'T CHANGE THE MAIN FUNCTION
```
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <config.json>")
        sys.exit(1)

    config_file = sys.argv[1]
    backtest = BacktesterIIT(config_file)
    print(datetime.now().strftime("%H:%M:%S"))  # only hh:mm:ss
    backtest.run(broadcast_callback=my_broadcast_callback, timer_callback=on_timer)
    print(datetime.now().strftime("%H:%M:%S"))  # only hh:mm:ss
```
```
def my_broadcast_callback(state, ts):
// Here you will get all the data. state is dict, with ticker being the key, value as data which is again a dict. Includes Time, Price and other fields 
```
```
def on_timer(ts):
    print("On timer callback") // called at regular intervals according to the config
```