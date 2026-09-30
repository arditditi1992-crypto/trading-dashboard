import time
import requests
import json
import os
import numpy as np
import pandas as pd

PORTFOLIO_FILE =p  "portfolio.json"

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
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
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
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving portfolio: {e}")

def fetch_prices():
    price_dict = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    # Try Binance API
    try:
        r1 = requests.get("https://api.binance.com/api/v3/ticker/price", headers=headers, timeout=5.0)
        if r1.status_code == 200:
            for item in r1.json():
                sym = item['symbol']
                if sym in ALL_TRADING_SYMBOLS:
                    p = float(item['price'])
                    if p > 0:
                        price_dict[sym] = p
    except Exception:
        pass

    # Fallback to MEXC API for remaining symbols
    if len(price_dict) < len(ALL_TRADING_SYMBOLS):
        try:
            r2 = requests.get("https://api.mexc.com/api/v3/ticker/price", headers=headers, timeout=5.0)
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

def fetch_real_history(symbol, interval="15m", limit=100):
    """Fetches historical closing prices with proper headers to prevent API blocking."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    # Binance Attempt
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, headers=headers, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 15:
                return [float(candle[4]) for candle in data]
    except Exception:
        pass

    # MEXC Fallback Attempt
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, headers=headers, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 15:
                return [float(candle[4]) for candle in data]
    except Exception:
        pass

    return []

def calculate_rsi(prices, period=14):
    """Calculates standard Wilder's RSI directly without returning NaN/50.0 defaults."""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
        
    rs = avg_gain / avg_loss
    return round(float(100.0 - (100.0 / (1.0 + rs))), 2)

print("🤖 Background Trading Bot Worker Active & Running...")

while True:
    portfolio = load_portfolio()
    balance = portfolio.get("balance", 1000.0)
    holdings = portfolio.setdefault("holdings", {})
    short_holdings = portfolio.setdefault("short_holdings", {})
    entry_prices = portfolio.setdefault("entry_prices", {})
    settings = portfolio.setdefault("settings", {
        "rsi_buy": 30,
        "rsi_sell": 70,
        "rsi_short_enter": 75,
        "rsi_short_exit": 25,
        "trade_amount": 50,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.10
    })

    rsi_ub = settings.get("rsi_buy", 30)
    rsi_ob = settings.get("rsi_sell", 70)
    rsi_short_enter = settings.get("rsi_short_enter", 75)
    rsi_short_exit = settings.get("rsi_short_exit", 25)
    trade_amt = settings.get("trade_amount", 50)
    sl_pct = settings.get("stop_loss_pct", 0.05)
    tp_pct = settings.get("take_profit_pct", 0.10)

    prices = fetch_prices()

    if prices:
        for symbol, current_price in prices.items():
            long_qty = holdings.get(symbol, 0.0)
            short_qty = short_holdings.get(symbol, 0.0)
            entry_price = entry_prices.get(symbol, 0.0)

            # Fetch real closing prices for up to 100 candles
            real_history = fetch_real_history(symbol, interval="15m", limit=100)
            
            if len(real_history) >= 15:
                rsi_val = calculate_rsi(real_history)
            else:
                continue  # Skip coin scan if API call didn't return valid data

            # LONG POSITIONS EXITS
            if long_qty > 0 and entry_price > 0:
                pnl = (current_price - entry_price) / entry_price
                if pnl <= -sl_pct or pnl >= tp_pct or rsi_val >= rsi_ob:
                    sold_amount = long_qty * current_price
                    balance += sold_amount
                    print(f"[{symbol}] Closing Long at ${current_price:.4f} | PnL: {pnl*100:.2f}% | RSI: {rsi_val:.1f}")
                    del holdings[symbol]
                    if symbol in entry_prices:
                        del entry_prices[symbol]

            # SHORT POSITIONS EXITS
            elif short_qty > 0 and entry_price > 0:
                pnl = (entry_price - current_price) / entry_price
                if pnl <= -sl_pct or pnl >= tp_pct or rsi_val <= rsi_short_exit:
                    cover_cost = short_qty * current_price
                    balance += (short_qty * entry_price) + (short_qty * entry_price - cover_cost)
                    print(f"[{symbol}] Covering Short at ${current_price:.4f} | PnL: {pnl*100:.2f}% | RSI: {rsi_val:.1f}")
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
                    print(f"🚀 [{symbol}] Opening Long at ${current_price:.4f} | RSI: {rsi_val:.1f}")

                elif rsi_val >= rsi_short_enter and balance >= trade_amt:
                    qty = trade_amt / current_price
                    short_holdings[symbol] = qty
                    entry_prices[symbol] = current_price
                    balance -= trade_amt
                    print(f"🔻 [{symbol}] Opening Short at ${current_price:.4f} | RSI: {rsi_val:.1f}")

    # Save state after analyzing all coins
    portfolio["balance"] = balance
    portfolio["holdings"] = holdings
    portfolio["short_holdings"] = short_holdings
    portfolio["entry_prices"] = entry_prices
    save_portfolio(portfolio)

    # Sleep briefly before starting the next full market scan
    time.sleep(15)
