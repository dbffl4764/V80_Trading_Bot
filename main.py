import ccxt, time, os, pandas as pd, numpy as np
from datetime import datetime
from dotenv import load_dotenv

# 구글 클라우드 환경변수 자동 로드
load_dotenv()

class V80_Elite_Full_Force:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        # [지침] 3000불 미만 시 레버리지 5배 고정 (방어력 우선)
        self.leverage = 5 
        self.log_file = "trading_history.csv"

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] 🧬 {msg}", flush=True)

    def learn_logic(self):
        """[AI 학습] 실패한 이격도를 분석하여 필터를 스스로 강화"""
        try:
            if os.path.exists(self.log_file):
                df = pd.read_csv(self.log_file)
                if len(df) >= 3:
                    loss_df = df[df['result'] == 'Loss']
                    if not loss_df.empty:
                        return round(loss_df['ma_gap'].mean() * 0.85, 2)
            return 3.5 # 사령관님 혈통 기본 이격
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
            c_ma60 = ma60.iloc[-1]
            curr = df['c'].iloc[-1]

            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            # 5% 변동성 임계치 + 혈통 필터
            if 1.0 <= ma_gap <= dynamic_gap and ma5_gap <= 2.5:
                # 정배열 태동 (롱)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr, ma_gap
                # 역배열 태동 (숏)
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr, ma_gap
            return None, curr, 0
        except: return None, 0, 0

    def run(self):
        self.log("⚔️ V80 ELITE ALL-IN-ONE 가동 (13불 부활 작전)")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                # [지침] 자산 규모별 종목 수 조절 (13불은 1종목 집중)
                max_pos = 1 if bal < 3000 else (2 if bal < 5000 else 5)

                tickers = self.ex.fetch_tickers()
                targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                           and t.get('quoteVolume', 0) >= 100000000 and abs(t.get('percentage', 0)) >= 5.0]

                for s in sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:max_pos]:
                    side, price, gap = self.check_v80_signal(s)
                    if side:
                        self.ex.set_leverage(self.leverage, s)
                        qty = float(self.ex.amount_to_precision(s, (bal * 0.95 * self.leverage) / price))
                        
                        # [지침] 1.75% 즉시 손절 예약
                        sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                        
                        self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                        self.log(f"🎯 [사격] {s} {side} 진입 (이격: {gap:.2f}%)")
                        
                        time.sleep(600) # 10분 관망
                        break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 보정: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Elite_Full_Force().run()
