import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import concurrent.futures
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="24/7 Multi-Timeframe Crypto AI Bot", layout="wide")

# Hide Streamlit spinner/status overlays for smooth background updating
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

# --- AUTOMATIC BROWSER REFRESH (EVERY 10 SECONDS) ---
# Prevents mobile browsers and inactive tabs from putting the WebSocket to sleep
st_autorefresh(interval=10000, limit=None, key="bot_autorefresh_loop")

st.title("🤖 24/7 Crypto AI Bot (1H Multi-Timeframe Strategy)")

PORTFOLIO_FILE = "portfolio.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

TOP_100_HISTORICAL_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", 
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SHIBUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "NEARUSDT", "MATICUSDT", "UNIUSDT", "BCHUSDT",
    "APTUSDT", "PEPEUSDT", "ICPUSDT", "TRXUSDT", "ETCUSDT", "FILUSDT", "SUIUSDT", "XLMUSDT",
    "ATOMUSDT", "FETUSDT", "INJUSDT", "RENDERUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "STXUSDT",
    "RUNEUSDT", "AAVEUSDT", "GRTUSDT", "FLOKIUSDT", "THETAUSDT", "FTMUSDT", "MKRUSDT", "LDOUSDT",
    "SEIUSDT", "BONKUSDT", "ORDIUSDT", "ALGOUSDT", "EGLDUSDT", "GALAUSDT", "FLOWUSDT", "SANDUSDT",
    "AXSUSDT", "MANAUSDT", "SNXUSDT", "KASUSDT", "CRVUSDT", "DYDXUSDT", "EOSUSDT", "XTZUSDT",
    "BEAMUSDT", "NEOUSDT", "JUPUSDT", "WIFUSDT", "NOTUSDT", "KSMUSDT", "CHZUSDT", "MINAUSDT",
    "ZECUSDT", "COMPUSDT", "XMRUSDT", "DASHUSDT", "IOTAUSDT", "1INCHUSDT", "GMXUSDT", "WOOUSDT",
    "ENSUSDT", "PENDLEUSDT", "BLURUSDT", "LRCUSDT", "ENJUSDT", "BATUSDT", "QTUMUSDT", "ZROUSDT",
    "PYTHUSDT", "STRKUSDT", "IMXUSDT", "ASTRUSDT", "ARKMUSDT", "ALTUSDT", "PORTALUSDT",
    "PIXELUSDT", "MANTAUSDT", "ONDOUSDT", "RONINUSDT", "MEMEUSDT", "ORCAUSDT", "RAYUSDT",
    "POPCATUSDT", "BRETTUSDT", "MOGUSDT", "NEIROUSDT"
]

TOP_10_HISTORICAL_SYMBOLS = TOP_100_HISTORICAL_SYMBOLS[:10]

@st.cache_data(ttl=3600)
def build_coin_directory():
    pairs_map = {}
    price_map = {}

    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        r = requests.get(url, headers=HEADERS, timeout=5.0)
        if r.status_code == 200:
            res = r.json()
            if not res.get("error") and "result" in res:
                kraken_pairs = res["result"]
                for sym in TOP_100_HISTORICAL_SYMBOLS:
                    base = sym.replace("USDT", "").replace("USD", "")
                    found = False
                    for p_key, p_info in kraken_pairs.items():
                        altname = p_info.get("altname", "")
                        wsname = p_info.get("wsname", "")
                        if base in altname or f"{base}/" in wsname:
                            pairs_map[sym] = p_key
                            found = True
                            break
                    if not found:
                        pairs_map[sym] = sym
    except Exception:
        for sym in TOP_100_HISTORICAL_SYMBOLS:
            pairs_map[sym] = sym

    try:
        ticker_url = "https://api.kraken.com/0/public/Ticker"
        tr = requests.get(ticker_url, headers=HEADERS, timeout=4.0)
        if tr.status_code == 200 and "result" in tr.json():
            tdata = tr.json()["result"]
            for sym in TOP_100_HISTORICAL_SYMBOLS:
                p_id = pairs_map.get(sym, sym)
                if p_id in tdata:
                    price_map[sym] = float(tdata[p_id]["c"][0])
                elif sym in tdata:
                    price_map[sym] = float(tdata[sym]["c"][0])
                else:
                    price_map[sym] = 0.0
    except Exception:
        for sym in TOP_100_HISTORICAL_SYMBOLS:
            price_map[sym] = 0.0

    return pairs_map, price_map

