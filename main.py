import ccxt, time, os, pandas as pd, numpy as np
from datetime import datetime

class V80_Full_Integrated:
    def __init__(self):
        # 구글 클라우드 설정값에서 API 키 로드
        self.ex = ccxt.binance({
            'apiKey': os.environ.get('BINANCE_API_KEY'),
            'secret': os.environ.get('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 5 # 사령관님 지침: 5배 고정

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def check_v80_logic(self, symbol):
        """[사령관님 혈통] v80_logic.py 내용을 이 안으로 통합"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()

            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60 = ma60.iloc[-1]
            curr = df['c'].iloc[-1]

            # 응축(3.5%) & 수렴(2.5%) 필터
            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60): return "LONG", curr
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5): return "SHORT", curr
            return None, curr
        except: return None, 0

    def run(self):
        self.log("⚔️ V80 통합 엔진 가동 (GCP 워크플로우 최적화)")
        try:
            bal = float(self.ex.fetch_balance()['total']['USDT'])
            if bal < 5: return

            # 변동성 5% 이상 종목 중 거래량 상위 10개만 타격
            tickers = self.ex.fetch_tickers()
            targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                       and abs(t.get('percentage', 0)) >= 5.0]
            top_10 = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]

            for s in top_10:
                side, price = self.check_v80_logic(s)
                if side:
                    self.ex.set_leverage(self.leverage, s)
                    qty = float(self.ex.amount_to_precision(s, (bal * 0.45 * self.leverage) / price))
                    sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                    
                    self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                    self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                    self.log(f"🎯 [사격성공] {s} {side} 진입 완료")
                    break # 크론탭 방식이므로 한 종목 진입 후 종료
        except Exception as e:
            self.log(f"⚠️ 오류 발생: {e}")

if __name__ == "__main__":
    V80_Full_Integrated().run()
