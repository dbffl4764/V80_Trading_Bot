# 1. 기존 프로세스 완전 종료
sudo pkill -9 -f python3

# 2. main.py 파일을 깨끗한 코드로 강제 덮어쓰기 (들여쓰기 완벽 교정)
cat << 'EOF' > main.py
import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_IronClad_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.stop_loss_roe = -35.0
        self.half_profit_roe = 100.0
        self.trail_percent = 1.0
        self.half_profit_taken = False
        self.highest_price = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def check_v80_signal(self, symbol):
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            m5 = df['c'].rolling(5).mean().iloc[-1]
            m20 = df['c'].rolling(20).mean().iloc[-1]
            m60 = df['c'].rolling(60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            ma_gap = abs(m20 - m60) / m60 * 100
            if 3.5 <= ma_gap <= 15.0:
                if m5 > m20 > m60 and curr > m5: return "LONG", curr
                if m60 > m20 > m5 and curr < m5: return "SHORT", curr
            return None, curr
        except: return None, 0

    def execute_mission(self, symbol, side, entry_price):
        try:
            self.ex.set_leverage(self.leverage, symbol)
            bal = float(self.ex.fetch_balance()['total']['USDT'])
            max_pos = 1 if bal < 3000 else (2 if bal < 5000 else (3 if bal < 10000 else 5))
            amount = float(self.ex.amount_to_precision(symbol, (bal * 0.4 / max_pos * self.leverage) / entry_price))
            
            self.ex.create_market_order(symbol, 'buy' if side == "LONG" else 'sell', amount)
            sl_p = entry_price * (1 - 0.0175) if side == "LONG" else entry_price * (1 + 0.0175)
            self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', amount, None, {'stopPrice': self.ex.price_to_precision(symbol, sl_p), 'reduceOnly': True})
            
            self.half_profit_taken = False
            self.highest_price = entry_price
            self.log(f"⚔️ {symbol} {side} 진입완료 (SL: {sl_p})")

            while True:
                time.sleep(3)
                ticker = self.ex.fetch_ticker(symbol); curr = ticker['last']
                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == symbol]
                if not pos or abs(float(pos[0]['positionAmt'])) == 0: break
                
                roe = ((curr - entry_price) / entry_price * 100 * self.leverage) if side == "LONG" else ((entry_price - curr) / entry_price * 100 * self.leverage)
                if side == "LONG": self.highest_price = max(self.highest_price, curr)
                else: self.highest_price = min(self.highest_price, curr)

                if not self.half_profit_taken and roe >= self.half_profit_roe:
                    self.ex.cancel_all_orders(symbol)
                    half_qty = float(self.ex.amount_to_precision(symbol, abs(float(pos[0]['positionAmt'])) / 2))
                    self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', half_qty, {'reduceOnly': True})
                    safe_p = entry_price * 1.025 if side == "LONG" else entry_price * 0.975
                    self.ex.create_order(symbol, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', half_qty, None, {'stopPrice': self.ex.price_to_precision(symbol, safe_p), 'reduceOnly': True})
                    self.half_profit_taken = True
                    self.log(f"💰 반익절 완료! 방어선 구축.")

                if self.half_profit_taken:
                    drop = (self.highest_price - curr) / self.highest_price * 100 if side == "LONG" else (curr - self.highest_price) / self.highest_price * 100
                    if drop >= self.trail_percent:
                        self.ex.create_market_order(symbol, 'sell' if side == "LONG" else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                        self.log(f"🏁 고점대비 1% 하락 익절! ROE: {roe:.2f}%")
                        break
        except Exception as e: self.log(f"⚠️ 에러: {e}")

    def run(self):
        self.log("🛡️ V80 Iron-Clad 가동 시작")
        while True:
            try:
                tickers = self.ex.fetch_tickers()
                targets = sorted([s for s, t in tickers.items() if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0], key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:15]
                for s in targets:
                    side, price = self.check_v80_signal(s)
                    if side: self.execute_mission(s, side, price); break
                time.sleep(20)
            except Exception as e: print(e); time.sleep(10)

if __name__ == "__main__":
    V80_IronClad_Striker().run()
EOF

# 3. 백그라운드 실행
nohup python3 -u main.py > binance.out 2>&1 &

# 4. 로그 확인
tail -f binance.out
