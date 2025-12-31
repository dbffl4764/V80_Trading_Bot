def safety_transfer(exchange, profit_usd, profit_pct):
    if profit_usd <= 0: return
    
    # 100% 넘으면 40%, 아니면 30% 안전자산으로!
    ratio = 0.4 if profit_pct >= 1.0 else 0.3
    amount = profit_usd * ratio
    
    # 선물 계정 -> 현물 계정 이체
    exchange.transfer("USDT", amount, "future", "spot")
    print(f"💰 {amount} USDT 안전자산 이체 완료!")
