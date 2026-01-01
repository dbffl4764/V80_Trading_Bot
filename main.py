import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Profit_Master:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 {msg}", flush=True)

    def get_total_balance(self):
        try:
            return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        """[사령관님 특명] 이격은 열고 서열은 조여서 수익 극대화"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            if not ohlcv or len(ohlcv) < 60: return None, 0
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5, ma20, ma60 = df['c'].rolling(5).mean().iloc[-1], df['c'].rolling(20).mean().iloc[-1], df['c'].rolling(60).mean().iloc[-1]
            ma60_prev = df['c'].rolling(60).mean().iloc[-2]
            curr = df['c'].iloc[-1]
            
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            curr_gap = abs(curr - ma20) / ma20 * 100

            # 20-60 이격 5% 이내(응축 확인) & 가격 유격 6%까지 허용(가속 확인)
            if ma_gap <= 5.0 and curr_gap <= 6.0:
                # 롱: 5 > 20 > 60 완벽 서열 + 60선 우상향
                if (ma5 > ma20 > ma60) and (ma60 >= ma60_prev):
                    return "LONG", curr
                # 숏: 60 > 20 > 5 완벽 서열 + 60선 우하향
                elif (ma60 > ma20 > ma5) and (ma60 <= ma60_prev):
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            # 2000불 미만 1종목 화력 집중
            max_pos = 1 if total_bal < 3000 else 2
            
            firepower = (total_bal * 0.45) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [진격] {symbol} {side} 사격! 잔고: {total_bal:.2f}")

            # -35% 방패 예약
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': stop_p, 'reduceOnly': True})

            while True:
                ticker = self.ex.fetch_ticker(symbol)
                roe = ((ticker['last'] - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - ticker['last']) / entry_price * 100 * self.leverage)
                
                # 포지션 종료 확인 로직
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0:
                    if roe > 0 and total_bal >= 2000: self.log("💰 수익의 30%를 안전자산으로!")
                    break
                time.sleep(20)
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("⚔️ V80 PROFIT MASTER 가동! 수익을 가져오겠습니다.")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:10]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 5.0:
                        side, price = self.check_v80_signal(s)
                        if side: self.execute_mission(s, side, price); break
                time.sleep(20)
            except: time.sleep(10)

if __name__ == "__main__":
    V80_Profit_Master().run()
