sudo pkill -9 -f python3
rm -f binance.out

cat << 'EOF' > main.py
import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Survivor:
    def __init__(self):
        self.ex = ccxt.binance({'apiKey': os.getenv('BINANCE_API_KEY'), 'secret': os.getenv('BINANCE_SECRET_KEY'), 'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        self.leverage = 20
        self.half_taken = False
        self.high_p = 0

    def log(self, msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def run(self):
        self.log("🔥 130불 전원 사격 준비 완료.")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 10: break
                
                ts = self.ex.fetch_tickers()
                targets = sorted([s for s, t in ts.items() if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 8.0], key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:20]
                
                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=60)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    m5, m20, m60 = df['c'].rolling(5).mean().iloc[-1], df['c'].rolling(20).mean().iloc[-1], df['c'].rolling(60).mean().iloc[-1]
                    curr, gap = df['c'].iloc[-1], abs(m20 - m60) / m60 * 100
                    
                    if 3.5 <= gap <= 15.0 and ((m5 > m20 > m60 and curr > m5) or (m60 > m20 > m5 and curr < m5)):
                        side = "buy" if m5 > m20 else "sell"
                        self.ex.set_leverage(self.leverage, s)
                        amt = float(self.ex.amount_to_precision(s, (bal * 0.95 * self.leverage) / curr))
                        self.ex.create_market_order(s, side, amt)
                        
                        sl = curr * (1-0.0175) if side == "buy" else curr * (1+0.0175)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "buy" else 'buy', amt, None, {'stopPrice': self.ex.price_to_precision(s, sl), 'reduceOnly': True})
                        self.log(f"⚔️ {s} {side.upper()} 진입! (총알: {bal:.1f}불)")
                        
                        self.half_taken, self.high_p = False, curr
                        while True:
                            time.sleep(2)
                            t_info = self.ex.fetch_ticker(s); now_p = t_info['last']
                            pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                            c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                            if c_amt == 0: break
                            
                            roe = ((now_p - curr) / curr * 100 * self.leverage) if side == "buy" else ((curr - now_p) / curr * 100 * self.leverage)
                            self.high_p = max(self.high_p, now_p) if side == "buy" else min(self.high_p, now_p)
                            
                            if not self.half_taken and roe >= 100.0:
                                h_amt = float(self.ex.amount_to_precision(s, c_amt / 2))
                                self.ex.create_market_order(s, 'sell' if side == "buy" else 'buy', h_amt, {'reduceOnly': True})
                                self.half_taken = True
                                self.log("💰 100% 돌파! 반익절 완료.")
                            
                            if self.half_taken:
                                drop = (self.high_p - now_p) / self.high_p * 100 if side == "buy" else (now_p - self.high_p) / self.high_p * 100
                                if drop >= 1.0:
                                    self.ex.create_market_order(s, 'sell' if side == "buy" else 'buy', c_amt, {'reduceOnly': True})
                                    self.log(f"🏁 고점대비 1% 하락 익절! ROE: {roe:.2f}%")
                                    break
                        break
                time.sleep(10)
            except Exception as e: print(e); time.sleep(10)

if __name__ == "__main__":
    V80_Survivor().run()
EOF

nohup python3 -u main.py > binance.out 2>&1 &
tail -f binance.out
