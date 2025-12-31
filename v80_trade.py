def safety_transfer(exchange, profit_usd, profit_pct):
    if profit_usd <= 0: return
    ratio = 0.4 if profit_pct >= 1.0 else 0.3
    amount = profit_usd * ratio
    exchange.transfer("USDT", amount, "future", "spot")
    print(f"💰 {amount} USDT 안전자산 이동 완료!")
