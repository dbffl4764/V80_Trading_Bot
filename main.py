import os
import time
import ccxt
from dotenv import load_dotenv

# 사용자 정의 모듈 불러오기
from v80_logic import check_trend
from v80_trade import safety_transfer, get_open_positions_count

# 1. 환경 변수 로드 (API 키)
load_dotenv()

# 2. 바이낸스 선물 거래소 설정
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

# 3. 설정값
TARGET_SYMBOLS = ['BTC/USDT', 'ETH/USDT'] # 거래 종목
MAX_POSITIONS = 2  # 최대 2개 종목 제한

def run_bot():
    print("💰 [V80 전략] 봇 가동 시작 - 100억 목표!")
    
    while True:
        try:
            # 현재 열린 포지션 개수 확인
            current_count = get_open_positions_count(exchange)
            print(f"\n--- 현재 포지션 수: {current_count} / {MAX_POSITIONS} ---")

            for symbol in TARGET_SYMBOLS:
                # 포지션이 이미 2개면 더 이상 분석 안 함
                if current_count >= MAX_POSITIONS:
                    break
                
                # 6개 타임프레임 추세 체크 (v80_logic 호출)
                signal = check_trend(exchange, symbol)
                print(f"🔍 {symbol} 분석: {signal}")

                if signal == "LONG":
                    print(f"🚀 {symbol} 모든 추세 상승! LONG 진입 실행")
                    # 여기에 실제 매수 코드 추가 가능
                    
                elif signal == "SHORT":
                    print(f"🔻 {symbol} 모든 추세 하락! SHORT 진입 실행")
                    # 여기에 실제 매도 코드 추가 가능

            # 수익 정산 예시 (포지션 종료 시점에 실행되도록 설정 필요)
            # 만약 수익이 났다면 safety_transfer(exchange, 수익금, 수익률) 호출

            time.sleep(60 * 5) # 5분마다 반복 실행
            
        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
