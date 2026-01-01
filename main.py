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
        """현재 잡고 있는 포지션이 있는지 확인"""
        try:
            balance = self.ex.fetch_balance()
            positions = balance['info']['positions']
            for p in positions:
                if float(p['positionAmt']) != 0:
                    return p['symbol'].replace('USDT', '/USDT:USDT'), float(p['positionAmt'])
            return None, 0
        except: return None, 0

    def check_v80_signal(self, symbol):
        """정배열 롱/역배열 숏 판독"""
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
        """[사령관님 필승 지침] 1차 손절 & 불타기 & 즉시 다음 타겟 전환"""
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

                # 1. 1차분 -35% 손절
                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 삭제! 바로 다음 타겟 찾으러 갑니다.")
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', first_amount)
                    break 

                # 2. 150% 불타기
                if step == 1 and roe >= 150.0:
                    self.log(f"🔥 [불타기] 150% 돌파! 추가 투입!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 2

                # 3. 300% 불타기
                if step == 2 and roe >= 300.0:
                    self.log(f"🚀 [불타기] 300% 돌파! 극한 수익 모드!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', first_amount)
                    step = 3

                # 포지션 종료 확인 (사령관님이 직접 종료하거나 익절 시)
                s, amt = self.get_active_symbol()
                if not s:
                    self.log("🏁 상황 종료. 지체 없이 다음 타겟을 정찰합니다.")
                    break
                time.sleep(10)

        except Exception as e:
            self.log(f"⚠️ 작전 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 무한 스트라이커 발진! (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            symbol, amt = self.get_active_symbol()
            
            if amt == 0:
                self.log("👀 정찰 중... 5% 이상 쏜 놈들 탐색...")
                tickers = self.ex.fetch_tickers()
                candidates = []
                for s, t in tickers.items():
                    if s.endswith('/USDT:USDT'):
                        if abs(t.get('percentage', 0)) >= 5.0:
                            candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                
                for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                    side, price = self.check_v80_signal(cand['s'])
                    if side:
                        self.execute_mission(cand['s'], side, price)
                        break # 한 작전 끝나면 루프에 의해 다시 여기로 와서 정찰함
            time.sleep(15)

if __name__ == "__main__":
    V80_Infinite_Striker().run()
