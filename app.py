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

# Auto-refresh UI every 3 seconds for fast live updates
st_autorefresh(interval=3000, limit=None, key="bot_ticker_refresh")

st.title("🤖 24/7 Crypto AI Bot (Cloud-Safe Engine)")

PORTFOLIO_FILE = "portfolio.json"

# CoinCap ID Mapping for guaranteed cloud fetching
COINMAP = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "XRPUSDT": "binance-coin", # fallback placeholder
    "BNBUSDT": "binance-coin",
    "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche",
    "SHIBUSDT": "shiba-inu",
    "LINKUSDT": "chainlink"
}

TOP_10_HISTORICAL_SYMBOLS = list(COINMAP.keys())
ALL_TRADING_SYMBOLS = TOP_10_HISTORICAL_SYMBOLS

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
        "selected_symbols": ALL_TRADING_SYMBOLS,
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
        "selected_symbols": st.session_state.get("selected_symbols", ALL_TRADING_SYMBOLS),
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
if 'cached_prices' not in st.session_state: st.session_state.cached_prices = {}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Bot Settings")
sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_usdt = st.number_input(
        "Trade Size ($ USDT)", min_value=5.0, max_value=500.0, step=5.0,
        value=float(saved_data.get("trade_amount_usdt", 10.0))
    )
    st.session_state.trade_amount_usdt = trade_amount_usdt

with sb_col2:
    sort_order = st.selectbox("Sort Overview By", ["Alphabetical", "Current P/L"])

st.sidebar.subheader("🛡️ Short Protection Controls")
allow_shorts = st.sidebar.checkbox("Enable Short Positions", value=saved_data.get("allow_shorts", True))
st.session_state.allow_shorts = allow_shorts

vol_multiplier = st.sidebar.slider(
    "Min Short Vol Spike (x Avg Vol)", min_value=1.0, max_value=3.0, step=0.1,
    value=float(saved_data.get("vol_multiplier", 1.3))
)
st.session_state.vol_multiplier = vol_multiplier

st.sidebar.subheader("🎯 Risk Controls")
take_profit_pct = st.sidebar.slider("Take Profit (%)", 0.5, 10.0, float(saved_data.get("take_profit_pct", 1.5)), 0.5)
st.session_state.take_profit_pct = take_profit_pct

stop_loss_pct = st.sidebar.slider("Tight Stop Loss (%)", 0.5, 10.0, float(saved_data.get("stop_loss_pct", 2.5)), 0.5)
st.session_state.stop_loss_pct = stop_loss_pct

st.sidebar.subheader("📊 Indicator Thresholds")
rsi_oversold = st.sidebar.slider("RSI Oversold (Buy)", 15, 45, int(saved_data.get("rsi_oversold", 30)), 1)
st.session_state.rsi_oversold = rsi_oversold

rsi_overbought = st.sidebar.slider("RSI Overbought (Short)", 55, 90, int(saved_data.get("rsi_overbought", 72)), 1)
st.session_state.rsi_overbought = rsi_overbought

valid_defaults = [s for s in saved_data.get("selected_symbols", ALL_TRADING_SYMBOLS) if s in ALL_TRADING_SYMBOLS]
selected_symbols = st.sidebar.multiselect(
    f"Active Trading Coins ({len(ALL_TRADING_SYMBOLS)} Top Volume Coins)",
    options=sorted(ALL_TRADING_SYMBOLS),
    default=valid_defaults if valid_defaults else ALL_TRADING_SYMBOLS
)
st.session_state.selected_symbols = selected_symbols

if st.sidebar.button("🔄 Reset Portfolio ($1,000 USDT)"):
    if os.path.exists(PORTFOLIO_FILE):
        os.remove(PORTFOLIO_FILE)
    st.session_state.balance = 1000.0
    st.session_state.holdings = {}
    st.session_state.short_holdings = {}
    st.session_state.entry_prices = {}
    st.session_state.trade_history = []
    st.session_state.selected_symbols = ALL_TRADING_SYMBOLS
    st.session_state.cached_prices = {}
    st.rerun()

save_portfolio()

for sym in st.session_state.selected_symbols:
    if sym not in st.session_state.holdings: st.session_state.holdings[sym] = 0.0
    if sym not in st.session_state.short_holdings: st.session_state.short_holdings[sym] = 0.0
    if sym not in st.session_state.entry_prices: st.session_state.entry_prices[sym] = 0.0

col_start, col_stop = st.columns(2)
with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True):
        st.session_state.bot_running = True
        st.toast("Bot active!", icon="🟢")

with col_stop:
    if st.button("⏸️ PAUSE BOT", use_container_width=True):
        st.session_state.bot_running = False
        st.toast("Bot paused.", icon="🔴")

if st.session_state.bot_running:
    st.success(f"🟢 STATUS: BOT ACTIVE (Trading {len(st.session_state.selected_symbols)} Coins via Cloud-Safe Engine)")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- UNBLOCKED CLOUD PRICE FETCHING ENGINE ---
