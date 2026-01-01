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
        self.target_roe = 100.0  # 1차 목표 수익률 (50% 익절 지점)
        self.stop_loss_roe = -35.0
        self.max_entry_count = 3
        self.half_profit_taken = False # 반익절 여부 체크

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
            self.half_profit_taken = False # 초기화
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2
            firepower = ((total_bal * 0.45) / max_pos) / self.max_entry_count
            
            for entry_num in range(1, self.max_entry_count + 1):
                amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
                self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                self.log(f"🎯 [사격] {symbol} {side} {entry_num}차 진입!")

                if entry_num == 1:
                    stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         amount * self.max_entry_count, None, {'stopPrice': stop_p, 'reduceOnly': True})
                time.sleep(1)

            while True:
                time.sleep(10)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                current_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                
                if current_amt == 0: break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                # 1. 손절 감시
                if roe <= self.stop_loss_roe:
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                    self.log(f"🚨 [손절] ROE {roe:.2f}% 탈출.")
                    break

                # 2. 사령관님 지시: 100% 도달 시 50% 던지기
                if not self.half_profit_taken and roe >= 100.0:
                    half_amt = float(self.ex.amount_to_precision(symbol, current_amt / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_amt, {'reduceOnly': True})
                    self.half_profit_taken = True
                    self.log(f"💰 [1차 익절] ROE 100% 달성! 물량 50% 던졌습니다. 이제부터 극대화 모드!")

                # 3. 수익 극대화: 반익절 이후 5일선 이탈 시 전량 익절
                if self.half_profit_taken:
                    ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=5)
                    ma5 = pd.Series([x[4] for x in ohlcv]).mean()
                    if (side == "LONG" and curr < ma5) or (side == "SHORT" and curr > ma5):
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                        self.log(f"🏁 [최종 익절] 추세 꺾임 감지. 수익 극대화 종료! ROE: {roe:.2f}%")
                        self.log(f"📢 원칙: 수익의 30% 안전자산 이체하십시오!")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 [100% 반익절/극대화] 가동.")
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
                self.log(f"⚠️ 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_5M_Striker().run()
