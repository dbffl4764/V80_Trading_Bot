import ccxt
import time
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class BinanceV80:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })
        self.target_symbols = []
        self.max_trade_count = 1  # 2000불 이하는 1종목 집중 타격
        self.consecutive_losses = 0

    def log(self, msg):
        # flush=True를 넣어 무전기(로그)가 절대 끊기지 않게 함
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏰 {msg}", flush=True)

    def get_target_candidates(self):
        """5% 이상 급등한 종목 중 거래대금 상위 10개 추출"""
        try:
            tickers = self.ex.fetch_tickers()
            candidates = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT:USDT'):
                    change = ticker.get('percentage')
                    if change is not None and change >= 5.0:
                        candidates.append({
                            'symbol': symbol,
                            'change': change,
                            'quoteVolume': ticker.get('quoteVolume', 0)
                        })
            
            # 거래대금 순으로 정렬 후 상위 10개 선정
            sorted_candidates = sorted(candidates, key=lambda x: x['quoteVolume'], reverse=True)[:10]
            return [c['symbol'] for c in sorted_candidates]
        except Exception as e:
            self.log(f"⚠️ 후보군 분석 에러: {e}")
            return []

    def check_entry_signal(self, symbol):
        """MA20 유격 2.5% 이내 진입 시 사격"""
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=30)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            ma20 = df['c'].rolling(window=20).mean().iloc[-1]
            current_price = df['c'].iloc[-1]
            
            # 유격 계산: 현재가와 MA20의 차이가 2.5% 이내인지
            gap = abs(current_price - ma20) / ma20 * 100
            if gap <= 2.5:
                return True, current_price
            return False, current_price
        except:
            return False, 0

    def execute_3step_entry(self, symbol, current_price):
        """실전 3분할 사격: 1차 시장가 + 2,3차 지정가(거미줄)"""
        try:
            # 1. 내 잔고 확인 및 화력(40%) 계산
            balance = self.ex.fetch_balance()
            usdt_free = balance['free'].get('USDT', 0)
            
            total_firepower = usdt_free * 0.4  # 전체 시드의 40%
            step_firepower = total_firepower / 3
            
            self.log(f"⚔️ 실전 투입! {symbol} 화력 40% 투입 작전 개시")

            # 수량 계산 (현재가 기준)
            amount = step_firepower / current_price
            
            # --- [1차 포격: 시장가] ---
            order1 = self.ex.create_market_buy_order(symbol, amount)
            self.log(f"  🔥 [1차 시장가 체결] {current_price:.4f}에 포격 완료")

            # --- [2차/3차 포격: 지정가 매복] ---
            # 2차: -1% 지점에서 대기
            price2 = current_price * 0.99
            self.ex.create_limit_buy_order(symbol, amount, price2)
            self.log(f"  🕸️ [2차 매복 완료] {price2:.4f} 거미줄 설치")

            # 3차: -2% 지점에서 대기
            price3 = current_price * 0.98
            self.ex.create_limit_buy_order(symbol, amount, price3)
            self.log(f"  🕸️ [3차 매복 완료] {price3:.4f} 거미줄 설치")
            
            self.log(f"✅ {symbol} 3분할 배치 끝. 이제 시장이 물어주길 기다립니다.")

        except Exception as e:
            self.log(f"⚠️ 실전 사격 중 에러 발생: {e}")

    def run(self):
        self.log("V80 무적 엔진 바이낸스 전선 가동!")
        while True:
            try:
                # 3연패 시 셧다운 (사령관님 지침)
                if self.consecutive_losses >= 3:
                    self.log("❌ 3연패 발생. 금일 작전 종료. 내일 09시를 기약합니다.")
                    break

                # 1. 5% 이상 쏜 놈들 정찰
                self.target_symbols = self.get_target_candidates()
                self.log(f"👀 정찰 중... 후보군: {len(self.target_symbols)}개 종목")

                for symbol in self.target_symbols:
                    # 2. MA20 유격 2.5% 이내인지 확인
                    signal, price = self.check_entry_signal(symbol)
                    if signal:
                        # 3. 3분할 사격 실시
                        self.execute_3step_entry(symbol, price)
                        # 진입 후에는 상황 보고를 위해 루프 잠시 대기
                        time.sleep(600) 
                
                time.sleep(20) # 정찰 간격

            except Exception as e:
                self.log(f"⚠️ 엔진 일시 정지: {e}")
                time.sleep(10)

if __name__ == "__main__":
    BinanceV80().run()
