import time
import json
import os
from datetime import datetime

STATE_FILE = "bot_state.json"

def init_state():
    """Create the initial state file if it doesn't exist yet."""
    if not os.path.exists(STATE_FILE):
        default_state = {
            "total_net_worth": 1000.00,
            "available_usdt": 1000.00,
            "invested_capital": 0.00,
            "open_positions": [],
            "last_update": str(datetime.now())
        }
        with open(STATE_FILE, "w") as f:
            json.dump(default_state, f, indent=4)

def run_bot():
    print("Starting 24/7 Crypto AI Bot Engine...")
    init_state()
    
    while True:
        try:
            # 1. Load current state
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            
            # 2. Market Scanning / Trading Logic Goes Here
            # The bot analyzes the market and updates the state JSON
            state["last_update"] = str(datetime.now())
            
            # 3. Save state so the dashboard can read it
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            
            print(f"[{datetime.now()}] Market scanned. Monitoring for opportunities...")
            
            # Sleep for 60 seconds before next scan
            time.sleep(60)
            
        except Exception as e:
            print(f"Error in bot engine loop: {e}")
            time.sleep(10) # Pause briefly on error before retrying

if __name__ == "__main__":
    run_bot()
