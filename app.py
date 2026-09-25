import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
import os
import concurrent.futures

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

st.title("🤖 24/7 Crypto AI Bot (Enhanced Short Guard Edition)")

PORTFOLIO_FILE = "portfolio.json"

@st.cache_data(ttl=1800)
def fetch_top_usdt_pairs():
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/24hr"
        res = requests.get(url, timeout=10).json()
        usdt_pairs = []
        excluded_keywords = ["UPUSDT", "DOWNUSDT", "BEARUSDT", "BULLUSDT", "NVDAB", "AAPLB", "TSLAB"]
        
        for ticker in res:
            symbol = ticker.get("symbol", "")
            if symbol.endswith("USDT") and not any(x in symbol for x in excluded_keywords):
                try:
                    quote_volume = float(ticker.get("quoteVolume", 0))
                    usdt_pairs.append((symbol, quote_volume))
                except ValueError:
                    continue
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = [item[0] for item in usdt_pairs[:50]]
        return top_pairs if top_pairs else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    except Exception:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

ALL_BINANCE_PAIRS = fetch_top_usdt_pairs()

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
        "selected_symbols": ALL_BINANCE_PAIRS[:15],
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
        "selected_symbols": st.session_state.get("selected_symbols", ALL_BINANCE_PAIRS[:15]),
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
    sort_order = st.sidebar.selectbox("Sort Table By", ["Price (High to Low)", "Price (Low to High)", "Alphabetical"], key="sort_order_select")

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