PAIR_LOOKUP_MAP, REFERENCE_PRICE_MAP = build_coin_directory()
ALL_TRADING_SYMBOLS = TOP_100_HISTORICAL_SYMBOLS

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
if 'last_valid_ta' not in st.session_state: st.session_state.last_valid_ta = {}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Bot Settings")
sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_usdt = st.sidebar.number_input(
        "Trade Size ($ USDT)", min_value=5.0, max_value=500.0, step=5.0,
        value=float(saved_data.get("trade_amount_usdt", 10.0)),
        key="trade_amount_usdt_input"
    )
    st.session_state.trade_amount_usdt = trade_amount_usdt

with sb_col2:
    sort_order = st.sidebar.selectbox("Sort Overview By", ["Price (High to Low)", "Price (Low to High)", "Alphabetical"], key="sort_order_select")

st.sidebar.subheader("🛡️ Short Protection Controls")
allow_shorts = st.sidebar.checkbox("Enable Short Positions", value=saved_data.get("allow_shorts", True), key="allow_shorts_check")
st.session_state.allow_shorts = allow_shorts

vol_multiplier = st.sidebar.slider(
    "Min Short Vol Spike (x Avg Vol)", min_value=1.0, max_value=3.0, step=0.1,
    value=float(saved_data.get("vol_multiplier", 1.3)),
    key="vol_multiplier_slider"
)
st.session_state.vol_multiplier = vol_multiplier

st.sidebar.subheader("🎯 Risk Controls")
take_profit_pct = st.sidebar.slider("Take Profit (%)", 0.5, 10.0, float(saved_data.get("take_profit_pct", 1.5)), 0.5, key="tp_slider")
st.session_state.take_profit_pct = take_profit_pct

stop_loss_pct = st.sidebar.slider("Tight Stop Loss (%)", 0.5, 10.0, float(saved_data.get("stop_loss_pct", 2.5)), 0.5, key="sl_slider")
st.session_state.stop_loss_pct = stop_loss_pct

st.sidebar.subheader("📊 Indicator Thresholds")
rsi_oversold = st.sidebar.slider("RSI Oversold (Buy)", 15, 45, int(saved_data.get("rsi_oversold", 30)), 1, key="rsi_os_slider")
st.session_state.rsi_oversold = rsi_oversold

rsi_overbought = st.sidebar.slider("RSI Overbought (Short)", 55, 90, int(saved_data.get("rsi_overbought", 72)), 1, key="rsi_ob_slider")
st.session_state.rsi_overbought = rsi_overbought

st.sidebar.subheader("🔍 Coin Directory & Selection")
coin_sort_choice = st.sidebar.selectbox(
    "Sort Coin Selection List By",
    ["High/Low Price", "Low/High Price", "Alphabetical"],
    key="coin_sort_choice_select"
)

if coin_sort_choice == "High/Low Price":
    sorted_coins = sorted(ALL_TRADING_SYMBOLS, key=lambda s: REFERENCE_PRICE_MAP.get(s, 0.0), reverse=True)
elif coin_sort_choice == "Low/High Price":
    sorted_coins = sorted(ALL_TRADING_SYMBOLS, key=lambda s: REFERENCE_PRICE_MAP.get(s, 0.0), reverse=False)
else:
    sorted_coins = sorted(ALL_TRADING_SYMBOLS)

valid_defaults = [s for s in saved_data.get("selected_symbols", ALL_TRADING_SYMBOLS) if s in ALL_TRADING_SYMBOLS]
selected_symbols = st.sidebar.multiselect(
    f"Active Trading Coins ({len(ALL_TRADING_SYMBOLS)} Top Volume Coins)",
    options=sorted_coins,
    default=valid_defaults if valid_defaults else ALL_TRADING_SYMBOLS,
    key="selected_symbols_multi"
)
st.session_state.selected_symbols = selected_symbols

if st.sidebar.button("🔄 Reset Portfolio ($1,000 USDT)", key="reset_btn"):
    if os.path.exists(PORTFOLIO_FILE):
        os.remove(PORTFOLIO_FILE)
    st.session_state.balance = 1000.0
    st.session_state.holdings = {}
    st.session_state.short_holdings = {}
    st.session_state.entry_prices = {}
    st.session_state.trade_history = []
    st.session_state.selected_symbols = ALL_TRADING_SYMBOLS
    st.session_state.last_valid_ta = {}
    st.rerun()

save_portfolio()

for sym in st.session_state.selected_symbols:
    if sym not in st.session_state.holdings: st.session_state.holdings[sym] = 0.0
    if sym not in st.session_state.short_holdings: st.session_state.short_holdings[sym] = 0.0
    if sym not in st.session_state.entry_prices: st.session_state.entry_prices[sym] = 0.0

