cat << 'EOF' > requirements.txt
ccxt
pandas
numpy
EOF

cat << 'EOF' > v80_logic.py
import pandas as pd
def check_logic(df_d, df_m):
    ma60 = df_d['c'].rolling(60).mean().iloc[-1]
    ma20 = df_d['c'].rolling(20).mean().iloc[-1]
    curr = df_d['c'].iloc[-1]
    disparity = abs(ma20 - ma60) / ma60 * 100
    m_ma20 = df_m['c'].rolling(20).mean().iloc[-1]
    if disparity >= 3.0:
        if curr > ma20 and curr > m_ma20: return "LONG"
        if curr < ma20 and curr < m_ma20: return "SHORT"
    return None
EOF

cat << 'EOF' > v80_trade.py
def calculate_size(balance, price, leverage):
    total_budget = balance * 0.45 * leverage
    return total_budget * 0.4 / price
EOF

cat << 'EOF' > main.py
import ccxt, time, pandas as pd
from v80_logic import check_logic
from v80_trade import calculate_size
from datetime import datetime
print("🚀 [v80-Final] 엔진 시동 중...", flush=True)
ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
while True:
    try:
        now = datetime.now().strftime('%H:%M:%S')
        ticker = ex.fetch_ticker('SOL/USDT')
        print(f"[{now}] SOL 정찰 중... ㅋ", end='\r', flush=True)
    except Exception as e:
        print(f"\n⚠️ 연결 대기: {e}")
    time.sleep(5)
EOF
