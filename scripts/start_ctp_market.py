"""
CTP 行情采集启动脚本
处理配置加载、异常重连、日志记录
"""
import sys
import os
import time
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quant.data_collector.ctp_market import run_collector
from quant.common.config import config

# 配置日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/ctp_market.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("CTP 行情采集器启动")
    logger.info("=" * 60)
    logger.info(f"  broker_id={config.ctp.broker_id}")
    logger.info(f"  account_id={config.ctp.account_id}")
    logger.info(f"  md_address={config.ctp.md_address}")
    logger.info(f"  symbol={config.strategy.symbol}")

    max_retries = 5
    retry_delay = 10
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(f"启动采集器 (尝试 {retry_count + 1}/{max_retries})")
            run_collector(
                broker_id=config.ctp.broker_id,
                user_id=config.ctp.account_id,
                password=config.ctp.password.get_secret_value(),
                md_address=config.ctp.md_address,
                symbols=[config.strategy.symbol]
            )
            logger.info("采集器正常退出")
            break

        except KeyboardInterrupt:
            logger.info("收到中断信号，退出")
            break

        except Exception as e:
            retry_count += 1
            logger.error(f"采集器异常: {e} (重试 {retry_count}/{max_retries})")
            if retry_count < max_retries:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                logger.error("达到最大重试次数，退出")
                sys.exit(1)

    logger.info("CTP 行情采集器已停止")


if __name__ == "__main__":
    main()
