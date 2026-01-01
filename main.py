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
            
            # 20-60 이격 (사령관님 명령: 아주 촘촘하게 1.5%)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            curr_gap = abs(curr - ma20) / ma20 * 100

            if ma_gap <= 1.5: 
                if curr_gap <= 2.5:
                    if ma5 > ma20 > ma60 and curr > ma20:
                        return "LONG", curr
                    elif ma5 < ma20 < ma60 and curr < ma20:
                        return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            # 1. 진입
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3 
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            order = self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [진격] {symbol} {side} 사격!")

            # 2. [퍼센트 기반 방패] 진입가 기준 -3.5% 지점 (ROE -35%)
            # 가격 계산 후 바이낸스 정밀도에 맞춰 바로 전송
            stop_price = self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035)
            
            # 3. 방패 예약 (실패 시 무한 재시도)
            params = {'stopPrice': stop_price, 'reduceOnly': True, 'workingType': 'MARK_PRICE'}
            while True:
                try:
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)
                    self.log(f"🛡️ [방패] ROE -35% 지점 예약 완료 ({stop_price})")
                    break
                except Exception as e:
                    self.log(f"🚨 방패 예약 재시도 중... {e}")
                    time.sleep(1)

            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_p = ticker['last']
                roe = ((curr_p - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_p) / entry_price * 100 * self.leverage)

                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 삭제!")
                    break 

                # 불타기
                if step == 1 and roe >= 150.0:
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    self.log(f"🔥 [불타기] 150% 돌파!")
                    step = 2
                elif step == 2 and roe >= 300.0:
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    self.log(f"🚀 [불타기] 300% 돌파!")
                    step = 3

                s, amt = self.get_active_symbol()
                if not s: break
                time.sleep(10)
        except Exception as e:
            self.log(f"⚠️ 작전 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 최종 스트라이커 발진! (20-60 촘촘 필터 장착)")
        while True:
            try:
                symbol, amt = self.get_active_symbol()
                if amt == 0:
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
                            break
                time.sleep(15)
            except Exception as e:
                self.log(f"⚠️ 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Infinite_Striker().run()
