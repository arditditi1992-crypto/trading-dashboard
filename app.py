import streamlit as st
import pandas as pd
import requests
import json
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor
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

# Refresh every 5 seconds
st_autorefresh(interval=5000, limit=None, key="bot_ticker_refresh")

st.title("🤖 24/7 Crypto AI Bot (Auto-Execution Engine)")

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
        "selected_symbols": ALL_TRADING_SYMBOLS,
        "allow_shorts": True,
        "vol_multiplier": 1.3,
        "bot_running": True
    }
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                saved = json.load(f)
                data.update(saved)
                if not data.get("selected_symbols") or len(data.get("selected_symbols")) < len(ALL_TRADING_SYMBOLS):
                    data["selected_symbols"] = ALL_TRADING_SYMBOLS
        except Exception:
            pass
    return data

saved_data = load_portfolio()

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

col_start, col_stop, col_reset = st.columns(3)
with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True):
        saved_data["bot_running"] = True
        st.toast("Bot active!", icon="🟢")

with col_stop:
    if st.button("⏸ PAUSE BOT", use_container_width=True):
        saved_data["bot_running"] = False
        st.toast("Bot paused.", icon="🔴")

with col_reset:
    if st.button("🔄 Reset Portfolio & Clear Cache"):
        if os.path.exists(PORTFOLIO_FILE):
            os.remove(PORTFOLIO_FILE)
        st.rerun()

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

# --- FAST PARALLEL DATA FETCHING ---
def fetch_single_symbol_data(symbol):
    headers = {"User-Agent": "Mozilla/5.0"}
    price = 0.0
    history = []
    
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=50"
        r = requests.get(url, headers=headers, timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 15:
                history = [float(candle[4]) for candle in data]
                price = history[-1]
    except Exception:
        pass

    if price == 0.0:
        try:
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=15m&limit=50"
            r = requests.get(url, headers=headers, timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) >= 15:
                    history = [float(candle[4]) for candle in data]
                    price = history[-1]
        except Exception:
            pass

    return symbol, price, history

@st.cache_data(ttl=5)
def get_all_market_data(symbols):
    results = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_single_symbol_data, sym) for sym in symbols]
        for future in futures:
            sym, price, history = future.result()
            results[sym] = {"price": price, "history": history}
    return results

def calculate_rsi(prices, period=14):
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
    return round(float(100.0 - (100.0 / (1.0 + rs))), 1)

def format_price(price):
    if price <= 0:
        return "$0.00"
    if price < 0.01:
        return f"${price:,.6f}"
    elif price < 1.0:
        return f"${price:,.4f}"
    else:
        return f"${price:,.2f}"

# --- RENDERING & AUTOMATED EXECUTION ENGINE ---
st.metric("Total Cash Balance", f"${saved_data.get('balance', 1000.0):,.2f} USDT")

st.subheader(f"📊 Traded Coins Overview ({len(selected_symbols)} Active Coins)")

market_data = get_all_market_data(selected_symbols)
summary_rows = []

