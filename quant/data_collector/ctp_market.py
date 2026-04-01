"""
CTP 行情数据采集模块 - 函数式版本
避免类封装导致的 GC 问题
"""
import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Deque, Dict

import pandas as pd
from openctp_ctp import mdapi

from quant.common.db_pool import get_db_connection

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 全局状态
_tick_cache: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=12000))
_bars = {}
_connected = False
_tick_count = 0


class MdSpi(mdapi.CThostFtdcMdSpi):
    """行情回调接口"""

    def __init__(self, api, broker_id, user_id, password, symbols):
        super().__init__()
        self.api = api
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.symbols = symbols

    def OnFrontConnected(self):
        """连接成功"""
        logger.info("CTP 连接成功")

        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.broker_id
        req.UserID = self.user_id
        req.Password = self.password

        self.api.ReqUserLogin(req, 0)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登录响应"""
        global _connected

        if pRspInfo and pRspInfo.ErrorID != 0:
            logger.error(f"登录失败: {pRspInfo.ErrorMsg}")
            return

        logger.info("登录成功")
        _connected = True

        for symbol in self.symbols:
            instrument_id = symbol.encode('utf-8')  # 不用 upper()
            ret = self.api.SubscribeMarketData([instrument_id], 1)
            logger.info(f"订阅 {symbol} -> ret={ret}")

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        """订阅行情响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            logger.error(f"订阅失败 {symbol}: {pRspInfo.ErrorMsg}")
        else:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            logger.info(f"订阅确认: {symbol}")

    def OnRtnDepthMarketData(self, pDepthMarketData):
        """行情数据回调"""
        global _tick_count

        if not pDepthMarketData:
            return

        _tick_count += 1

        tick_data = {
            'symbol': pDepthMarketData.InstrumentID,
            'last_price': pDepthMarketData.LastPrice,
            'volume': pDepthMarketData.Volume,
            'open_interest': pDepthMarketData.OpenInterest,
            'datetime': datetime.now()
        }

        logger.info(f"Tick #{_tick_count}: {tick_data['symbol']} {tick_data['last_price']:.2f}")

        # 缓存 tick
        _tick_cache[tick_data['symbol']].append(tick_data.copy())

        # 聚合 K 线
        try:
            aggregate_klines(tick_data)
        except Exception as e:
            logger.error(f"K线聚合失败: {e}")


def aggregate_klines(tick_data: dict):
    """聚合多周期 K 线"""
    symbol = tick_data['symbol']
    tick_time = tick_data['datetime']

    periods = {
        '1min': 1,
        '5min': 5,
        '15min': 15,
        '30min': 30,
        '1h': 60
    }

    for period_name, minutes in periods.items():
        key = (symbol, period_name)

        bar_start = get_bar_start(tick_time, minutes)

        if key not in _bars:
            _bars[key] = create_bar(tick_data, bar_start)
            continue

        current_bar = _bars[key]
        bar_end = current_bar['timestamp'] + timedelta(minutes=minutes)

        if tick_time >= bar_end:
            # K 线完成
            save_bar_to_db(current_bar, period_name)
            _bars[key] = create_bar(tick_data, bar_start)
        else:
            # 更新当前 bar
            current_bar['high'] = max(current_bar['high'], tick_data['last_price'])
            current_bar['low'] = min(current_bar['low'], tick_data['last_price'])
            current_bar['close'] = tick_data['last_price']
            current_bar['volume'] = tick_data['volume']
            current_bar['open_interest'] = tick_data['open_interest']


def get_bar_start(dt: datetime, minutes: int) -> datetime:
    """计算 bar 起始时间"""
    minute = (dt.minute // minutes) * minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def create_bar(tick_data: dict, bar_start: datetime) -> dict:
    """创建新 bar"""
    return {
        'timestamp': bar_start,
        'symbol': tick_data['symbol'],
        'open': tick_data['last_price'],
        'high': tick_data['last_price'],
        'low': tick_data['last_price'],
        'close': tick_data['last_price'],
        'volume': tick_data['volume'],
        'open_interest': tick_data['open_interest']
    }


def save_bar_to_db(bar: dict, period: str):
    """保存 K 线到数据库"""
    logger.info(f"K线完成 [{period}] {bar['symbol']} {bar['timestamp']} "
               f"O:{bar['open']:.2f} H:{bar['high']:.2f} L:{bar['low']:.2f} C:{bar['close']:.2f}")

    interval_map = {
        '1min': '1m',
        '5min': '5m',
        '15min': '15m',
        '30min': '30m',
        '1h': '1h'
    }
    db_interval = interval_map.get(period, period)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO kline_data
                    (time, symbol, interval, open, high, low, close, volume, open_interest)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, symbol, interval)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        open_interest = EXCLUDED.open_interest
                """
                cursor.execute(query, (
                    bar['timestamp'],
                    bar['symbol'],
                    db_interval,
                    bar['open'],
                    bar['high'],
                    bar['low'],
                    bar['close'],
                    bar['volume'],
                    bar.get('open_interest', 0),
                ))
                conn.commit()
    except Exception as e:
        logger.error(f"K线保存失败: {e}")


def get_recent_klines(symbol: str, count: int = 60, period: str = '1min') -> pd.DataFrame:
    """获取最近 N 根 K 线"""
    interval_map = {
        '1min': '1m',
        '5min': '5m',
        '15min': '15m',
        '30min': '30m',
        '1h': '1h'
    }
    db_interval = interval_map.get(period, period)

    # 从数据库读取
    try:
        with get_db_connection() as conn:
            query = """
                SELECT time AS timestamp,
                       open, high, low, close, volume
                FROM kline_data
                WHERE symbol = %s AND interval = %s
                ORDER BY time DESC
                LIMIT %s
            """
            df = pd.read_sql(query, conn, params=(symbol, db_interval, count))

        if not df.empty:
            df.sort_values('timestamp', inplace=True)
            df.reset_index(drop=True, inplace=True)
            return df
    except Exception as e:
        logger.warning(f"数据库查询失败: {e}")

    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


def start_collector(broker_id: str, user_id: str, password: str, md_address: str, symbols: list):
    """启动采集器（后台线程），返回 api 对象用于后续释放"""
    global _connected

    logger.info("采集器初始化完成")
    logger.info("开始连接 CTP...")

    flow_path = "./ctp_flow/"
    os.makedirs(flow_path, exist_ok=True)

    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
    spi = MdSpi(api, broker_id, user_id, password, symbols)
    api.RegisterSpi(spi)
    api.RegisterFront(md_address)
    api.Init()

    max_wait = 10
    for i in range(max_wait):
        time.sleep(1)
        if _connected:
            break

    if not _connected:
        raise TimeoutError("CTP 连接超时")

    logger.info("CTP 连接完成")
    return api


def run_collector(broker_id: str, user_id: str, password: str, md_address: str, symbols: list):
    """运行采集器（阻塞模式）"""
    api = start_collector(broker_id, user_id, password, md_address, symbols)

    logger.info("采集器运行中...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        api.Release()
        logger.info("采集器已关闭")


def main():
    """测试入口"""
    from quant.common.config import config

    run_collector(
        broker_id=config.ctp.broker_id,
        user_id=config.ctp.account_id,
        password=config.ctp.password.get_secret_value(),
        md_address=config.ctp.md_address,
        symbols=[config.strategy.symbol]
    )


if __name__ == "__main__":
    main()
