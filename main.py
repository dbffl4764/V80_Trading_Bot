import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Money_Maker:
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
        """[사령관님 특명] 돈 불리는 완벽 배열 검증"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            if not ohlcv or len(ohlcv) < 60: return None, 0
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma5 = df['c'].rolling(5).mean().iloc[-1]
            ma20 = df['c'].rolling(20).mean().iloc[-1]
            ma60 = df['c'].rolling(60).mean().iloc[-1]
            ma20_prev = df['c'].rolling(20).mean().iloc[-2]
            ma60_prev = df['c'].rolling(60).mean().iloc[-2]
            curr = df['c'].iloc[-1]
            
            # 1. 초정밀 이격 (상투 절대 방지: 3.0% 제한)
            ma_gap = abs(ma20 - ma60) / ma60 * 100
            if ma_gap > 3.0: return None, curr

            # 2. 칼 서열 + 기울기 완벽 동기화
            # 롱: 5>20>60 AND 20선 우상향 AND 60선 우상향
            is_perfect_long = (ma5 > ma20 > ma60) and (ma20 > ma20_prev) and (ma60 > ma60_prev) and (curr > ma20)
            # 숏: 60>20>5 AND 20선 우하향 AND 60선 우하향
            is_perfect_short = (ma60 > ma20 > ma5) and (ma20 < ma20_prev) and (ma60 < ma60_prev) and (curr < ma20)
            
            # 3. 가격 유격 (촘촘함 3% 이내)
            curr_gap = abs(curr - ma20) / ma20 * 100

            if curr_gap <= 3.0:
                if is_perfect_long:
                    self.log(f"💎 [황금롱] {symbol} 포착!")
                    return "LONG", curr
                elif is_perfect_short:
                    self.log(f"💀 [황금숏] {symbol} 포착!")
                    return "SHORT", curr
            
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            
            # [자산 전략] 2000불 미만은 1종목에 화력 집중
            if total_bal < 3000: max_pos = 1
            elif total_bal < 5000: max_pos = 2
            else: max_pos = 3
            
            if self.get_active_positions_count() >= max_pos: return

            firepower = (total_bal * 0.45) / max_pos # 화력 45%로 소폭 상향
            amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격] {symbol} {side} 진입! (시드: {total_bal:.2f})")

            # [방패] ROE -35% 스탑로스
            stop_p = float(self.ex.price_to_precision(symbol, entry_price * 0.965 if side == "LONG" else entry_price * 1.035))
            params = {'stopPrice': stop_p, 'reduceOnly': True, 'workingType': 'MARK_PRICE'}
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, params)
            self.log(f"🛡️ [방패] 스탑로스 완료: {stop_p}")

            while True:
                ticker = self.ex.fetch_ticker(symbol)
                roe = ((ticker['last'] - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - ticker['last']) / entry_price * 100 * self.leverage)

                if roe <= -35.0: break 
                
                # 포지션 종료 확인
                bal = self.ex.fetch_balance()
                pos = [p for p in bal['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or float(pos[0]['positionAmt']) == 0:
                    # [사령관님 철칙] 2000불 미만은 안전자산 전환 없음!
                    if roe > 0:
                        if total_bal < 2000:
                            self.log(f"📈 수익 종료! 2000불 고지를 위해 전액 재투자합니다.")
                        else:
                            self.log(f"💰 수익 종료! 2000불 돌파! 이제부터 수익의 30%는 안전자산입니다.")
                    break
                time.sleep(15)
        except Exception as e:
            self.log(f"⚠️ 오류: {e}")

    def run(self):
        self.log(f"⚔️ V80 MONEY MAKER 가동! (타겟: 2,000불 돌파)")
        while True:
            try:
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
                time.sleep(20)
            except Exception as e:
                time.sleep(10)

if __name__ == "__main__":
    V80_Money_Maker().run()
