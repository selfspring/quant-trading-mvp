"""
CTP 交易接口工厂函数
统一管理 CTPTradeApi 的创建，避免重复硬编码连接参数
"""
from contextlib import contextmanager
from typing import Any, Generator
import logging

logger = logging.getLogger(__name__)


def create_ctp_trade_api(config: Any) -> Any:
    """
    根据 config 创建 CTPTradeApi 实例（未连接）
    
    Args:
        config: 全局配置对象（需包含 config.ctp）
    
    Returns:
        CTPTradeApi 实例
    """
    from quant.data_collector.ctp_trade import CTPTradeApi
    return CTPTradeApi(
        broker_id=config.ctp.broker_id,
        account_id=config.ctp.account_id,
        password=config.ctp.password.get_secret_value(),
        td_address=config.ctp.td_address,
        app_id=config.ctp.app_id,
        auth_code=config.ctp.auth_code,
    )


@contextmanager
def ctp_trade_session(config: Any) -> Generator[Any, None, None]:
    """
    CTP 交易接口上下文管理器，自动连接和断开
    
    用法：
        with ctp_trade_session(config) as trade_api:
            trade_api.get_current_position(...)
    
    Args:
        config: 全局配置对象
    
    Yields:
        已连接的 CTPTradeApi 实例
    
    Raises:
        RuntimeError: 连接失败时抛出
    """
    trade_api = create_ctp_trade_api(config)
    try:
        if not trade_api.connect():
            raise RuntimeError('CTP 交易接口连接失败')
        logger.info('CTP 交易接口已连接')
        yield trade_api
    finally:
        try:
            trade_api.disconnect()
            logger.info('CTP 交易接口已断开')
        except Exception as e:
            logger.warning(f'CTP disconnect 异常（忽略）: {e}')
