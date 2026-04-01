import sys
sys.path.insert(0, r'E:\quant-trading-mvp')

from quant.common.config import config
from quant.common.tq_factory import tq_trade_session

def test_tq_connection():
    print("Testing TqKq Connection...")
    try:
        with tq_trade_session(config) as api:
            # 获取账户资金
            acc = api.get_account()
            if acc:
                print("\n=== Account Info ===")
                print(f"Balance: {acc.get('balance', 0):.2f}")
                print(f"Available: {acc.get('available', 0):.2f}")
                print(f"Risk Ratio: {acc.get('risk_ratio', 0):.2%}")
            
            # 获取 au2606 持仓
            pos_long = api.get_position('SHFE.au2606', 'buy')
            pos_short = api.get_position('SHFE.au2606', 'sell')
            
            print("\n=== Positions ===")
            print(f"SHFE.au2606 Long: {pos_long.get('volume', 0)} (Price: {pos_long.get('price', 0)})")
            print(f"SHFE.au2606 Short: {pos_short.get('volume', 0)} (Price: {pos_short.get('price', 0)})")
            
            print("\n✅ Connection successful!")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")

if __name__ == "__main__":
    test_tq_connection()
