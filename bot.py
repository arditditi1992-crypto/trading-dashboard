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
        "trade_history": [],
        "trade_amount_usdt": 10.0,
        "take_profit_pct": 1.5,
        "stop_loss_pct": 2.5,
        "rsi_oversold": 30,
        "rsi_overbought": 72,
        "allow_shorts": True,
        "bot_running": True
    }

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_prices():
    price_dict = {}
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5.0)
        if r.status_code == 200:
            for item in r.json():
                if item['symbol'] in ALL_TRADING_SYMBOLS:
                    p = float(item['price'])
                    if p > 0:
                        price_dict[item['symbol']] = p
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

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100.0
    return float(100.0 - (100.0 / (1.0 + (up / down))))

print("🤖 Background Trading Bot Worker Started...")

while True:
    try:
        portfolio = load_portfolio()
        if portfolio.get("bot_running", True):
            prices = fetch_prices()
            take_profit = portfolio.get("take_profit_pct", 1.5)
            stop_loss = portfolio.get("stop_loss_pct", 2.5)
            rsi_os = portfolio.get("rsi_oversold", 30)
            rsi_ob = portfolio.get("rsi_overbought", 72)
            allow_shorts = portfolio.get("allow_shorts", True)

            holdings = portfolio.setdefault("holdings", {})
            short_holdings = portfolio.setdefault("short_holdings", {})
            entry_prices = portfolio.setdefault("entry_prices", {})
            trade_history = portfolio.setdefault("trade_history", [])

            for symbol, current_price in prices.items():
                long_qty = holdings.get(symbol, 0.0)
                short_qty = short_holdings.get(symbol, 0.0)
                entry_price = entry_prices.get(symbol, 0.0)

                np.random.seed(hash(symbol) % 10000)
                sim_history = [current_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(15)]
                sim_history.append(current_price)
                rsi_val = calculate_rsi(sim_history)

                if long_qty > 0 and entry_price > 0:
                    raw_pl = ((current_price - entry_price) / entry_price) * 100
                    if raw_pl >= take_profit or raw_pl <= -stop_loss or rsi_val >= rsi_ob:
                        portfolio["balance"] += (long_qty * current_price)
                        holdings[symbol] = 0.0
                        trade_history.append({
                            "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Asset": symbol,
                            "Type": "CLOSE LONG",
                            "Price": current_price,
                            "Value": long_qty * current_price,
                            "Note": f"Exit target reached ({raw_pl:+.2f}%)"
                        })

                elif short_qty > 0 and entry_price > 0:
                    raw_pl = ((entry_price - current_price) / entry_price) * 100
                    if raw_pl >= take_profit or raw_pl <= -stop_loss or rsi_val <= rsi_os:
                        portfolio["balance"] += (short_qty * current_price)
                        short_holdings[symbol] = 0.0
                        trade_history.append({
                            "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Asset": symbol,
                            "Type": "CLOSE SHORT",
                            "Price": current_price,
                            "Value": short_qty * current_price,
                            "Note": f"Exit target reached ({raw_pl:+.2f}%)"
                        })

                elif long_qty == 0 and short_qty == 0:
                    cash = portfolio.get("balance", 1000.0)
                    trade_size = portfolio.get("trade_amount_usdt", 10.0)
                    if cash >= trade_size:
                        if rsi_val <= rsi_os:
                            portfolio["balance"] -= trade_size
                            holdings[symbol] = trade_size / current_price
                            entry_prices[symbol] = current_price
                            trade_history.append({
                                "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Asset": symbol,
                                "Type": "BUY (LONG)",
                                "Price": current_price,
                                "Value": trade_size,
                                "Note": f"Auto Buy (RSI: {rsi_val:.1f})"
                            })
                        elif allow_shorts and rsi_val >= rsi_ob:
                            portfolio["balance"] -= trade_size
                            short_holdings[symbol] = trade_size / current_price
                            entry_prices[symbol] = current_price
                            trade_history.append({
                                "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Asset": symbol,
                                "Type": "SHORT",
                                "Price": current_price,
                                "Value": trade_size,
                                "Note": f"Auto Short (RSI: {rsi_val:.1f})"
                            })

            save_portfolio(portfolio)
    except Exception as e:
        print(f"Error in background worker: {e}")
    
    time.sleep(3)
