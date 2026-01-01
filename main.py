import ccxt
import pandas as pd
import time
from datetime import datetime

class V90_Strategic_Sniper:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': 'API_KEY',
            'secret': 'SECRET_KEY',
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 5

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 {msg}", flush=True)

    def check_logic(self, symbol):
        try:
            # 일봉(1D) 데이터로 큰 흐름(60-20 이격도) 파악 ㅋ
            ohlcv_d = self.ex.fetch_ohlcv(symbol, '1d', limit=100)
            df_d = pd.DataFrame(ohlcv_d, columns=['t','o','h','l','c','v'])
            
            ma60 = df_d['c'].rolling(60).mean().iloc[-1]
            ma20 = df_d['c'].rolling(20).mean().iloc[-1]
            curr_p = df_d['c'].iloc[-1]

            # [사령관님 필살기] 이격도 계산 (60일선과 20일선 사이의 괴리)
            disparity = abs(ma20 - ma60) / ma60 * 100
            
            # [거름망] 이격도가 일정 수준(예: 3%~5%) 이상 벌어지거나 좁혀질 때 ㅋ
            if disparity >= 3.0:
                # 5분봉(5M)으로 세부 타점 정렬 확인
                ohlcv_m = self.ex.fetch_ohlcv(symbol, '5m', limit=100)
                df_m = pd.DataFrame(ohlcv_m, columns=['t','o','h','l','c','v'])
                
                m_ma20 = df_m['c'].rolling(20).mean().iloc[-1]
                m_ma60 = df_m['c'].rolling(60).mean().iloc[-1]

                # 정배열/역배열 태동 시 2분할 진입 신호 생성 ㅋ
                if (curr_p > ma20 > ma60) and (curr_p > m_ma20 > m_ma60):
                    return "LONG", curr_p
                elif (curr_p < ma20 < ma60) and (curr_p < m_ma20 < m_ma60):
                    return "SHORT", curr_p
            return None, 0
        except: return None, 0

    def run(self):
        self.log("🚀 [v90.0] 60-20 이격도 분할 매수 엔진 가동! ㅋ")
        try:
            # 1. 5% 변동성 종목 선별 ㅋ
            tickers = self.ex.fetch_tickers()
            targets = [s for s, t in tickers.items() if s.endswith('/USDT') and abs(t.get('percentage', 0)) >= 5.0]
            
            for s in targets[:10]:
                side, price = self.check_logic(s)
                if side:
                    self.log(f"🔥 {s} 타점 포착! [2분할 사격 개시]")
                    
                    # [사령관님 2분할 공식] 1차 40%, 2차 60% (또는 5:5) ㅋ
                    total_qty = 100 # 예시 수량
                    first_entry = total_qty * 0.4
                    second_entry = total_qty * 0.6
                    
                    self.log(f"💰 1차 진입 완료: {first_entry} 수량")
                    # 지정가나 시간차를 두고 2차 진입 예약 로직...
                    break 

        except Exception as e:
            self.log(f"⚠️ 시스템 오류: {e}")

if __name__ == "__main__":
    bot = V90_Strategic_Sniper()
    while True:
        bot.run()
        time.sleep(10)
