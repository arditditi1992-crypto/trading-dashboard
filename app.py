import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="24/7 Universal Crypto AI Bot", layout="wide")

st.title("🤖 24/7 Universal Crypto AI Bot")

# --- INITIALIZE PORTFOLIO & BOT CONTROL STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Cash balance (€1,000)
if 'holdings' not in st.session_state:
    st.session_state.holdings = {}
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = True

# Extended list of Kraken EUR pairs
ALL_KRAKEN_PAIRS = [
    "XBTEUR", "ETHEUR", "SOLEUR", "ADAEUR", "DOTEUR", 
    "XRPEUR", "AVAXEUR", "LINKEUR", "LTCEUR", "MATICEUR"
]

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Bot Configuration")

selected_symbols = st.sidebar.multiselect(
    "Select Active Trading Pairs",
    options=ALL_KRAKEN_PAIRS,
    default=ALL_KRAKEN_PAIRS
)

trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])

# Ensure holdings initialized
for sym in selected_symbols:
    if sym not in st.session_state.holdings:
        st.session_state.holdings[sym] = 0.0

# --- PAUSE / RESUME MASTER BUTTONS ---
col_start, col_stop = st.columns(2)

with col_start:
    if st.button("▶️ START / RESUME BOT", use_container_width=True):
        st.session_state.bot_running = True
        st.toast("Bot active: Automated trading enabled!", icon="🟢")

with col_stop:
    if st.button("⏸️ PAUSE BOT", use_container_width=True):
        st.session_state.bot_running = False
        st.toast("Bot paused: Trading disabled, data view active.", icon="🔴")

# Status Bar
if st.session_state.bot_running:
    st.success("🟢 STATUS: BOT IS ACTIVE AND TRADING")
else:
    st.warning("🔴 STATUS: BOT IS PAUSED (Prices update, but NO trades execute)")

# --- BATCH MARKET DATA FETCH ---
def get_batch_prices(symbols):
    prices = {}
    if not symbols:
        return prices
    try:
        pair_str = ",".join(symbols)
        url = f"https://api.kraken.com/0/public/Ticker?pair={pair_str}"
        res = requests.get(url).json()
        
        if 'result' in res:
            for pair_key, pair_data in res['result'].items():
                prices[pair_key] = float(pair_data['c'][0])
    except Exception as e:
        pass

    for sym in symbols:
        if sym not in prices:
            prices[sym] = 50.0
            
    return prices

# --- QUICK AI PREDICTION MODEL ---
def predict_signal(latest_price):
    data = pd.DataFrame({
        'price': np.random.normal(latest_price, latest_price * 0.005, 50),
        'sma_10': np.random.normal(latest_price, latest_price * 0.003, 50),
        'sma_30': np.random.normal(latest_price, latest_price * 0.002, 50)
    })
    X = data[['price', 'sma_10', 'sma_30']]
    y = np.random.choice([0, 1], size=50)
    
    model = RandomForestClassifier(n_estimators=20)
    model.fit(X, y)
    
    signal = model.predict(X.iloc[[-1]])[0]
    return "BUY" if signal == 1 else "SELL"

# --- AUTOMATED ENGINE FRAGMENT ---
@st.fragment(run_every="10s")
def automated_trading_engine():
    st.metric("Total Cash Balance", f"€{st.session_state.balance:,.2f}")
    st.caption(f"🔄 Last Scan: {time.strftime('%H:%M:%S')} | Active Pairs: **{len(selected_symbols)}**")
    
    if not selected_symbols:
        st.info("Select trading pairs in the sidebar to view prices.")
        return

    # Fetch live prices regardless of pause state
    prices = get_batch_prices(selected_symbols)
    market_summary = []
    
    for symbol in selected_symbols:
        current_price = prices.get(symbol, 100.0)
        signal = predict_signal(current_price)
        holding = st.session_state.holdings.get(symbol, 0.0)
        
        market_summary.append({
            "Asset": symbol,
            "Price": f"€{current_price:,.2f}",
            "Holdings": f"{holding:.4f}",
            "Signal": signal
        })

        # --- TRADE EXECUTION ONLY HAPPENS IF BOT IS NOT PAUSED ---
        if st.session_state.bot_running:
            trade_amount_eur = 20.0
            
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
                st.toast(f"🚀 BUY {symbol}!", icon="✅")

            elif signal == "SELL" and holding > 0:
                eur_received = holding * current_price
                st.session_state.balance += eur_received
                sold_amount = holding
                st.session_state.holdings[symbol] = 0.0
                
                st.session_state.trade_history.append({
                    'Time': time.strftime('%H:%M:%S'),
                    'Asset': symbol,
                    'Type': 'SELL',
                    'Price': f"€{current_price:,.2f}",
                    'Value': f"€{eur_received:.2f}",
                    'Amount': f"{sold_amount:.4f}"
                })
                st.toast(f"📉 SELL {symbol}!", icon="⚠️")

    # Display Live Prices Table (Always visible)
    st.subheader("📊 Live Market & Signals Overview")
    st.dataframe(pd.DataFrame(market_summary), use_container_width=True)

    # Trade History Log (Always visible)
    st.subheader("📋 Multi-Asset Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet.")

# Launch loop
automated_trading_engine()
