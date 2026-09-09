import sys
from datetime import datetime
from collections import deque, defaultdict
import numpy as np

from alpha_research import BacktesterIIT, Side, Ticker



WINDOW = 1500
EPS = 1e-9
w = 500


class RollingBuffer:
    """Efficient rolling buffer for time series calculations."""
    def __init__(self, maxlen):
        self.buffer = deque(maxlen=maxlen)
        self.maxlen = maxlen
    
    def append(self, value):
        self.buffer.append(value)
    
    def get_array(self):
        """Return buffer as numpy array."""
        return np.array(self.buffer) if len(self.buffer) > 0 else np.array([])
    
    def mean(self):
        """Calculate mean of buffer."""
        if len(self.buffer) == 0:
            return 0.0
        return np.mean(self.buffer)
    
    def std(self):
        """Calculate standard deviation of buffer."""
        if len(self.buffer) < 2:
            return 0.0
        return np.std(self.buffer)
    
    def __len__(self):
        return len(self.buffer)


class AnomalyStrategy:
    """
    Implements user's anomaly detection logic EXACTLY as provided.
    NO modifications or additions.
    """
    def __init__(self, ticker):
        self.ticker = ticker
        
        # Rolling buffers for Price statistics
        self.price_buffer_1500 = RollingBuffer(WINDOW)  # For rolling mean
        self.price_buffer_100 = RollingBuffer(100)      # For rolling std
        
        # Buffers for Z-Score calculations
        self.zscore_buffer = RollingBuffer(w)           # For Price_ZScore
        self.zscore_mul_buffer = RollingBuffer(5000)    # For Price_mul_ZScore
        
        # Store Dynamic_Neg_Threshold history for curve calculation
        self.threshold_history = RollingBuffer(300)
        
        # Current calculated values
        self.price_zscore = None
        self.price_mul_zscore = None
        self.dynamic_neg_threshold = None
        self.curve = None
        self.dyn_threshold_upper_mul = None
        self.dyn_threshold_lower_mul = None
        
    def update(self, price):
        """
        Update all calculations with new price.
        User's logic preserved EXACTLY.
        """
        # Add price to buffers
        self.price_buffer_1500.append(price)
        self.price_buffer_100.append(price)
        
        if len(self.price_buffer_1500) < 2:
            return False  # Need at least 2 points
        
        # 1. Calculate basic Rolling Stats for Price
        rolling_mean_price = self.price_buffer_1500.mean()
        rolling_std_price = self.price_buffer_100.std()
        
        # 2. Calculate Price Z-Score
        self.price_zscore = (price - rolling_mean_price) / (rolling_std_price + EPS)
        self.price_mul_zscore = (price - rolling_mean_price) * (rolling_std_price + EPS)
        
        # Add to z-score buffers
        self.zscore_buffer.append(self.price_zscore)
        self.zscore_mul_buffer.append(self.price_mul_zscore)
        
        # 3. Calculate Dynamic Thresholds
        z_roll_mean = self.zscore_buffer.mean()
        z_roll_std = self.zscore_buffer.std()
        
        z_roll_mean_mul = self.zscore_mul_buffer.mean()
        z_roll_std_mul = self.zscore_mul_buffer.std()
        
        self.dynamic_neg_threshold = z_roll_mean
        
        # Store for curve calculation
        self.threshold_history.append(self.dynamic_neg_threshold)
        
        # Calculate curve: current - 2*shift(150) + shift(300)
        threshold_array = self.threshold_history.get_array()
        if len(threshold_array) >= 300:
            current = threshold_array[-1]
            shift_150 = threshold_array[-151] if len(threshold_array) > 150 else threshold_array[0]
            shift_300 = threshold_array[-301] if len(threshold_array) > 300 else threshold_array[0]
            self.curve = current - 2 * shift_150 + shift_300
        else:
            self.curve = 0.0
        
        self.dyn_threshold_upper_mul = z_roll_mean_mul + 2 * z_roll_std_mul
        self.dyn_threshold_lower_mul = z_roll_mean_mul - 2 * z_roll_std_mul
        
        return True
    
    def check_signals(self):
        """
        Check for anomaly signals.
        User's logic: mask_upper and mask_lower conditions.
        """
        if self.curve is None or self.price_mul_zscore is None:
            return None, None
        
        # mask_upper: (curve < -1) & (Price_mul_ZScore > Dyn_Threshold_Upper_mul)
        mask_upper = (self.curve < -1) and (self.price_mul_zscore > self.dyn_threshold_upper_mul)
        
        # mask_lower: (curve > 1) & (Price_mul_ZScore < Dyn_Threshold_Lower_mul)
        mask_lower = (self.curve > 1) and (self.price_mul_zscore < self.dyn_threshold_lower_mul)
        
        return mask_upper, mask_lower


strategies = {}  # ticker -> AnomalyStrategy
current_positions = defaultdict(int)
last_time = None
backtest = None


def my_broadcast_callback(state, ts):
    """
    Broadcast callback - receives all data each tick.
    """
    global strategies, backtest, current_positions, last_time
    
    # Convert timestamp to string for comparison
    if isinstance(ts, str):
        current_time = ts
    else:
        current_time = str(ts)
    
    # Reset positions when new day starts (time goes back to early morning)
    if last_time and current_time < '01:00:00' and last_time >= '06:00:00':
        current_positions.clear()
    
    last_time = current_time
    
    # Squareoff logic at 06:25:00
    if current_time >= '06:25:00':
        for ticker in list(current_positions.keys()):
            pos = current_positions[ticker]
            if pos > 0:
                backtest.place_order(ticker=ticker, qty=pos, side=Side.SELL)
                current_positions[ticker] = 0
            elif pos < 0:
                backtest.place_order(ticker=ticker, qty=abs(pos), side=Side.BUY)
                current_positions[ticker] = 0
        return
    
    # Get valid tickers (non-zero price)
    valid_tickers = [t for t, d in state.items() if d['Price'] != 0]
    
    if len(valid_tickers) < 2:
        return
    
    for ticker in valid_tickers:
        price = state[ticker]['Price']
        
        # Get or create strategy for this ticker
        if ticker not in strategies:
            strategies[ticker] = AnomalyStrategy(ticker)
        
        strategy = strategies[ticker]
        
        # Update strategy with new price
        if not strategy.update(price):
            continue
        
        # Check for signals
        mask_upper, mask_lower = strategy.check_signals()
        
        # Trade on signals
        if mask_upper:
            # Upper anomaly detected - place SELL order
            trade_sell = backtest.place_order(
                ticker=ticker,
                qty=1,
                side=Side.SELL
            )
            if trade_sell:
                current_positions[ticker] -= 1
        
        elif mask_lower:
            # Lower anomaly detected - place BUY order
            trade_buy = backtest.place_order(
                ticker=ticker,
                qty=1,
                side=Side.BUY
            )
            if trade_buy:
                current_positions[ticker] += 1


def on_timer(ts):
    """Timer callback."""
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
