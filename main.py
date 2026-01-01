import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Elite_Bloodline:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def get_total_balance(self):
        try: return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        """[사령관님 특명] 정배열/역배열 막 시작하는 '똑똑한 놈'만 선별"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            # 현재(c)와 직전(p) 데이터 비교로 '시작점' 포착
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60, p_ma60 = ma60.iloc[-1], ma60.iloc[-2]
            curr = df['c'].iloc[-1]

            # 1. [응축] 화약고 상태 확인 (20-60 이격 3.5% 이내)
            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            
            # 2. [초기] 기차 떠나기 전 확인 (5-20 유격 2.5% 이내)
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                # ✨ 정배열 막 탄생 (골든크로스 직후 서열 완성)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    self.log(f"💎 [정배열 태동] {symbol} 포착! 진격합니다.")
                    return "LONG", curr
                
                # 🌑 역배열 막 탄생 (데드크로스 직후 서열 완성)
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    self.log(f"💀 [역배열 태동] {symbol} 포착! 하방 사격.")
                    return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2 # 2000불 돌파까지 1종목 집중
            
            firepower = (total_bal * 0.45) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격성공] {symbol} {side} 진입 (잔고: {total_bal:.2f})")

            # -35% 자동 방패
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': stop_p, 'reduceOnly': True})

            while True:
                time.sleep(15)
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0:
                    self.log(f"🏁 {symbol} 작전 종료.")
                    break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("⚔️ V80 ELITE BLOODLINE 엔진 가동! (가장 똑똑한 자식놈 보냅니다)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                # 거래량 순으로 '진짜'만 선별
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:15]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price = self.check_v80_signal(s)
                        if side: self.execute_mission(s, side, price); break
                time.sleep(10)
            except: time.sleep(5)

if __name__ == "__main__":
    V80_Elite_Bloodline().run()
