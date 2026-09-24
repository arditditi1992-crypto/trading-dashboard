import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Crypto Paper Trading Bot",
    page_icon="📈",
    layout="wide"
)

st.title("🤖 Crypto Paper Trading Bot")

# --- SESSION STATE INITIALIZATION ---
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Bot Settings")

# Updated currency pairs to Binance format (BTCEUR, ETHEUR, etc.)
selected_symbols = st.sidebar.multiselect(
    "Active Currency Pairs",
    options=["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "DOGEEUR"],
    default=["BTCEUR", "ETHEUR", "SOLEUR"]
)

st.sidebar.subheader("Trading Parameters")
tp_pct = st.sidebar.slider("Take Profit (%)", 0.5, 10.0, 2.0, 0.1) / 100.0
sl_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 10.0, 1.0, 0.1) / 100.0

# --- BOT START / STOP CONTROLS ---
col_start, col_stop = st.columns(2)

with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True):
        st.session_state.bot_running = True
        st.toast("Bot active: Automated trading enabled.")

with col_stop:
    if st.button("⏸️ PAUSE BOT", use_container_width=True):
        st.session_state.bot_running = False
        st.toast("Bot paused: Trading disabled.")

if st.session_state.bot_running:
    st.success("🟢 STATUS: BOT IS ACTIVE AND RUNNING")
else:
    st.warning("🔴 STATUS: BOT IS PAUSED")

# --- FETCH REAL BINANCE OHLC CANDLES & COMPUTE INDICATORS ---
def fetch_ta_data(symbol, interval="5m"):
    """
    Fetches live 5-minute candles directly from Binance's public API
    and calculates RSI, MACD, Moving Averages, and Bollinger Bands.
    """
    try:
        # Standardize pair ticker format
        formatted_symbol = symbol.replace("/", "").replace("-", "").upper()

        url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval={interval}&limit=100"
        res = requests.get(url, timeout=3).json()
        
        if isinstance(res, dict) and "code" in res:
            return None

        # Load candle array into pandas DataFrame
        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)

        if len(df) < 30:
            return None

        # --- TECHNICAL INDICATOR CALCULATIONS ---
        
        # 1. RSI (14 Period)
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))

        # 2. MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # 3. Moving Averages (EMA 50 & 200)
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

        # 4. Bollinger Bands (20 Period)
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = sma20 + (2 * std20)
        df['bb_lower'] = sma20 - (2 * std20)

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "current_price": float(latest['close']),
            "rsi": float(latest['rsi']),
            "macd": float(latest['macd']),
            "macd_signal": float(latest['macd_signal']),
            "prev_macd": float(prev['macd']),
            "prev_macd_signal": float(prev['macd_signal']),
            "ema50": float(latest['ema50']),
            "ema200": float(latest['ema200']),
            "bb_lower": float(latest['bb_lower']),
            "bb_upper": float(latest['bb_upper'])
        }

    except Exception:
        return None

# --- MULTI-INDICATOR SIGNAL ENGINE ---
def analyze_market_signal(symbol):
    data = fetch_ta_data(symbol)
    if not data:
        return 0.0, "HOLD", "Data Unavailable"

    price = data["current_price"]
    score = 0.0
    reasons = []

    # Factor 1: RSI Overbought/Oversold
    if data["rsi"] < 30:
        score += 1.0
        reasons.append(f"RSI Oversold ({data['rsi']:.1f})")
    elif data["rsi"] > 70:
        score -= 1.0
        reasons.append(f"RSI Overbought ({data['rsi']:.1f})")

    # Factor 2: MACD Bullish/Bearish Crossover
    if data["prev_macd"] <= data["prev_macd_signal"] and data["macd"] > data["macd_signal"]:
        score += 1.0
        reasons.append("MACD Bullish Crossover")
    elif data["prev_macd"] >= data["prev_macd_signal"] and data["macd"] < data["macd_signal"]:
        score -= 1.0
        reasons.append("MACD Bearish Crossover")

    # Factor 3: Price vs Moving Average Trend
    if price > data["ema50"] and data["ema50"] > data["ema200"]:
        score += 1.0
        reasons.append("Uptrend (Price > EMA50 > EMA200)")
    elif price < data["ema50"] and data["ema50"] < data["ema200"]:
        score -= 1.0
        reasons.append("Downtrend (Price < EMA50 < EMA200)")

    # Factor 4: Bollinger Band Bounce
    if price <= data["bb_lower"]:
        score += 1.0
        reasons.append("Price touching Lower Bollinger Band")
    elif price >= data["bb_upper"]:
        score -= 1.0
        reasons.append("Price touching Upper Bollinger Band")

    # Determine Action
    if score >= 2.0:
        action = "BUY"
    elif score <= -2.0:
        action = "SELL"
    else:
        action = "HOLD"

    reason_str = " | ".join(reasons) if reasons else "Neutral Indicators"
    return score, action, reason_str

# --- DISPLAY LIVE MARKET SCANNER ---
st.subheader("📊 Live Market Scanner")

scanner_data = []
for symbol in selected_symbols:
    score, action, reason = analyze_market_signal(symbol)
    ta_data = fetch_ta_data(symbol)
    price = f"€{ta_data['current_price']:,.2f}" if ta_data else "N/A"
    
    scanner_data.append({
        "Symbol": symbol,
        "Current Price": price,
        "Signal": action,
        "Score": score,
        "Indicator Summary": reason
    })

st.table(pd.DataFrame(scanner_data))
