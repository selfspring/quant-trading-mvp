"""天勤量化(tqsdk) 行情采集进程 - au2606 实时 1m K线 + 30m 聚合"""
import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta

sys.path.insert(0, 'E:/quant-trading-mvp')
from quant.common.config import config
from quant.common.db import db_connection

# ============ 配置 ============
SYMBOL_TQ = "SHFE.au2606"       # tqsdk 订阅用
SYMBOL_DB = "au2606"            # 数据库存储用（小写，与现有数据一致）
PID_FILE = r"E:\quant-trading-mvp\data\tq_collector.pid"
LOG_DIR = r"E:\quant-trading-mvp\logs"

# 交易时段
TRADING_SESSIONS = [
    (8, 58, 11, 30),   # 早盘（提前2分钟，定时任务08:59启动）
    (13, 28, 15, 0),   # 午盘（提前2分钟，定时任务13:29启动）
    (20, 58, 23, 59),  # 夜盘前半（提前2分钟，定时任务20:59启动）
    (0, 0, 2, 30)      # 夜盘后半（次日凌晨）
]

# 僵尸进程判定阈值（秒）
ZOMBIE_THRESHOLD_SECONDS = 6 * 3600  # 6小时

# ============ 日志 ============
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"tq_collector_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    force=True
)
logger = logging.getLogger(__name__)


# ============ 进程管理 ============
def is_process_alive(pid):
    """检查进程是否存活（Windows）"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def check_pid():
    """检查是否已运行，清理僵尸 PID"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid_info = json.loads(f.read().strip())
            old_pid = str(pid_info.get('pid', ''))
            start_time_str = pid_info.get('start_time', '')

            if old_pid and is_process_alive(old_pid):
                # 检查是否僵尸进程
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
                    logger.warning(f"强制终止僵尸进程 PID: {old_pid}")
                    try:
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        handle = kernel32.OpenProcess(0x0001, False, int(old_pid))
                        if handle:
                            kernel32.TerminateProcess(handle, 1)
                            kernel32.CloseHandle(handle)
                            time.sleep(2)
                            logger.info(f"僵尸进程 {old_pid} 已终止")
                    except Exception as e:
                        logger.error(f"终止僵尸进程失败: {e}")
                    os.remove(PID_FILE)
                else:
                    logger.error(f"天勤采集器已在运行 (PID: {old_pid})")
                    sys.exit(1)
            else:
                logger.warning(f"清理僵尸 PID 文件 (旧 PID: {old_pid} 已不存在)")
                os.remove(PID_FILE)
        except Exception as e:
            logger.warning(f"读取 PID 文件异常: {e}，清理并继续")
            os.remove(PID_FILE)

    # 写入 PID 文件
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    pid_info = {
        'pid': os.getpid(),
        'start_time': datetime.now().isoformat()
    }
    with open(PID_FILE, 'w') as f:
        json.dump(pid_info, f)


# ============ 交易时段 ============
def is_trading_time():
    """检查是否在交易时段"""
    now = datetime.now()
    h, m = now.hour, now.minute
    for start_h, start_m, end_h, end_m in TRADING_SESSIONS:
        if (start_h, start_m) <= (h, m) < (end_h, end_m):
            return True
    return False


# ============ 数据库操作 ============
def save_bar(bar_time, open_p, high_p, low_p, close_p, volume, oi):
    """保存 1m K线到数据库"""
    try:
        with db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO kline_data (time, symbol, interval, open, high, low, close, volume, open_interest)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol, interval) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, volume=EXCLUDED.volume, open_interest=EXCLUDED.open_interest
            """, (bar_time, SYMBOL_DB, '1m', open_p, high_p, low_p, close_p, volume, oi))
            conn.commit()
            cur.close()
        logger.info(f"1m K线保存: {bar_time} O:{open_p:.2f} H:{high_p:.2f} L:{low_p:.2f} C:{close_p:.2f} V:{volume}")
        # 每根 1m 线保存后，更新当前 30m 窗口聚合
        aggregate_30m(SYMBOL_DB, bar_time)
    except Exception as e:
        logger.error(f"保存 1m K线失败: {e}")


def aggregate_30m(symbol, bar_time):
    """从 1m K线聚合当前 30m 窗口，每根 1m 保存后都更新"""
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


# ============ 主逻辑 ============
def main():
    check_pid()

    if not is_trading_time():
        logger.info("当前不在交易时段，退出")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return

    logger.info(f"启动天勤采集器，合约: {SYMBOL_TQ}")

    # 延迟导入 tqsdk（避免非交易时段也加载）
    from tqsdk import TqApi, TqAuth

    try:
        # 天勤账号登录（免费版也需要 auth）
        api = TqApi(auth=TqAuth("17340696348", "@Cmx1454697261"))
    except Exception as e:
        logger.warning(f"TqAuth 登录失败({e})，尝试无 auth 创建")
        try:
            api = TqApi()
        except Exception as e2:
            logger.error(f"TqApi 创建失败: {e2}")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return

    logger.info("天勤 API 初始化成功")

    # 获取 1 分钟 K 线序列（tqsdk 自动维护更新）
    klines = api.get_kline_serial(SYMBOL_TQ, 60, data_length=10)

    # 记录已处理的最后一根 K 线时间，避免重复保存
    last_saved_dt = None

    try:
        while True:
            api.wait_update()

            # 每次更新后检查交易时段
            if not is_trading_time():
                logger.info("交易时段结束，退出")
                break

            # 检查 K 线是否有更新
            if api.is_changing(klines):
                # 取倒数第二根（已完成的 K 线），倒数第一根是当前未完成的
                if len(klines) >= 2:
                    bar = klines.iloc[-2]
                    # tqsdk 的 datetime 是纳秒时间戳
                    bar_dt_ns = bar['datetime']
                    bar_dt = datetime.fromtimestamp(bar_dt_ns / 1e9)
                    bar_time = bar_dt.replace(second=0, microsecond=0)

                    # 只保存新的已完成 K 线
                    if last_saved_dt is None or bar_time > last_saved_dt:
                        save_bar(
                            bar_time=bar_time,
                            open_p=float(bar['open']),
                            high_p=float(bar['high']),
                            low_p=float(bar['low']),
                            close_p=float(bar['close']),
                            volume=int(bar['volume']),
                            oi=float(bar.get('open_interest', bar.get('close_oi', 0)))
                        )
                        last_saved_dt = bar_time

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
    finally:
        try:
            api.close()
        except Exception:
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        logger.info("天勤采集器已关闭")


if __name__ == "__main__":
    main()
