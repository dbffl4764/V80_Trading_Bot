import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Profit_Hunter:
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
        """[사령관님 지시] 가짜 구별 + 초입 타격 로직"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            vol_avg = df['v'].rolling(5).mean() # 거래량 이평

            c5, p5 = ma5.iloc[-1], ma5.iloc[-2]
            c20, p20 = ma20.iloc[-1], ma20.iloc[-2]
            c60, p60 = ma60.iloc[-1], ma60.iloc[-2]
            curr_vol = df['v'].iloc[-1]
            curr = df['c'].iloc[-1]

            # 1. 응축도 확인 (3.5% 이내)
            ma_gap = abs(c20 - c60) / c60 * 100
            
            if ma_gap <= 3.5:
                # 💎 [진짜 롱] 5>20 크로스 + 60선 우상향 + 거래량 동반
                if (p5 <= p20 and c5 > c20 > c60) and (c60 >= p60) and (curr_vol > vol_avg.iloc[-2]):
                    return "LONG", curr
                
                # 💀 [진짜 숏] 20>5 크로스 + 60선 우하향 + 거래량 동반
                if (p5 >= p20 and c60 > c20 > c5) and (c60 <= p60) and (curr_vol > vol_avg.iloc[-2]):
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2
            
            firepower = (total_bal * 0.45) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격] {symbol} {side} 진입! (거래량/기울기 검증완료)")

            # -3.5% 손절 (포지션 기준 약 -35%)
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
        self.log("⚔️ V80 PROFIT HUNTER 가동. (말보다 결과로 보여주겠습니다)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                # 거래량 상위 15개 집중 감시
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:15]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price = self.check_v80_signal(s)
                        if side: self.execute_mission(s, side, price); break
                time.sleep(10)
            except: time.sleep(5)

if __name__ == "__main__":
    V80_Profit_Hunter().run()
