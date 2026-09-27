import streamlit as st
import pandas as pd
import json
import os
from streamlit_autorefresh import st_autorefresh

# -------------------------------------------------------------------
# 1. SETUP & CONFIGURATION
# -------------------------------------------------------------------
# Point to Railway's persistent storage so your dashboard reads the live bot data
VOLUME_PATH = "/data"
PORTFOLIO_FILE = os.path.join(VOLUME_PATH, "portfolio.json") if os.path.exists(VOLUME_PATH) else "portfolio.json"

st.set_page_config(page_title="Crypto AI Bot Dashboard", page_icon="🤖", layout="wide")

# Auto-refresh the dashboard every 3 seconds to see live trades
st_autorefresh(interval=3000, limit=None, key="dashboard_refresh")

# -------------------------------------------------------------------
# 2. LOAD BOT DATA
# -------------------------------------------------------------------
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback if the bot hasn't saved the file yet
    return {"balance": 1000.0, "holdings": {}, "entry_prices": {}, "trade_history": []}

data = load_portfolio()

# -------------------------------------------------------------------
# 3. DASHBOARD HEADER & METRICS
# -------------------------------------------------------------------
st.title("🤖 24/7 Crypto AI Bot Dashboard")
st.markdown("---")

# Calculate portfolio totals
available_cash = data.get('balance', 1000.0)
invested_capital = sum([data['entry_prices'].get(sym, 0.0) * qty for sym, qty in data.get('holdings', {}).items() if qty > 0])
total_net_worth = available_cash + invested_capital

col1, col2, col3 = st.columns(3)
col1.metric("Total Net Worth", f"${total_net_worth:,.2f}")
col2.metric("Available USDT", f"${available_cash:,.2f}")
col3.metric("Invested Capital", f"${invested_capital:,.2f}")

st.markdown("---")

# -------------------------------------------------------------------
# 4. ACTIVE POSITIONS
# -------------------------------------------------------------------
st.subheader("💼 Active Open Positions")

active_positions = []
for sym, qty in data.get('holdings', {}).items():
    if qty > 0:
        entry_price = data['entry_prices'].get(sym, 0.0)
        invested = entry_price * qty
        active_positions.append({
            "Asset": sym, 
            "Coins Held": round(qty, 6),
            "Entry Price": f"${entry_price:,.4f}",
            "Invested Value": f"${invested:,.2f}"
        })

if active_positions:
    df_active = pd.DataFrame(active_positions)
    st.dataframe(df_active, use_container_width=True, hide_index=True)
else:
    st.info("No open trades currently. The bot is scanning the markets for opportunities.")

st.markdown("---")

# -------------------------------------------------------------------
# 5. TRADE HISTORY LOG
# -------------------------------------------------------------------
st.subheader("📋 Historical Trade Log")

trade_history = data.get('trade_history', [])

if trade_history:
    # Convert list of dictionaries to a pandas DataFrame
    df_history = pd.DataFrame(trade_history)
    
    # Format the Price column to look like currency
    if 'Price' in df_history.columns:
        df_history['Price'] = df_history['Price'].apply(lambda x: f"${float(x):,.4f}")
        
    # Reverse the dataframe so the newest trades show up at the very top
    df_history = df_history.iloc[::-1]
    
    st.dataframe(df_history, use_container_width=True, hide_index=True)
else:
    st.info("No trades have been executed yet.")
