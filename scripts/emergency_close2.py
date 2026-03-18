"""
紧急平仓 - 区分今仓/昨仓
"""
import sys, os, time, logging
sys.path.insert(0, 'E:\\quant-trading-mvp')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', force=True)
logger = logging.getLogger(__name__)

from quant.common.config import config
from quant.data_collector.ctp_trade import CTPTradeApi
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Sell = tdapi.THOST_FTDC_D_Sell
    THOST_FTDC_OF_Close = tdapi.THOST_FTDC_OF_Close
    THOST_FTDC_OF_CloseToday = tdapi.THOST_FTDC_OF_CloseToday
    THOST_FTDC_OF_CloseYesterday = tdapi.THOST_FTDC_OF_CloseYesterday
except ImportError:
    logger.error("openctp-ctp 未安装")
    sys.exit(1)

trade_api = CTPTradeApi(
    broker_id=config.ctp.broker_id,
    account_id=config.ctp.account_id,
    password=config.ctp.password.get_secret_value(),
    td_address=config.ctp.td_address,
    app_id=config.ctp.app_id,
    auth_code=config.ctp.auth_code
)
trade_api.connect()
time.sleep(1)

pos = trade_api.get_current_position()
long_vol = pos.get('long_volume', 0)
logger.info(f"当前持仓: 多头={long_vol}手")

if long_vol == 0:
    logger.info("无持仓，无需平仓")
    trade_api.disconnect()
    sys.exit(0)

# 先尝试平今仓
logger.info(f"尝试平今仓 {long_vol} 手...")
ref = trade_api.send_order(
    instrument_id='au2606',
    direction=THOST_FTDC_D_Sell,
    offset_flag=THOST_FTDC_OF_CloseToday,
    volume=long_vol,
    price=0,
    exchange_id='SHFE'
)
logger.info(f"平今仓报单已提交 OrderRef={ref}")
time.sleep(5)

# 检查平仓后持仓
pos2 = trade_api.get_current_position()
long_vol2 = pos2.get('long_volume', 0)
logger.info(f"平今仓后持仓: 多头={long_vol2}手")

if long_vol2 > 0:
    logger.warning(f"仍有 {long_vol2} 手持仓，尝试平昨仓...")
    ref2 = trade_api.send_order(
        instrument_id='au2606',
        direction=THOST_FTDC_D_Sell,
        offset_flag=THOST_FTDC_OF_CloseYesterday,
        volume=long_vol2,
        price=0,
        exchange_id='SHFE'
    )
    logger.info(f"平昨仓报单已提交 OrderRef={ref2}")
    time.sleep(5)
    pos3 = trade_api.get_current_position()
    logger.info(f"最终持仓: {pos3}")

trade_api.disconnect()
