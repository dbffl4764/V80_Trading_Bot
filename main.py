import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Perfect_Order_Striker:
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
        """[사령관님 특명] 칼 서열 엄수 + 이격도 5% 미만 + 예쁜 배열만 사격"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            if not ohlcv or len(ohlcv) < 60: return None, 0
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            ma60_prev = df['c'].rolling(60).mean().iloc[-2]
            curr = df['c'].iloc[-1]
            
            # 1. [칼 서열 검증] 사령관님이 지적하신 60>5>20 같은 혼조세 원천 차단
            is_long_order = (ma5 > ma20) and (ma20 > ma60)  # 정배열: 5 > 20 > 60
            is_short_order = (ma60 > ma20) and (ma20 > ma5) # 역배열: 60 > 20 > 5
            
            # 2. [이격도 검증] 20-60 이격 5% 이상 종목 제외 (저장 정보 반영)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            curr_gap = abs(curr - ma20) / ma20 * 100

            if ma_gap <= 3.5 and curr_gap <= 4.0: # 촘촘한 구간 우선
                # 롱: 서열 완벽 + 60선 우상향
                if is_long_order and ma60 > ma60_prev and curr > ma20:
                    self.log(f"💎 [칼배열 롱] {symbol} (이격: {ma_gap:.2f}%)")
                    return "LONG", curr
                # 숏: 서열 완벽 + 60선 우하향
                elif is_short_order and ma60 < ma60_prev and curr < ma20:
                    self.log(f"💀 [칼배열 숏] {symbol} (이격: {ma_gap:.2f}%)")
                    return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            
            # [전략 반영] 금액대별 종목 수 제한
            if total_bal < 2000: max_pos = 1
            elif total_bal < 3000: max_pos = 1 # 2000불까지 1종목
            elif total_bal < 5000: max_pos = 2 # 3000불부터 2종목
            elif total_bal < 10000: max_pos = 3 # 5000불부터 3종목
            else: max_pos = 5 # 1만불부터 5종목
            
            if self.get_active_positions_count() >= max_pos: return

            firepower = (total_bal * 0.4) / max_pos
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [진격] {symbol} {side} 사격! (화력: {firepower:.2f}USDT)")

            # [방패] ROE -35% 시스템 스탑로스
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            params = {'stopPrice': stop_p, 'reduceOnly': True, 'workingType': 'MARK_PRICE'}
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)
            self.log(f"🛡️ [방패] 스탑로스 완료: {stop_p}")

            step = 1
            while True:
                ticker = self.ex.fetch_ticker(symbol)
                curr_p = ticker['last']
                roe = ((curr_p - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr_p) / entry_price * 100 * self.leverage)

                if roe <= -35.0:
                    self.log(f"🚨 [손절] 작전 종료.")
                    break 

                if step == 1 and roe >= 150.0:
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    self.log(f"🔥 [불타기] 150% 돌파! 추가 투입!")
                    step = 2
                elif step == 2 and roe >= 300.0:
                    self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                    self.log(f"🚀 [불타기] 300% 돌파! 화력 집중!")
                    step = 3

                # 종료 확인 및 수익 시 30% 안전자산 규칙 알림
                bal = self.ex.fetch_balance()
                pos = [p for p in bal['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0:
                    if roe > 0: self.log(f"💰 수익 종료! [지침] 수익금의 30%를 안전자산으로 즉시 예치하십시오!")
                    break
                time.sleep(20)
        except Exception as e:
            self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 정예 스트라이커 가동! (잔고: {self.get_total_balance():.2f}USDT)")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                candidates = []
                for s, t in tickers.items():
                    if s.endswith('/USDT:USDT') and t.get('percentage') is not None:
                        if abs(t['percentage']) >= 5.0: # 5% 변동성 임계값 준수
                            candidates.append({'s': s, 'v': t.get('quoteVolume', 0)})
                
                for cand in sorted(candidates, key=lambda x: x['v'], reverse=True)[:10]:
                    side, price = self.check_v80_signal(cand['s'])
                    if side:
                        self.execute_mission(cand['s'], side, price)
                        break
                time.sleep(20)
            except Exception as e:
                time.sleep(10)

if __name__ == "__main__":
    V80_Perfect_Order_Striker().run()
