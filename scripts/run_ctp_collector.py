"""CTP 长驻采集进程 - 最小化版本"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from openctp_ctp import mdapi
import psycopg2

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
    """检查是否已运行，清理僵尸 PID"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            old_pid = f.read().strip()
        if old_pid and is_process_alive(old_pid):
            logger.error(f"采集器已在运行 (PID: {old_pid})")
            sys.exit(1)
        else:
            logger.warning(f"清理僵尸 PID 文件 (旧 PID: {old_pid} 已不存在)")
            os.remove(PID_FILE)
    
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def is_trading_time():
    """检查是否在交易时段"""
    now = datetime.now()
    h, m = now.hour, now.minute
    for start_h, start_m, end_h, end_m in TRADING_SESSIONS:
        if (start_h, start_m) <= (h, m) < (end_h, end_m):
            return True
    return False


def get_db_conn():
    """获取数据库连接"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='quant_trading',
        user='postgres',
        password='@Cmx1454697261'
    )


def aggregate_30m(symbol, bar_time):
    """从1m K线聚合当前30m窗口，每根1m保存后都更新"""
    try:
        from datetime import timedelta
        bar_30m_start = bar_time.replace(minute=(bar_time.minute // 30) * 30, second=0, microsecond=0)
        bar_30m_end = bar_30m_start + timedelta(minutes=30)
        conn = get_db_conn()
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
        conn.close()
    except Exception as e:
        logger.error(f"30m聚合失败: {e}")


def save_bar(bar):
    """保存K线到数据库"""
    try:
        conn = get_db_conn()
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
        conn.close()
        logger.info(f"K线保存: {bar['time']} O:{bar['open']:.2f} H:{bar['high']:.2f} L:{bar['low']:.2f} C:{bar['close']:.2f}")
        # 每根1m线保存后，更新当前30m窗口的聚合
        aggregate_30m(bar['symbol'], bar['time'])
    except Exception as e:
        logger.error(f"保存失败: {e}")


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


def main():
    check_pid()
    
    if not is_trading_time():
        logger.info("当前不在交易时段，退出")
        os.remove(PID_FILE)
        return
    
    logger.info("启动 CTP 采集器")
    
    flow_path = "./ctp_flow/"
    os.makedirs(flow_path, exist_ok=True)
    
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
    spi = MdSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(MD_ADDRESS)
    api.Init()
    
    # 等待连接
    for _ in range(10):
        time.sleep(1)
        if connected:
            break
    
    if not connected:
        logger.error("连接超时")
        os.remove(PID_FILE)
        return
    
    logger.info("采集器运行中")
    
    try:
        last_check = datetime.now()
        last_tick_time = datetime.now()
        while True:
            time.sleep(1)
            
            # 每分钟检查一次
            if (datetime.now() - last_check).seconds >= 60:
                last_check = datetime.now()
                if not is_trading_time():
                    logger.info("交易时段结束，退出")
                    break
                # 检查是否长时间没收到 tick（超过5分钟可能断连）
                if connected and current_bar and (datetime.now() - last_tick_time).seconds > 300:
                    logger.warning(f"超过5分钟未收到Tick，可能断连")
            
            # 更新最后tick时间
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
