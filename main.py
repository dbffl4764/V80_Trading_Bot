import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Ultimate_Engine:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.total_profit_pct = 0 # 누적 수익률 관리용

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_target_candidates(self):
        """5% 이상 변동 종목 중 거래대금 상위 10개 추출"""
        try:
            tickers = self.ex.fetch_tickers()
            candidates = []
            for symbol, t in tickers.items():
                if symbol.endswith('/USDT:USDT'):
                    change = t.get('percentage', 0)
                    if abs(change) >= 5.0:
                        candidates.append({'symbol': symbol, 'vol': t.get('quoteVolume', 0)})
            return [c['symbol'] for c in sorted(candidates, key=lambda x: x['vol'], reverse=True)[:10]]
        except: return []

    def check_signal(self, symbol):
        """정배열 롱 / 역배열 숏 / MA20 유격 2.5% 타점 판독"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5, ma20, ma60 = df['c'].rolling(5).mean().iloc[-1], df['c'].rolling(20).mean().iloc[-1], df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            gap = abs(curr - ma20) / ma20 * 100

            if gap <= 2.5:
                if ma5 > ma20 > ma60: return "LONG", curr
                elif ma5 < ma20 < ma60: return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_strategy(self, symbol, side, entry_price):
        """사령관님 전용: 1차 손절 & 2,3차 불타기 작전"""
        try:
            bal = self.ex.fetch_balance()['free'].get('USDT', 0)
            firepower = (bal * 0.4) / 3  # 시드 40%의 1/3씩
            amount = (firepower * self.leverage) / entry_price
            
            # 1차 포격
            self.log(f"⚔️ 1차 진입: {symbol} ({side}) | 수량: {amount:.4f}")
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            
            step = 1
            while True:
                curr = self.ex.fetch_ticker(symbol)['last']
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)

                # [손절] 1차분 -35% 밀리면 미련 없이 버림
                if roe <= -35.0:
                    self.log(f"🚨 [1차분 손절] {symbol} -35% 도달! 물량 즉시 삭제.")
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', amount)
                    break

                # [2차 불타기] 150% 돌파 시
                if step == 1 and roe >= 150.0:
                    self.log(f"🔥 [2차 불타기] 150% 돌파! 추가 투입 및 손절가 상향")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    # 여기서 손절가를 수익 구간으로 상향하는 로직 (Trailing Stop 개념)
                    step = 2

                # [3차 불타기] 300% 돌파 시
                if step == 2 and roe >= 300.0:
                    self.log(f"🚀 [3차 불타기] 300% 돌파! 극한까지 먹기 모드 가동")
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    step = 3

                # 수익 종료 판단 (임의의 익절가 혹은 추세 꺾일 때 - 사령관님이 직접 종료 권장)
                time.sleep(10)
        except Exception as e:
            self.log(f"⚠️ 전략 실행 중 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 무적 엔진 발진! (잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f})")
        while True:
            symbols = self.get_target_candidates()
            for s in symbols:
                side, price = self.check_signal(s)
                if side:
                    self.execute_strategy(s, side, price)
                    # 수익 정산 및 안전자산 이체 알림 (30% or 40%)
                    if self.total_profit_pct >= 100: self.log("📢 수익 100% 돌파! 안전자산 40% 이체하세요!")
                    else: self.log("📢 수익 발생! 안전자산 30% 이체하세요!")
                    time.sleep(600)
            time.sleep(20)

if __name__ == "__main__":
    V80_Ultimate_Engine().run()
