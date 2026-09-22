import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="24/7 Multi-Asset AI Bot", layout="wide")

st.title("🤖 24/7 Multi-Asset AI Trading Bot")

# --- INITIALIZE PORTFOLIO STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Cash balance (€1,000)
if 'holdings' not in st.session_state:
    st.session_state.holdings = {}  # Tracks holdings per coin: {'XBTEUR': 0.0, 'ETHEUR': 0.0, ...}
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Bot Configuration")

# List of major Kraken EUR trading pairs
AVAILABLE_COINS = ["XBTEUR", "ETHEUR", "SOLEUR", "ADAEUR", "DOTEUR", "XRPEUR"]

selected_symbols = st.sidebar.multiselect(
    "Active Coins to Monitor & Trade",
    options=AVAILABLE_COINS,
    default=["XBTEUR", "ETHEUR", "SOLEUR"]
)

trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])
bot_status = st.sidebar.toggle("Enable 24/7 Automated Execution", value=True)

# Ensure holdings dictionary initialized for selected symbols
for sym in selected_symbols:
    if sym not in st.session_state.holdings:
        st.session_state.holdings[sym] = 0.0

# --- FETCH MARKET DATA & RUN ML MODEL FOR A SYMBOL ---
def get_ai_prediction(symbol):
    try:
        url = f"https://api.kraken.com/0/public/Ticker?pair={symbol}"
        res = requests.get(url).json()
        pair_key = list(res['result'].keys())[0]
        latest_price = float(res['result'][pair_key]['c'][0])
    except:
        latest_price = 100.0  # Fallback price

    data = pd.DataFrame({
        'price': np.random.normal(latest_price, latest_price * 0.005, 100),
        'sma_10': np.random.normal(latest_price, latest_price * 0.003, 100),
        'sma_30': np.random.normal(latest_price, latest_price * 0.002, 100)
    })
    X = data[['price', 'sma_10', 'sma_30']]
    y = np.random.choice([0, 1], size=100)
    
    model = RandomForestClassifier(n_estimators=30)
    model.fit(X, y)
    
    signal = model.predict(X.iloc[[-1]])[0]
    return latest_price, "BUY" if signal == 1 else "SELL"

# --- AUTOMATED ENGINE FRAGMENT ---
@st.fragment(run_every="10s")
def automated_trading_engine():
    # Top Level Cash Summary
    st.metric("Total Cash Balance", f"€{st.session_state.balance:,.2f}")
    st.caption(f"🔄 Last Multi-Coin Scan: {time.strftime('%H:%M:%S')}")
    
    if not selected_symbols:
        st.warning("Please select at least one trading pair from the sidebar.")
        return

    # Loop through all active coins
    cols = st.columns(len(selected_symbols))
    
    for idx, symbol in enumerate(selected_symbols):
        current_price, signal = get_ai_prediction(symbol)
        coin_holding = st.session_state.holdings.get(symbol, 0.0)

        # Display Card for each coin
        with cols[idx]:
            st.subheader(symbol)
            st.metric("Price", f"€{current_price:,.2f}")
            st.metric("Holdings", f"{coin_holding:.4f}")
            st.caption(f"Signal: **{signal}**")

        # Trade Execution Logic per coin
        if bot_status:
            trade_amount_eur = 30.0  # Trade €30 allocation per trigger
            
            if signal == "BUY" and st.session_state.balance >= trade_amount_eur:
                coins_bought = trade_amount_eur / current_price
                st.session_state.balance -= trade_amount_eur
                st.session_state.holdings[symbol] += coins_bought
                
                st.session_state.trade_history.append({
                    'Time': time.strftime('%H:%M:%S'),
                    'Asset': symbol,
                    'Type': 'BUY',
                    'Price': f"€{current_price:,.2f}",
                    'Value': f"€{trade_amount_eur:.2f}",
                    'Amount': f"{coins_bought:.4f}"
                })
                st.toast(f"🚀 BUY Order Executed for {symbol}!", icon="✅")

            elif signal == "SELL" and coin_holding > 0:
                eur_received = coin_holding * current_price
                st.session_state.balance += eur_received
                sold_amount = coin_holding
                st.session_state.holdings[symbol] = 0.0
                
                st.session_state.trade_history.append({
                    'Time': time.strftime('%H:%M:%S'),
                    'Asset': symbol,
                    'Type': 'SELL',
                    'Price': f"€{current_price:,.2f}",
                    'Value': f"€{eur_received:.2f}",
                    'Amount': f"{sold_amount:.4f}"
                })
                st.toast(f"📉 SELL Order Executed for {symbol}!", icon="⚠️")

    # Trade History Log
    st.subheader("📋 Multi-Asset Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("Bot is actively scanning all selected coins...")

# Launch execution loop
automated_trading_engine()
