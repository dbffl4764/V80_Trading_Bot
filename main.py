import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Aggressive_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 {msg}", flush=True)

    def get_total_balance(self):
        try:
            bal = self.ex.fetch_balance()
            return float(bal['total']['USDT'])
        except: return 0

    def get_active_positions_count(self):
        try:
            balance = self.ex.fetch_balance()
            positions = balance['info']['positions']
            return sum(1 for p in positions if float(p.get('positionAmt', 0)) != 0)
        except: return 0

    def check_v80_signal(self, symbol):
        """[사령관님 지침] 너무 촘촘하게 막지 말고 가속 구간 포착"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            if not ohlcv or len(ohlcv) < 60: return None, 0
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            ma60_prev = df['c'].rolling(60).mean().iloc[-2]
            curr = df['c'].iloc[-1]
            
            # 1. 20-60 이격: 5%까지 허용 (사령관님 지침 반영)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            
            # 2. 가격 유격: 20선에서 6%까지 벌어져도 추격 허용 (가속 포착)
            curr_gap = abs(curr - ma20) / ma20 * 100

            if ma_gap <= 5.0 and curr_gap <= 6.0:
                # 롱: 완벽 서열 + 60선 방향
                if ma5 > ma20 > ma60 and ma60 >= ma60_prev:
                    self.log(f"🔥 [롱 가속] {symbol} 진입 (이격: {ma_gap:.2f}%)")
                    return "LONG", curr
                # 숏: 완벽 서열 + 60선 방향
                elif ma60 > ma20 > ma5 and ma60 <= ma60_prev:
                    self.log(f"📉 [숏 가속] {symbol} 진입 (이격: {ma_gap:.2f}%)")
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            # 2000불 미만 1종목, 3000불부터 2종목 전략
            if total_bal < 3000: max_pos = 1
            elif total_bal < 5000: max_pos = 2
            else: max_pos = 3
            
            if self.get_active_positions_count() >= max_pos: return

            firepower = (total_bal * 0.4) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [진격] {symbol} {side} 사격!")

            # [방패] ROE -35% 스탑로스
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            params = {'stopPrice': stop_p, 'reduceOnly': True, 'workingType': 'MARK_PRICE'}
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)

            while True:
                ticker = self.ex.fetch_ticker(symbol)
                roe = ((ticker['last'] - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - ticker['last']) / entry_price * 100 * self.leverage)
                if roe <= -35.0: break 
                
                # 포지션 종료 확인
                bal = self.ex.fetch_balance()
                pos = [p for p in bal['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0:
                    # 2000불 전까지는 안전자산 전환 없음!
                    if roe > 0: self.log(f"💰 수익 종료! 현재 자산: {total_bal:.2f} (목표: 2000불)")
                    break
                time.sleep(20)
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 가속 엔진 기동! (화력 개방 모드)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                candidates = []
                for s, t in tickers.items():
                    if s.endswith('/USDT:USDT') and t.get('percentage') is not None:
                        if abs(t['percentage']) >= 5.0: # 5% 변동성 기준 준수
                            candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                
                for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                    side, price = self.check_v80_signal(cand['s'])
                    if side:
                        self.execute_mission(cand['s'], side, price)
                        break
                time.sleep(20)
            except: time.sleep(10)

if __name__ == "__main__":
    V80_Aggressive_Striker().run()
