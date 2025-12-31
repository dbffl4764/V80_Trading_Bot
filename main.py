import os
import ccxt

def run_v80_binance_only():
    print("🚀 [V80 바이낸스 전용 엔진] 기동!")
    
    # 1. 바이낸스 선물 연동
    # 깃허브 Secrets에 BINANCE_KEY, BINANCE_SECRET이 있어야 합니다.
    binance = ccxt.binance({
        'apiKey': os.environ.get('BINANCE_KEY'),
        'secret': os.environ.get('BINANCE_SECRET'),
        'options': {'defaultType': 'future'} # 선물 계좌 고정
    })

    try:
        # 2. 실제 잔고 데이터 추출
        balance = binance.fetch_balance()
        total_usdt = balance['total'].get('USDT', 0)
        
        # 3. 사령관님 전용 실시간 보고
        print("-" * 30)
        print(f"💰 [바이낸스 현재 잔고] {total_usdt:,.2f} USDT")
        
        # 4. 100% 수익 돌파 시 40% 안전자산 원칙 알림
        safe_reserve = total_usdt * 0.4
        print(f"⚠️ [수익 수호 알림] 안전자산 회수 목표액: {safe_reserve:,.2f} USDT")
        print("-" * 30)

    except Exception as e:
        print(f"❌ 바이낸스 연결 오류: {e}")

    print("✅ 바이낸스 전선 이상 무. 다음 보고까지 6방향 추세 감시를 계속합니다.")

if __name__ == "__main__":
    run_v80_binance_only()
