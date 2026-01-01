cat << 'EOF' > main.py
import ccxt
import time
from v80_logic import check_logic
from v80_trade import calculate_size
from datetime import datetime

ex = ccxt.binance({'options': {'defaultType': 'future'}})

while True:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ v80 정찰 중...", flush=True)
    try:
        # 5% 변동성 코인 스캔
        tickers = ex.fetch_tickers()
        for s, t in tickers.items():
            if '/USDT' in s and abs(t.get('percentage', 0)) >= 5.0:
                # 데이터 로드 및 로직 판별
                ohlcv_d = ex.fetch_ohlcv(s, '1d', limit=100)
                ohlcv_m = ex.fetch_ohlcv(s, '5m', limit=100)
                df_d = pd.DataFrame(ohlcv_d, columns=['t','o','h','l','c','v'])
                df_m = pd.DataFrame(ohlcv_m, columns=['t','o','h','l','c','v'])
                
                signal = check_logic(df_d, df_m)
                if signal:
                    print(f"🔥 {s} {signal} 타점 포착! ㅋ")
    except Exception as e:
        print(f"⚠️ 지연 발생: {e}")
    time.sleep(10)
EOF
