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
                if float(p.get('positionAmt', 0)) != 0:
                    return p['symbol'].replace('USDT', '/USDT:USDT'), float(p['positionAmt'])
            return None, 0
        except: return None, 0

    def check_v80_signal(self, symbol):
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            if not ohlcv or len(ohlcv) < 60: return None, 0
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            
            # [사령관님 긴급 수정] 20-60 이격 2.5% (적절한 타협점)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            curr_gap = abs(curr - ma20) / ma20 * 100

            if ma_gap <= 2.5 and curr_gap <= 2.5:
                if ma5 > ma20 > ma60 and curr > ma20:
                    self.log(f"💎 [적정타점] {symbol} (이격: {ma_gap:.2f}%)")
                    return "LONG", curr
                elif ma5 < ma20 < ma60 and curr < ma20:
                    self.log(f"💀 [적정타점] {symbol} (이격: {ma_gap:.2f}%)")
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3 
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [진격] {symbol} {side} 사격 성공!")

            # 퍼센트 기반 방패 (ROE -35%)
            stop_price = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            params = {'stopPrice': stop_price, 'reduceOnly': True, 'workingType': 'MARK_PRICE'}
            
            for i in range(5):
                try:
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)
                    self.log(f"🛡️ [방패] 스탑로스 완료: {stop_price}")
                    break
                except:
                    time.sleep(2)

            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_p = ticker['last']
                roe = ((curr_p - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_p) / entry_price * 100 * self.leverage)

                if roe <= -35.0:
                    self.log(f"🚨 [손절] 1차분 삭제.")
                    break 

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
                time.sleep(15)
        except Exception as e:
            self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 중도파 엔진 가동! (2.5% 이격 필터)")
        while True:
            try:
                symbol, amt = self.get_active_symbol()
                if amt == 0:
                    tickers = self.ex.fetch_tickers()
                    candidates = []
                    for s, t in tickers.items():
                        if s.endswith('/USDT:USDT') and t.get('percentage') is not None:
                            if abs(t['percentage']) >= 5.0:
                                candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                    
                    for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                        side, price = self.check_v80_signal(cand['s'])
                        if side:
                            self.execute_mission(cand['s'], side, price)
                            break
                time.sleep(15)
            except Exception as e:
                self.log(f"⚠️ 메인 루프 에러 방어: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Infinite_Striker().run()
    
