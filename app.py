import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="AI Trading Bot Dashboard", layout="wide")

st.title("🤖 AI Algo Trading Bot Dashboard")

# --- INITIALIZE SIMULATION PORTFOLIO STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Starting simulated cash (€1,000)
if 'crypto_balance' not in st.session_state:
    st.session_state.crypto_balance = 0.0
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Bot Configuration")
api_key = st.sidebar.text_input("Kraken API Key", type="password")
secret_key = st.sidebar.text_input("Kraken Secret Key", type="password")
symbol = st.sidebar.selectbox("Trading Pair", ["XBTEUR", "XBTUSD", "ETHUSD"])
trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])

# --- FETCH MARKET DATA & RUN ML MODEL ---
def get_ai_prediction():
    # Fetch real live price from Kraken public API
    try:
        url = f"https://api.kraken.com/0/public/Ticker?pair={symbol}"
        res = requests.get(url).json()
        pair_key = list(res['result'].keys())[0]
        latest_price = float(res['result'][pair_key]['c'][0])
    except:
        latest_price = 60000.0  # Fallback price

    # Create dummy technical dataset for model prediction
    data = pd.DataFrame({
        'price': np.random.normal(latest_price, 200, 100),
        'sma_10': np.random.normal(latest_price, 150, 100),
        'sma_30': np.random.normal(latest_price, 100, 100)
    })
    X = data[['price', 'sma_10', 'sma_30']]
    y = np.random.choice([0, 1], size=100)
    
    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)
    
    signal = model.predict(X.iloc[[-1]])[0]
    return data, latest_price, "BUY" if signal == 1 else "SELL"

data, current_price, signal = get_ai_prediction()

# --- TOP METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Selected Asset", symbol)
col2.metric("Live Market Price", f"€{current_price:,.2f}")
col3.metric("Simulated Cash", f"€{st.session_state.balance:,.2f}")
col4.metric("Crypto Holdings", f"{st.session_state.crypto_balance:.4f} BTC")

st.markdown("---")

# --- CHART ---
st.subheader("Price Movement & Indicators")
st.line_chart(data[['price', 'sma_10', 'sma_30']])

# --- SIMULATION EXECUTION ACTION ---
if st.button("Run Simulation Trade Analysis"):
    trade_amount_eur = 100.0  # Simulated trade size in Euros
    
    if signal == "BUY":
        if st.session_state.balance >= trade_amount_eur:
            btc_bought = trade_amount_eur / current_price
            st.session_state.balance -= trade_amount_eur
            st.session_state.crypto_balance += btc_bought
            
            st.session_state.trade_history.append({
                'Time': time.strftime('%H:%M:%S'),
                'Type': 'BUY',
                'Price': f"€{current_price:,.2f}",
                'Value': f"€{trade_amount_eur:.2f}",
                'Crypto Acquired': f"{btc_bought:.6f}"
            })
            st.success(f"✅ Executed BUY: Bought {btc_bought:.6f} BTC at €{current_price:,.2f}")
        else:
            st.error("⚠️ Insufficient Cash Balance for BUY simulation.")
            
    elif signal == "SELL":
        if st.session_state.crypto_balance > 0:
            eur_received = st.session_state.crypto_balance * current_price
            st.session_state.balance += eur_received
            old_crypto = st.session_state.crypto_balance
            st.session_state.crypto_balance = 0.0
            
            st.session_state.trade_history.append({
                'Time': time.strftime('%H:%M:%S'),
                'Type': 'SELL',
                'Price': f"€{current_price:,.2f}",
                'Value': f"€{eur_received:.2f}",
                'Crypto Sold': f"{old_crypto:.6f}"
            })
            st.warning(f"📉 Executed SELL: Sold {old_crypto:.6f} BTC for €{eur_received:.2f}")
        else:
            st.info("ℹ️ AI generated SELL signal, but you hold 0 BTC to sell.")

# --- DISPLAY SIMULATED TRADE HISTORY TABLE ---
st.subheader("📋 Simulated Trade Log")
if len(st.session_state.trade_history) > 0:
    st.table(pd.DataFrame(st.session_state.trade_history))
else:
    st.info("No trades executed yet. Click 'Run Simulation Trade Analysis' to place paper trades.")
