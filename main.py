import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_5M_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.target_roe = 30.0 
        self.stop_loss_roe = -35.0
        self.max_entry_count = 3  # [사령관님 지시] 딱 3분할만 한다!

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def get_total_balance(self):
        try: return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        try:
            o5 = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            df5 = pd.DataFrame(o5, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            m5 = df5['c'].rolling(5).mean().iloc[-1]
            m20 = df5['c'].rolling(20).mean().iloc[-1]
            m60 = df5['c'].rolling(60).mean().iloc[-1]
            curr = df5['c'].iloc[-1]
            vol_avg = df5['v'].rolling(10).mean().iloc[-1]
            ma_gap = abs(m20 - m60) / m60 * 100

            if 3.5 <= ma_gap <= 15.0: 
                if m5 > m20 > m60 and curr > m5 and df5['v'].iloc[-1] > vol_avg:
                    return "LONG", curr
                if m60 > m20 > m5 and curr < m5 and df5['v'].iloc[-1] > vol_avg:
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2
            
            # [3분할 로직] 전체 화력을 3으로 나눠서 진입
            firepower = ((total_bal * 0.45) / max_pos) / self.max_entry_count
            
            for entry_num in range(1, self.max_entry_count + 1):
                amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
                
                # 포지션 진입
                self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                self.log(f"🎯 [사격] {symbol} {side} {entry_num}차 진입! (남은 분할: {self.max_entry_count - entry_num})")

                # 첫 진입 시에만 손절가 서버 예약
                if entry_num == 1:
                    stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         amount * self.max_entry_count, None, {'stopPrice': stop_p, 'reduceOnly': True})

                # 추가 분할 매수 사이의 대기 시간 (5분봉 기준이므로 적당한 간격 유지)
                if entry_num < self.max_entry_count:
                    self.log(f"⏳ 다음 분할 대기 중... (현재 {entry_num}/{self.max_entry_count})")
                    time.sleep(30) 

            # 감시 루프
            while True:
                time.sleep(10)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                current_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                
                if current_amt == 0: break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                if roe <= self.stop_loss_roe:
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                    self.log(f"🚨 [강제 손절] ROE {roe:.2f}% 도달!")
                    break

                if roe > self.target_roe:
                    ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=5)
                    ma5 = pd.Series([x[4] for x in ohlcv]).mean()
                    if (side == "LONG" and curr < ma5) or (side == "SHORT" and curr > ma5):
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                        self.log(f"💰 [익절] ROE: {roe:.2f}%")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 {self.max_entry_count}분할 리미터 가동 중.")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:25]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0:
                        side, price = self.check_v80_signal(s)
                        if side: 
                            self.execute_mission(s, side, price)
                            break
                time.sleep(15)
            except Exception as e: 
                self.log(f"⚠️ 루프 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_5M_Striker().run()
