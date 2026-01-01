import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

class AI_Sniper_V95:
    def __init__(self):
        # 사령관님 API 설정 (실행 시 본인 키 확인 필수 ㅋ)
        self.ex = ccxt.binance({
            'apiKey': 'YOUR_API_KEY',
            'secret': 'YOUR_SECRET_KEY',
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.leverage = 5

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ {msg}", flush=True)

    def get_indicators(self, symbol):
        """사령관님의 60-20 이격도 및 RSI 정밀 분석"""
        try:
            # 일봉 데이터 (장기 추세)
            ohlcv_d = self.ex.fetch_ohlcv(symbol, '1d', limit=100)
            df_d = pd.DataFrame(ohlcv_d, columns=['t','o','h','l','c','v'])
            ma60 = df_d['c'].rolling(60).mean().iloc[-1]
            ma20 = df_d['c'].rolling(20).mean().iloc[-1]
            curr_p = df_d['c'].iloc[-1]

            # 이격도 계산 (사령관님 지표 ㅋ)
            disparity = abs(ma20 - ma60) / ma60 * 100

            # 5분봉 데이터 (단기 타점)
            ohlcv_m = self.ex.fetch_ohlcv(symbol, '5m', limit=100)
            df_m = pd.DataFrame(ohlcv_m, columns=['t','o','h','l','c','v'])
            
            # RSI 계산 ㅋ
            delta = df_m['c'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            return curr_p, ma20, ma60, disparity, rsi
        except: return None, None, None, 0, 50

    def run(self):
        self.log("⚔️ AI Sniper 엔진 가동... 주도주 정찰 중 ㅋ")
        try:
            # 1. 5% 변동성 컷 (사령관님 입구 컷)
            tickers = self.ex.fetch_tickers()
            targets = [s for s, t in tickers.items() if s.endswith('/USDT') 
                       and abs(t.get('percentage', 0)) >= 5.0]

            for s in targets[:10]:
                price, ma20, ma60, disp, rsi = self.get_indicators(s)
                
                # 사령관님의 필승 조건: 60-20 이격도 3% 이상 & RSI 과매수/과매도 탈출
                if disp >= 3.0:
                    if price > ma20 > ma60 and rsi < 70: # 롱 타점 ㅋ
                        self.log(f"🎯 {s} [1차 사격] LONG 진입 (이격도: {disp:.2f}%)")
                        # self.execute_order(s, 'buy', 0.4) # 40% 1차 진입
                        break
                    elif price < ma20 < ma60 and rsi > 30: # 숏 타점 ㅋ
                        self.log(f"🎯 {s} [1차 사격] SHORT 진입 (이격도: {disp:.2f}%)")
                        # self.execute_order(s, 'sell', 0.4) # 40% 1차 진입
                        break
                
                print(f"🔎 {s.split('/')[0]} 분석 중... (이격도: {disp:.1f}%)", end='\r')

        except Exception as e:
            self.log(f"⚠️ 일시적 지연: {e}")

if __name__ == "__main__":
    sniper = AI_Sniper_V95()
    while True:
        sniper.run()
        time.sleep(10)
