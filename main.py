import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()

class V80_Final_Engine:
    def __init__(self):
        # 바이낸스 선물 계정 설정
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.consecutive_losses = 0

    def log(self, msg):
        """실시간 로그 출력 (버퍼링 방지용 flush 적용)"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_target_candidates(self):
        """[1단계] 5% 이상 쏜 종목 중 거래량 상위 10개 추출"""
        try:
            markets = self.ex.load_markets()
            tickers = self.ex.fetch_tickers()
            candidates = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT:USDT'):
                    m_info = markets.get(symbol)
                    if m_info and m_info.get('active'):
                        change = ticker.get('percentage', 0)
                        # 상승(+5%) 혹은 하락(-5%) 모두 감지
                        if abs(change) >= 5.0:
                            candidates.append({
                                'symbol': symbol,
                                'change': change,
                                'vol': ticker.get('quoteVolume', 0)
                            })
            # 거래대금 상위 10개 정찰대 편성
            return [c['symbol'] for c in sorted(candidates, key=lambda x: x['vol'], reverse=True)[:10]]
        except Exception as e:
            self.log(f"⚠️ 정찰 에러: {e}")
            return []

    def check_signal(self, symbol):
        """[2단계] 정배열 롱 / 역배열 숏 / 유격 2.5% 판독"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            # 이평선 정렬: 5일(단기), 20일(중기), 60일(장기)
            ma5 = df['c'].rolling(window=5).mean().iloc[-1]
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            ma60 = df['c'].rolling(window=60).mean().iloc[-1]
            curr = df['c'].iloc[-1]
            
            # MA20과의 이격도(유격) 계산
            gap = abs(curr - ma20) / ma20 * 100

            if gap <= 2.5:
                # 🌕 정배열 (5 > 20 > 60) -> 롱(LONG)
                if ma5 > ma20 > ma60:
                    return "LONG", curr
                # 🌑 역배열 (5 < 20 < 60) -> 숏(SHORT)
                elif ma5 < ma20 < ma60:
                    return "SHORT", curr
            return None, curr
        except:
            return None, 0

    def execute_3step_order(self, symbol, side, price):
        try:
            # 1. 현재 총 자산(Total USDT) 기준으로 40% 계산
            bal = self.ex.fetch_balance()
            total_usdt = bal['total'].get('USDT', 0)
            
            # 총 화력 40%를 3분할 (약 13.3%씩 3번)
            # 200불 기준 1회 진입 시 약 26.6불 투입
            firepower_per_step = (total_usdt * 0.4) / 3 
            
            # 레버리지를 감안한 실제 코인 수량(amount) 계산
            # 레버리지가 10배라면, 26.6불로 266불어치 코인을 사는 셈
            # 여기서는 증거금(Margin) 기준으로 수량을 맞춥니다.
            leverage = 10 # 사령관님 레버리지 설정값 (예: 10배)
            amount = (firepower_per_step * leverage) / price
            
            self.log(f"⚔️ 실전 사격! [{symbol}] 회당 {firepower_per_step:.2f} USDT 투입 (시드 대비 13.3%)")

            if side == "LONG":
                self.ex.create_market_buy_order(symbol, amount)
                self.ex.create_limit_buy_order(symbol, amount, price * 0.99)
                self.ex.create_limit_buy_order(symbol, amount, price * 0.98)
                
            elif side == "SHORT":
                self.ex.create_market_sell_order(symbol, amount)
                self.ex.create_limit_sell_order(symbol, amount, price * 1.01)
                self.ex.create_limit_sell_order(symbol, amount, price * 1.02)

        except Exception as e:
            self.log(f"⚠️ 사격 에러 발생: {e}")

    def run(self):
        self.log(f"⚔️ V80 무적 엔진 발진! (현재 잔고: {self.ex.fetch_balance()['total'].get('USDT', 0):.2f} USDT)")
        while True:
            try:
                # 3연패 셧다운 원칙 (시드 보호)
                if self.consecutive_losses >= 3:
                    self.log("🚨 3연패 달성. 작전 중지 및 기지 복귀.")
                    break

                symbols = self.get_target_candidates()
                self.log(f"👀 정찰 중... (급등/급락 후보: {len(symbols)}개)")

                for s in symbols:
                    side, price = self.check_signal(s)
                    if side:
                        self.execute_3step_order(s, side, price)
                        # 진입 후 10분간 상황 주시 (중복 진입 방지)
                        time.sleep(600)
                
                time.sleep(20) # 20초 간격으로 계속 그물 던지기
            except Exception as e:
                self.log(f"⚠️ 시스템 오류 발생: {e}")
                time.sleep(10)

if __name__ == "__main__":
    V80_Final_Engine().run()
