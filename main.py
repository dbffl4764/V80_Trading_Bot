from v80_logic import check_v80_strategy
from v80_trade import connect_binance, get_current_balance
import time
import os
from dotenv import load_dotenv
load_dotenv()

MY_API = os.getenv('BINANCE_API_KEY')
MY_SECRET = os.getenv('BINANCE_SECRET_KEY')

def start_bot():
    print("📢 V80 자동 감시 시스템을 시작합니다.")
    
    # 바이낸스 연결
    bot = connect_binance(MY_API, MY_SECRET)
    
    while True:
        try:
            # 현재 수익률 (사령관님 보고: 340%)
            current_profit = 340 
            
            # 전략 체크 (20일선 수호 여부 및 안전자산 비율)
            # 여기서는 예시 데이터를 사용하지만, 실제로는 바이낸스 가격을 가져옵니다.
            # is_safe: 20일선 위에 있으면 True
            # ratio: 수익의 40% (100% 넘었으므로)
            is_safe, ratio, ma20 = check_v80_strategy(None, current_profit)
            
            if is_safe:
                print(f"✅ 현재 20일선({ma20}) 위에서 안전하게 순항 중! 1000%까지 홀딩.")
            else:
                print("🚨 경보! 20일선 이탈 감지. 대응 준비!")

            print(f"💰 수익 관리 원칙: 현재 수익의 {ratio*100}%를 안전자산으로 관리합니다.")
            
            # 1시간마다 반복 체크
            time.sleep(3600) 
            
        except Exception as e:
            print(f"잠시 오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_bot()