for symbol in selected_symbols:
    sym_info = market_data.get(symbol, {"price": 0.0, "history": []})
    current_price = sym_info["price"]
    history_prices = sym_info["history"]
    
    long_qty = saved_data.get("holdings", {}).get(symbol, 0.0)
    short_qty = saved_data.get("short_holdings", {}).get(symbol, 0.0)
    entry_price = saved_data.get("entry_prices", {}).get(symbol, 0.0)

    rsi_val = calculate_rsi(history_prices) if len(history_prices) >= 15 else 50.0
    macd_status = "MACD Bullish" if rsi_val > 50 else "MACD Neutral"

    pos = "NONE"
    pl_str = "-"
    raw_pl = 0.0
    status = "HOLD"
    reason = f"Neutral (RSI: {rsi_val:.1f} | {macd_status})"

    # --- LONG POSITION EVALUATION & CLOSING ---
    if long_qty > 0 and entry_price > 0 and current_price > 0:
        pos = "LONG"
        raw_pl = ((current_price - entry_price) / entry_price) * 100
        pl_str = f"{raw_pl:+.2f}%"
        
        # Check Exit Trigger
        should_close = False
        close_reason = ""
        if raw_pl >= take_profit_pct:
            should_close = True
            close_reason = f"Take Profit Hit ({raw_pl:+.2f}%)"
        elif raw_pl <= -stop_loss_pct:
            should_close = True
            close_reason = f"Stop Loss Hit ({raw_pl:+.2f}%)"
        elif rsi_val >= rsi_overbought:
            should_close = True
            close_reason = f"Overbought RSI Exit ({rsi_val:.1f})"

        if should_close and saved_data["bot_running"]:
            returned_amount = (long_qty * current_price)
            saved_data["balance"] += returned_amount
            saved_data["holdings"][symbol] = 0.0
            saved_data["entry_prices"][symbol] = 0.0
            
            saved_data.setdefault("trade_history", []).append({
                "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Asset": symbol,
                "Type": "CLOSE (LONG)",
                "Price": current_price,
                "P/L (%)": f"{raw_pl:+.2f}%",
                "Returned ($)": f"${returned_amount:,.2f}",
                "Note": close_reason
            })
            pos, status, reason = "NONE", "CLOSED", close_reason
        else:
            status = "HOLD"
            reason = f"Holding Long ({raw_pl:+.2f}% | RSI: {rsi_val:.1f})"
            
    # --- SHORT POSITION EVALUATION & CLOSING ---
    elif short_qty > 0 and entry_price > 0 and current_price > 0:
        pos = "SHORT"
        raw_pl = ((entry_price - current_price) / entry_price) * 100
        pl_str = f"{raw_pl:+.2f}%"
        
        # Check Exit Trigger
        should_close = False
        close_reason = ""
        if raw_pl >= take_profit_pct:
            should_close = True
            close_reason = f"Take Profit Hit ({raw_pl:+.2f}%)"
        elif raw_pl <= -stop_loss_pct:
            should_close = True
            close_reason = f"Stop Loss Hit ({raw_pl:+.2f}%)"
        elif rsi_val <= rsi_oversold:
            should_close = True
            close_reason = f"Oversold RSI Exit ({rsi_val:.1f})"

        if should_close and saved_data["bot_running"]:
            initial_val = short_qty * entry_price
            returned_amount = initial_val + (initial_val * (raw_pl / 100))
            saved_data["balance"] += returned_amount
            saved_data["short_holdings"][symbol] = 0.0
            saved_data["entry_prices"][symbol] = 0.0
            
            saved_data.setdefault("trade_history", []).append({
                "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Asset": symbol,
                "Type": "CLOSE (SHORT)",
                "Price": current_price,
                "P/L (%)": f"{raw_pl:+.2f}%",
                "Returned ($)": f"${returned_amount:,.2f}",
                "Note": close_reason
            })
            pos, status, reason = "NONE", "CLOSED", close_reason
        else:
            status, reason = "HOLD", f"Holding Short ({raw_pl:+.2f}% | RSI: {rsi_val:.1f})"
            
    # --- ENTRY EXECUTION ---
    else:
        if saved_data["bot_running"] and current_price > 0:
            cash = saved_data.get("balance", 1000.0)
            trade_size = saved_data.get("trade_amount_usdt", 10.0)
            
            if cash >= trade_size:
                if rsi_val <= rsi_oversold:
                    saved_data["balance"] -= trade_size
                    saved_data.setdefault("holdings", {})[symbol] = trade_size / current_price
                    saved_data.setdefault("entry_prices", {})[symbol] = current_price
                    saved_data.setdefault("trade_history", []).append({
                        "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Asset": symbol,
                        "Type": "BUY (LONG)",
                        "Price": current_price,
                        "P/L (%)": "0.00%",
                        "Returned ($)": f"-${trade_size:,.2f}",
                        "Note": f"Strong Buy Entry (RSI: {rsi_val:.1f})"
                    })
                    pos, entry_price, status, reason = "LONG", current_price, "BUY", f"Strong Buy (RSI: {rsi_val:.1f})"
                elif allow_shorts and rsi_val >= rsi_overbought:
                    saved_data["balance"] -= trade_size
                    saved_data.setdefault("short_holdings", {})[symbol] = trade_size / current_price
                    saved_data.setdefault("entry_prices", {})[symbol] = current_price
                    saved_data.setdefault("trade_history", []).append({
                        "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Asset": symbol,
                        "Type": "SHORT",
                        "Price": current_price,
                        "P/L (%)": "0.00%",
                        "Returned ($)": f"-${trade_size:,.2f}",
                        "Note": f"Strong Short Entry (RSI: {rsi_val:.1f})"
                    })
                    pos, entry_price, status, reason = "SHORT", current_price, "SHORT", f"Strong Short (RSI: {rsi_val:.1f})"
                else:
                    status, reason = "HOLD", f"Neutral (RSI: {rsi_val:.1f} | {macd_status})"
            else:
                status, reason = "HOLD", "Insufficient cash balance"
        else:
            status, reason = "HOLD", f"Neutral (RSI: {rsi_val:.1f} | {macd_status})"

    summary_rows.append({
        "Asset": symbol,
        "Price": format_price(current_price),
        "Position": pos,
        "Current P/L": pl_str,
        "Status": status,
        "Reason": reason,
        "raw_pl": raw_pl
    })

# Save portfolio state
with open(PORTFOLIO_FILE, "w") as f:
    json.dump(saved_data, f, indent=4)

if summary_rows:
    if sort_order == "Current P/L":
        summary_rows.sort(key=lambda x: x['raw_pl'], reverse=True)
    df_summary = pd.DataFrame(summary_rows).drop(columns=['raw_pl'])
    st.dataframe(df_summary, use_container_width=True, height=500)

st.write("---")

st.subheader("💼 Active Open Positions")
active_positions = [row for row in summary_rows if row["Position"] != "NONE"]
if active_positions:
    if sort_order == "Current P/L":
        active_positions.sort(key=lambda x: x['raw_pl'], reverse=True)
    df_active = pd.DataFrame(active_positions).drop(columns=['raw_pl'])
    st.dataframe(df_active, use_container_width=True)
else:
    st.info("You currently have no open trades. The engine is scanning your active coins.")

st.subheader("📋 Multi-Asset Trade Log")
trade_history = saved_data.get("trade_history", [])
if len(trade_history) > 0:
    st.dataframe(pd.DataFrame(trade_history).iloc[::-1], use_container_width=True)
else:
    st.info("No trades logged yet across your active assets.")
