"""查询 CTP 当日委托和成交"""
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
time.sleep(3)  # 等待数据同步

print("\n=== 查询今日委托 ===")
try:
    orders = trade_api.get_orders_by_day()
    if orders:
        for o in orders:
            print(o)
    else:
        print("今日无委托")
except Exception as e:
    print(f"查询失败：{e}")

print("\n=== 查询今日成交 ===")
try:
    trades = trade_api.get_trades_by_day()
    if trades:
        for t in trades:
            print(t)
    else:
        print("今日无成交")
except Exception as e:
    print(f"查询失败：{e}")

print("\n=== 查询持仓 ===")
try:
    positions = trade_api.get_current_position()
    if positions:
        for p in positions:
            print(p)
    else:
        print("无持仓")
except Exception as e:
    print(f"查询失败：{e}")