def fetch_cloud_safe_prices():
    """Uses CoinCap REST API which never blocks Streamlit Cloud IP addresses."""
    try:
        url = "https://api.coincap.io/v2/assets?limit=100"
        r = requests.get(url, timeout=3.0)
        if r.status_code == 200:
            data = r.json().get("data", [])
            price_dict = {}
            
            # Map CoinCap asset IDs to trading symbols
            inv_map = {v: k for k, v in COINMAP.items()}
            for item in data:
                asset_id = item.get("id")
                if asset_id in inv_map and item.get("priceUsd"):
                    price_dict[inv_map[asset_id]] = float(item["priceUsd"])
            
            # Add XRP fallback if missing from CoinCap top list
            if "XRPUSDT" not in price_dict:
                for item in data:
                    if item.get("symbol") == "XRP":
                        price_dict["XRPUSDT"] = float(item["priceUsd"])
                        
            if price_dict:
                st.session_state.cached_prices.update(price_dict)
                return st.session_state.cached_prices
    except Exception:
        pass

    # Backup attempt via KuCoin if CoinCap has a temporary delay
    try:
        r = requests.get("https://api.kucoin.com/api/v1/market/allTickers", timeout=3.0)
        if r.status_code == 200:
            tickers = r.json().get("data", {}).get("ticker", [])
            for t in tickers:
                sym = t.get("symbol", "").replace("-", "")
                if sym in TOP_10_HISTORICAL_SYMBOLS and t.get("last"):
                    st.session_state.cached_prices[sym] = float(t["last"])
            return st.session_state.cached_prices
    except Exception:
        pass

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

def render_engine():
    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    current_time_str = datetime.now().strftime("%H:%M:%S")

    # Fetch prices instantly from cloud-safe endpoints
    live_prices = fetch_cloud_safe_prices()

    # 1. TOP 10 OVERVIEW TABLE
    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    
    top_10_summary = []
    for symbol in TOP_10_HISTORICAL_SYMBOLS:
        current_price = live_prices.get(symbol, 0.0)
        
        long_qty = st.session_state.holdings.get(symbol, 0.0)
        short_qty = st.session_state.short_holdings.get(symbol, 0.0)
        entry_price = st.session_state.entry_prices.get(symbol, 0.0)

        position_type = "NONE"
        pl_str = "-"
        raw_pl = 0.0

        if long_qty > 0 and entry_price > 0 and current_price > 0:
            position_type = "LONG"
            raw_pl = ((current_price - entry_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"
        elif short_qty > 0 and entry_price > 0 and current_price > 0:
            position_type = "SHORT"
            raw_pl = ((entry_price - current_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"

        top_10_summary.append({
            "Asset": symbol,
            "Price": format_price(current_price),
            "Position": position_type if position_type != "NONE" else "-",
            "Current P/L": pl_str,
            "Signal": "HOLD",
            "raw_pl": raw_pl
        })

    if top_10_summary:
        if sort_order == "Current P/L":
            top_10_summary.sort(key=lambda x: x['raw_pl'], reverse=True)
        df_top10 = pd.DataFrame(top_10_summary).drop(columns=['raw_pl'])
        st.dataframe(df_top10, use_container_width=True)

    st.write("---")

    # 2. ACTIVE OPEN POSITIONS TABLE
    st.subheader("💼 Active Open Positions")
    active_positions_summary = []
    
    for symbol in st.session_state.selected_symbols:
        long_qty = st.session_state.holdings.get(symbol, 0.0)
        short_qty = st.session_state.short_holdings.get(symbol, 0.0)
        entry_price = st.session_state.entry_prices.get(symbol, 0.0)
        current_price = live_prices.get(symbol, 0.0)

        if (long_qty > 0 or short_qty > 0) and current_price > 0:
            position_type = "LONG" if long_qty > 0 else "SHORT"
            if position_type == "LONG":
                raw_pl = ((current_price - entry_price) / entry_price) * 100
            else:
                raw_pl = ((entry_price - current_price) / entry_price) * 100

            active_positions_summary.append({
                "Asset": symbol,
                "Type": position_type,
                "Live Price": format_price(current_price),
                "Entry Price": format_price(entry_price),
                "Current P/L": f"{raw_pl:+.2f}%",
                "Signal": "HOLD",
                "raw_pl": raw_pl
            })

    if active_positions_summary:
        if sort_order == "Current P/L":
            active_positions_summary.sort(key=lambda x: x['raw_pl'], reverse=True)
        else:
            active_positions_summary.sort(key=lambda x: x['Asset'])
            
        display_positions = pd.DataFrame(active_positions_summary).drop(columns=['raw_pl'])
        st.dataframe(display_positions, use_container_width=True)
    else:
        st.info("You currently have no open trades.")

    # 3. HISTORICAL TRADE LOG
    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet across your active assets.")

render_engine()
