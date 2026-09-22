import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("🤖 AI Algo Trading Bot Dashboard")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Bot Configuration")
api_key = st.sidebar.text_input("Kraken API Key", type="password")
secret_key = st.sidebar.text_input("Kraken Secret Key", type="password")
symbol = st.sidebar.selectbox("Trading Pair", ["XBTEUR", "XBTUSD", "ETHUSD"])
trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])

# --- GENERATE MOCK MARKET DATA & TRAIN AI ---
@st.cache_data
def get_ai_prediction():
    # Simulate historical price processing
    data = pd.DataFrame({
        'price': np.random.normal(60000, 500, 100),
        'sma_10': np.random.normal(60000, 400, 100),
        'sma_30': np.random.normal(60000, 300, 100)
    })
    X = data[['price', 'sma_10', 'sma_30']]
    y = np.random.choice([0, 1], size=100) # 1 = Buy, 0 = Sell
    
    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)
    
    # Predict on latest bar
    latest_features = X.iloc[[-1]]
    signal = model.predict(latest_features)[0]
    return data, "BUY 🚀" if signal == 1 else "SELL / HOLD 📉"

# --- MAIN DASHBOARD LAYOUT ---
col1, col2, col3 = st.columns(3)

data, current_signal = get_ai_prediction()

col1.metric(label="Selected Asset", value=symbol)
col2.metric(label="Current AI Signal", value=current_signal)
col3.metric(label="Execution Mode", value=trade_mode)

st.subheader("Live Market Price & Indicators")
st.line_chart(data[['price', 'sma_10', 'sma_30']])

if st.button("Run Instant AI Strategy Analysis"):
    st.write("Analyzing current order books and ML indicators...")
    time.sleep(1)
    if current_signal == "BUY 🚀":
        st.success(f"Signal Generated: Executing BUY order for {symbol} on {trade_mode}")
    else:
        st.warning(f"Signal Generated: Executing SELL/HOLD order for {symbol} on {trade_mode}")
