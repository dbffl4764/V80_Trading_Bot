import ccxt, time, os, pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class V80_Final_Survivor:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 20
        self.target_roe = 100.0
        self.trailing_percent = 1.0  # 고점 대비 1% 하락 시 익절

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}")

    def run(self):
        self.log("🚀 130불 복구 엔진 최종 기동 (10% 변동성 필터 적용)")
        while True:
            try:
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 10: break

                tickers = self.ex.fetch_tickers()
                # [사령관님 지침] 10% 이상 변동 종목만 추출
                targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and abs(t.get('percentage', 0)) >= 10.0]
                targets = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:15]

                for s in targets:
                    o = self.ex.fetch_ohlcv(s, '5m', limit=65)
                    df = pd.DataFrame(o, columns=['t','o','h','l','c','v'])
                    c = df['c']
                    m5, m20, m60 = c.rolling(5).mean().iloc[-1], c.rolling(20).mean().iloc[-1], c.rolling(60).mean().iloc[-1]
                    curr, gap = c.iloc[-1], abs(m20 - m60) / m60 * 100

                    # V80 진입 조건 체크
                    if 3.5 <= gap <= 15.0:
                        side = None
                        if m5 > m20 > m60 and curr > m5: side = 'buy'
                        elif m60 > m20 > m5 and curr < m5: side = 'sell'
                        
                        if side:
                            self.ex.set_leverage(self.leverage, s)
                            amt = float(self.ex.amount_to_precision(s, (bal * 0.9 * self.leverage) / curr))
                            self.ex.create_market_order(s, side, amt)
                            
                            # SL -35% 예약
                            sl_p = curr * (1-0.0175) if side == 'buy' else curr * (1+0.0175)
                            self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == 'buy' else 'buy', 
                                                 amt, None, {'stopPrice': self.ex.price_to_precision(s, sl_p), 'reduceOnly': True})
                            self.log(f"⚔️ {s} {side.upper()} 진입 (변동률 확인됨)")

                            high_p, half_taken = curr, False
                            while True:
                                time.sleep(3)
                                now_p = self.ex.fetch_ticker(s)['last']
                                pos = [p for p in self.ex.fetch_balance()['info']['positions'] if p['symbol'].replace('USDT', '/USDT:USDT') == s]
                                c_amt = abs(float(pos[0]['positionAmt'])) if pos else 0
                                if c_amt == 0: break

                                roe = ((now_p - curr) / curr * 100 * self.leverage) if side == 'buy' else ((curr - now_p) / curr * 100 * self.leverage)
                                high_p = max(high_p, now_p) if side == 'buy' else min(high_p, now_p)

                                if not half_taken and roe >= self.target_roe:
                                    h_amt = float(self.ex.amount_to_precision(s, c_amt / 2))
                                    self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', h_amt, {'reduceOnly': True})
                                    half_taken = True
                                    self.log("💰 [1차 익절] 100% 달성 완료!")

                                if half_taken:
                                    drop = (high_p - now_p) / high_p * 100 if side == 'buy' else (now_p - high_p) / high_p * 100
                                    if drop >= self.trailing_percent:
                                        self.ex.create_market_order(s, 'sell' if side == 'buy' else 'buy', abs(float(pos[0]['positionAmt'])), {'reduceOnly': True})
                                        self.log(f"🏁 [최종 익절] 고점 대비 1% 하락 정리. ROE: {roe:.2f}%")
                                        break
                            break
                time.sleep(20)
            except Exception as e:
                print(f"관리 중: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Final_Survivor().run()
