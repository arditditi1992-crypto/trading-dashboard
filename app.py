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

# 10 SECOND REFRESH - Safe to use because live prices are bulk-fetched
st_autorefresh(interval=10000, limit=None)

st.title("🤖 24/7 Crypto AI Bot (Hybrid Live-Tick Engine)")

PORTFOLIO_FILE = "portfolio.json"

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
    st.success(f"🟢 STATUS: BOT ACTIVE (Trading {len(st.session_state.selected_symbols)} Coins via Hybrid Live-Tick Engine)")
else:
    st.warning("🔴 STATUS: BOT PAUSED")

# --- HYBRID DATA ENGINE ---

# 1. Fetches all live prices globally in ONE request every 10 seconds
@st.cache_data(ttl=10, show_spinner=False)
def fetch_all_live_prices():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5.0)
        if r.status_code == 200:
            return {item['symbol']: float(item['price']) for item in r.json()}
    except Exception:
        pass
    return {}

# 2. Caches the heavy historical data for 5 minutes (prevents rate limits)
@st.cache_data(ttl=300, show_spinner=False)
def fetch_historical_candles(symbol):
    try:
        url_5m = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
        r_5m = requests.get(url_5m, timeout=5.0)

        url_1h = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
        r_1h = requests.get(url_1h, timeout=5.0)

        if r_5m.status_code == 200 and r_1h.status_code == 200:
            candles_5m = r_5m.json()
            candles_1h = r_1h.json()

            if len(candles_5m) >= 20 and len(candles_1h) >= 20:
                columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_vol', 'trades', 'tb', 'tq', 'ignore']
                
                df5 = pd.DataFrame(candles_5m, columns=columns)
                df5['close'] = df5['close'].astype(float)
                df5['volume'] = df5['volume'].astype(float)

                df1h = pd.DataFrame(candles_1h, columns=columns)
                df1h['close'] = df1h['close'].astype(float)
                
                return {"df5": df5, "df1h": df1h}
    except Exception:
        pass
    return None

# 3. Stitch live price to the cached history and calculate mathematically accurate indicators
def calculate_live_indicators(history, live_price, vol_multiplier):
    df5 = history["df5"].copy()
    df1h = history["df1h"].copy()

    # Update the last candle close price with the real-time live ticker
    df5.at[df5.index[-1], 'close'] = live_price
    df1h.at[df1h.index[-1], 'close'] = live_price

    span_val = min(50, len(df1h))
    ema50_1h = df1h['close'].ewm(span=span_val, adjust=False).mean().iloc[-1]

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

    macro_1h_trend = "BULLISH" if live_price >= ema50_1h else "BEARISH"
    vol_spike = float(latest['volume']) >= (float(latest['vol_ma20']) * vol_multiplier)

    return {
        "current_price": live_price,
        "rsi": float(latest['rsi']) if not pd.isna(latest['rsi']) else 50.0,
        "prev_rsi": float(prev['rsi']) if not pd.isna(prev['rsi']) else 50.0,
        "macd": float(latest['macd']) if not pd.isna(latest['macd']) else 0.0,
        "macd_signal": float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) else 0.0,
        "prev_macd": float(prev['macd']) if not pd.isna(prev['macd']) else 0.0,
        "prev_macd_signal": float(prev['macd_signal']) if not pd.isna(prev['macd_signal']) else 0.0,
        "bb_lower": float(latest['bb_lower']) if not pd.isna(latest['bb_lower']) else live_price,
        "bb_upper": float(latest['bb_upper']) if not pd.isna(latest['bb_upper']) else live_price,
        "volume_spike": vol_spike,
        "macro_1h_trend": macro_1h_trend
    }

def analyze_market_signal(symbol, data):
    price = data['current_price']
    long_qty = st.session_state.holdings.get(symbol, 0.0)
    short_qty = st.session_state.short_holdings.get(symbol, 0.0)
    entry_price = st.session_state.entry_prices.get(symbol, 0.0)

    # 100% Real-Time SL/TP Evaluation based on Live Price
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

    if data['macro_1h_trend'] == "BULLISH":
        if (data['rsi'] <= st.session_state.rsi_oversold or rsi_turning_up) and (data['macd'] > data['macd_signal'] or price <= data['bb_lower']):
            return price, "BUY", f"1H Trend-Aligned Buy Dip (RSI: {data['rsi']:.1f})"

    if st.session_state.allow_shorts and data['macro_1h_trend'] == "BEARISH":
        if (data['rsi'] >= st.session_state.rsi_overbought or rsi_turning_down):
            if macd_bearish_cross and data['volume_spike']:
                return price, "SHORT", f"1H Trend Short Reversal (RSI: {data['rsi']:.1f} | Vol Spike 🔥)"
            elif price >= data['bb_upper'] and data['volume_spike']:
                return price, "SHORT", f"1H Bearish Upper BB Rejection 🔥"

    vol_str = " 🔥" if data['volume_spike'] else ""
    return price, "HOLD", f"Neutral (RSI: {data['rsi']:.1f} | 1H Trend: {data['macro_1h_trend']}{vol_str})"

