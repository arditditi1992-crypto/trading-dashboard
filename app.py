import streamlit as st
import pandas as pd
import requests
import json
import os
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

# Refresh every 3 seconds
st_autorefresh(interval=3000, limit=None, key="bot_ticker_refresh")

st.title("🤖 24/7 Crypto AI Bot (Railway Production Engine)")

PORTFOLIO_FILE = "portfolio.json"

# Complete list of 88+ Active Trading Coins
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
    data = {
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
        "selected_symbols": ALL_TRADING_SYMBOLS,  # Force all 88+ by default
        "allow_shorts": True,
        "vol_multiplier": 1.3,
        "bot_running": True
    }
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                saved = json.load(f)
                data.update(saved)
                # Force override selected symbols if it was stuck on 10 or empty
                if not data.get("selected_symbols") or len(data.get("selected_symbols")) < len(ALL_TRADING_SYMBOLS):
                    data["selected_symbols"] = ALL_TRADING_SYMBOLS
        except Exception:
            pass
    return data

saved_data = load_portfolio()

if 'cached_prices' not in st.session_state: 
    st.session_state.cached_prices = {}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Bot Settings")
sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_usdt = st.number_input(
        "Trade Size ($ USDT)", min_value=5.0, max_value=500.0, step=5.0,
        value=float(saved_data.get("trade_amount_usdt", 10.0))
    )

with sb_col2:
    sort_order = st.selectbox("Sort Overview By", ["Alphabetical", "Current P/L"])

st.sidebar.subheader("🛡️ Short Protection Controls")
allow_shorts = st.sidebar.checkbox("Enable Short Positions", value=saved_data.get("allow_shorts", True))

vol_multiplier = st.sidebar.slider(
    "Min Short Vol Spike (x Avg Vol)", min_value=1.0, max_value=3.0, step=0.1,
    value=float(saved_data.get("vol_multiplier", 1.3))
)

st.sidebar.subheader("🎯 Risk Controls")
take_profit_pct = st.sidebar.slider("Take Profit (%)", 0.5, 10.0, float(saved_data.get("take_profit_pct", 1.5)), 0.5)
stop_loss_pct = st.sidebar.slider("Tight Stop Loss (%)", 0.5, 10.0, float(saved_data.get("stop_loss_pct", 2.5)), 0.5)

st.sidebar.subheader("📊 Indicator Thresholds")
rsi_oversold = st.sidebar.slider("RSI Oversold (Buy)", 15, 45, int(saved_data.get("rsi_oversold", 30)), 1)
rsi_overbought = st.sidebar.slider("RSI Overbought (Short)", 55, 90, int(saved_data.get("rsi_overbought", 72)), 1)

selected_symbols = st.sidebar.multiselect(
    f"Active Trading Coins ({len(ALL_TRADING_SYMBOLS)} Available)",
    options=sorted(ALL_TRADING_SYMBOLS),
    default=saved_data.get("selected_symbols", ALL_TRADING_SYMBOLS)
)

# Control Buttons
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
    if st.button("🔄 Reset Portfolio & Clear Cache"):
        if os.path.exists(PORTFOLIO_FILE):
            os.remove(PORTFOLIO_FILE)
        st.session_state.cached_prices = {}
        st.rerun()

# Save settings back to JSON
saved_data.update({
    "trade_amount_usdt": trade_amount_usdt,
    "allow_shorts": allow_shorts,
    "vol_multiplier": vol_multiplier,
    "take_profit_pct": take_profit_pct,
    "stop_loss_pct": stop_loss_pct,
    "rsi_oversold": rsi_oversold,
    "rsi_overbought": rsi_overbought,
    "selected_symbols": selected_symbols
})
with open(PORTFOLIO_FILE, "w") as f:
    json.dump(saved_data, f, indent=4)

if saved_data["bot_running"]:
    st.success(f"🟢 STATUS: BOT ACTIVE (Tracking {len(selected_symbols)} Active Coins)")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- BULLETPROOF PRICE FETCHING WITH DIAGNOSTICS ---
