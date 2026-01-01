import ccxt, time, os, pandas as pd, numpy as np
from datetime import datetime
from dotenv import load_dotenv

# 구글 클라우드 환경변수 로드 (API Key 등)
load_dotenv()

class V80_Elite_AI_Commander:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        # [지침] 2000불 미만 시 레버리지 5배 고정
        self.leverage = 5 
        self.log_file = "trading_history.csv" # AI 학습용

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] 🧬 {msg}", flush=True)

    def check_v80_signal(self, symbol):
        """[사령관님 혈통 로직] 15분봉 정배열/역배열 태동 포착"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            # 태동 시점 포착을 위한 현재(c)와 직전(p) 비교
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60 = ma60.iloc[-1]
            curr = df['c'].iloc[-1]

            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            # 사령관님 지침: 응축(3.5%) 및 수렴(2.5%) 확인
            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                # ✨ 정배열 막 탄생 (Long)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr
                # 🌑 역배열 막 탄생 (Short)
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def run(self):
        self.log("⚔️ V80 ELITE COMMANDER 가동 (13불 부활 작전)")
        while True:
            try:
                # 구글 클라우드에서 잔고 실시간 확인
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: 
                    self.log("⚠️ 시드 고갈... 작전 중지"); break

                # [지침] 자산 규모별 종목 수 조절 (13불은 무조건 1종목 집중)
                max_pos = 1 if bal < 3000 else (2 if bal < 5000 else 5)

                tickers = self.ex.fetch_tickers()
                # [지침] 큰 폭으로 오르내린 종목(5% 이상) 중 상위 10개만 추출
                targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                           and abs(t.get('percentage', 0)) >= 5.0]
                
                # 거래량 순 상위 10개 종목 선별
                top_10 = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in top_10:
                    side, price = self.check_v80_signal(s)
                    if side:
                        self.ex.set_leverage(self.leverage, s)
                        # 시드 화력 45% 투입
                        qty = float(self.ex.amount_to_precision(s, (bal * 0.45 * self.leverage) / price))
                        
                        # [지침] 1.75% 즉시 손절 서버 예약 (필수 방패)
                        sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                        
                        self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                        self.log(f"🎯 [사격] {s} {side} 진입 (잔고: {bal:.2f})")
                        
                        time.sleep(600) # 10분 관망
                        break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 보정: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Elite_AI_Commander().run()