def render_engine():
    st.metric("Total Cash Balance", f"${st.session_state.balance:,.2f} USDT")
    current_time_str = datetime.now().strftime("%H:%M:%S")

    if not st.session_state.selected_symbols:
        st.info("Select active trading coins in the sidebar.")
        return

    # FETCH 1: Instantly get ALL live prices across the market
    live_prices = fetch_all_live_prices()

    # FETCH 2: Maintain cached historical candle logic silently in background
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        cached_histories = list(executor.map(fetch_historical_candles, st.session_state.selected_symbols))

    top_10_summary = []
    active_positions_summary = []
    executed_any_trade = False

    for symbol, history in zip(st.session_state.selected_symbols, cached_histories):
        live_price = live_prices.get(symbol, 0.0)
        
        # Skip only if the live price endpoint failed completely
        if live_price == 0.0:
            continue

        # If historical candles are ready, calculate signals; otherwise fall back safely
        if history is not None:
            ta_data = calculate_live_indicators(history, live_price, st.session_state.vol_multiplier)
            current_price, signal, reason = analyze_market_signal(symbol, ta_data)
        else:
            current_price = live_price
            signal = "HOLD"
            reason = "⏳ Loading historical indicator data..."

        long_qty = st.session_state.holdings.get(symbol, 0.0)
        short_qty = st.session_state.short_holdings.get(symbol, 0.0)
        entry_price = st.session_state.entry_prices.get(symbol, 0.0)

        position_type = "NONE"
        pl_str = "0.00%"
        raw_pl = 0.0

        if long_qty > 0 and entry_price > 0:
            position_type = "LONG"
            raw_pl = ((current_price - entry_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"
        elif short_qty > 0 and entry_price > 0:
            position_type = "SHORT"
            raw_pl = ((entry_price - current_price) / entry_price) * 100
            pl_str = f"{raw_pl:+.2f}%"

        if long_qty > 0 or short_qty > 0:
            active_positions_summary.append({
                "Asset": symbol,
                "Type": position_type,
                "Live Price": f"${current_price:,.4f}" if current_price < 1 else f"${current_price:,.2f}",
                "Entry Price": f"${entry_price:,.4f}" if entry_price < 1 else f"${entry_price:,.2f}",
                "Current P/L": pl_str,
                "Signal": signal,
                "raw_pl": raw_pl
            })

        if symbol in TOP_10_HISTORICAL_SYMBOLS:
            top_10_summary.append({
                "Asset": symbol,
                "Price": f"${current_price:,.4f}" if current_price < 1 else f"${current_price:,.2f}",
                "Position": position_type if position_type != "NONE" else "-",
                "Current P/L": pl_str if position_type != "NONE" else "-",
                "Signal": signal,
                "Reason": reason
            })

        trade_amt = st.session_state.trade_amount_usdt
        if st.session_state.bot_running and history is not None:
            if signal == "BUY" and st.session_state.balance >= trade_amt:
                coins_bought = trade_amt / current_price
                st.session_state.balance -= trade_amt
                st.session_state.holdings[symbol] = coins_bought
                st.session_state.entry_prices[symbol] = current_price
                st.session_state.trade_history.append({'Time': current_time_str, 'Asset': symbol, 'Type': 'BUY (LONG)', 'Price': f"${current_price:,.2f}", 'Value': f"${trade_amt:.2f}", 'Note': reason})
                executed_any_trade = True

            elif signal == "SELL" and long_qty > 0:
                usdt_received = long_qty * current_price
                net_pnl = usdt_received - trade_amt
                st.session_state.balance += usdt_received
                st.session_state.holdings[symbol] = 0.0
                st.session_state.entry_prices[symbol] = 0.0
                st.session_state.trade_history.append({'Time': current_time_str, 'Asset': symbol, 'Type': 'SELL (CLOSE LONG)', 'Price': f"${current_price:,.2f}", 'Value': f"${usdt_received:.2f}", 'Note': f"{reason} | Net: ${net_pnl:+.2f}"})
                executed_any_trade = True

            elif signal == "SHORT" and st.session_state.balance >= trade_amt:
                coins_shorted = trade_amt / current_price
                st.session_state.balance -= trade_amt
                st.session_state.short_holdings[symbol] = coins_shorted
                st.session_state.entry_prices[symbol] = current_price
                st.session_state.trade_history.append({'Time': current_time_str, 'Asset': symbol, 'Type': 'SHORT (OPEN)', 'Price': f"${current_price:,.2f}", 'Value': f"${trade_amt:.2f}", 'Note': reason})
                executed_any_trade = True

            elif signal == "COVER" and short_qty > 0:
                cost_to_buy_back = short_qty * current_price
                net_pnl = trade_amt - cost_to_buy_back
                st.session_state.balance += (trade_amt + net_pnl)
                st.session_state.short_holdings[symbol] = 0.0
                st.session_state.entry_prices[symbol] = 0.0
                st.session_state.trade_history.append({'Time': current_time_str, 'Asset': symbol, 'Type': 'COVER (CLOSE SHORT)', 'Price': f"${current_price:,.2f}", 'Value': f"${(trade_amt + net_pnl):.2f}", 'Note': f"{reason} | Net: ${net_pnl:+.2f}"})
                executed_any_trade = True

    if executed_any_trade:
        save_portfolio()

    st.subheader("💼 Active Open Positions")
    if active_positions_summary:
        if sort_order == "Current P/L":
            active_positions_summary.sort(key=lambda x: x['raw_pl'], reverse=True)
        else:
            active_positions_summary.sort(key=lambda x: x['Asset'])
            
        display_positions = pd.DataFrame(active_positions_summary).drop(columns=['raw_pl'])
        st.dataframe(display_positions, use_container_width=True)
    else:
        st.info("You currently have no open trades.")

    st.write("---")

    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    if top_10_summary:
        st.dataframe(pd.DataFrame(top_10_summary), use_container_width=True)
    else:
        st.info("⏳ Initializing top 10 market data...")

    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet across your active assets.")

render_engine()
