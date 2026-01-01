import ccxt, time, os, pandas as pd
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
        self.leverage = 20  # [수정] 레버리지 20배
        self.target_roe = 100.0  # [수정] 1차 목표 100%
        self.stop_loss_roe = -35.0
        self.max_entry_count = 3
        self.half_profit_taken = False
        self.highest_price = 0 # [추가] 고점 추적용

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
            self.half_profit_taken = False
            self.highest_price = entry_price
            total_bal = self.get_total_balance()
            
            # 사령관님 자산 지침 반영
            if total_bal < 3000: max_pos = 1
            elif total_bal < 5000: max_pos = 2
            elif total_bal < 10000: max_pos = 3
            else: max_pos = 5
            
            firepower = ((total_bal * 0.45) / max_pos) / self.max_entry_count
            self.ex.set_leverage(self.leverage, symbol)

            # [사령관님 원본] 3회 분할 사격 로직 유지
            for entry_num in range(1, self.max_entry_count + 1):
                amount = float(self.ex.amount_to_precision(symbol, (firepower * self.leverage) / entry_price))
                self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
                self.log(f"🎯 [사격] {symbol} {side} {entry_num}차 진입!")
                if entry_num == 1:
                    sl_p = entry_price * (1 - 0.0175) if side == "LONG" else entry_price * (1 + 0.0175)
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         amount * self.max_entry_count, None, {'stopPrice': self.ex.price_to_precision(symbol, sl_p), 'reduceOnly': True})
                time.sleep(1)

            while True:
                time.sleep(3)
                ticker = self.ex.fetch_ticker(symbol); curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                current_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                if current_amt == 0: break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                
                # 고점 갱신
                if side == "LONG": self.highest_price = max(self.highest_price, curr)
                else: self.highest_price = min(self.highest_price, curr)

                # 1. ROE 100% 시 반익절 (서버 방어선 구축)
                if not self.half_profit_taken and roe >= 100.0:
                    self.ex.cancel_all_orders(symbol)
                    half_amt = float(self.ex.amount_to_precision(symbol, current_amt / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_amt, {'reduceOnly': True})
                    
                    # 수익 방어선 (ROE 50% 지점)
                    safe_p = entry_price * 1.025 if side == "LONG" else entry_price * 0.975
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', 
                                         half_amt, None, {'stopPrice': self.ex.price_to_precision(symbol, safe_p), 'reduceOnly': True})
                    self.half_profit_taken = True
                    self.log(f"💰 [1차 익절] 100% 달성! 절반 던지고 방어선 구축.")

                # 2. 고점 대비 1% 하락 시 전량 익절 (Trailing)
                if self.half_profit_taken:
                    drop = (self.highest_price - curr) / self.highest_price * 100 if side == "LONG" else (curr - self.highest_price) / self.highest_price * 100
                    if drop >= 1.0:
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', current_amt, {'reduceOnly': True})
                        self.log(f"🏁 [최종 익절] 고점대비 1% 하락 정리! ROE: {roe:.2f}%")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log(f"⚔️ V80 [20배/익절강화] 가동.")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                for s, t in sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)[:25]:
                    if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0:
                        side, price = self.check_v80_signal(s)
                        if side: self.execute_mission(s, side, price); break
                time.sleep(15)
            except Exception as e: self.log(f"⚠️ 에러: {e}"); time.sleep(10)

if __name__ == "__main__":
    V80_5M_Striker().run()