def fetch_live_prices():
    price_dict = {}
    error_log = []

    # 1. Try Binance US/Global API
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=4.0)
        if r.status_code == 200:
            for item in r.json():
                sym = item['symbol']
                if sym in ALL_TRADING_SYMBOLS:
                    price_dict[sym] = float(item['price'])
        else:
            error_log.append(f"Binance code: {r.status_code}")
    except Exception as e:
        error_log.append(f"Binance error: {str(e)}")

    # 2. Fallback: MEXC Public API (Very reliable on cloud servers)
    if not price_dict:
        try:
            r2 = requests.get("https://api.mexc.com/api/v3/ticker/price", timeout=4.0)
            if r2.status_code == 200:
                for item in r2.json():
                    sym = item['symbol']
                    if sym in ALL_TRADING_SYMBOLS:
                        price_dict[sym] = float(item['price'])
        except Exception as e:
            error_log.append(f"MEXC error: {str(e)}")

    if price_dict:
        st.session_state.cached_prices.update(price_dict)
    elif error_log:
        st.sidebar.error(f"Price Fetch Warning: {error_log[0]}")
        
    return st.session_state.cached_prices

def format_price(price):
    if price <= 0:
        return "Syncing..."
    if price < 0.01:
        return f"${price:,.6f}"
    elif price < 1.0:
        return f"${price:,.4f}"
    else:
        return f"${price:,.2f}"

# --- RENDERING ENGINE ---
st.metric("Total Cash Balance", f"${saved_data.get('balance', 1000.0):,.2f} USDT")
live_prices = fetch_live_prices()

# 1. OVERVIEW TABLE
st.subheader(f"📊 Traded Coins Overview ({len(selected_symbols)} Active Coins)")

summary_rows = []
for symbol in selected_symbols:
    current_price = live_prices.get(symbol, 0.0)
    
    long_qty = saved_data.get("holdings", {}).get(symbol, 0.0)
    short_qty = saved_data.get("short_holdings", {}).get(symbol, 0.0)
    entry_price = saved_data.get("entry_prices", {}).get(symbol, 0.0)

    pos = "NONE"
    pl_str = "-"
    raw_pl = 0.0

    if long_qty > 0 and entry_price > 0 and current_price > 0:
        pos = "LONG"
        raw_pl = ((current_price - entry_price) / entry_price) * 100
        pl_str = f"{raw_pl:+.2f}%"
    elif short_qty > 0 and entry_price > 0 and current_price > 0:
        pos = "SHORT"
        raw_pl = ((entry_price - current_price) / entry_price) * 100
        pl_str = f"{raw_pl:+.2f}%"

    summary_rows.append({
        "Asset": symbol,
        "Price": format_price(current_price),
        "Position": pos,
        "Current P/L": pl_str,
        "raw_pl": raw_pl
    })

if summary_rows:
    if sort_order == "Current P/L":
        summary_rows.sort(key=lambda x: x['raw_pl'], reverse=True)
    df_summary = pd.DataFrame(summary_rows).drop(columns=['raw_pl'])
    st.dataframe(df_summary, use_container_width=True)

st.write("---")

# 2. ACTIVE OPEN POSITIONS
st.subheader("💼 Active Open Positions")
active_positions = [row for row in summary_rows if row["Position"] != "NONE"]

if active_positions:
    if sort_order == "Current P/L":
        active_positions.sort(key=lambda x: x['raw_pl'], reverse=True)
    df_active = pd.DataFrame(active_positions).drop(columns=['raw_pl'])
    st.dataframe(df_active, use_container_width=True)
else:
    st.info("You currently have no open trades. The engine is scanning your active coins.")

# 3. HISTORICAL TRADE LOG
st.subheader("📋 Global Multi-Asset Historical Trade Log")
trade_history = saved_data.get("trade_history", [])
if len(trade_history) > 0:
    st.table(pd.DataFrame(trade_history).iloc[::-1])
else:
    st.info("No trades logged yet across your active assets.")
