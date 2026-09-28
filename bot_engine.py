import time
import json
import os
from datetime import datetime
import pandas as pd
import ccxt

PORTFOLIO_FILE = "portfolio.json"

exchange = ccxt.binance({'enableRateLimit': True})

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def calculate_rsi(symbol, timeframe="15m", period=14):
    """Fetch OHLCV and calculate RSI natively using Pandas"""
    try:
        # ccxt format for binance pairs needs a slash, e.g. BTC/USDT
        formatted_symbol = symbol.replace("USDT", "/USDT") 
        bars = exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return df['close'].iloc[-1], rsi.iloc[-1]
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None, None

def run_bot():
    print("Starting 24/7 Background Trading Engine...")
    
    while True:
        try:
            state = load_portfolio()
            if not state:
                time.sleep(5)
                continue
                
            if not state.get("bot_running", True):
                print(f"[{datetime.now()}] Bot is paused via UI.")
                time.sleep(10)
                continue
                
            print(f"[{datetime.now()}] Scanning markets...")
            
            # Read thresholds set by the user in the Streamlit Sidebar
            rsi_oversold = state.get("rsi_oversold", 30)
            rsi_overbought = state.get("rsi_overbought", 72)
            trade_size = state.get("trade_amount_usdt", 10.0)
            
            for symbol in state.get("selected_symbols", []):
                price, rsi = calculate_rsi(symbol)
                if price is None or rsi is None:
                    continue
                    
                current_holdings = state["holdings"].get(symbol, 0.0)
                
                # BUY LOGIC
                if rsi < rsi_oversold and current_holdings == 0.0 and state["balance"] >= trade_size:
                    state["balance"] -= trade_size
                    qty = trade_size / price
                    state["holdings"][symbol] = qty
                    state["entry_prices"][symbol] = price
                    
                    trade_record = {"Time": str(datetime.now()), "Action": "BUY", "Asset": symbol, "Price": price, "Amount": trade_size}
                    state["trade_history"].append(trade_record)
                    print(f"*** BOUGHT {symbol} at ${price} (RSI: {rsi:.2f}) ***")
                
                # SELL LOGIC
                elif rsi > rsi_overbought and current_holdings > 0.0:
                    sold_value = current_holdings * price
                    state["balance"] += sold_value
                    
                    trade_record = {"Time": str(datetime.now()), "Action": "SELL", "Asset": symbol, "Price": price, "Amount": sold_value}
                    state["trade_history"].append(trade_record)
                    
                    state["holdings"][symbol] = 0.0
                    state["entry_prices"][symbol] = 0.0
                    print(f"*** SOLD {symbol} at ${price} (RSI: {rsi:.2f}) ***")

            # Save updated data back to portfolio.json for the UI to display
            save_portfolio(state)
            
            # Wait 60 seconds before checking the market again
            time.sleep(60)
            
        except Exception as e:
            print(f"Error in background engine loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
