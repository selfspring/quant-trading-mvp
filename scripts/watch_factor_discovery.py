"""
因子发现守护脚本
每 10 分钟由 Windows 定时任务触发
检查 factor_discovery 进程是否在跑，没在跑才启动
"""
import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

PID_FILE = Path('E:/quant-trading-mvp/data/factor_discovery.pid')
LOG_FILE = Path('E:/quant-trading-mvp/logs/factor_discovery.log')
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


def is_running():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        # 检查进程是否存在
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def start():
    script = 'E:/quant-trading-mvp/scripts/factor_discovery_batch3.py'
    if not Path(script).exists():
        logger.error(f'找不到因子发现脚本: {script}')
        return

    proc = subprocess.Popen(
        [sys.executable, script],
        cwd='E:/quant-trading-mvp',
        stdout=open(LOG_FILE, 'a', encoding='utf-8'),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    PID_FILE.write_text(str(proc.pid))
    logger.info(f'已启动因子发现进程 PID={proc.pid}')


if __name__ == '__main__':
    if is_running():
        logger.info('因子发现进程仍在运行，跳过')
    else:
        logger.info('因子发现进程未运行，启动...')
        start()
