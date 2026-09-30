import time
import requests
import json
import os
import numpy as np

PORTFOLIO_FILE = "portfolio.json"

ALL_TRADING_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", 
    "SHIBUSDT", "LINKUSDT", "SUIUSDT", "PEPEUSDT", "NEARUSDT", "RENDERUSDT", "FETUSDT", 
    "INJUSDT", "OPUSDT", "ARBUSDT", "MATICUSDT", "DOTUSDT", "ATOMUSDT", "UNIUSDT", "LTCUSDT", 
    "ETCUSDT", "BCHUSDT", "APTUSDT", "ICPUSDT", "FILUSDT", "HBARUSDT", "STXUSDT", "IMXUSDT", 
    "GRTUSDT", "RNDRUSDT", "RUNEUSDT", "AAVEUSDT", "SNXUSDT", "MKRUSDT", "FTMUSDT", 
    "THETAUSDT", "TIAUSDT", "SEIUSDT", "STRKUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "JUPUSDT", 
    "PYTHUSDT", "MANTAUSDT", "ALTUSDT", "ZETAUSDT", "DYMUSDT", "PORTALUSDT", "AXLUSDT", "ETHFIUSDT", 
    "ENAUSDT", "SAGAUSDT", "TNSRUSDT", "OMNIUSDT", "REZUSDT", "BBUSDT", "NOTUSDT", "IOUSDT", 
    "ZKUSDT", "LISTAUSDT", "BANANAUSDT", "TONUSDT", "DOGSUSDT", "NEIROUSDT", "TURBOUSDT", 
    "CATIUSDT", "HMSTRUSDT", "EIGENUSDT", "BNSOLUSDT", "SCRUSDT", "GOATUSDT", "PNUTUSDT", "ACTUSDT", 
    "CHILLGUYUSDT", "USUALUSDT", "THEUSDT", "PENGUUSDT", "TRUMPUSDT", "MELANIAUSDT", "VIRTUALUSDT", "AI16ZUSDT"
]

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"holdings": {}, "short_holdings": {}, "entry_prices": {}, "balance": 1000.0}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_prices():
    price_dict = {}
    try:
        r1 = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5.0)
        if r1.status_code == 200:
            for item in r1.json():
                sym = item['symbol']
                if sym in ALL_TRADING_SYMBOLS:
                    p = float(item['price'])
                    if p > 0:
                        price_dict[sym] = p
    except Exception:
        pass

    if len(price_dict) < len(ALL_TRADING_SYMBOLS):
        try:
            r2 = requests.get("https://api.mexc.com/api/v3/ticker/price", timeout=5.0)
            if r2.status_code == 200:
                for item in r2.json():
                    sym = item['symbol']
                    if sym in ALL_TRADING_SYMBOLS and sym not in price_dict:
                        p = float(item['price'])
                        if p > 0:
                            price_dict[sym] = p
        except Exception:
            pass
            
    return price_dict

