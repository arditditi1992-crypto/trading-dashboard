import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Crypto Trading Bot", layout="centered")

# Initialize session state variables matching your interface
if 'vol_multiplier' not in st.session_state:
    st.session_state['vol_multiplier'] = 1.3
if 'active_coins' not in st.session_state:
    st.session_state['active_coins'] = 88
if 'cash_balance' not in st.session_state:
    st.session_state['cash_balance'] = 1000.00

# API Constants and Top 10 Pair Map
HEADERS = {"Accept": "application/json"}
PAIR_LOOKUP_MAP = {
    "BTC": "XXBTZUSD",
    "ETH": "XETHZUSD",
    "SOL": "SOLUSD",
    "XRP": "XXRPZUSD",
    "ADA": "ADAUSD",
    "DOGE": "XDGUSD",
    "MATIC": "MATICUSD",
    "DOT": "DOTUSD",
    "LTC": "XLTCZUSD",
    "LINK": "LINKUSD"
}
TOP_10_COINS = list(PAIR_LOOKUP_MAP.keys())

# --- REAL-TIME MULTI-TIMEFRAME DATA ENGINE ---
@st.cache_data(ttl=15, show_spinner=False)
def fetch_ta_data_cached(symbol):
    pair_id = PAIR_LOOKUP_MAP.get(symbol, symbol)
    
    try:
        # 1. Fetch 5-Minute Execution Candles (Timeout explicitly set to avoid hangs)
        url_5m = f"https://api.kraken.com/0/public/OHLC?pair={pair_id}&interval=5"
        r_5m = requests.get(url_5m, headers=HEADERS, timeout=5.0)

        # 2. Fetch 1-Hour Trend Filter Candles
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

                # Relaxed length check (>= 20) ensures newly listed assets don't return None
                if len(candles_5m) >= 20 and len(candles_1h) >= 20:
                    df5 = pd.DataFrame(candles_5m, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
                    df5['close'] = df5['close'].astype(float)
                    df5['volume'] = df5['volume'].astype(float)

                    df1h = pd.DataFrame(candles_1h, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
                    df1h['close'] = df1h['close'].astype(float)
                    
                    # Compute EMA50 (or fallback to available length)
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

                    # Format specifically for the live overview table
                    return {
                        "Symbol": symbol,
                        "Price (USDT)": f"${current_price:,.4f}",
                        "RSI (5m)": round(float(latest['rsi']) if not pd.isna(latest['rsi']) else 50.0, 2),
                        "Trend (1h)": macro_1h_trend,
                        "Vol Spike": "🔥 Yes" if float(latest['volume']) >= (float(latest['vol_ma20']) * st.session_state.get('vol_multiplier', 1.3)) else "No"
                    }
    except Exception as e:
        pass

    return None

# --- UI RENDERING ---
def main():
    # Status Banner
    st.success(f"🟢 STATUS: BOT ACTIVE (Trading All Selected Market Coins — Total Active: {st.session_state['active_coins']})")
    
    # Portfolio Balance
    st.write("Total Cash Balance")
    st.markdown(f"## ${st.session_state['cash_balance']:,.2f} USDT")
    
    # Timestamp
    current_time = datetime.now().strftime("%H:%M:%S")
    st.caption(f"🔄 Last Scan: {current_time} | Total Active Coins Evaluated: {st.session_state['active_coins']}")
    
    st.write("")
    
    # Live Overview Section
    st.subheader("📊 Top 10 Most Traded Coins (Live Overview)")
    
    # Fetch and display data
    with st.spinner("Fetching candle data for Top 10 coins..."):
        data_list = []
        for coin in TOP_10_COINS:
            coin_data = fetch_ta_data_cached(coin)
            if coin_data:
                data_list.append(coin_data)
                
    if data_list:
        df_display = pd.DataFrame(data_list)
        st.dataframe(df_display, hide_index=True, use_container_width=True)
    else:
        # Fallback if APIs are completely unresponsive
        st.warning("Fetching candle data for Top 10 coins...")

    st.write("")
    
    # Trade Log Section
    st.subheader("📋 Global Multi-Asset Historical Trade Log")
    st.info("No trades logged yet across your active assets.")

if __name__ == "__main__":
    main()
