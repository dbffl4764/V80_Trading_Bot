import os
from dotenv import load_dotenv
import ccxt
import time
from v80_logic import check_v80_strategy
from v80_trade import connect_binance

# 1. 내 컴퓨터의 .env 파일에서 키를 읽어옵니다.
load_dotenv()

MY_API = os.getenv('BINANCE_API_KEY')
MY_SECRET = os.getenv('BINANCE_SECRET_KEY')

def start_bot():
    print("📢 V80 자동 감시 시스템 시동 중...")
    
    # API 키 확인
    if not MY_API or not MY_SECRET:
        print("🚨 에러: .env 파일에서 API 키를 찾을 수 없습니다! 파일을 확인해 주세요.")
        return

    bot = connect_binance(MY_API, MY_SECRET)
    
    while True:
        try:
            # 실시간 데이터 가져오기 (수정된 부분)
            ohlcv = bot.fetch_ohlcv("BTC/USDT", timeframe='1d', limit=100)
            if not ohlcv:
                print("⚠️ 데이터를 가져오지 못했습니다. 잠시 후 다시 시도합니다.")
                time.sleep(10)
                continue

            import pandas as pd
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 현재 수익률 (사령관님 보고: 340%)
            current_profit = 340 
            
            # 전략 체크
            is_safe, ratio, ma20 = check_v80_strategy(df, current_profit)
            
            price = df['close'].iloc[-1]
            print(f"\n[실시간 보고] 현재가: {price} | 20일선: {ma20:.2f}")

            if is_safe:
                print(f"✅ 결과: 20일선 위에서 순항 중! (수익 {current_profit}% 유지)")
            else:
                print("🚨 경보: 20일선 이탈! 사령관님, 확인이 필요합니다.")

            print(f"💰 안전자산 이체 비율: {ratio*100}% 적용 중")
            
            time.sleep(60) # 1분마다 체크
            
        except Exception as e:
            print(f"❌ 실행 중 오류 발생: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_bot()
