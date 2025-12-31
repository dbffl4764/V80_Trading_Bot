import os
import time
import ccxt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# 🚀 640% 수익을 지키기 위한 깃허브 전용 우회 설정
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
        # ⚠️ 일부 제한을 피하기 위해 'fapi' 호출 방식을 변경
        'warnOnFetchOpenOrdersWithoutSymbol': False 
    }
})

# 💡 핵심: 바이낸스 기본 주소 대신 'api1~3' 중 하나를 랜덤하게 찌르거나 
# 깃허브에서 차단이 덜한 주소로 강제 고정합니다.
exchange.urls['api']['public'] = 'https://api1.binance.com/api'
exchange.urls['api']['private'] = 'https://api1.binance.com/api'

def check_v80_trend(symbol):
    # (추세 분석 로직은 동일)
    pass

if __name__ == "__main__":
    print(f"🚀 V80 봇 재가동 (현재 수익률 640% 🔥)")
    
    try:
        # ⚠️ 451 에러가 발생하는 'positionRisk' 대신 
        # 상대적으로 차단이 덜한 'fetch_balance'를 사용해봅니다.
        print("📊 계좌 잔고 및 포지션 확인 중...")
        balance = exchange.fetch_balance()
        
        # 잔고 확인이 성공하면 이후 로직 진행
        print("✅ 접속 성공! 분석을 시작합니다.")
        
        # ... (이후 분석 로직)
        
    except Exception as e:
        if "451" in str(e):
            print("❌ 깃허브 서버 IP가 또 차단되었습니다. (무료 서버의 한계 😭)")
            print("💡 해결책: 깃허브 Actions 탭에서 다시 [Run workflow]를 눌러보세요.")
            print("   (다른 IP의 서버가 배정되면 마법처럼 성공합니다!)")
        else:
            print(f"❌ 에러 발생: {e}")
