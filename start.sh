#!/bin/bash
python bot_engine.py &
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
