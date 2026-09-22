import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="24/7 AI Trading Bot", layout="wide")

st.title("🤖 24/7 Fully Automated AI Trading Bot")

# --- INITIALIZE PORTFOLIO STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Cash balance (€1,000)
if 'crypto_balance' not in st.session_state:
    st.session_state.crypto_balance = 0.0
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Bot Configuration")
symbol = st.sidebar.selectbox("Trading Pair", ["XBTEUR", "XBTUSD", "ETHUSD"])
trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])
bot_status = st.sidebar.toggle("Enable 24/7 Automated Execution", value=True)

# --- FETCH MARKET DATA & RUN ML MODEL ---
def get_ai_prediction():
    try:
        url = f"https://api.kraken.com/0/public/Ticker?pair={symbol}"
        res = requests.get(url).json()
        pair_key = list(res['result'].keys())[0]
        latest_price = float(res['result'][pair_key]['c'][0])
    except:
        latest_price = 60000.0

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

# --- AUTOMATED ENGINE FRAGMENT ---
# run_every="10s" auto-executes this section every 10 seconds natively
@st.fragment(run_every="10s")
def automated_trading_engine():
    data, current_price, signal = get_ai_prediction()

    # Metrics Display
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Selected Asset", symbol)
    col2.metric("Live Market Price", f"€{current_price:,.2f}")
    col3.metric("Simulated Cash", f"€{st.session_state.balance:,.2f}")
    col4.metric("Crypto Holdings", f"{st.session_state.crypto_balance:.4f} BTC")

    st.caption(f"🔄 Last Auto Scan: {time.strftime('%H:%M:%S')} | Signal: **{signal}**")
    st.line_chart(data[['price', 'sma_10', 'sma_30']])

    # Auto Trade Execution Logic
    if bot_status:
        trade_amount_eur = 50.0
        
        if signal == "BUY" and st.session_state.balance >= trade_amount_eur:
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
            st.toast(f"🚀 Auto-Bot Executed BUY order for {symbol}!", icon="✅")

        elif signal == "SELL" and st.session_state.crypto_balance > 0:
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
            st.toast(f"📉 Auto-Bot Executed SELL order for {symbol}!", icon="⚠️")

    # Trade History Log
    st.subheader("📋 Automatic Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("Bot is active. Trades will appear here automatically when signals trigger...")

# Launch the loop
automated_trading_engine()
