import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
import os

st.set_page_config(page_title="24/7 Universal Crypto AI Bot", layout="wide")

st.title("🤖 24/7 Universal Crypto AI Bot (Long & Short)")

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
        "holdings": {},      # Long holdings (units)
        "short_holdings": {},# Short holdings (units)
        "entry_prices": {},  # Entry price per coin
        "trade_history": []
    }

def save_portfolio():
    data = {
        "balance": st.session_state.balance,
        "holdings": st.session_state.holdings,
        "short_holdings": st.session_state.short_holdings,
        "entry_prices": st.session_state.entry_prices,
        "trade_history": st.session_state.trade_history
    }
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- INITIALIZE PERSISTENT STATE ---
if 'balance' not in st.session_state:
    saved_data = load_portfolio()
    st.session_state.balance = saved_data.get("balance", 1000.0)
    st.session_state.holdings = saved_data.get("holdings", {})
    st.session_state.short_holdings = saved_data.get("short_holdings", {})
    st.session_state.entry_prices = saved_data.get("entry_prices", {})
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

st.sidebar.subheader("🎯 Profit & Protection")
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
    st.session_state.short_holdings = {}
    st.session_state.entry_prices = {}
    st.session_state.trade_history = []
    save_portfolio()
    st.sidebar.success("Portfolio reset!")

for sym in selected_symbols:
    if sym not in st.session_state.holdings:
        st.session_state.holdings[sym] = 0.0
    if sym not in st.session_state.short_holdings:
        st.session_state.short_holdings[sym] = 0.0
    if sym not in st.session_state.entry_prices:
        st.session_state.entry_prices[sym] = 0.0

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

# --- SMART SIGNAL ENGINE (LONG & SHORT) ---
def analyze_market_signal(symbol, current_price):
    long_qty = st.session_state.holdings.get(symbol, 0.0)
    short_qty = st.session_state.short_holdings.get(symbol, 0.0)
    entry_price = st.session_state.entry_prices.get(symbol, 0.0)

    if current_price <= 0:
        return "HOLD", "Invalid Price"

    # 1. EVALUATE OPEN LONG POSITION
    if long_qty > 0 and entry_price > 0:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
        if pnl_pct >= take_profit_pct:
            return "SELL", f"Long Take-Profit Hit (+{pnl_pct:.2f}%)"
        if pnl_pct <= -stop_loss_pct:
            return "SELL", f"Long Stop-Loss Triggered ({pnl_pct:.2f}%)"
        return "HOLD", f"Holding Long ({pnl_pct:+.2f}%)"

    # 2. EVALUATE OPEN SHORT POSITION
    if short_qty > 0 and entry_price > 0:
        # Profit on Short = Price Decreases
        pnl_pct = ((entry_price - current_price) / entry_price) * 100.0
        if pnl_pct >= take_profit_pct:
            return "COVER", f"Short Take-Profit Hit (+{pnl_pct:.2f}%)"
        if pnl_pct <= -stop_loss_pct:
            return "COVER", f"Short Stop-Loss Triggered ({pnl_pct:.2f}%)"
        return "HOLD", f"Holding Short ({pnl_pct:+.2f}%)"

    # 3. IF NO OPEN POSITIONS: CHECK BUY (LONG) OR SHORT SIGNALS
    rsi_mock = np.random.uniform(15, 85)

    if rsi_mock < 35:
        return "BUY", "Oversold Signal (Buying Dip)"
    elif rsi_mock > 65:
        return "SHORT", "Overbought Signal (Shorting Peak)"

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
            long_qty = st.session_state.holdings.get(symbol, 0.0)
            short_qty = st.session_state.short_holdings.get(symbol, 0.0)
            entry_price = st.session_state.entry_prices.get(symbol, 0.0)

            # Determine position type & P/L calculation
            position_type = "NONE"
            pl_str = "0.00%"

            if long_qty > 0 and entry_price > 0:
                position_type = f"LONG ({long_qty:.4f})"
                pl_val = ((current_price - entry_price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"
            elif short_qty > 0 and entry_price > 0:
                position_type = f"SHORT ({short_qty:.4f})"
                pl_val = ((entry_price - current_price) / entry_price) * 100
                pl_str = f"{pl_val:+.2f}%"

            market_summary.append({
                "raw_price": current_price,
                "Asset": symbol,
                "Price": f"€{current_price:,.2f}",
                "Position": position_type,
                "Entry Price": f"€{entry_price:,.2f}" if entry_price > 0 else "-",
                "Current P/L": pl_str,
                "Signal": signal,
                "Reason": reason
            })

            # --- AUTOMATED EXECUTION ENGINE ---
            if st.session_state.bot_running:
                # BUY (OPEN LONG)
                if signal == "BUY" and st.session_state.balance >= trade_amount_eur:
                    coins_bought = trade_amount_eur / current_price
                    st.session_state.balance -= trade_amount_eur
                    st.session_state.holdings[symbol] = coins_bought
                    st.session_state.entry_prices[symbol] = current_price
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'BUY (LONG)',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{trade_amount_eur:.2f}",
                        'Note': reason
                    })
                    executed_any_trade = True

                # SELL (CLOSE LONG)
                elif signal == "SELL" and long_qty > 0:
                    eur_received = long_qty * current_price
                    st.session_state.balance += eur_received
                    net_pnl = eur_received - trade_amount_eur
                    
                    st.session_state.holdings[symbol] = 0.0
                    st.session_state.entry_prices[symbol] = 0.0
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'SELL (CLOSE LONG)',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{eur_received:.2f}",
                        'Note': f"{reason} | Net: €{net_pnl:+.2f}"
                    })
                    executed_any_trade = True

                # SHORT (OPEN SHORT POSITION)
                elif signal == "SHORT" and st.session_state.balance >= trade_amount_eur:
                    coins_shorted = trade_amount_eur / current_price
                    # Reserve collateral for the short position
                    st.session_state.balance -= trade_amount_eur
                    st.session_state.short_holdings[symbol] = coins_shorted
                    st.session_state.entry_prices[symbol] = current_price
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'SHORT (OPEN)',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{trade_amount_eur:.2f}",
                        'Note': reason
                    })
                    executed_any_trade = True

                # COVER (CLOSE SHORT POSITION)
                elif signal == "COVER" and short_qty > 0:
                    cost_to_buy_back = short_qty * current_price
                    net_pnl = trade_amount_eur - cost_to_buy_back
                    # Return collateral + profit or minus loss
                    st.session_state.balance += (trade_amount_eur + net_pnl)
                    
                    st.session_state.short_holdings[symbol] = 0.0
                    st.session_state.entry_prices[symbol] = 0.0
                    
                    st.session_state.trade_history.append({
                        'Time': time.strftime('%H:%M:%S'),
                        'Asset': symbol,
                        'Type': 'COVER (CLOSE SHORT)',
                        'Price': f"€{current_price:,.2f}",
                        'Value': f"€{(trade_amount_eur + net_pnl):.2f}",
                        'Note': f"{reason} | Net: €{net_pnl:+.2f}"
                    })
                    executed_any_trade = True

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
