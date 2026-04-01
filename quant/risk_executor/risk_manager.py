"""
风控管理器
处理持仓冲突，反向信号自动转平仓，止损止盈检查
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .position_manager import PositionManager
from .signal_processor import TradeIntent

logger = logging.getLogger(__name__)


class RiskManager:
    """风控管理器"""

    def __init__(self, position_manager: PositionManager, config):
        """
        初始化风控管理器

        Args:
            position_manager: 持仓管理器实例
            config: 配置对象
        """
        self.position_manager = position_manager
        self.max_position_ratio = config.strategy.max_position_ratio
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3  # 连败熔断阈值
        self.circuit_break_minutes = 60  # 熔断暂停时长（分钟）
        self.last_trade_time = None
        self.circuit_break_until = None  # 熔断解除时间
        logger.info(f"RiskManager 初始化完成，最大仓位比例: {self.max_position_ratio}，连败熔断: {self.max_consecutive_losses} 次")

    def check_stop_loss_take_profit(self, current_price: float, open_positions: List[Dict]) -> List[TradeIntent]:
        """
        平仓方式2：止损止盈检查

        Args:
            current_price: 当前价格
            open_positions: 持仓列表，每个元素包含:
                - direction: 'buy' 或 'sell'
                - entry_price: 开仓价格
                - predicted_return: 预测收益率
                - stop_loss: 止损价
                - take_profit: 止盈价
                - volume: 持仓量

        Returns:
            需要平仓的 TradeIntent 列表
        """
        close_intents = []

        for pos in open_positions:
            direction = pos.get('direction')
            pos.get('entry_price', 0)
            stop_loss = pos.get('stop_loss', 0)
            take_profit = pos.get('take_profit', 0)
            volume = pos.get('volume', 1)

            if direction == 'buy':
                # 多头：当前价 >= 止盈价 或 当前价 <= 止损价
                if current_price >= take_profit:
                    intent = TradeIntent(
                        direction='sell', action='close',
                        confidence=1.0, volume=volume,
                        reason=f'止盈平多: 当前{current_price:.2f} >= 止盈{take_profit:.2f}'
                    )
                    logger.info(f"触发止盈平多: {intent}")
                    close_intents.append(intent)
                elif current_price <= stop_loss:
                    intent = TradeIntent(
                        direction='sell', action='close',
                        confidence=1.0, volume=volume,
                        reason=f'止损平多: 当前{current_price:.2f} <= 止损{stop_loss:.2f}'
                    )
                    logger.warning(f"触发止损平多: {intent}")
                    close_intents.append(intent)

            elif direction == 'sell':
                # 空头：当前价 <= 止盈价 或 当前价 >= 止损价
                if current_price <= take_profit:
                    intent = TradeIntent(
                        direction='buy', action='close',
                        confidence=1.0, volume=volume,
                        reason=f'止盈平空: 当前{current_price:.2f} <= 止盈{take_profit:.2f}'
                    )
                    logger.info(f"触发止盈平空: {intent}")
                    close_intents.append(intent)
                elif current_price >= stop_loss:
                    intent = TradeIntent(
                        direction='buy', action='close',
                        confidence=1.0, volume=volume,
                        reason=f'止损平空: 当前{current_price:.2f} >= 止损{stop_loss:.2f}'
                    )
                    logger.warning(f"触发止损平空: {intent}")
                    close_intents.append(intent)

        return close_intents

    @staticmethod
    def calc_stop_loss_take_profit(direction: str, entry_price: float, predicted_return: float) -> Dict:
        """
        根据开仓价和预测收益率计算止损止盈价
        盈亏比 2:1 => 止盈 = predicted_return * 1.25, 止损 = predicted_return * 0.5

        Args:
            direction: 'buy' 或 'sell'
            entry_price: 开仓价格
            predicted_return: 预测收益率（绝对值）

        Returns:
            包含 stop_loss 和 take_profit 的字典
        """
        abs_return = abs(predicted_return)
        if direction == 'buy':
            take_profit = entry_price * (1 + abs_return * 1.25)
            stop_loss = entry_price * (1 - abs_return * 0.5)
        else:  # sell
            take_profit = entry_price * (1 - abs_return * 1.25)
            stop_loss = entry_price * (1 + abs_return * 0.5)
        return {
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2)
        }

    def record_trade_result(self, pnl: float):
        """
        记录交易结果，更新连败计数

        Args:
            pnl: 本次交易盈亏（正数=盈利，负数=亏损）
        """
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"亏损交易，连败计数: {self.consecutive_losses}/{self.max_consecutive_losses}")
            if self.consecutive_losses >= self.max_consecutive_losses:
                from datetime import timedelta
                self.circuit_break_until = datetime.now() + timedelta(minutes=self.circuit_break_minutes)
                logger.warning(f"触发连败熔断！暂停交易至 {self.circuit_break_until.strftime('%H:%M')}")
        else:
            if self.consecutive_losses > 0:
                logger.info(f"盈利交易，重置连败计数（原: {self.consecutive_losses}）")
            self.consecutive_losses = 0
            self.circuit_break_until = None

    def check_and_adjust(self, intent: Optional[TradeIntent]) -> Optional[TradeIntent]:
        """
        检查并调整交易意图

        Args:
            intent: 原始交易意图

        Returns:
            调整后的交易意图或 None（拦截）
        """
        if intent is None:
            return None

        # 连败熔断检查（仅对开仓指令生效，平仓不受限）
        if intent.action == 'open':
            if self.consecutive_losses >= self.max_consecutive_losses:
                # 检查熔断是否已过期
                if self.circuit_break_until is None:
                    self.circuit_break_until = datetime.now().replace(second=0, microsecond=0)
                    from datetime import timedelta
                    self.circuit_break_until = datetime.now() + timedelta(minutes=self.circuit_break_minutes)
                if datetime.now() < self.circuit_break_until:
                    remaining = (self.circuit_break_until - datetime.now()).seconds // 60
                    logger.warning(f"连败熔断生效！连败 {self.consecutive_losses} 次，暂停交易，剩余 {remaining} 分钟")
                    return None
                else:
                    # 熔断期已过，重置
                    logger.info("熔断期已过，恢复交易，重置连败计数")
                    self.consecutive_losses = 0
                    self.circuit_break_until = None

        # 获取当前持仓
        has_long = self.position_manager.has_long_position()
        has_short = self.position_manager.has_short_position()

        # 规则 1: 如果没有持仓，直接放行开仓指令
        if not has_long and not has_short:
            logger.info(f"无持仓，放行开仓指令: {intent}")
            return intent

        # 规则 2: 如果已有多头持仓，且收到看多/买入指令
        if has_long and intent.direction == 'buy' and intent.action == 'open':
            if self.position_manager.long_volume >= 3:
                logger.warning(f"多头持仓已达上限 {self.position_manager.long_volume} 手，拦截加仓")
                return None
            logger.info(f"已有多头持仓，继续看多，放行: {intent}")
            return intent

        # 规则 3: 如果已有多头持仓，但收到看空/卖出指令
        if has_long and intent.direction == 'sell' and intent.action == 'open':
            # 拦截开空，修改为平多
            logger.warning("已有多头持仓，收到看空信号，拦截开空并转为平多")
            adjusted_intent = TradeIntent(
                direction='sell',
                action='close',  # 修改为平仓
                confidence=intent.confidence,
                volume=self.position_manager.long_volume  # 平掉所有多头
            )
            logger.info(f"调整后的交易意图: {adjusted_intent}")
            return adjusted_intent

        # 规则 4: 如果已有空头持仓，且收到看空/卖出指令
        if has_short and intent.direction == 'sell' and intent.action == 'open':
            if self.position_manager.short_volume >= 3:
                logger.warning(f"空头持仓已达上限 {self.position_manager.short_volume} 手，拦截加仓")
                return None
            logger.info(f"已有空头持仓，继续看空，放行: {intent}")
            return intent

        # 规则 4: 如果已有空头持仓，但收到看多/买入指令
        if has_short and intent.direction == 'buy' and intent.action == 'open':
            # 拦截开多，修改为平空
            logger.warning("已有空头持仓，收到看多信号，拦截开多并转为平空")
            adjusted_intent = TradeIntent(
                direction='buy',
                action='close',  # 修改为平仓
                confidence=intent.confidence,
                volume=self.position_manager.short_volume  # 平掉所有空头
            )
            logger.info(f"调整后的交易意图: {adjusted_intent}")
            return adjusted_intent

        # 其他情况：平仓指令直接放行
        if intent.action == 'close':
            logger.info(f"平仓指令，直接放行: {intent}")
            return intent

        # 未匹配的情况，拦截
        logger.warning(f"未匹配的交易意图，拦截: {intent}")
        return None