col_start, col_stop = st.columns(2)
with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True, key="start_btn"):
        st.session_state.bot_running = True
        st.toast("Bot active!", icon="🟢")

with col_stop:
    if st.button("⏸️ PAUSE BOT", use_container_width=True, key="stop_btn"):
        st.session_state.bot_running = False
        st.toast("Bot paused.", icon="🔴")

if st.session_state.bot_running:
    st.success(f"🟢 STATUS: BOT ACTIVE (Trading All Selected Market Coins — Total Active: {len(st.session_state.selected_symbols)})")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- REAL-TIME MULTI-TIMEFRAME DATA ENGINE (LOW-LATENCY CACHE) ---
@st.cache_data(ttl=5, show_spinner=False)
def fetch_ta_data_cached(symbol):
    pair_id = PAIR_LOOKUP_MAP.get(symbol, symbol)
    
    try:
        # 1. Fetch 5-Minute Execution Candles
        url_5m = f"https://api.kraken.com/0/public/OHLC?pair={pair_id}&interval=5"
        r_5m = requests.get(url_5m, headers=HEADERS, timeout=5.0)

        # 2. Fetch 1-Hour Trend Filter Candles (Multi-Timeframe Check)
        url_1h = f"https://api.kraken.com/0/public/OHLC?pair={pair_id}&interval=60"
        r_1h = requests.get(url_1h, headers=HEADERS, timeout=5.0)

        if r_5m.status_code == 200 and r_1h.status_code == 200:
            res_5m = r_5m.json()
            res_1h = r_1h.json()

            if not res_5m.get("error") and not res_1h.get("error"):
                p_key_5m = list(res_5m["result"].keys())[0]
                p_key_1h = list(res_1h["result"].keys())[0]

                candles_5m = res_5m["result"][p_key_5m]
                candles_1h = res_1h["result"][p_key_1h]

                # Relaxed length check so newly listed assets don't fail
                if len(candles_5m) >= 20 and len(candles_1h) >= 20:
                    df5 = pd.DataFrame(candles_5m, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
                    df5['close'] = df5['close'].astype(float)
                    df5['volume'] = df5['volume'].astype(float)

                    df1h = pd.DataFrame(candles_1h, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
                    df1h['close'] = df1h['close'].astype(float)
                    
                    # Compute EMA50
                    span_val = min(50, len(df1h))
                    ema50_1h = df1h['close'].ewm(span=span_val, adjust=False).mean().iloc[-1]

                    # Indicators on 5m chart
                    delta = df5['close'].diff()
                    gain = delta.clip(lower=0)
                    loss = -delta.clip(upper=0)
                    avg_gain = gain.rolling(window=14).mean()
                    avg_loss = loss.rolling(window=14).mean()
                    rs = avg_gain / (avg_loss + 1e-10)
                    df5['rsi'] = 100 - (100 / (1 + rs))

                    ema12 = df5['close'].ewm(span=12, adjust=False).mean()
                    ema26 = df5['close'].ewm(span=26, adjust=False).mean()
                    df5['macd'] = ema12 - ema26
                    df5['macd_signal'] = df5['macd'].ewm(span=9, adjust=False).mean()

                    sma20 = df5['close'].rolling(window=20).mean()
                    std20 = df5['close'].rolling(window=20).std()
                    df5['bb_upper'] = sma20 + (2 * std20)
                    df5['bb_lower'] = sma20 - (2 * std20)
                    df5['vol_ma20'] = df5['volume'].rolling(window=20).mean()

                    latest = df5.iloc[-1]
                    prev = df5.iloc[-2]

                    current_price = float(latest['close'])
                    macro_1h_trend = "BULLISH" if current_price >= ema50_1h else "BEARISH"

                    vol_spike = float(latest['volume']) >= (float(latest['vol_ma20']) * st.session_state.get('vol_multiplier', 1.3))

                    return {
                        "current_price": current_price,
                        "volume_24h": float(df5['volume'].sum()),
                        "rsi": float(latest['rsi']) if not pd.isna(latest['rsi']) else 50.0,
                        "prev_rsi": float(prev['rsi']) if not pd.isna(prev['rsi']) else 50.0,
                        "macd": float(latest['macd']) if not pd.isna(latest['macd']) else 0.0,
                        "macd_signal": float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) else 0.0,
                        "prev_macd": float(prev['macd']) if not pd.isna(prev['macd']) else 0.0,
                        "prev_macd_signal": float(prev['macd_signal']) if not pd.isna(prev['macd_signal']) else 0.0,
                        "bb_lower": float(latest['bb_lower']) if not pd.isna(latest['bb_lower']) else current_price,
                        "bb_upper": float(latest['bb_upper']) if not pd.isna(latest['bb_upper']) else current_price,
                        "volume_spike": vol_spike,
                        "macro_1h_trend": macro_1h_trend,
                        "ema50_1h": float(ema50_1h)
                    }
    except Exception:
        pass

    return None

# --- SIGNAL ENGINE WITH MULTI-TIMEFRAME FILTERING ---
def analyze_market_signal(symbol, data):
    if not data:
        return 0.0, "HOLD", "Data Unavailable"

    price = data['current_price']
    long_qty = st.session_state.holdings.get(symbol, 0.0)
    short_qty = st.session_state.short_holdings.get(symbol, 0.0)
    entry_price = st.session_state.entry_prices.get(symbol, 0.0)

    # Position Management (TP/SL)
    if long_qty > 0 and entry_price > 0:
        pnl_pct = ((price - entry_price) / entry_price) * 100.0
        if pnl_pct >= st.session_state.take_profit_pct: return price, "SELL", f"Long TP (+{pnl_pct:.2f}%)"
        if pnl_pct <= -st.session_state.stop_loss_pct: return price, "SELL", f"Long SL ({pnl_pct:.2f}%)"
        return price, "HOLD", f"Holding Long ({pnl_pct:+.2f}%)"

    if short_qty > 0 and entry_price > 0:
        pnl_pct = ((entry_price - price) / entry_price) * 100.0
        if pnl_pct >= st.session_state.take_profit_pct: return price, "COVER", f"Short TP (+{pnl_pct:.2f}%)"
        if pnl_pct <= -st.session_state.stop_loss_pct: return price, "COVER", f"Short SL ({pnl_pct:.2f}%)"
        return price, "HOLD", f"Holding Short ({pnl_pct:+.2f}%)"

    macd_bearish_cross = (data['prev_macd'] > data['prev_macd_signal']) and (data['macd'] < data['macd_signal'])
    rsi_turning_down = data['prev_rsi'] > st.session_state.rsi_overbought and data['rsi'] < data['prev_rsi']
    rsi_turning_up = data['prev_rsi'] < st.session_state.rsi_oversold and data['rsi'] > data['prev_rsi']

    # --- 1. MULTI-TIMEFRAME LONG CHECK (1H Trend must be Bullish) ---
    if data['macro_1h_trend'] == "BULLISH":
        if (data['rsi'] <= st.session_state.rsi_oversold or rsi_turning_up) and (data['macd'] > data['macd_signal'] or price <= data['bb_lower']):
            return price, "BUY", f"1H Trend-Aligned Buy Dip (RSI: {data['rsi']:.1f} | 1H EMA50: ${data['ema50_1h']:,.2f})"

    # --- 2. MULTI-TIMEFRAME SHORT CHECK (1H Trend must be Bearish) ---
    if st.session_state.allow_shorts and data['macro_1h_trend'] == "BEARISH":
        if (data['rsi'] >= st.session_state.rsi_overbought or rsi_turning_down):
            if macd_bearish_cross and data['volume_spike']:
                return price, "SHORT", f"1H Trend Short Reversal (RSI: {data['rsi']:.1f} | Vol Spike 🔥)"
            elif price >= data['bb_upper'] and data['volume_spike']:
                return price, "SHORT", f"1H Bearish Upper BB Rejection 🔥"

    vol_str = " 🔥" if data['volume_spike'] else ""
    return price, "HOLD", f"Neutral (RSI: {data['rsi']:.1f} | 1H Trend: {data['macro_1h_trend']}{vol_str})"

# --- MAIN RENDER ENGINE ---
def render_engine():
    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    
    # Precise live seconds timestamp for visible refresh tracking
    current_time_str = datetime.now().strftime("%H:%M:%S")
    st.caption(f"🔄 Last Scan: **{current_time_str}** | Total Active Coins Evaluated: **{len(st.session_state.selected_symbols)}**")

    if not st.session_state.selected_symbols:
        st.info("Select active trading coins in the sidebar.")
        return

    # Multithreaded concurrent API fetch
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        ta_data_list = list(executor.map(fetch_ta_data_cached, st.session_state.selected_symbols))

    top_10_summary = []
    executed_any_trade = False

    for symbol, ta_data in zip(st.session_state.selected_symbols, ta_data_list):
        if ta_data is not None:
            st.session_state.last_valid_ta[symbol] = ta_data
        else:
            ta_data = st.session_state.last_valid_ta.get(symbol, None)

        if ta_data is None:
            continue

        current_price, signal, reason = analyze_market_signal(symbol, ta_data)
        
        if current_price > 0:
            long_qty = st.session_state.holdings.get(symbol, 0.0)
            short_qty = st.session_state.short_holdings.get(symbol, 0.0)
            entry_price = st.session_state.entry_prices.get(symbol, 0.0)

            position_type = "NONE"
            pl_str = "0.00%"

            if long_qty > 0 and entry_price > 0:
                position_type = f"LONG ({long_qty:.4f})"
                pl_val = ((current_price - entry_price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"
            elif short_qty > 0 and entry_price > 0:
                position_type = f"SHORT ({short_qty:.4f})"
                pl_val = ((entry_price - current_price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"

            if symbol in TOP_10_HISTORICAL_SYMBOLS:
                top_10_summary.append({
                    "raw_price": current_price,
                    "Asset": symbol,
                    "Price": f"${current_price:,.4f}" if current_price < 1 else f"${current_price:,.2f}",
                    "Position": position_type,
                    "Entry Price": f"${entry_price:,.2f}" if entry_price > 0 else "-",
                    "Current P/L": pl_str,
                    "Signal": signal,
                    "Reason": reason
                })

            trade_amt = st.session_state.trade_amount_usdt
            if st.session_state.bot_running:
                if signal == "BUY" and st.session_state.balance >= trade_amt:
                    coins_bought = trade_amt / current_price
                    st.session_state.balance -= trade_amt
                    st.session_state.holdings[symbol] = coins_bought
                    st.session_state.entry_prices[symbol] = current_price
                    st.session_state.trade_history.append({
                        'Time': current_time_str,
                        'Asset': symbol,
                        'Type': 'BUY (LONG)',
                        'Price': f"${current_price:,.2f}",
                        'Value': f"${trade_amt:.2f}",
                        'Note': reason
                    })
                    executed_any_trade = True

                elif signal == "SELL" and long_qty > 0:
                    usdt_received = long_qty * current_price
                    net_pnl = usdt_received - trade_amt
                    st.session_state.balance += usdt_received
                    st.session_state.holdings[symbol] = 0.0
                    st.session_state.entry_prices[symbol] = 0.0
                    st.session_state.trade_history.append({
                        'Time': current_time_str,
                        'Asset': symbol,
                        'Type': 'SELL (CLOSE LONG)',
                        'Price': f"${current_price:,.2f}",
                        'Value': f"${usdt_received:.2f}",
                        'Note': f"{reason} | Net: ${net_pnl:+.2f}"
                    })
                    executed_any_trade = True

                elif signal == "SHORT" and st.session_state.balance >= trade_amt:
                    coins_shorted = trade_amt / current_price
                    st.session_state.balance -= trade_amt
                    st.session_state.short_holdings[symbol] = coins_shorted
                    st.session_state.entry_prices[symbol] = current_price
                    st.session_state.trade_history.append({
                        'Time': current_time_str,
                        'Asset': symbol,
                        'Type': 'SHORT (OPEN)',
                        'Price': f"${current_price:,.2f}",
                        'Value': f"${trade_amt:.2f}",
                        'Note': reason
                    })
                    executed_any_trade = True

                elif signal == "COVER" and short_qty > 0:
                    cost_to_buy_back = short_qty * current_price
                    net_pnl = trade_amt - cost_to_buy_back
                    st.session_state.balance += (trade_amt + net_pnl)
                    st.session_state.short_holdings[symbol] = 0.0
                    st.session_state.entry_prices[symbol] = 0.0
                    st.session_state.trade_history.append({
                        'Time': current_time_str,
                        'Asset': symbol,
                        'Type': 'COVER (CLOSE SHORT)',
                        'Price': f"${current_price:,.2f}",
                        'Value': f"${(trade_amt + net_pnl):.2f}",
                        'Note': f"{reason} | Net: ${net_pnl:+.2f}"
                    })
                    executed_any_trade = True

    if executed_any_trade:
        save_portfolio()

    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    if top_10_summary:
        if sort_order == "Price (High to Low)":
            top_10_summary.sort(key=lambda x: x['raw_price'], reverse=True)
        elif sort_order == "Price (Low to High)":
            top_10_summary.sort(key=lambda x: x['raw_price'], reverse=False)
        elif sort_order == "Alphabetical":
            top_10_summary.sort(key=lambda x: x['Asset'])

        display_df = pd.DataFrame(top_10_summary).drop(columns=['raw_price'])
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Fetching candle data for Top 10 coins...")

    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet across your active assets.")

render_engine()
