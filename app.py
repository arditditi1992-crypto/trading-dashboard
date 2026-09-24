import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import json
import os

st.set_page_config(page_title="24/7 Universal Crypto AI Bot", layout="wide")

st.title("🤖 24/7 Crypto AI Bot (Live TA Engine)")

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
        "short_holdings": {},
        "entry_prices": {},
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
        res = requests.get(url, timeout=10).json()
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

st.sidebar.subheader("🎯 Risk & Execution Controls")
take_profit_pct = st.sidebar.slider("Min Take Profit (%)", min_value=0.5, max_value=10.0, value=1.5, step=0.5)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=1.0, max_value=15.0, value=3.0, step=0.5)

st.sidebar.subheader("📊 Technical Indicator Sensitivity")
rsi_oversold = st.sidebar.slider("RSI Oversold (Buy Threshold)", 15, 45, 30, 1)
rsi_overbought = st.sidebar.slider("RSI Overbought (Short Threshold)", 55, 85, 70, 1)

selected_symbols = st.sidebar.multiselect(
    f"Select Trading Pairs ({len(ALL_KRAKEN_PAIRS)} Available)",
    options=ALL_KRAKEN_PAIRS,
    default=["XBTEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR"]
)

# Reset Button
if st.sidebar.button("🔄 Reset Portfolio (€1,000)"):
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
        st.toast("Bot paused: Trading disabled.", icon="🔴")

if st.session_state.bot_running:
    st.success("🟢 STATUS: BOT IS ACTIVE AND RUNNING TA STRATEGY")
else:
    st.warning("🔴 STATUS: BOT IS PAUSED")

# --- FETCH REAL KRAKEN OHLC CANDLES & COMPUTE TA INDICATORS ---
def fetch_ta_data(symbol, interval="5m"):
    """
    Fetches live 5-minute candles directly from Binance API
    and calculates RSI, MACD, Moving Averages, and Bollinger Bands.
    """
    try:
        formatted_symbol = symbol.replace("/", "").replace("-", "").upper()

        url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval={interval}&limit=100"
        res = requests.get(url, timeout=3).json()
        
        if isinstance(res, dict) and "code" in res:
            return None

        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)

        if len(df) < 30:
            return None

        # --- TECHNICAL INDICATOR CALCULATIONS ---
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))

        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

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

    price = data['current_price']
    long_qty = st.session_state.holdings.get(symbol, 0.0)
    short_qty = st.session_state.short_holdings.get(symbol, 0.0)
    entry_price = st.session_state.entry_prices.get(symbol, 0.0)

    # 1. RISK CONTROL FIRST (OPEN POSITIONS)
    if long_qty > 0 and entry_price > 0:
        pnl_pct = ((price - entry_price) / entry_price) * 100.0
        if pnl_pct >= take_profit_pct:
            return price, "SELL", f"Long Take-Profit Hit (+{pnl_pct:.2f}%)"
        if pnl_pct <= -stop_loss_pct:
            return price, "SELL", f"Long Stop-Loss Triggered ({pnl_pct:.2f}%)"
        return price, "HOLD", f"Holding Long ({pnl_pct:+.2f}%)"

    if short_qty > 0 and entry_price > 0:
        pnl_pct = ((entry_price - price) / entry_price) * 100.0
        if pnl_pct >= take_profit_pct:
            return price, "COVER", f"Short Take-Profit Hit (+{pnl_pct:.2f}%)"
        if pnl_pct <= -stop_loss_pct:
            return price, "COVER", f"Short Stop-Loss Triggered ({pnl_pct:.2f}%)"
        return price, "HOLD", f"Holding Short ({pnl_pct:+.2f}%)"

    # 2. ENTRY SIGNALS (COMBINED TA STRATEGY)
    # Check MACD Bullish / Bearish Crossovers
    macd_bullish_cross = (data['prev_macd'] < data['prev_macd_signal']) and (data['macd'] > data['macd_signal'])
    macd_bearish_cross = (data['prev_macd'] > data['prev_macd_signal']) and (data['macd'] < data['macd_signal'])

    # BUY CONDITIONS
    buy_score = 0
    if data['rsi'] < rsi_oversold: buy_score += 1
    if macd_bullish_cross or data['macd'] > data['macd_signal']: buy_score += 1
    if price <= data['bb_lower']: buy_score += 1
    if price >= data['ema50']: buy_score += 1  # Bullish trend alignment

    # SHORT CONDITIONS
    short_score = 0
    if data['rsi'] > rsi_overbought: short_score += 1
    if macd_bearish_cross or data['macd'] < data['macd_signal']: short_score += 1
    if price >= data['bb_upper']: short_score += 1
    if price <= data['ema50']: short_score += 1  # Bearish trend alignment

    # Signal Threshold (Requires at least 3 matching confirmations)
    if buy_score >= 3:
        return price, "BUY", f"Strong Buy (RSI: {data['rsi']:.1f}, BB Lower Hit, MACD Bullish)"
    elif short_score >= 3:
        return price, "SHORT", f"Strong Short (RSI: {data['rsi']:.1f}, BB Upper Hit, MACD Bearish)"

    return price, "HOLD", f"Neutral (RSI: {data['rsi']:.1f} | MACD Neutral)"

# --- AUTOMATED ENGINE FRAGMENT ---
@st.fragment(run_every="10s")
def automated_trading_engine():
    st.metric("Total Cash Balance", f"€{st.session_state.balance:,.2f}")
    st.caption(f"🔄 Last Scan: {time.strftime('%H:%M:%S')} | Active Pairs: **{len(selected_symbols)}**")
    
    if not selected_symbols:
        st.info("Select trading pairs in the sidebar to start live monitoring.")
        return

    market_summary = []
    executed_any_trade = False
    
    for symbol in selected_symbols:
        current_price, signal, reason = analyze_market_signal(symbol)
        
        if current_price > 0:
            long_qty = st.session_state.holdings.get(symbol, 0.0)
            short_qty = st.session_state.short_holdings.get(symbol, 0.0)
            entry_price = st.session_state.entry_prices.get(symbol, 0.0)

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

            # EXECUTION LOGIC
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

                # SHORT (OPEN SHORT)
                elif signal == "SHORT" and st.session_state.balance >= trade_amount_eur:
                    coins_shorted = trade_amount_eur / current_price
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

                # COVER (CLOSE SHORT)
                elif signal == "COVER" and short_qty > 0:
                    cost_to_buy_back = short_qty * current_price
                    net_pnl = trade_amount_eur - cost_to_buy_back
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

    # SORTING LOGIC
    if sort_order == "Price (High to Low)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=True)
    elif sort_order == "Price (Low to High)":
        market_summary.sort(key=lambda x: x['raw_price'], reverse=False)
    elif sort_order == "Alphabetical":
        market_summary.sort(key=lambda x: x['Asset'])

    st.subheader("📊 Live Technical Analysis & Signal Overview")
    if market_summary:
        display_df = pd.DataFrame(market_summary).drop(columns=['raw_price'])
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Fetching candle data from Kraken...")

    st.subheader("📋 Multi-Asset Trade Log")
    if len(st.session_state.trade_history) > 0:
        st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
    else:
        st.info("No trades logged yet.")

# Launch loop
automated_trading_engine()
