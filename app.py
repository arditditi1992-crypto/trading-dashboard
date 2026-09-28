import streamlit as st
import pandas as pd
import requests
import json
import os
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

st_autorefresh(interval=3000, limit=None, key="bot_ticker_refresh")

st.title("🤖 24/7 Crypto AI Bot (Cloud-Safe Engine)")

PORTFOLIO_FILE = "portfolio.json"

# Full 88+ Active Trading Coins list
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
        "balance": 1000.0, "holdings": {}, "short_holdings": {}, "entry_prices": {},
        "trade_history": [], "trade_amount_usdt": 10.0, "take_profit_pct": 1.5,
        "stop_loss_pct": 2.5, "rsi_oversold": 30, "rsi_overbought": 72,
        "selected_symbols": ALL_TRADING_SYMBOLS[:10], "allow_shorts": True,
        "vol_multiplier": 1.3, "bot_running": True
    }

saved_data = load_portfolio()
if 'cached_prices' not in st.session_state: st.session_state.cached_prices = {}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Bot Settings")
sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_usdt = st.number_input("Trade Size ($ USDT)", min_value=5.0, max_value=500.0, step=5.0, value=float(saved_data.get("trade_amount_usdt", 10.0)))
with sb_col2:
    sort_order = st.selectbox("Sort Overview By", ["Alphabetical", "Current P/L"])

st.sidebar.subheader("🛡️ Short Protection Controls")
allow_shorts = st.sidebar.checkbox("Enable Short Positions", value=saved_data.get("allow_shorts", True))
vol_multiplier = st.sidebar.slider("Min Short Vol Spike (x Avg Vol)", 1.0, 3.0, float(saved_data.get("vol_multiplier", 1.3)), 0.1)

st.sidebar.subheader("🎯 Risk Controls")
take_profit_pct = st.sidebar.slider("Take Profit (%)", 0.5, 10.0, float(saved_data.get("take_profit_pct", 1.5)), 0.5)
stop_loss_pct = st.sidebar.slider("Tight Stop Loss (%)", 0.5, 10.0, float(saved_data.get("stop_loss_pct", 2.5)), 0.5)

st.sidebar.subheader("📊 Indicator Thresholds")
rsi_oversold = st.sidebar.slider("RSI Oversold (Buy)", 15, 45, int(saved_data.get("rsi_oversold", 30)), 1)
rsi_overbought = st.sidebar.slider("RSI Overbought (Short)", 55, 90, int(saved_data.get("rsi_overbought", 72)), 1)

valid_defaults = [s for s in saved_data.get("selected_symbols", ALL_TRADING_SYMBOLS[:10]) if s in ALL_TRADING_SYMBOLS]
selected_symbols = st.sidebar.multiselect(f"Active Trading Coins", options=sorted(ALL_TRADING_SYMBOLS), default=valid_defaults if valid_defaults else ALL_TRADING_SYMBOLS[:10])

col_start, col_stop, col_reset = st.columns(3)
with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True):
        saved_data["bot_running"] = True
        st.toast("Bot active!", icon="🟢")
with col_stop:
    if st.button("⏸️ PAUSE BOT", use_container_width=True):
        saved_data["bot_running"] = False
        st.toast("Bot paused.", icon="🔴")
with col_reset:
    if st.button("🔄 Reset Portfolio ($1,000)"):
        saved_data = load_portfolio()
        saved_data["balance"] = 1000.0
        saved_data["holdings"] = {}
        saved_data["trade_history"] = []
        st.rerun()

saved_data.update({
    "trade_amount_usdt": trade_amount_usdt, "allow_shorts": allow_shorts,
    "vol_multiplier": vol_multiplier, "take_profit_pct": take_profit_pct,
    "stop_loss_pct": stop_loss_pct, "rsi_oversold": rsi_oversold,
    "rsi_overbought": rsi_overbought, "selected_symbols": selected_symbols
})
with open(PORTFOLIO_FILE, "w") as f:
    json.dump(saved_data, f, indent=4)

if saved_data["bot_running"]:
    st.success(f"🟢 STATUS: BOT ACTIVE (Trading {len(selected_symbols)} Coins)")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- LIGHTWEIGHT BINANCE REST PRICE FETCHING ---
def fetch_binance_prices():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            price_dict = {item['symbol']: float(item['price']) for item in data if item['symbol'] in ALL_TRADING_SYMBOLS}
            if price_dict:
                st.session_state.cached_prices.update(price_dict)
    except Exception:
        pass
    return st.session_state.cached_prices

def format_price(price):
    if price <= 0: return "Syncing..."
    if price < 0.01: return f"${price:,.6f}"
    elif price < 1.0: return f"${price:,.4f}"
    else: return f"${price:,.2f}"

# --- RENDERING ENGINE ---
st.metric("Total Cash Balance", f"${saved_data.get('balance', 1000.0):,.2f} USDT")
live_prices = fetch_binance_prices()

st.subheader(f"📊 Top Traded Coins Overview ({len(selected_symbols)} Active Coins)")
summary_rows = []
for symbol in selected_symbols:
    current_price = live_prices.get(symbol, 0.0)
    long_qty = saved_data.get("holdings", {}).get(symbol, 0.0)
    entry_price = saved_data.get("entry_prices", {}).get(symbol, 0.0)
    
    pos = "NONE"
    pl_str = "-"
    raw_pl = 0.0
    if long_qty > 0 and entry_price > 0 and current_price > 0:
        pos = "LONG"
        raw_pl = ((current_price - entry_price) / entry_price) * 100
        pl_str = f"{raw_pl:+.2f}%"

    summary_rows.append({"Asset": symbol, "Price": format_price(current_price), "Position": pos, "Current P/L": pl_str, "raw_pl": raw_pl})

if summary_rows:
    if sort_order == "Current P/L": summary_rows.sort(key=lambda x: x['raw_pl'], reverse=True)
    st.dataframe(pd.DataFrame(summary_rows).drop(columns=['raw_pl']), use_container_width=True)

st.write("---")
st.subheader("💼 Active Open Positions")
active_positions = [row for row in summary_rows if row["Position"] != "NONE"]
if active_positions:
    st.dataframe(pd.DataFrame(active_positions).drop(columns=['raw_pl']), use_container_width=True)
else:
    st.info("You currently have no open trades.")

st.subheader("📋 Global Multi-Asset Historical Trade Log")
if len(saved_data.get("trade_history", [])) > 0:
    st.table(pd.DataFrame(saved_data["trade_history"]).iloc[::-1])
else:
    st.info("No trades logged yet across your active assets.")
