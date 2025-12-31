import ccxt

def connect_binance(api_key, secret_key):
    """바이낸스 거래소 연결"""
    return ccxt.binance({
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True
    })

def get_current_balance(binance):
    """현재 내 지갑 잔고 확인 (안전자산 30% 계산용)"""
    balance = binance.fetch_balance()
    return balance['total']['USDT']

def execute_safe_move(binance, amount):
    """수익금의 일부를 안전자산으로 이체 (예: 현물->펀딩 지갑)"""
    print(f"🛡️ 사령관님 지침: {amount} USDT를 안전자산으로 이동합니다.")
    # 실제 이체 실행 명령 (보안을 위해 필요시 주석 해제)
    # binance.transfer("USDT", amount, "spot", "funding")

print("✅ 바이낸스 거래 모듈 로드 완료")
