"""快速查询 CTP 账户实际持仓"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config
from quant.data_collector.ctp_trade import CTPTradeApi

print("连接 CTP 交易接口...")
trade_api = CTPTradeApi(
    broker_id=config.ctp.broker_id,
    account_id=config.ctp.account_id,
    password=config.ctp.password.get_secret_value(),
    td_address=config.ctp.td_address,
    app_id=config.ctp.app_id,
    auth_code=config.ctp.auth_code
)
trade_api.connect()
time.sleep(2)

print("\n=== 查询持仓 ===")
try:
    positions = trade_api.get_current_position()
    if positions:
        for p in positions:
            print(p)
    else:
        print("无持仓")
except Exception as e:
    print(f"查询失败: {e}")

print("\n=== 查询资金 ===")
try:
    account = trade_api.get_account_info()
    if account:
        print(account)
    else:
        print("无资金信息")
except Exception as e:
    print(f"查询失败: {e}")