# Limit default selection to 15 pairs max
valid_defaults = [s for s in saved_data.get("selected_symbols", ALL_BINANCE_PAIRS[:15]) if s in ALL_BINANCE_PAIRS]
selected_symbols = st.sidebar.multiselect(
    f"Select Trading Pairs ({len(ALL_BINANCE_PAIRS)} Available)",
    options=ALL_BINANCE_PAIRS,
    default=valid_defaults[:15],
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
    st.session_state.selected_symbols = ALL_BINANCE_PAIRS[:15]
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
    st.success("🟢 STATUS: BOT ACTIVE (Enhanced Short Protection & Volume Filters)")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- TA DATA FETCHING ---
@st.cache_data(ttl=12, show_spinner=False)
def fetch_ta_data_cached(symbol):
    try:
        formatted_symbol = symbol.replace("/", "").replace("-", "").upper()

        url_5m = f"https://data-api.binance.vision/api/v3/klines?symbol={formatted_symbol}&interval=5m&limit=50"
        res_5m = requests.get(url_5m, timeout=3.0).json()
        
        if isinstance(res_5m, dict) or not isinstance(res_5m, list): return None

        df_5m = pd.DataFrame(res_5m, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qav', 'nt', 'tba', 'tbq', 'ig'])
        df_5m['close'] = df_5m['close'].astype(float)
        df_5m['volume'] = df_5m['volume'].astype(float)
        if len(df_5m) < 30: return None

        delta = df_5m['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df_5m['rsi'] = 100 - (100 / (1 + rs))

        ema12 = df_5m['close'].ewm(span=12, adjust=False).mean()
        ema26 = df_5m['close'].ewm(span=26, adjust=False).mean()
        df_5m['macd'] = ema12 - ema26
        df_5m['macd_signal'] = df_5m['macd'].ewm(span=9, adjust=False).mean()

        sma20 = df_5m['close'].rolling(window=20).mean()
        std20 = df_5m['close'].rolling(window=20).std()
        df_5m['bb_upper'] = sma20 + (2 * std20)
        df_5m['bb_lower'] = sma20 - (2 * std20)
        df_5m['vol_ma20'] = df_5m['volume'].rolling(window=20).mean()

        latest_5m = df_5m.iloc[-1]
        prev_5m = df_5m.iloc[-2]

        url_1h = f"https://data-api.binance.vision/api/v3/klines?symbol={formatted_symbol}&interval=1h&limit=50"
        res_1h = requests.get(url_1h, timeout=3.0).json()
        
        macro_trend = "NEUTRAL"
        macro_ema20 = 0.0
        if isinstance(res_1h, list) and len(res_1h) >= 30:
            df_1h = pd.DataFrame(res_1h, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qav', 'nt', 'tba', 'tbq', 'ig'])
            df_1h['close'] = df_1h['close'].astype(float)
            df_1h['ema20'] = df_1h['close'].ewm(span=20, adjust=False).mean()
            df_1h['ema50'] = df_1h['close'].ewm(span=50, adjust=False).mean()
            
            latest_1h = df_1h.iloc[-1]
            macro_ema20 = float(latest_1h['ema20'])
            if float(latest_1h['close']) > float(latest_1h['ema50']):
                macro_trend = "BULLISH"
            else:
                macro_trend = "BEARISH"

        return {
            "current_price": float(latest_5m['close']),
            "rsi": float(latest_5m['rsi']),
            "prev_rsi": float(prev_5m['rsi']),
            "macd": float(latest_5m['macd']),
            "macd_signal": float(latest_5m['macd_signal']),
            "prev_macd": float(prev_5m['macd']),
            "prev_macd_signal": float(prev_5m['macd_signal']),
            "bb_lower": float(latest_5m['bb_lower']),
            "bb_upper": float(latest_5m['bb_upper']),
            "volume_spike": float(latest_5m['volume']) >= (float(latest_5m['vol_ma20']) * st.session_state.vol_multiplier),
            "macro_trend": macro_trend,
            "macro_ema20": macro_ema20
        }

    except Exception:
        return None

# --- SIGNAL ENGINE ---
def analyze_market_signal(symbol, data):
    if not data:
        return 0.0, "HOLD", "Data Unavailable"

    price = data['current_price']
    long_qty = st.session_state.holdings.get(symbol, 0.0)
    short_qty = st.session_state.short_holdings.get(symbol, 0.0)
    entry_price = st.session_state.entry_prices.get(symbol, 0.0)

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
    macd_bullish_cross = (data['prev_macd'] < data['prev_macd_signal']) and (data['macd'] > data['macd_signal'])
    rsi_turning_down = data['prev_rsi'] > st.session_state.rsi_overbought and data['rsi'] < data['prev_rsi']
    rsi_turning_up = data['prev_rsi'] < st.session_state.rsi_oversold and data['rsi'] > data['prev_rsi']

    if st.session_state.allow_shorts:
        if data['macro_trend'] != "BULLISH":
            if (data['rsi'] >= st.session_state.rsi_overbought or rsi_turning_down):
                if macd_bearish_cross and data['volume_spike']:
                    return price, "SHORT", f"High-Volume Bearish Reversal (RSI: {data['rsi']:.1f})"
                elif price >= data['bb_upper'] and data['volume_spike']:
                    return price, "SHORT", f"Upper BB Breakout Rejection + Vol Spike"

    if data['macro_trend'] == "BULLISH":
        if (data['rsi'] <= st.session_state.rsi_oversold or rsi_turning_up) and (data['macd'] > data['macd_signal'] or price <= data['bb_lower']):
            return price, "BUY", f"Trend-Aligned Buy Dip (1h Bullish | RSI: {data['rsi']:.1f})"
    else:
        if rsi_turning_up and macd_bullish_cross:
            return price, "BUY", f"Bear-Market Reversal Buy (RSI: {data['rsi']:.1f} + MACD Cross)"

    return price, "HOLD", f"Neutral (RSI: {data['rsi']:.1f} | 1h Trend: {data['macro_trend']})"

# --- RENDER ENGINE ---
@st.fragment(run_every="10s")
def render_engine():
    if not st.session_state.selected_symbols:
        st.info("Select trading pairs in the sidebar.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        ta_data_list = list(executor.map(fetch_ta_data_cached, st.session_state.selected_symbols))

    market_summary = []
    executed_any_trade = False

    for symbol, ta_data in zip(st.session_state.selected_symbols, ta_data_list):
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

            market_summary.append({
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
                        'Time': time.strftime('%H:%M:%S'),
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
                        'Time': time.strftime('%H:%M:%S'),
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
                        'Time': time.strftime('%H:%M:%S'),
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
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'COVER (CLOSE SHORT)',
                        'Price': f"${current_price:,.2f}",
                        'Value': f"${(trade_amt + net_pnl):.2f}",
                        'Note': f"{reason} | Net: ${net_pnl:+.2f}"
                    })
                    executed_any_trade = True

    if executed_any_trade:
        save_portfolio()

    if sort_order == "Price (High to Low)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=True)
    elif sort_order == "Price (Low to High)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=False)
    elif sort_order == "Alphabetical":
        market_summary.sort(key=lambda x: x['Asset'])

    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    st.caption(f"🔄 Last Scan: {time.strftime('%H:%M:%S')} | Active Pairs: **{len(st.session_state.selected_symbols)}**")
    
    st.subheader("📊 Live Technical Analysis & Signal Overview")
    if market_summary:
        display_df = pd.DataFrame(market_summary).drop(columns=['raw_price'])
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Fetching candle data from Binance...")

    st.subheader("📋 Multi-Asset Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet.")

render_engine()
