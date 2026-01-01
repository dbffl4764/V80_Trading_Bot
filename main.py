import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Infinite_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_active_symbol(self):
        try:
            balance = self.ex.fetch_balance()
            positions = balance['info']['positions']
            for p in positions:
                if float(p['positionAmt']) != 0:
                    return p['symbol'].replace('USDT', '/USDT:USDT'), float(p['positionAmt'])
            return None, 0
        except: return None, 0

    def check_v80_signal(self, symbol):
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            gap = abs(curr - ma20) / ma20 * 100
            if gap <= 2.5:
                if ma5 > ma20 > ma60: return "LONG", curr
                elif ma5 < ma20 < ma60: return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3 
            first_amount = (firepower * self.leverage) / entry_price
            self.log(f"🎯 [진격] {symbol} {side} 사격! (화력: {firepower:.2f}USDT)")
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
            
            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_price = ticker['last']
                roe = ((curr_price - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_price) / entry_price * 100 * self.leverage)

                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 삭제! 바로 다음 타겟 정찰.")
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', first_amount)
                    break 

                if step == 1 and roe >= 150.0:
                    self.log(f"🔥 [불타기] 150% 돌파! 2차 투입!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 2

                if step == 2 and roe >= 300.0:
                    self.log(f"🚀 [불타기] 300% 돌파! 극한 수익 모드!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 3

                s, amt = self.get_active_symbol()
                if not s:
                    self.log("🏁 상황 종료. 다음 타겟 정찰 시작.")
                    break
                time.sleep(10)
        except Exception as e:
            self.log(f"⚠️ 작전 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 무한 스트라이커(수리완료) 발진! (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            try:
                symbol, amt = self.get_active_symbol()
                if amt == 0:
                    self.log("👀 정찰 중... 5% 이상 쏜 놈들 탐색...")
                    tickers = self.ex.fetch_tickers()
                    candidates = []
                    for s, t in tickers.items():
                        if s.endswith('/USDT:USDT'):
                            # 에러 방지: None 체크 로직 추가
                            change = t.get('percentage') if t.get('percentage') is not None else 0.0
                            if abs(change) >= 5.0:
                                candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                    
                    for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                        side, price = self.check_v80_signal(cand['s'])
                        if side:
                            self.execute_mission(cand['s'], side, price)
                            break
                time.sleep(15)
            except Exception as e:
                self.log(f"⚠️ 메인 루프 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Infinite_Striker().run()
