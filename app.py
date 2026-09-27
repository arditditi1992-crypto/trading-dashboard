import streamlit as st
import pandas as pd
import requests
import json
import os
import concurrent.futures
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="24/7 Multi-Timeframe Crypto AI Bot", layout="wide")

st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > div,
    [data-testid="stElementContainer"],
    [data-testid="stDataFrame"],
    .stApp div[aria-busy="true"] {
        opacity: 1 !important;
        transition: none !important;
        filter: none !important;
    }
    div[data-testid="stStatusWidget"] { display: none !important; }
    .stSpinner { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# Auto-refresh interval (5 seconds for fast price updates)
st_autorefresh(interval=5000, limit=None)

st.title("🤖 24/7 Crypto AI Bot (Batch-Optimized Engine)")

PORTFOLIO_FILE = "portfolio.json"

TOP_100_HISTORICAL_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", 
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SHIBUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "NEARUSDT", "MATICUSDT", "UNIUSDT", "BCHUSDT",
    "APTUSDT", "PEPEUSDT", "ICPUSDT", "TRXUSDT", "ETCUSDT", "FILUSDT", "SUIUSDT", "XLMUSDT",
    "ATOMUSDT", "FETUSDT", "INJUSDT", "RENDERUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "STXUSDT"
]

TOP_10_HISTORICAL_SYMBOLS = TOP_100_HISTORICAL_SYMBOLS[:10]

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
        "selected_symbols": TOP_100_HISTORICAL_SYMBOLS,
        "allow_shorts": True,
        "vol_multiplier": 1.3
    }

def save_portfolio():
    data = {
        "balance": st.session_state.get("balance", 1000.0),
        "holdings": st.session_state.get("holdings", {}),
        "short_holdings": st.session_state.get("short_holdings", {}),
        "entry_prices": st.session_state.get("entry_prices", {}),
        "trade_history": st.session_state.get("trade_history", []),
        "trade_amount_usdt": st.session_state.get("trade_amount_usdt", 10.0),
        "take_profit_pct": st.session_state.get("take_profit_pct", 1.5),
        "stop_loss_pct": st.session_state.get("stop_loss_pct", 2.5),
        "rsi_oversold": st.session_state.get("rsi_oversold", 30),
        "rsi_overbought": st.session_state.get("rsi_overbought", 72),
        "selected_symbols": st.session_state.get("selected_symbols", TOP_100_HISTORICAL_SYMBOLS),
        "allow_shorts": st.session_state.get("allow_shorts", True),
        "vol_multiplier": st.session_state.get("vol_multiplier", 1.3)
    }
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

saved_data = load_portfolio()

if 'balance' not in st.session_state: st.session_state.balance = saved_data.get("balance", 1000.0)
if 'holdings' not in st.session_state: st.session_state.holdings = saved_data.get("holdings", {})
if 'short_holdings' not in st.session_state: st.session_state.short_holdings = saved_data.get("short_holdings", {})
if 'entry_prices' not in st.session_state: st.session_state.entry_prices = saved_data.get("entry_prices", {})
if 'trade_history' not in st.session_state: st.session_state.trade_history = saved_data.get("trade_history", [])
if 'bot_running' not in st.session_state: st.session_state.bot_running = True

# --- FAST BATCH TICKER FETCH (Single API Call for ALL coins) ---
def fetch_all_live_prices():
    endpoints = [
        "https://api.binance.com/api/v3/ticker/price",
        "https://api.binance.us/api/v3/ticker/price"
    ]
    for url in endpoints:
        try:
            r = requests.get(url, timeout=1.5)
            if r.status_code == 200:
                return {item['symbol']: float(item['price']) for item in r.json()}
        except Exception:
            continue
    return {}

# Cache historical candles for 60s so price updates don't trigger heavy network requests repeatedly
@st.cache_data(ttl=60, show_spinner=False)
def fetch_historical_candles_cached(symbol):
    try:
        url_5m = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=30"
        r_5m = requests.get(url_5m, timeout=1.5)
        if r_5m.status_code == 200:
            candles = r_5m.json()
            if len(candles) >= 15:
                df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_vol', 'trades', 'tb', 'tq', 'ignore'])
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                return df
    except Exception:
        pass
    return None

def render_engine():
    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    
    # 1. Fetch ALL prices at once (Instant)
    live_prices = fetch_all_live_prices()
    
    if not live_prices:
        st.error("⚠️ Connection issue: Unable to fetch live ticker prices from Binance endpoints.")
        return

    # 2. Render Top 10 Table immediately using batch prices
    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    top_10_summary = []
    
    for symbol in TOP_10_HISTORICAL_SYMBOLS:
        current_price = live_prices.get(symbol, 0.0)
        long_qty = st.session_state.holdings.get(symbol, 0.0)
        short_qty = st.session_state.short_holdings.get(symbol, 0.0)
        entry_price = st.session_state.entry_prices.get(symbol, 0.0)

        position_type = "NONE"
        pl_str = "-"

        if long_qty > 0 and entry_price > 0:
            position_type = "LONG"
            raw_pl = ((current_price - entry_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"
        elif short_qty > 0 and entry_price > 0:
            position_type = "SHORT"
            raw_pl = ((entry_price - current_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"

        price_fmt = f"${current_price:,.4f}" if 0 < current_price < 1 else f"${current_price:,.2f}"

        top_10_summary.append({
            "Asset": symbol,
            "Price": price_fmt if current_price > 0 else "Updating...",
            "Position": position_type,
            "Current P/L": pl_str,
            "Signal": "HOLD",
            "Status": "⚡ Synchronized" if current_price > 0 else "Waiting"
        })

    st.dataframe(pd.DataFrame(top_10_summary), use_container_width=True)

    # 3. Active Positions Table
    st.subheader("💼 Active Open Positions")
    active_positions = []
    for symbol, qty in st.session_state.holdings.items():
        if qty > 0:
            entry = st.session_state.entry_prices.get(symbol, 0.0)
            curr = live_prices.get(symbol, 0.0)
            pnl = ((curr - entry) / entry) * 100 if entry > 0 else 0.0
            active_positions.append({
                "Asset": symbol,
                "Type": "LONG",
                "Live Price": f"${curr:,.2f}",
                "Entry Price": f"${entry:,.2f}",
                "P/L (%)": f"{pnl:+.2f}%"
            })
            
    for symbol, qty in st.session_state.short_holdings.items():
        if qty > 0:
            entry = st.session_state.entry_prices.get(symbol, 0.0)
            curr = live_prices.get(symbol, 0.0)
            pnl = ((entry - curr) / entry) * 100 if entry > 0 else 0.0
            active_positions.append({
                "Asset": symbol,
                "Type": "SHORT",
                "Live Price": f"${curr:,.2f}",
                "Entry Price": f"${entry:,.2f}",
                "P/L (%)": f"{pnl:+.2f}%"
            })

    if active_positions:
        st.dataframe(pd.DataFrame(active_positions), use_container_width=True)
    else:
        st.info("You currently have no open trades.")

    # 4. Historical Trade Log
    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    if st.session_state.trade_history:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet across your active assets.")

render_engine()
