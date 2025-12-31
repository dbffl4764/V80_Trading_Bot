import os
import ccxt
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ================= 설정값 (사령관님 특명) =================
SYMBOL_COUNT = 10       # 감시 종목 수
BET_RATIO = 0.40        # 총 자산의 40% 투입
LEVERAGE = 5            # 5배 레버리지
ENTRY_GAP = 0.01        # 1% 간격으로 추가 진입 (평단 조절)
LOSS_LIMIT = 3          # 3연패 시 셧다운
# =====================================================

class BinanceV80:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.consecutive_losses = 0
        self.shutdown_until = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    def is_trading_available(self):
        now = datetime.now()
        if self.shutdown_until and now < self.shutdown_until:
            return False
        if self.shutdown_until and now >= self.shutdown_until:
            self.log("☀️ 셧다운 해제! 작전을 재개합니다.")
            self.shutdown_until = None
            self.consecutive_losses = 0
        return True

    def get_data(self, symbol):
        ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        df['ma20'] = df['c'].rolling(20).mean()
        df['ma60'] = df['c'].rolling(60).mean()
        return df.iloc[-1]

    def execute_logic(self):
        if not self.is_trading_available(): return

        try:
            balance = self.ex.fetch_balance()
            total_usdt = float(balance['total']['USDT'])
            
            # 포지션 체크 (이미 있으면 쉬기)
            pos = [p for p in balance['info']['positions'] if float(p['positionAmt']) != 0]
            if len(pos) > 0: return

            # 5% 이상 변동성 종목 탐색
            tickers = self.ex.fetch_tickers()
            candidates = []
            for s, t in tickers.items():
                if 'USDT' in s and '/' not in s and abs(t.get('percentage', 0)) >= 5.0:
                    candidates.append(s)

            for symbol in candidates[:SYMBOL_COUNT]:
                data = self.get_data(symbol)
                curr_price = data['c']
                ma20, ma60 = data['ma20'], data['ma60']

                # 🎯 유격 2.5% 타점 분석
                is_long = ma20 > ma60 and (ma20 <= curr_price <= ma20 * 1.025)
                is_short = ma20 < ma60 and (ma20 * 0.975 <= curr_price <= ma20)

                if is_long or is_short:
                    side = 'BUY' if is_long else 'SELL'
                    self.log(f"🎯 타점 포착: {symbol} ({side}) | 화력 40% 분할 투입")
                    
                    # 40% 시드를 1:1:1로 분할 (약 13.3%씩)
                    step_usdt = (total_usdt * BET_RATIO) / 3
                    
                    # 1차: 시장가 진입
                    amount = (step_usdt * LEVERAGE) / curr_price
                    self.ex.create_market_order(symbol, side.lower(), amount)
                    
                    # 2차/3차: 거미줄 설치 (1% 간격 지정가)
                    for i in range(1, 3):
                        gap_price = curr_price * (1 - (ENTRY_GAP * i)) if is_long else curr_price * (1 + (ENTRY_GAP * i))
                        step_amount = (step_usdt * LEVERAGE) / gap_price
                        self.ex.create_limit_order(symbol, side.lower(), step_amount, gap_price)
                    
                    # 결과 감시 로직은 거래소 히스토리 API와 연동하여 
                    # 익절 시 consecutive_losses = 0, 손절 시 +1 처리가 필요함
                    # (이 부분은 거래가 종료된 시점에 체크하도록 설계)
                    break

        except Exception as e:
            self.log(f"⚠️ 에러 발생: {e}")

bot = BinanceV80()
while True:
    bot.execute_logic()
    time.sleep(20)
