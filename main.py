import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# .env 파일에서 API 키 불러오기
load_dotenv()

class V80_PC_Striker:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.half_taken = False
        self.high_p = 0

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}")

    def run(self):
        self.log("🚀 130불 복구 엔진 가동 (윈도우 PC용)")
        while True:
            try:
                # 잔고 확인 및 거래량 상위 종목 감시
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                ts = self.ex.fetch_tickers()
                targets = sorted([s for s, t in ts.items() if s.endswith('/USDT:USDT')], 
                                key=lambda x: ts[x].get('quoteVolume', 0), reverse=True)[:10]
                
                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=65)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    curr = c.iloc[-1]
                    
                    # V80 정배열/역배열 포착
                    if (m5 > m20 > m60 and curr > m5) or (m60 > m20 > m5 and curr < m5):
                        side = 'buy' if m5 > m20 else 'sell'
                        self.ex.set_leverage(self.leverage, s)
                        
                        # 130불 잔고의 90% 사격
                        amt = float(self.ex.amount_to_precision(s, (bal * 0.9 * self.leverage) / curr))
                        self.ex.create_market_order(s, side, amt)
                        
                        # 손절 예약 (-35% ROE 지점)
                        sl = curr * (1-0.0175) if side == 'buy' else curr * (1+0.0175)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', 
                                             amt, None, {'stopPrice': self.ex.price_to_precision(s, sl), 'reduceOnly': True})
                        
                        self.log(f"⚔️ {s} {side.upper()} 진입!")
                        
                        self.half_taken, self.high_p = False, curr
                        while True:
                            time.sleep(3)
                            now_p = self.ex.fetch_ticker(s)['last']
                            pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                            if not pos or abs(float(pos[0]['positionAmt'])) == 0: break
                            
                            roe = ((now_p - curr) / curr * 100 * self.leverage) if side == 'buy' else ((curr - now_p) / curr * 100 * self.leverage)
                            self.high_p = max(self.high_p, now_p) if side == 'buy' else min(self.high_p, now_p)

                            # 100% 수익 시 반익절
                            if not self.half_taken and roe >= 100:
                                self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', amt/2, {'reduceOnly': True})
                                self.half_taken = True
                                self.log("💰 100% 달성! 반익절 완료.")

                            # 고점 대비 1% 하락 시 익절
                            if self.half_taken:
                                drop = (self.high_p - now_p) / self.high_p * 100 if side == 'buy' else (now_p - self.high_p) / self.high_p * 100
                                if drop >= 1.0:
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                                    self.log(f"🏁 1% 하락 익절 완료! ROE: {roe:.2f}%")
                                    break
                        break
                time.sleep(20)
            except Exception as e:
                print(f"오류 발생: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_PC_Striker().run()
