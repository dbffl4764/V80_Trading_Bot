cat << 'EOF' > main.py
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# [사령관님 전용 v95.0 AI Sniper - 60/20 이격도 & 2분할]
class AISniper:
    def __init__(self):
        self.ex = ccxt.binance({
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 5

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 {msg}", flush=True)

    def run(self):
        self.log("🚀 사령관님! 60-20 이격도 레이더 가동 중! (GCP 복구완료) ㅋ")
        try:
            tickers = self.ex.fetch_tickers()
            targets = [s for s, t in tickers.items() if s.endswith('/USDT') and abs(t.get('percentage', 0)) >= 5.0]
            
            for s in targets[:10]:
                ohlcv = self.ex.fetch_ohlcv(s, '1d', limit=100)
                df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
                ma60 = df['c'].rolling(60).mean().iloc[-1]
                ma20 = df['c'].rolling(20).mean().iloc[-1]
                curr = df['c'].iloc[-1]

                disparity = abs(ma20 - ma60) / ma60 * 100
                if disparity >= 3.0: 
                    self.log(f"🔥 {s} 포착! 이격도: {disparity:.2f}% | 2분할 대기 중 ㅋ")
        except Exception as e:
            self.log(f"⚠️ 정찰 지연: {e}")

if __name__ == "__main__":
    bot = AISniper()
    while True:
        bot.run()
        time.sleep(10)
EOF

# 꼬인 프로세스 죽이고, 방금 만든 파일 강제 실행! ㅋ
pkill -9 -f python3
nohup python3 -u main.py > binance.out 2>&1 & tail -f binance.out
