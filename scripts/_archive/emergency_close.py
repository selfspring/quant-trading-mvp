"""紧急平仓脚本 - 清理所有 SimNow 持仓"""
import sys, os, time, logging
sys.path.insert(0, r'E:\quant-trading-mvp')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', force=True)
logger = logging.getLogger(__name__)

from quant.common.config import config
from quant.data_collector.ctp_trade import CTPTradeApi
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Buy = tdapi.THOST_FTDC_D_Buy
    THOST_FTDC_D_Sell = tdapi.THOST_FTDC_D_Sell
    THOST_FTDC_OF_Close = tdapi.THOST_FTDC_OF_Close
    THOST_FTDC_OF_CloseToday = tdapi.THOST_FTDC_OF_CloseToday
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
logger.info(f"当前持仓: {pos}")

long_vol = pos.get('long_volume', 0)
short_vol = pos.get('short_volume', 0)

if long_vol == 0 and short_vol == 0:
    logger.info("无持仓，无需平仓")
else:
    if long_vol > 0:
        logger.info(f"平多 {long_vol} 手...")
        ref = trade_api.send_order(
            instrument_id='au2606',
            direction=THOST_FTDC_D_Sell,
            offset_flag=THOST_FTDC_OF_CloseToday,
            volume=long_vol,
            price=0,
            exchange_id='SHFE'
        )
        logger.info(f"平多报单已提交 OrderRef={ref}")
        time.sleep(3)
    if short_vol > 0:
        logger.info(f"平空 {short_vol} 手...")
        ref = trade_api.send_order(
            instrument_id='au2606',
            direction=THOST_FTDC_D_Buy,
            offset_flag=THOST_FTDC_OF_CloseToday,
            volume=short_vol,
            price=0,
            exchange_id='SHFE'
        )
        logger.info(f"平空报单已提交 OrderRef={ref}")
        time.sleep(3)

# 等待成交
time.sleep(5)
pos2 = trade_api.get_current_position()
logger.info(f"平仓后持仓: {pos2}")
trade_api.disconnect()
