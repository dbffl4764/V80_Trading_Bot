cat << 'EOF' > v80_trade.py
def calculate_size(balance, price, leverage):
    # 사령관님 지침: 시드의 45% 투입, 2분할(1차 40%)
    total_budget = balance * 0.45 * leverage
    first_entry = total_budget * 0.4 / price
    return first_entry
EOF
