"""
等待 CTP 委托回报和成交回报的测试脚本
发一笔限价单，等待 10 秒看 SimNow 的反馈
"""
import sys, os, time, threading, logging
sys.path.insert(0, 'E:\\quant-trading-mvp')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

from quant.common.config import config
from quant.data_collector.ctp_trade import CTPTradeApi
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Buy = tdapi.THOST_FTDC_D_Buy
    THOST_FTDC_OF_Open = tdapi.THOST_FTDC_OF_Open
except ImportError:
    THOST_FTDC_D_Buy = '0'
    THOST_FTDC_OF_Open = '0'

# 事件收集
order_events = []
trade_events = []
ev_done = threading.Event()

# 连接 CTP
trade_api = CTPTradeApi(
    broker_id=config.ctp.broker_id,
    account_id=config.ctp.account_id,
    password=config.ctp.password.get_secret_value(),
    td_address=config.ctp.td_address,
    app_id=config.ctp.app_id,
    auth_code=config.ctp.auth_code
)

if not trade_api.connect():
    logger.error("CTP 连接失败")
    sys.exit(1)

# 查询当前持仓
pos = trade_api.get_current_position('au2606')
logger.info(f"发单前持仓: {pos}")

# 注册回调
def order_callback(event_type, data):
    if event_type == 'order':
        status_map = {
            '0': '全部成交', '1': '部分成交', '2': '未成交',
            '3': '未成交(撤销中)', '4': '已撤销', '5': '撤单中',
            'a': '未知', 'b': '尚未触发', 'c': '已触发'
        }
        status = status_map.get(str(data.OrderStatus), str(data.OrderStatus))
        logger.info(f"[委托回报] 状态={status} 价格={data.LimitPrice} 合约={data.InstrumentID} 错误={getattr(data, 'StatusMsg', '')}")
        order_events.append((event_type, status))
    elif event_type == 'trade':
        logger.info(f"[成交回报] 价格={data.Price} 手数={data.Volume} 合约={data.InstrumentID}")
        trade_events.append((event_type, data.Price, data.Volume))
        ev_done.set()

# 获取当前价格
from quant.common.db import db_connection
with db_connection(config) as conn:
    cur = conn.cursor()
    cur.execute("SELECT close FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 1")
    row = cur.fetchone()
current_price = float(row[0]) if row else 1116.0
limit_price = round(current_price + 2.0, 2)  # 限价高于当前价 2 元，容易成交
logger.info(f"当前价格: {current_price}, 报单限价: {limit_price}")

# 发送限价买单
ref = trade_api.send_order(
    instrument_id='au2606',
    direction=THOST_FTDC_D_Buy,
    offset_flag=THOST_FTDC_OF_Open,
    volume=1,
    price=limit_price,
    exchange_id='SHFE',
)
trade_api._order_callbacks[ref] = order_callback
logger.info(f"报单已发送 OrderRef={ref}，等待回报（最多 15 秒）...")

# 等待成交回报或超时
ev_done.wait(timeout=15)
time.sleep(2)  # 额外等待可能的委托回报

logger.info(f"\n=== 结果 ===")
logger.info(f"委托回报数: {len(order_events)} 条: {order_events}")
logger.info(f"成交回报数: {len(trade_events)} 条: {trade_events}")

# 查询发单后持仓
time.sleep(1)
pos_after = trade_api.get_current_position('au2606')
logger.info(f"发单后持仓: {pos_after}")

trade_api.disconnect()
