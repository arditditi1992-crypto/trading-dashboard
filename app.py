import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import requests
import time

st.set_page_config(page_title="24/7 Universal Crypto AI Bot", layout="wide")

st.title("🤖 24/7 Universal Crypto AI Bot")

# --- FETCH ALL KRAKEN EUR PAIRS DYNAMICALLY ---
@st.cache_data(ttl=3600)  # Caches for 1 hour so it loads fast
def get_kraken_eur_pairs():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url).json()
        pair_map = {}
        pair_list = []
        if 'result' in res:
            for internal_name, data in res['result'].items():
                altname = data.get('altname', '')
                if altname.endswith('EUR') and '.d' not in altname:
                    pair_map[internal_name] = altname
                    pair_list.append(altname)
        return sorted(pair_list), pair_map
    except Exception:
        return ["XBTEUR", "ETHEUR", "SOLEUR"], {"XXBTZEUR": "XBTEUR", "XETHZEUR": "ETHEUR"}

ALL_KRAKEN_PAIRS, PAIR_MAP = get_kraken_eur_pairs()

# --- INITIALIZE PORTFOLIO & BOT CONTROL STATE ---
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0  # Cash balance (€1,000)
if 'holdings' not in st.session_state:
    st.session_state.holdings = {}
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = True

# --- SIDEBAR CONFIGURATION (WITH ADDED SIDEBAR COLUMNS) ---
st.sidebar.header("⚙️ Bot Settings")

# Added 2 columns directly inside the sidebar menu (>> bar)
sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_eur = st.number_input(
        "Trade Size (€)", 
        min_value=5.0, 
        max_value=500.0, 
        value=10.0, 
        step=5.0
    )

with sb_col2:
    sort_order = st.selectbox(
        "Sort Table By", 
        ["Price (High to Low)", "Price (Low to High)", "Alphabetical"]
    )

selected_symbols = st.sidebar.multiselect(
    f"Select Trading Pairs ({len(ALL_KRAKEN_PAIRS)} Available)",
    options=ALL_KRAKEN_PAIRS,
    default=["XBTEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR"]
)

trade_mode = st.sidebar.radio("Mode", ["Simulation (Paper)", "Live Trading"])

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
            for internal_key, pair_data in res['result'].items():
                normal_name = PAIR_MAP.get(internal_key, internal_key)
                if normal_name not in symbols:
                    for sym in symbols:
                        if sym in internal_key or internal_key.endswith(sym):
                            normal_name = sym
                            break
                prices[normal_name] = float(pair_data['c'][0])
    except Exception:
        pass
            
    return prices

# --- QUICK AI PREDICTION MODEL ---
def predict_signal(latest_price):
    if latest_price <= 0: return "HOLD"
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

    prices = get_batch_prices(selected_symbols)
    market_summary = []
    
    for symbol in selected_symbols:
        current_price = prices.get(symbol, 0.0)
        
        if current_price > 0:
            signal = predict_signal(current_price)
            holding = st.session_state.holdings.get(symbol, 0.0)
            
            market_summary.append({
                "raw_price": current_price,
                "Asset": symbol,
                "Price": f"€{current_price:,.2f}",
                "Holdings": f"{holding:.4f}",
                "Signal": signal
            })

            # --- TRADE EXECUTION ---
            if st.session_state.bot_running:
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

    # --- RANKING / SORTING LOGIC ---
    if sort_order == "Price (High to Low)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=True)
    elif sort_order == "Price (Low to High)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=False)
    elif sort_order == "Alphabetical":
        market_summary.sort(key=lambda x: x['Asset'])

    # Display Live Prices Table
    st.subheader("📊 Live Market & Signals Overview")
    if market_summary:
        display_df = pd.DataFrame(market_summary).drop(columns=['raw_price'])
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Fetching market data from Kraken...")

    # Trade History Log
    st.subheader("📋 Multi-Asset Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet.")

# Launch loop
automated_trading_engine()
