"""
天勤交易接口工厂函数
统一管理 TqTradeApi 的创建
"""
import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


def create_tq_trade_api(config: Any) -> Any:
    """
    根据 config 创建 TqTradeApi 实例（未连接）

    Args:
        config: 全局配置对象（需包含 config.ctp）

    Returns:
        TqTradeApi 实例
    """
    from quant.data_collector.tq_trade import TqTradeApi
    return TqTradeApi(
        account_id=config.ctp.account_id,
        password=config.ctp.password.get_secret_value(),
    )


@contextmanager
def tq_trade_session(config: Any) -> Generator[Any, None, None]:
    """
    天勤交易接口上下文管理器，自动连接和断开

    用法：
        with tq_trade_session(config) as trade_api:
            trade_api.get_position(...)

    Args:
        config: 全局配置对象

    Yields:
        已连接的天勤 TqTradeApi 实例

    Raises:
        RuntimeError: 连接失败时抛出
    """
    trade_api = create_tq_trade_api(config)
    try:
        if not trade_api.connect():
            raise RuntimeError('天勤交易接口连接失败')
        if not trade_api.login():
            raise RuntimeError('天勤交易接口登录失败')
        logger.info('天勤快期模拟盘已连接')
        yield trade_api
    finally:
        try:
            trade_api.close()
            logger.info('天勤交易接口已关闭')
        except Exception:
            pass
