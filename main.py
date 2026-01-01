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
        """[이격도 철저 검증] 20-60이 멀면 5-20이 아무리 좋아도 절대 금지"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            
            # 1. 20선과 60선의 이격도 계산 (사령관님 최우선 지침)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            
            # 2. 현재가와 20선(생명선)의 유격 계산
            curr_gap = abs(curr - ma20) / ma20 * 100

            # [사령관님 명령 반영]
            # 조건 1: 20-60 간격이 '초촘촘'(2% 이내)해야만 함
            # 조건 2: 그 상태에서 현재가가 20선에 붙어야 함(2.5% 이내)
            # 조건 3: 서열이 완벽해야 함
            
            if ma_gap <= 2.0: # 1순위: 20-60이 벌어지면 여기서 바로 탈락!
                if curr_gap <= 2.5: # 2순위: 20선 근처일 때
                    # 롱 조건: 5 > 20 > 60
                    if ma5 > ma20 and ma20 > ma60 and curr > ma20:
                        self.log(f"💎 [수렴타격] {symbol} (20-60이격: {ma_gap:.2f}% / 초촘촘)")
                        return "LONG", curr
                    # 숏 조건: 5 < 20 < 60
                    elif ma5 < ma20 and ma20 < ma60 and curr < ma20:
                        self.log(f"💀 [수렴타격] {symbol} (20-60이격: {ma_gap:.2f}% / 초촘촘)")
                        return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3 
            raw_amount = (firepower * self.leverage) / entry_price
            amount = float(self.ex.amount_to_precision(symbol, raw_amount))
            
            self.log(f"🎯 [진격] {symbol} {side} 사격! (화력: {firepower:.2f}USDT)")
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            
            # [방패] ROE -35% 시스템 스탑로스 예약
            stop_percent = 0.35 / self.leverage
            raw_stop = entry_price * (1 - stop_percent) if side == "LONG" else entry_price * (1 + stop_percent)
            stop_price = float(self.ex.price_to_precision(symbol, raw_stop))
            
            params = {'stopPrice': stop_price, 'reduceOnly': True}
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)
            self.log(f"🛡️ [방패] 스탑로스 예약 완료: {stop_price}")

            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_price = ticker['last']
                roe = ((curr_price - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_price) / entry_price * 100 * self.leverage)

                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 삭제!")
                    break 

                if step == 1 and roe >= 150.0:
                    self.log(f"🔥 [불타기] 150% 돌파! 2차 투입!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    step = 2
                elif step == 2 and roe >= 300.0:
                    self.log(f"🚀 [불타기] 300% 돌파! 극한 수익!")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    step = 3

                s, amt = self.get_active_symbol()
                if not s: break
                time.sleep(10)
        except Exception as e:
            self.log(f"⚠️ 작전 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 최종 스트라이커 발진! (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            try:
                symbol, amt = self.get_active_symbol()
                if amt == 0:
                    tickers = self.ex.fetch_tickers()
                    candidates = []
                    for s, t in tickers.items():
                        if s.endswith('/USDT:USDT'):
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
