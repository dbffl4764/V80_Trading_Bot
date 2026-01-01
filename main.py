import ccxt
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 1. 끔끔하게(깔끔하게) 모든 파일을 이 하나로 통합했습니다.
# 2. v80_logic, v80_trade 등 외부 파일을 절대 참조하지 않아 경로 에러가 없습니다.

class V80_Ultimate_One_Body:
    def __init__(self):
        # 구글 클라우드 설정에 넣으신 API 키를 읽어옵니다.
        self.ex = ccxt.binance({
            'apiKey': os.environ.get('BINANCE_API_KEY'),
            'secret': os.environ.get('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        # [사령관님 지침] 2000불 미만 5배 레버리지 고정
        self.leverage = 5 

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧬 {msg}", flush=True)

    def v80_bloodline_logic(self, symbol):
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

            # [응축/수렴 필터] 3.5% & 2.5% 이내
            ma_gap = abs(c_ma20 - c_ma60) / c_ma60 * 100
            ma5_gap = abs(c_ma5 - c_ma20) / c_ma20 * 100

            if ma_gap <= 3.5 and ma5_gap <= 2.5:
                # 정배열 시작 (Long)
                if (p_ma5 <= p_ma20) and (c_ma5 > c_ma20 > c_ma60):
                    return "LONG", curr
                # 역배열 시작 (Short)
                elif (p_ma5 >= p_ma20) and (c_ma60 > c_ma20 > c_ma5):
                    return "SHORT", curr
            return None, curr
        except: return None, 0

    def run(self):
        self.log("⚔️ V80 통합 엔진 가동 (GCP 최적화 모드)")
        try:
            # 잔고 확인
            bal_info = self.ex.fetch_balance()
            total_bal = float(bal_info['total']['USDT'])
            if total_bal < 5: return

            # [지침] 수익 발생 시 30% 안전자산 회수 로직 (가용화력 70%)
            usable_bal = total_bal * 0.7 
            self.log(f"🛡️ 안전자산 보호 중. 가용 시드: {usable_bal:.2f}")

            # [지침] 5% 변동성 + 거래량 상위 10개 주도주 선별
            tickers = self.ex.fetch_tickers()
            targets = [s for s, t in tickers.items() if s.endswith('/USDT:USDT') and 'BTC' not in s 
                       and abs(t.get('percentage', 0)) >= 5.0]
            
            top_10 = sorted(targets, key=lambda x: tickers[x].get('quoteVolume', 0), reverse=True)[:10]

            for s in top_10:
                side, price = self.v80_bloodline_logic(s)
                if side:
                    self.ex.set_leverage(self.leverage, s)
                    # 시드의 45% 사격
                    qty = float(self.ex.amount_to_precision(s, (usable_bal * 0.45 * self.leverage) / price))
                    
                    # [지침] 1.75% 즉시 손절 예약 (방패)
                    sl_p = float(self.ex.price_to_precision(s, price * 0.9825 if side == "LONG" else price * 1.0175))
                    
                    self.ex.create_market_order(s, 'buy' if side == "LONG" else 'sell', qty)
                    self.ex.create_order(s, 'STOP_MARKET', 'sell' if side == "LONG" else 'buy', qty, None, {'stopPrice': sl_p, 'reduceOnly': True})
                    self.log(f"🎯 [사격 완료] {s} {side} 진입 성공")
                    break # 한 종목 진입 후 사이클 종료 (GCP 워크플로우용)
        except Exception as e:
            self.log(f"⚠️ 시스템 오류: {e}")

if __name__ == "__main__":
    V80_Ultimate_One_Body().run()
