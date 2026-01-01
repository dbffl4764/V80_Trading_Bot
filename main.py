import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_5M_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 10
        self.target_roe = 30.0 
        self.stop_loss_roe = -35.0 # 레버리지 10배 기준 -3.5% 변동 시 칼손절

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def get_total_balance(self):
        try: return float(self.ex.fetch_balance()['total']['USDT'])
        except: return 0

    def check_v80_signal(self, symbol):
        try:
            o5 = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            df5 = pd.DataFrame(o5, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            m5 = df5['c'].rolling(5).mean().iloc[-1]
            m20 = df5['c'].rolling(20).mean().iloc[-1]
            m60 = df5['c'].rolling(60).mean().iloc[-1]
            curr = df5['c'].iloc[-1]
            vol_avg = df5['v'].rolling(10).mean().iloc[-1]
            ma_gap = abs(m20 - m60) / m60 * 100

            if 3.5 <= ma_gap <= 15.0: 
                if m5 > m20 > m60 and curr > m5 and df5['v'].iloc[-1] > vol_avg:
                    return "LONG", curr
                if m60 > m20 > m5 and curr < m5 and df5['v'].iloc[-1] > vol_avg:
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            total_bal = self.get_total_balance()
            max_pos = 1 if total_bal < 3000 else 2
            firepower = (total_bal * 0.45) / max_pos
            
            # 수량 계산 시 정밀도 강화
            raw_amount = (firepower * self.leverage) / entry_price
            amount = float(self.ex.amount_to_precision(symbol, raw_amount))
            
            # 1. 포지션 진입
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            self.log(f"🎯 [사격] {symbol} {side} 진입! (가격: {entry_price})")

            # 2. 서버 측 STOP_MARKET 주문 (강력 권장)
            try:
                stop_price_val = entry_price * 0.965 if side == "LONG" else entry_price * 1.035
                stop_p = float(self.ex.price_to_precision(symbol, stop_price_val))
                self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                     amount, None, {'stopPrice': stop_p, 'reduceOnly': True})
                self.log(f"🛡️ [서버 손절 걸기] 완료: {stop_p}")
            except Exception as e:
                self.log(f"⚠️ 서버 손절 주문 실패(봇 내부 감시로 대체): {e}")

            # 3. 실시간 감시 루프 (익절 & 봇 내부 강제 손절)
            while True:
                time.sleep(10)
                ticker = self.ex.fetch_ticker(symbol)
                curr = ticker['last']
                
                # 포지션 상태 확인
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                current_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                
                if current_amt == 0: 
                    self.log(f"🏁 {symbol} 작전 종료(체결됨).")
                    break
                
                # ROE 계산
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                # [손절 방어선] 서버 주문 실패 대비 봇이 직접 시장가로 던짐
                if roe <= self.stop_loss_roe:
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                    self.log(f"🚨 [강제 손절] ROE {roe:.2f}% 도달! 시장가 탈출!")
                    break

                # [익절 라인]
                if roe > self.target_roe:
                    ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=5)
                    ma5 = pd.Series([x[4] for x in ohlcv]).mean()
                    if (side == "LONG" and curr < ma5) or (side == "SHORT" and curr > ma5):
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                        self.log(f"💰 [익절] ROE: {roe:.2f}% | 30% 안전자산 이체!")
                        break

        except Exception as e: self.log(f"⚠️ 미션 실행 에러: {e}")

    def run(self):
        self.log("⚔️ V80 [손절방어 강화] 버전 가동.")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:25]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0:
                        side, price = self.check_v80_signal(s)
                        if side: 
                            self.execute_mission(s, side, price)
                            break
                time.sleep(15)
            except Exception as e: 
                self.log(f"⚠️ 루프 에러: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_5M_Striker().run()