def fetch_real_history(symbol, interval="15m", limit=15):
    """Fetches real historical closing prices from Binance, with MEXC fallback."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if len(data) >= limit:
                return [float(candle[4]) for candle in data]
    except Exception:
        pass
        
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if len(data) >= limit:
                return [float(candle[4]) for candle in data]
    except Exception:
        pass
        
    return []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 5Here is your fully updated `bot.py` script. The random price simulation has been removed, and the `fetch_real_history()` function has been implemented. It pulls real 15-minute candlestick data from Binance by default and includes a fallback to the MEXC API for meme coins that might not be listed on Binance.

```python
import time
import requests
import json
import os
import numpy as np
import pandas as pd

PORTFOLIO_FILE = "portfolio.json"

ALL_TRADING_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", 
    "SHIBUSDT", "LINKUSDT", "SUIUSDT", "PEPEUSDT", "NEARUSDT", "RENDERUSDT", "FETUSDT", 
    "INJUSDT", "OPUSDT", "ARBUSDT", "MATICUSDT", "DOTUSDT", "ATOMUSDT", "UNIUSDT", "LTCUSDT", 
    "ETCUSDT", "BCHUSDT", "APTUSDT", "ICPUSDT", "FILUSDT", "HBARUSDT", "STXUSDT", "IMXUSDT", 
    "GRTUSDT", "RNDRUSDT", "RUNEUSDT", "AAVEUSDT", "SNXUSDT", "MKRUSDT", "FTMUSDT", 
    "THETAUSDT", "TIAUSDT", "SEIUSDT", "STRKUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "JUPUSDT", 
    "PYTHUSDT", "MANTAUSDT", "ALTUSDT", "ZETAUSDT", "DYMUSDT", "PORTALUSDT", "AXLUSDT", "ETHFIUSDT", 
    "ENAUSDT", "SAGAUSDT", "TNSRUSDT", "OMNIUSDT", "REZUSDT", "BBUSDT", "NOTUSDT", "IOUSDT", 
    "ZKUSDT", "LISTAUSDT", "BANANAUSDT", "TONUSDT", "DOGSUSDT", "NEIROUSDT", "TURBOUSDT", 
    "CATIUSDT", "HMSTRUSDT", "EIGENUSDT", "BNSOLUSDT", "SCRUSDT", "GOATUSDT", "PNUTUSDT", "ACTUSDT", 
    "CHILLGUYUSDT", "USUALUSDT", "THEUSDT", "PENGUUSDT", "TRUMPUSDT", "MELANIAUSDT", "VIRTUALUSDT", "AI16ZUSDT"
]

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {
        "balance": 1000.0,
        "holdings": {},
        "short_holdings": {},
        "entry_prices": {},
        "settings": {
            "rsi_buy": 30,
            "rsi_sell": 70,
            "rsi_short_enter": 75,
            "rsi_short_exit": 25,
            "trade_amount": 50,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10
        }
    }

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_prices():
    price_dict = {}
    # Fetch from Binance first
    try:
        r1 = requests.get("[https://api.binance.com/api/v3/ticker/price](https://api.binance.com/api/v3/ticker/price)", timeout=5.0)
        if r1.status_code == 200:
            for item in r1.json():
                sym = item['symbol']
                if sym in ALL_TRADING_SYMBOLS:
                    price_dict[sym] = float(item['price'])
    except Exception:
        pass

    # Fallback for remaining coins to MEXC
    if len(price_dict) < len(ALL_TRADING_SYMBOLS):
        try:
            r2 = requests.get("[https://api.mexc.com/api/v3/ticker/price](https://api.mexc.com/api/v3/ticker/price)", timeout=5.0)
            if r2.status_code == 200:
                for item in r2.json():
                    sym = item['symbol']
                    if sym in ALL_TRADING_SYMBOLS and sym not in price_dict:
                        p = float(item['price'])
                        if p > 0:
                            price_dict[sym] = p
        except Exception:
            pass

    return price_dict

def fetch_real_history(symbol, interval="15m", limit=15):
    """Fetches real K-lines (candlesticks) using Binance API, falling back to MEXC."""
    # Try Binance API
    try:
        url = f"[https://api.binance.com/api/v3/klines?symbol=](https://api.binance.com/api/v3/klines?symbol=){symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 0:
                # Index 4 is the closing price in standard crypto kline responses
                return [float(candle[4]) for candle in data]
    except Exception:
        pass

    # Fallback to MEXC API if Binance fails or symbol isn't listed there
    try:
        mexc_url = f"[https://api.mexc.com/api/v3/klines?symbol=](https://api.mexc.com/api/v3/klines?symbol=){symbol}&interval={interval}&limit={limit}"
        r_mexc = requests.get(mexc_url, timeout=5.0)
        if r_mexc.status_code == 200:
            data = r_mexc.json()
            if len(data) > 0:
                return [float(candle[4]) for candle in data]
    except Exception:
        pass

    return []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    df = pd.DataFrame(prices, columns=['close'])
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    if pd.isna(val):
        return 50.0
    return float(val)

print("🤖 Background Trading Bot Worker Active & Running...")

while True:
    portfolio = load_portfolio()
    balance = portfolio["balance"]
    holdings = portfolio["holdings"]
    short_holdings = portfolio["short_holdings"]
    entry_prices = portfolio["entry_prices"]
    settings = portfolio["settings"]

    rsi_ub = settings["rsi_buy"]
    rsi_ob = settings["rsi_sell"]
    rsi_short_enter = settings["rsi_short_enter"]
    rsi_short_exit = settings["rsi_short_exit"]
    trade_amt = settings["trade_amount"]
    sl_pct = settings["stop_loss_pct"]
    tp_pct = settings["take_profit_pct"]

    prices = fetch_prices()

    if prices:
        for symbol, current_price in prices.items():
            long_qty = holdings.get(symbol, 0.0)
            short_qty = short_holdings.get(symbol, 0.0)
            entry_price = entry_prices.get(symbol, 0.0)

            # Fetch real closing prices for the last 15 periods
            real_history = fetch_real_history(symbol, interval="15m", limit=15)
            
            # Use real RSI if we successfully pulled enough data, otherwise fall back to neutral
            if len(real_history) >= 15:
                rsi_val = calculate_rsi(real_history)
            else:
                rsi_val = 50.0 

            # LONG POSITIONS EXITS
            if long_qty > 0 and entry_price > 0:
                pnl = (current_price - entry_price) / entry_price
                if pnl <= -sl_pct or pnl >= tp_pct or rsi_val >= rsi_ob:
                    sold_amount = long_qty * current_price
                    balance += sold_amount
                    print(f"[{symbol}] Closing Long at {current_price:.4f} | PnL: {pnl*100:.2f}% | RSI: {rsi_val:.1f}")
                    del holdings[symbol]
                    if symbol in entry_prices:
                        del entry_prices[symbol]

            # SHORT POSITIONS EXITS
            elif short_qty > 0 and entry_price > 0:
                pnl = (entry_price - current_price) / entry_price
                if pnl <= -sl_pct or pnl >= tp_pct or rsi_val <= rsi_short_exit:
                    cover_cost = short_qty * current_price
                    # Refund initial margin + (margin - cover_cost)
                    balance += (short_qty * entry_price) + (short_qty * entry_price - cover_cost)
                    print(f"[{symbol}] Covering Short at {current_price:.4f} | PnL: {pnl*100:.2f}% | RSI: {rsi_val:.1f}")
                    del short_holdings[symbol]
                    if symbol in entry_prices:
                        del entry_prices[symbol]

            # ENTRY CONDITIONS
            else:
                if rsi_val <= rsi_ub and balance >= trade_amt:
                    qty = trade_amt / current_price
                    holdings[symbol] = qty
                    entry_prices[symbol] = current_price
                    balance -= trade_amt
                    print(f"[{symbol}] Opening Long at {current_price:.4f} | RSI: {rsi_val:.1f}")

                elif rsi_val >= rsi_short_enter and balance >= trade_amt:
                    qty = trade_amt / current_price
                    short_holdings[symbol] = qty
                    entry_prices[symbol] = current_price
                    balance -= trade_amt
                    print(f"[{symbol}] Opening Short at {current_price:.4f} | RSI: {rsi_val:.1f}")

    # Save state after analyzing all coins
    portfolio["balance"] = balance
    portfolio["holdings"] = holdings
    portfolio["short_holdings"] = short_holdings
    portfolio["entry_prices"] = entry_prices
    save_portfolio(portfolio)

    # Rest before the next cycle
    time.sleep(15)
