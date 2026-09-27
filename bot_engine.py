import time
import json
import os
import requests
import pandas as pd
from datetime import datetime

# Points to Railway's safe persistent folder so balance isn't lost on restarts
VOLUME_PATH = "/data"
PORTFOLIO_FILE = os.path.join(VOLUME_PATH, "portfolio.json") if os.path.exists(VOLUME_PATH) else "portfolio.json"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT"] 
TRADE_AMOUNT = 10.0

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"balance": 1000.0, "holdings": {}, "entry_prices": {}, "trade_history": []}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_data(symbol):
    try:
        r_price = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3)
        price = float(r_price.json()['price'])
        return price
    except Exception:
        return None

def run_bot():
    print("🤖 Bot Engine Running 24/7 in Background...")
    while True:
        portfolio = load_portfolio()
        current_time = datetime.now().strftime("%H:%M:%S")
        
        for symbol in SYMBOLS:
            price = fetch_data(symbol)
            if not price:
                continue
                
            long_qty = portfolio['holdings'].get(symbol, 0.0)
            
            # Simulated entry condition
            if long_qty == 0 and portfolio['balance'] >= TRADE_AMOUNT:
                portfolio['balance'] -= TRADE_AMOUNT
                portfolio['holdings'][symbol] = TRADE_AMOUNT / price
                portfolio['entry_prices'][symbol] = price
                portfolio['trade_history'].append({'Time': current_time, 'Asset': symbol, 'Type': 'BUY', 'Price': price})
                
            elif long_qty > 0 and price > portfolio['entry_prices'][symbol] * 1.005:
                usdt_received = long_qty * price
                portfolio['balance'] += usdt_received
                portfolio['holdings'][symbol] = 0.0
                portfolio['entry_prices'][symbol] = 0.0
                portfolio['trade_history'].append({'Time': current_time, 'Asset': symbol, 'Type': 'SELL', 'Price': price})

        save_portfolio(portfolio)
        time.sleep(60) 

if __name__ == "__main__":
    run_bot()
