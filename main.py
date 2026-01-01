import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# 구글 클라우드 환경변수 로드
load_dotenv()

class V80_Elite_Final:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        # [사령관님 지침] 2000불까지 레버리지 5배 고정
        self.leverage = 5 

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] 🧬 {msg}", flush=True)

    def check_v80_signal(self, symbol):
        """[사령관님 혈통] 15분봉 정배열/역배열 태동 포착"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            # 현재(c)와 직전(p) 비교로 '태동' 포착
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60, p_ma60 = ma60.iloc[-1], ma60.iloc[-2]
            curr = df['c'].iloc[-1]

            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            # 혈통 필터: 이격 3.5% & 2.5% 이내 수렴 시만 진입
            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def run(self):
        self.log("⚔️ V80 ELITE BLOODLINE 가동 (Clean Build)")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: break

                tickers = self.ex.fetch_tickers()
                # 거래량 순 상위 15개 주도주 타격
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:15]:
                    if s.endswith('/USDT:USDT') and 'BTC' not in s:
                        side, price = self.check_v80_signal(s)
                        if side:
                            self.ex.set_leverage(self.leverage, s)
                            # 시드 전액 사격 (레버리지 5배)
                            qty = float(self.ex.amount_to_precision(s, (bal * 0.95 * self.leverage) / price))
                            
                            # [지침] 1.75% 즉시 손절 서버 예약
                            sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                            
                            self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                            self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                            self.log(f"🔥 사격: {s} {side} (진입: {price})")
                            
                            time.sleep(600) # 10분 대기
                            break
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 오류 보정: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_Elite_Final().run()
