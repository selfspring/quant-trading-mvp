"""
持仓管理器
负责记录和更新多空持仓数量
"""
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class PositionManager:
    """持仓管理器"""
    
    def __init__(self):
        """初始化持仓管理器"""
        self.long_volume: int = 0  # 多头持仓数量
        self.short_volume: int = 0  # 空头持仓数量
        logger.info("PositionManager 初始化完成")
    
    def update_position(self, direction: str, volume: int) -> None:
        """
        更新持仓
        
        Args:
            direction: 方向 ('long' 或 'short')
            volume: 变化量（正数增加，负数减少）
        """
        if direction == 'long':
            self.long_volume += volume
            self.long_volume = max(0, self.long_volume)  # 确保不为负
            logger.info(f"更新多头持仓: {volume:+d}, 当前多头: {self.long_volume}")
        elif direction == 'short':
            self.short_volume += volume
            self.short_volume = max(0, self.short_volume)  # 确保不为负
            logger.info(f"更新空头持仓: {volume:+d}, 当前空头: {self.short_volume}")
        else:
            logger.warning(f"未知的持仓方向: {direction}")
    
    def get_position(self) -> Dict[str, int]:
        """
        获取当前持仓
        
        Returns:
            包含多空持仓的字典
        """
        return {
            'long_volume': self.long_volume,
            'short_volume': self.short_volume
        }
    
    def has_long_position(self) -> bool:
        """是否有多头持仓"""
        return self.long_volume > 0
    
    def has_short_position(self) -> bool:
        """是否有空头持仓"""
        return self.short_volume > 0
    
    def has_any_position(self) -> bool:
        """是否有任何持仓"""
        return self.has_long_position() or self.has_short_position()
    
    def reset(self) -> None:
        """重置所有持仓"""
        logger.info(f"重置持仓 - 多头: {self.long_volume}, 空头: {self.short_volume}")
        self.long_volume = 0
        self.short_volume = 0

    def sync_from_ctp(self, td_api) -> None:
        """
        从 CTP 交易接口同步真实持仓，覆盖本地内存状态。
        应在系统启动、断线重连后调用，确保风控基于交易所真实仓位。

        Args:
            td_api: CTP 交易 API 实例，需提供 get_current_position() 方法
        """
        try:
            position_data = td_api.get_current_position()
            # 解析多头和空头的真实数量
            self.long_volume = int(position_data.get('long_volume', 0))
            self.short_volume = int(position_data.get('short_volume', 0))
            logger.info(f"已从 CTP 同步真实持仓 - 多头: {self.long_volume}, 空头: {self.short_volume}")
        except Exception as e:
            logger.error(f"从 CTP 同步持仓失败: {e}，本地持仓状态未更新")
            raise
