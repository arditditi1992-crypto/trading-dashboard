import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="24/7 Crypto AI Bot", layout="wide")

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

# 3-Second Auto-Refresh for instantaneous synchronization
st_autorefresh(interval=3000, limit=None, key="bot_ticker_refresh")

st.title("🤖 24/7 Crypto AI Bot (Batch Live-Tick Engine)")

PORTFOLIO_FILE = "portfolio.json"

TOP_10_HISTORICAL_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", 
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SHIBUSDT", "LINKUSDT"
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
        "trade_amount_usdt": 10.0
    }

def save_portfolio():
    data = {
        "balance": st.session_state.get("balance", 1000.0),
        "holdings": st.session_state.get("holdings", {}),
        "short_holdings": st.session_state.get("short_holdings", {}),
        "entry_prices": st.session_state.get("entry_prices", {}),
        "trade_history": st.session_state.get("trade_history", []),
        "trade_amount_usdt": st.session_state.get("trade_amount_usdt", 10.0)
    }
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

saved_data = load_portfolio()

if 'balance' not in st.session_state: st.session_state.balance = saved_data.get("balance", 1000.0)
if 'holdings' not in st.session_state: st.session_state.holdings = saved_data.get("holdings", {})
if 'short_holdings' not in st.session_state: st.session_state.short_holdings = saved_data.get("short_holdings", {})
if 'entry_prices' not in st.session_state: st.session_state.entry_prices = saved_data.get("entry_prices", {})
if 'trade_history' not in st.session_state: st.session_state.trade_history = saved_data.get("trade_history", [])

# --- SINGLE HTTP BATCH TICKER FETCH ---
def fetch_top_10_live_prices():
    """Fetches ALL top 10 symbol prices simultaneously in ONE single HTTP call."""
    symbols_param = json.dumps(TOP_10_HISTORICAL_SYMBOLS).replace(" ", "")
    url = f"https://api.binance.com/api/v3/ticker/price?symbols={symbols_param}"
    
    try:
        response = requests.get(url, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            return {item['symbol']: float(item['price']) for item in data}
    except Exception:
        pass
        
    # Fallback endpoint if Binance main is blocked/rate-limited
    try:
        url_us = f"https://api.binance.us/api/v3/ticker/price?symbols={symbols_param}"
        response = requests.get(url_us, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            return {item['symbol']: float(item['price']) for item in data}
    except Exception:
        pass

    return {}

def render_engine():
    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    
    # Batch fetch live prices instantly
    live_prices = fetch_top_10_live_prices()
    
    current_time_str = datetime.now().strftime("%H:%M:%S")

    # Render Top 10 Table
    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    
    if not live_prices:
        st.warning("⚡ Reconnecting to Binance price feed...")
    else:
        top_10_rows = []
        for symbol in TOP_10_HISTORICAL_SYMBOLS:
            price = live_prices.get(symbol, 0.0)
            
            long_qty = st.session_state.holdings.get(symbol, 0.0)
            short_qty = st.session_state.short_holdings.get(symbol, 0.0)
            entry_price = st.session_state.entry_prices.get(symbol, 0.0)

            pos_type = "-"
            pl_str = "-"

            if long_qty > 0 and entry_price > 0:
                pos_type = "LONG"
                pl_val = ((price - entry_price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"
            elif short_qty > 0 and entry_price > 0:
                pos_type = "SHORT"
                pl_val = ((entry_price - price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"

            price_formatted = f"${price:,.4f}" if 0 < price < 1 else f"${price:,.2f}"

            top_10_rows.append({
                "Asset": symbol,
                "Price": price_formatted if price > 0 else "Syncing...",
                "Position": pos_type,
                "Current P/L": pl_str,
                "Status": f"🟢 Updated at {current_time_str}" if price > 0 else "🔴 Offline"
            })

        st.dataframe(pd.DataFrame(top_10_rows), use_container_width=True)

    st.write("---")

    # Render Active Open Positions
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

    # Render Historical Trade Log
    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    if st.session_state.trade_history:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet across your active assets.")

render_engine()
