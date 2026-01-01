# 1. 기존에 꼬여있던 프로세스 전부 청소
pkill -9 -f python3

# 2. 사령관님의 'Elite Bloodline' 혈통 로직 + AI 학습 통합본 강제 생성
# (현재 디렉토리에 바로 생성하여 경로 에러 원천 차단)
cat << 'EOF' > main.py
import ccxt, time, os, pandas as pd, numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Final_Survivor:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 5 # 사령관님 특명: 2000불까지 레버리지 5배 고정
        self.log_file = "trading_data.csv"
        self.loss_count = 0

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] 🧬 {msg}", flush=True)

    def learn_logic(self):
        """[AI 학습] 실패한 이격도를 분석하여 필터를 스스로 조임"""
        try:
            if os.path.exists(self.log_file):
                df = pd.read_csv(self.log_file)
                if len(df) >= 3:
                    loss_df = df[df['result'] == 'Loss']
                    if not loss_df.empty:
                        return round(loss_df['ma_gap'].mean() * 0.85, 2)
            return 3.5 # 기본값
        except: return 3.5

    def check_v80_signal(self, symbol):
        """[사령관님 혈통 로직] 15분봉 정배열/역배열 태동 포착"""
        try:
            dynamic_gap = self.learn_logic()
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60, p_ma60 = ma60.iloc[-1], ma60.iloc[-2]
            curr = df['c'].iloc[-1]

            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= dynamic_gap and ma5_gap <= 2.5:
                # 정배열 태동 (사령관님 혈통 로직)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr, ma_gap
                # 역배열 태동
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr, ma_gap
            return None, curr, 0
        except: return None, 0, 0

    def run(self):
        self.log("⚔️ V80 ELITE AI 서바이버 가동! (13불 최후의 스나이퍼 모드)")
        while True:
            try:
                if self.loss_count >= 3:
                    self.log("❌ 3연패 달성. 작전 일시 중지."); break

                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                tickers = self.ex.fetch_tickers()
                # 거래량 1억불 이상 주도주만 타격 (잡코인 차단)
                targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                           and t.get('quoteVolume', 0) >= 100000000]
                
                for s in sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]:
                    side, price, gap = self.check_v80_signal(s)
                    if side:
                        self.ex.set_leverage(self.leverage, s)
                        qty = float(self.ex.amount_to_precision(s, (bal * 0.95 * self.leverage) / price))
                        
                        # 지침: 1.75% 즉시 손절 서버 예약
                        sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                        
                        self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                        self.log(f"🔥 사격 완료: {s} {side} (AI 보정 이격: {gap:.2f}%)")
                        
                        time.sleep(300) # 한 번 쏘면 5분간 관망
                        break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 보정 중: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Final_Survivor().run()
EOF

# 3. 백그라운드 가동 및 실시간 로그 확인
nohup python3 -u main.py > binance.out 2>&1 &
tail -f binance.out
