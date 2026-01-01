\import ccxt, time, os, pandas as pd, numpy as np
from datetime import datetime

class V80_Elite_Pure_Force:
    def __init__(self):
        # 구글 클라우드 콘솔에 직접 입력하신 환경변수를 읽어옵니다.
        # (혹은 '키값'을 직접 따옴표 안에 넣으셔도 됩니다)
        self.ex = ccxt.binance({
            'apiKey': os.environ.get('BINANCE_API_KEY', '여기에_직접_입력하셔도_됨'),
            'secret': os.environ.get('BINANCE_SECRET_KEY', '여기에_직접_입력하셔도_됨'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        
        # [사령관님 지침] 2000불 돌파 전까지 레버리지 5배 고정
        self.leverage = 5 

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] 🧬 {msg}", flush=True)

    def check_v80_signal(self, symbol):
        """[사령관님 혈통 로직] 15분봉 정배열/역배열 태동 포착"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=60)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            ma5 = df['c'].rolling(5).mean()
            ma20 = df['c'].rolling(20).mean()
            ma60 = df['c'].rolling(60).mean()
            
            c_ma5, p_ma5 = ma5.iloc[-1], ma5.iloc[-2]
            c_ma20, p_ma20 = ma20.iloc[-1], ma20.iloc[-2]
            c_ma60 = ma60.iloc[-1]
            curr = df['c'].iloc[-1]

            # [응축/수렴 필터] 사령관님 병법의 핵심 (3.5% & 2.5%)
            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                # ✨ 정배열 막 탄생 (롱 타점)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr
                # 🌑 역배열 막 탄생 (숏 타점)
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr
            return None, curr
        except:
            return None, 0

    def run(self):
        self.log("⚔️ V80 ELITE PURE FORCE 가동 (13불 부활 작전)")
        while True:
            try:
                # 잔고 확인 (구글 클라우드 환경에서 API 연결 테스트 겸용)
                bal = float(self.ex.fetch_balance()['total']['USDT'])
                if bal < 5: 
                    self.log("⚠️ 시드 부족... 작전 종료"); break

                # [지침] 13불일 때는 무조건 1종목 집중
                max_pos = 1 if bal < 3000 else 2

                # [지침] 변동성 5% 이상 + 거래량 상위 10개 추출
                tickers = self.ex.fetch_tickers()
                targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                           and abs(t.get('percentage', 0)) >= 5.0]
                
                top_10 = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]

                for s in top_10:
                    side, price = self.check_v80_signal(s)
                    if side:
                        self.ex.set_leverage(self.leverage, s)
                        # 화력 45% 사격
                        qty = float(self.ex.amount_to_precision(s, (bal * 0.45 * self.leverage) / price))
                        
                        # [지침] 1.75% 칼손절 예약 (방패)
                        sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                        
                        self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                        self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                        
                        self.log(f"🎯 [사격 완료] {s} {side} 진입 (잔고: {bal:.2f})")
                        time.sleep(600) # 10분 관망
                        break
                
                time.sleep(20) # 스캔 주기
            except Exception as e:
                self.log(f"⚠️ 시스템 오류 보정: {e}")
                time.sleep(15)

if __name__ == "__main__":
    V80_Elite_Pure_Force().run()
