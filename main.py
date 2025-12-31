import os
import ccxt

def run_v80():
    print("🚀 [V80 통합 엔진] 가동!")
    
    # 비트겟 확인
    bg_key = os.environ.get('BITGET_API_KEY')
    if bg_key:
        try:
            bg = ccxt.bitget({
                'apiKey': bg_key,
                'secret': os.environ.get('BITGET_SECRET_KEY'),
                'password': os.environ.get('BITGET_PASSPHRASE'),
                'options': {'defaultType': 'future'}
            })
            bal = bg.fetch_balance()
            total = bal['total'].get('USDT', 0)
            print(f"💰 [비트겟 잔고] {total:,.2f} USDT")
            if total > 200:
                print(f"⚠️ [수익 관리] 안전자산 {total * 0.3:,.2f} USDT 회수 대상")
        except Exception as e:
            print(f"❌ 비트겟 에러: {e}")

    # 바이낸스 확인
    bn_key = os.environ.get('BINANCE_KEY')
    if bn_key:
        try:
            bn = ccxt.binance({
                'apiKey': bn_key,
                'secret': os.environ.get('BINANCE_SECRET'),
                'options': {'defaultType': 'future'}
            })
            bal_bn = bn.fetch_balance()
            print(f"💰 [바이낸스 잔고] {bal_bn['total'].get('USDT', 0):,.2f} USDT")
        except Exception as e:
            print(f"❌ 바이낸스 에러: {e}")

if __name__ == "__main__":
    run_v80()
