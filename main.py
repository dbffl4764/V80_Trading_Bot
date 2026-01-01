import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Full_Engine:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.consecutive_losses = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_target_candidates(self):
        """5% 이상 변동 종목 중 거래대금 상위 10개 정찰"""
        try:
            markets = self.ex.load_markets()
            tickers = self.ex.fetch_tickers()
            candidates = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT:USDT'):
                    if markets.get(symbol) and markets[symbol].get('active'):
                        change = ticker.get('percentage', 0)
                        # 상승/하락 관계없이 변동폭 5% 이상 감지
                        if abs(change) >= 5.0:
                            candidates.append({
                                'symbol': symbol,
                                'change': change,
                                'vol': ticker.get('quoteVolume', 0)
                            })
            return [c['symbol'] for c in sorted(candidates, key=lambda x: x['vol'], reverse=True)[:10]]
        except Exception as e:
            self.log(f"⚠️ 정찰 에러: {e}")
            return []

    def check_signal(self, symbol):
        """[핵심] 정배열 롱 / 역배열 숏 판독기"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(window=5).mean().iloc[-1]
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            ma60 = df['c'].rolling(window=60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            
            gap = abs(curr - ma20) / ma20 * 100

            # 유격 2.5% 이내일 때만 진입
            if gap <= 2.5:
                # 1. 정배열 (5 > 20 > 60) -> 롱(LONG)
                if ma5 > ma20 > ma60:
                    return "LONG", curr
                # 2. 역배열 (5 < 20 < 60) -> 숏(SHORT)
                elif ma5 < ma20 < ma60:
                    return "SHORT", curr
            return None, curr
        except:
            return None, 0

    def execute_3step(self, symbol, side, price):
        """40% 화력 3분할 거미줄 사격"""
        try:
            bal = self.ex.fetch_balance()
            usdt = bal['free'].get('USDT', 0)
            
            amount = (usdt * 0.4 / 3) / price # 1회분 수량
            
            if side == "LONG":
                self.log(f"🏹 [정배열 롱] {symbol} 1차 시장가 진입")
                self.ex.create_market_buy_order(symbol, amount)
                self.ex.create_limit_buy_order(symbol, amount, price * 0.99) # 2차 -1%
                self.ex.create_limit_buy_order(symbol, amount, price * 0.98) # 3차 -2%
                
            elif side == "SHORT":
                self.log(f"🎯 [역배열 숏] {symbol} 1차 시장가 진입")
                self.ex.create_market_sell_order(symbol, amount)
                self.ex.create_limit_sell_order(symbol, amount, price * 1.01) # 2차 +1%
                self.ex.create_limit_sell_order(symbol, amount, price * 1.02) # 3차 +2%
                
            self.log(f"✅ {symbol} {side} 3분할 거미줄 설치 완료")
        except Exception as e:
            self.log(f"⚠️ 주문 실패: {e}")

    def run(self):
        self.log(f"⚔️ V80 엔진 재가동 (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            try:
                symbols = self.get_target_candidates()
                for s in symbols:
                    side, price = self.check_signal(s)
                    if side:
                        self.execute_3step(s, side, price)
                        time.sleep(600) # 진입 후 관찰
                time.sleep(20)
            except Exception as e:
                self.log(f"⚠️ 시스템 오류: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Full_Engine().run()
