"""CTP 长驻采集进程 - 最小化版本"""
import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from openctp_ctp import mdapi

sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

# 配置
BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "Cmx1454697261"
MD_ADDRESS = "tcp://182.254.243.31:30011"
SYMBOL = "au2606"
PID_FILE = "E:\\quant-trading-mvp\\data\\collector.pid"
LOG_DIR = "E:\\quant-trading-mvp\\logs"

# 交易时段
TRADING_SESSIONS = [
    (9, 0, 11, 30),   # 早盘
    (13, 30, 15, 0),  # 午盘
    (21, 0, 23, 59),  # 夜盘前半段
    (0, 0, 2, 30)     # 夜盘后半段（次日凌晨）
]

# 全局状态
current_bar = None
connected = False

# 日志
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"collector_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 僵尸进程判定阈值（秒）
ZOMBIE_THRESHOLD_SECONDS = 6 * 3600  # 6小时

# 无 Tick 超时阈值（秒）
NO_TICK_TIMEOUT = 300  # 5分钟

# 最大重连次数
MAX_RECONNECT_ATTEMPTS = 3


def is_process_alive(pid):
    """检查进程是否存活"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def check_pid():
    """检查是否已运行，清理僵尸 PID（支持启动时间检测）"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                content = f.read().strip()
            # 新格式：JSON，包含 pid 和 start_time
            # 兼容旧格式：纯 pid 数字
            try:
                pid_info = json.loads(content)
                old_pid = str(pid_info.get('pid', ''))
                start_time_str = pid_info.get('start_time', '')
            except (json.JSONDecodeError, ValueError):
                old_pid = content
                start_time_str = ''

            if old_pid and is_process_alive(old_pid):
                # 检查是否为僵尸进程：进程存在但启动超过6小时
                is_zombie = False
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        elapsed = (datetime.now() - start_time).total_seconds()
                        if elapsed > ZOMBIE_THRESHOLD_SECONDS:
                            is_zombie = True
                            logger.warning(
                                f"进程 {old_pid} 已运行 {elapsed/3600:.1f} 小时，"
                                f"超过 {ZOMBIE_THRESHOLD_SECONDS/3600:.0f} 小时阈值，视为僵尸进程"
                            )
                    except (ValueError, TypeError):
                        pass

                if is_zombie:
                    # 强制终止僵尸进程
                    logger.warning(f"强制终止僵尸进程 PID: {old_pid}")
                    try:
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        handle = kernel32.OpenProcess(0x0001, False, int(old_pid))  # PROCESS_TERMINATE
                        if handle:
                            kernel32.TerminateProcess(handle, 1)
                            kernel32.CloseHandle(handle)
                            time.sleep(2)  # 等待进程退出
                            logger.info(f"僵尸进程 {old_pid} 已终止")
                    except Exception as e:
                        logger.error(f"终止僵尸进程失败: {e}")
                    os.remove(PID_FILE)
                else:
                    logger.error(f"采集器已在运行 (PID: {old_pid})")
                    sys.exit(1)
            else:
                logger.warning(f"清理僵尸 PID 文件 (旧 PID: {old_pid} 已不存在)")
                os.remove(PID_FILE)
        except Exception as e:
            logger.warning(f"读取 PID 文件异常: {e}，清理并继续")
            os.remove(PID_FILE)

    # 写入新格式 PID 文件（包含启动时间）
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    pid_info = {
        'pid': os.getpid(),
        'start_time': datetime.now().isoformat()
    }
    with open(PID_FILE, 'w') as f:
        json.dump(pid_info, f)


def is_trading_time():
    """检查是否在交易时段"""
    now = datetime.now()
    h, m = now.hour, now.minute
    for start_h, start_m, end_h, end_m in TRADING_SESSIONS:
        if (start_h, start_m) <= (h, m) < (end_h, end_m):
            return True
    return False


def save_bar(bar):
    """保存K线到数据库"""
    try:
        with db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol, interval) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
            """, (bar['time'], bar['symbol'], '1m', bar['open'], bar['high'],
                  bar['low'], bar['close'], bar['volume'], bar['open_interest']))
            conn.commit()
            cur.close()
        logger.info(f"K线保存: {bar['time']} O:{bar['open']:.2f} H:{bar['high']:.2f} L:{bar['low']:.2f} C:{bar['close']:.2f}")
        # 每根1m线保存后，更新当前30m窗口的聚合
        aggregate_30m(bar['symbol'], bar['time'])
    except Exception as e:
        logger.error(f"保存失败: {e}")


def aggregate_30m(symbol, bar_time):
    """从1m K线聚合当前30m窗口，每���1m保存后都更新"""
    try:
        bar_30m_start = bar_time.replace(minute=(bar_time.minute // 30) * 30, second=0, microsecond=0)
        bar_30m_end = bar_30m_start + timedelta(minutes=30)
        with db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    (SELECT open FROM kline_data WHERE symbol=%s AND interval='1m' AND time >= %s AND time < %s ORDER BY time ASC LIMIT 1),
                    MAX(high), MIN(low),
                    (SELECT close FROM kline_data WHERE symbol=%s AND interval='1m' AND time >= %s AND time < %s ORDER BY time DESC LIMIT 1),
                    MAX(volume), MAX(open_interest)
                FROM kline_data WHERE symbol=%s AND interval='1m' AND time >= %s AND time < %s
            """, (symbol, bar_30m_start, bar_30m_end, symbol, bar_30m_start, bar_30m_end, symbol, bar_30m_start, bar_30m_end))
            row = cur.fetchone()
            if row and row[0] is not None:
                cur.execute("""
                    INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                    VALUES (%s, %s, '30m', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, symbol, interval) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
                """, (bar_30m_start, symbol, row[0], row[1], row[2], row[3], row[4], row[5]))
                conn.commit()
                logger.info(f"30m聚合: {bar_30m_start} O:{row[0]:.2f} H:{row[1]:.2f} L:{row[2]:.2f} C:{row[3]:.2f}")
            cur.close()
    except Exception as e:
        logger.error(f"30m聚合失败: {e}")


class MdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api

    def OnFrontConnected(self):
        global connected
        logger.info("CTP 连接成功")
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKER_ID
        req.UserID = ACCOUNT_ID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)

    def OnFrontDisconnected(self, nReason):
        global connected
        connected = False
        logger.warning(f"CTP 断线，原因: {nReason}，等待自动重连...")
        # 注：CTP API 会自动重连前置，重连成功后触发 OnFrontConnected -> OnRspUserLogin -> 重新订阅
        # 所以这里不需要手动重连，订阅逻辑在 OnRspUserLogin 中已处理

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        global connected
        if pRspInfo and pRspInfo.ErrorID != 0:
            logger.error(f"登录失败: {pRspInfo.ErrorMsg}")
            return
        logger.info("登录成功，订阅行情")
        connected = True
        self.api.SubscribeMarketData([SYMBOL.encode()], 1)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        global current_bar
        try:
            if not pDepthMarketData:
                return

            price = pDepthMarketData.LastPrice
            volume = pDepthMarketData.Volume
            oi = pDepthMarketData.OpenInterest
            now = datetime.now()
            bar_time = now.replace(second=0, microsecond=0)

            if current_bar is None or current_bar['time'] != bar_time:
                if current_bar:
                    save_bar(current_bar)
                current_bar = {
                    'time': bar_time,
                    'symbol': SYMBOL,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'open_interest': oi
                }
            else:
                current_bar['high'] = max(current_bar['high'], price)
                current_bar['low'] = min(current_bar['low'], price)
                current_bar['close'] = price
                current_bar['volume'] = volume
                current_bar['open_interest'] = oi
        except Exception as e:
            logger.error(f"Tick处理异常: {e}")


def create_md_api(flow_path):
    """创建并初始化 MdApi，返回 (api, spi)"""
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
    spi = MdSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(MD_ADDRESS)
    api.Init()
    return api, spi


def wait_for_connection(timeout=10):
    """等待连接成功，返回是否连接"""
    for _ in range(timeout):
        time.sleep(1)
        if connected:
            return True
    return False


def reconnect(api, flow_path):
    """
    主动重连：释放旧 API，重新创建连接。
    返回新的 (api, spi)，如果重连失败返回 (None, None)。
    """
    global connected, current_bar

    # 保存未完成的 bar
    if current_bar:
        save_bar(current_bar)
        current_bar = None

    for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
        logger.info(f"主动重连 第 {attempt}/{MAX_RECONNECT_ATTEMPTS} 次...")

        # 释放旧 API
        connected = False
        try:
            api.Release()
        except Exception as e:
            logger.warning(f"释放旧 API 异常（可忽略）: {e}")

        time.sleep(2)  # 等待资源释放

        # 重新创建
        try:
            api, spi = create_md_api(flow_path)
        except Exception as e:
            logger.error(f"创建 MdApi 失败: {e}")
            time.sleep(5)
            continue

        # 等待连接+登录
        if wait_for_connection(timeout=15):
            logger.info(f"重连成功（第 {attempt} 次）")
            return api, spi
        else:
            logger.warning(f"第 {attempt} 次重连超时")

    logger.error(f"重连 {MAX_RECONNECT_ATTEMPTS} 次均失败，放弃")
    return None, None


def main():
    global connected, current_bar

    check_pid()

    if not is_trading_time():
        logger.info("当前不在交易时段，退出")
        os.remove(PID_FILE)
        return

    logger.info("启动 CTP 采集器")

    flow_path = "./ctp_flow/"
    os.makedirs(flow_path, exist_ok=True)

    api, spi = create_md_api(flow_path)

    # 等待连接
    if not wait_for_connection(timeout=10):
        logger.error("连接超时")
        try:
            api.Release()
        except:
            pass
        os.remove(PID_FILE)
        return

    logger.info("采集器运行中")

    try:
        last_check = datetime.now()
        last_tick_time = datetime.now()
        while True:
            time.sleep(1)

            # 每分钟检查一次
            if (datetime.now() - last_check).total_seconds() >= 60:
                last_check = datetime.now()
                if not is_trading_time():
                    logger.info("交易时段结束，退出")
                    break

                # 检查是否长时间没收到 tick（超过5分钟触发主动重连）
                no_tick_seconds = (datetime.now() - last_tick_time).total_seconds()
                if connected and no_tick_seconds > NO_TICK_TIMEOUT:
                    logger.warning(f"超过 {NO_TICK_TIMEOUT} 秒未收到 Tick，触发主动重连")
                    api, spi = reconnect(api, flow_path)
                    if api is None:
                        logger.error("重连失败，采集器退出")
                        break
                    # 重连成功，重置计时器
                    last_tick_time = datetime.now()

            # 更新最后 tick 时间
            if current_bar and current_bar['time'] > last_tick_time.replace(second=0, microsecond=0):
                last_tick_time = datetime.now()

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
    finally:
        if current_bar:
            save_bar(current_bar)
        try:
            api.Release()
        except:
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        logger.info("采集器已关闭")


if __name__ == "__main__":
    main()
