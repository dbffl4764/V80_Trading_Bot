
import os
import ccxt
from dotenv import load_dotenv
from v80_logic import check_trend
from v80_trade import safety_transfer

load_dotenv()
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'options': {'defaultType': 'future'}
})

if __name__ == "__main__":
    print("🚀 V80 전략 봇 가동!")
    # 여기에 반복 로직...
