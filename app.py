import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
import os

st.set_page_config(page_title="24/7 Universal Crypto AI Bot", layout="wide")

st.title("🤖 24/7 Universal Crypto AI Bot")

PORTFOLIO_FILE = "portfolio.json"

# --- HELPER FUNCTIONS TO LOAD & SAVE PORTFOLIO ---
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
        "buy_prices": {},  # Stores average buy price per coin
        "trade_history": []
    }

def save_portfolio():
    data = {
        "balance": st.session_state.balance,
        "holdings": st.session_state.holdings,
        "buy_prices": st.session_state.buy_prices,
        "trade_history": st.session_state.trade_history
    }
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- INITIALIZE PERSISTENT STATE ---
if 'balance' not in st.session_state:
    saved_data = load_portfolio()
    st.session_state.balance = saved_data.get("balance", 1000.0)
    st.session_state.holdings = saved_data.get("holdings", {})
    st.session_state.buy_prices = saved_data.get("buy_prices", {})
    st.session_state.trade_history = saved_data.get("trade_history", [])

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = True

# --- FETCH ALL KRAKEN EUR PAIRS ---
@st.cache_data(ttl=3600)
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

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Bot Settings")

sb_col1, sb_col2 = st.sidebar.columns(2)

with sb_col1:
    trade_amount_eur = st.sidebar.number_input(
        "Trade Size (€)", 
        min_value=5.0, 
        max_value=500.0, 
        value=10.0, 
        step=5.0
    )

with sb_col2:
    sort_order = st.sidebar.selectbox(
        "Sort Table By", 
        ["Price (High to Low)", "Price (Low to High)", "Alphabetical"]
    )

st.sidebar.subheader("🎯 Profit Protection")
take_profit_pct = st.sidebar.slider("Min Take Profit (%)", min_value=0.5, max_value=10.0, value=1.5, step=0.5)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=1.0, max_value=15.0, value=3.0, step=0.5)

selected_symbols = st.sidebar.multiselect(
    f"Select Trading Pairs ({len(ALL_KRAKEN_PAIRS)} Available)",
    options=ALL_KRAKEN_PAIRS,
    default=["XBTEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR"]
)

# Reset Button to start fresh paper portfolio
if st.sidebar.button("🔄 Reset Portfolio Balance (€1,000)"):
    st.session_state.balance = 1000.0
    st.session_state.holdings = {}
    st.session_state.buy_prices = {}
    st.session_state.trade_history = []
    save_portfolio()
    st.sidebar.success("Portfolio reset!")

for sym in selected_symbols:
    if sym not in st.session_state.holdings:
        st.session_state.holdings[sym] = 0.0
    if sym not in st.session_state.buy_prices:
        st.session_state.buy_prices[sym] = 0.0

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

# --- SMART SIGNAL ENGINE ---
def analyze_market_signal(symbol, current_price):
    holding = st.session_state.holdings.get(symbol, 0.0)
    avg_buy = st.session_state.buy_prices.get(symbol, 0.0)

    if current_price <= 0:
        return "HOLD", "Invalid Price"

    # IF WE HOLD THE COIN: CHECK PROFIT / STOP-LOSS RULES FIRST
    if holding > 0 and avg_buy > 0:
        gain_loss_pct = ((current_price - avg_buy) / avg_buy) * 100.0

        if gain_loss_pct >= take_profit_pct:
            return "SELL", f"Take Profit Target Hit (+{gain_loss_pct:.2f}%)"
        
        if gain_loss_pct <= -stop_loss_pct:
            return "SELL", f"Stop-Loss Triggered ({gain_loss_pct:.2f}%)"
        
        return "HOLD", f"Holding (P/L: {gain_loss_pct:+.2f}%)"

    # IF WE DO NOT HOLD THE COIN: LOOK FOR BUY OPPORTUNITY
    if holding == 0:
        # Mock sentiment/RSI filter logic: dip buying pattern
        rsi_mock = np.random.uniform(25, 75)
        if rsi_mock < 40:
            return "BUY", "Oversold Signal (Buying Dip)"
        else:
            return "HOLD", "Waiting for Price Dip"

    return "HOLD", "Neutral Market"

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
    executed_any_trade = False
    
    for symbol in selected_symbols:
        current_price = prices.get(symbol, 0.0)
        
        if current_price > 0:
            signal, reason = analyze_market_signal(symbol, current_price)
            holding = st.session_state.holdings.get(symbol, 0.0)
            avg_buy = st.session_state.buy_prices.get(symbol, 0.0)

            # Calculate current P/L percentage
            pl_str = "0.00%"
            if holding > 0 and avg_buy > 0:
                pl_val = ((current_price - avg_buy) / avg_buy) * 100
                pl_str = f"{pl_val:+.2f}%"
            
            market_summary.append({
                "raw_price": current_price,
                "Asset": symbol,
                "Price": f"€{current_price:,.2f}",
                "Holdings": f"{holding:.4f}",
                "Avg Buy Price": f"€{avg_buy:,.2f}" if avg_buy > 0 else "-",
                "Current P/L": pl_str,
                "Signal": signal,
                "Reason": reason
            })

            # --- PROFIT-GUARDED TRADE EXECUTION ---
            if st.session_state.bot_running:
                # BUY: Only if cash is available and signal says BUY
                if signal == "BUY" and st.session_state.balance >= trade_amount_eur:
                    coins_bought = trade_amount_eur / current_price
                    st.session_state.balance -= trade_amount_eur
                    
                    # Update holdings and weighted average buy price
                    total_coins = holding + coins_bought
                    if total_coins > 0:
                        st.session_state.buy_prices[symbol] = current_price
                    st.session_state.holdings[symbol] = total_coins
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'BUY',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{trade_amount_eur:.2f}",
                        'Amount': f"{coins_bought:.4f}",
                        'Note': reason
                    })
                    executed_any_trade = True

                # SELL: Only triggered when Take-Profit or Stop-Loss target is reached
                elif signal == "SELL" and holding > 0:
                    eur_received = holding * current_price
                    st.session_state.balance += eur_received
                    sold_amount = holding
                    
                    profit_loss = eur_received - (holding * avg_buy)
                    
                    st.session_state.holdings[symbol] = 0.0
                    st.session_state.buy_prices[symbol] = 0.0
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'SELL',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{eur_received:.2f}",
                        'Amount': f"{sold_amount:.4f}",
                        'Note': f"{reason} | Net: €{profit_loss:+.2f}"
                    })
                    executed_any_trade = True

    # Save state if trades occurred
    if executed_any_trade:
        save_portfolio()

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
