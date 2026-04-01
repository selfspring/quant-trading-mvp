"""
信号处理器
将 ML 模型输出转换为交易意图
支持三种平仓逻辑：反向信号平仓、止损止盈平仓、ML预测反转平仓
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TradeIntent:
    """交易意图"""

    def __init__(self, direction: str, action: str, confidence: float, volume: int = 1, reason: str = ''):
        """
        初始化交易意图

        Args:
            direction: 方向 ('buy' 或 'sell')
            action: 动作 ('open' 或 'close')
            confidence: 置信度
            volume: 交易量（默认1手）
            reason: 平仓原因（用于日志）
        """
        self.direction = direction
        self.action = action
        self.confidence = confidence
        self.volume = volume
        self.reason = reason

    def __repr__(self) -> str:
        reason_str = f", reason={self.reason}" if self.reason else ""
        return f"TradeIntent(direction={self.direction}, action={self.action}, confidence={self.confidence:.2f}, volume={self.volume}{reason_str})"


class SignalProcessor:
    """信号处理器"""

    def __init__(self, config):
        """
        初始化信号处理器

        Args:
            config: 配置对象（需要包含 ml.confidence_threshold）
        """
        self.confidence_threshold = config.ml.confidence_threshold
        logger.info(f"SignalProcessor 初始化完成，置信度阈值: {self.confidence_threshold}")

    def process_signal(self, ml_output: Dict, position_manager=None) -> Optional[List[TradeIntent]]:
        """
        处理 ML 模型输出信号，支持平仓逻辑

        包含：
        - 平仓方式1：反向信号平仓（持多收到sell信号 / 持空收到buy信号）
        - 平仓方式3：ML预测反转平仓（持多时预测收益<0 / 持空时预测收益>0）

        Args:
            ml_output: ML 模型输出，格式如 {"prediction": 0.02, "confidence": 0.8, "signal": 1}
            position_manager: 持仓管理器（可选，传入后启用平仓逻辑）

        Returns:
            TradeIntent 列表（可能包含平仓+开仓），或 None
        """
        confidence = ml_output.get('confidence', 0.0)
        signal = ml_output.get('signal', 0)
        prediction = ml_output.get('prediction', 0.0)

        intents = []

        # === 平仓方式3：ML预测反转平仓（不需要置信度阈值） ===
        if position_manager is not None:
            has_long = position_manager.has_long_position()
            has_short = position_manager.has_short_position()

            if has_long and prediction < 0:
                # 持多但ML预测看跌 -> 平多
                close_intent = TradeIntent(
                    direction='sell',
                    action='close',
                    confidence=confidence,
                    volume=position_manager.long_volume,
                    reason='ML预测反转平仓'
                )
                logger.info(f"ML预测反转: 持多但预测收益={prediction:.4f}<0, 平多: {close_intent}")
                intents.append(close_intent)

            if has_short and prediction > 0:
                # 持空但ML预测看涨 -> 平空
                close_intent = TradeIntent(
                    direction='buy',
                    action='close',
                    confidence=confidence,
                    volume=position_manager.short_volume,
                    reason='ML预测反转平仓'
                )
                logger.info(f"ML预测反转: 持空但预测收益={prediction:.4f}>0, 平空: {close_intent}")
                intents.append(close_intent)

        # === 置信度过滤（开仓和反向信号平仓需要达到阈值） ===
        if confidence < self.confidence_threshold:
            if intents:
                logger.info(f"置信度不足开仓 ({confidence:.2f} < {self.confidence_threshold})，仅执行ML反转平仓")
                return intents
            logger.info(f"置信度不足 ({confidence:.2f} < {self.confidence_threshold})，不交易")
            return None

        # === 平仓方式1：反向信号平仓 ===
        if position_manager is not None:
            has_long = position_manager.has_long_position()
            has_short = position_manager.has_short_position()

            if has_long and signal == -1:
                # 持多收到sell信号 -> 先平多
                # 检查是否已经由ML反转生成了平仓意图
                already_closing = any(i.action == 'close' and i.direction == 'sell' for i in intents)
                if not already_closing:
                    close_intent = TradeIntent(
                        direction='sell',
                        action='close',
                        confidence=confidence,
                        volume=position_manager.long_volume,
                        reason='反向信号平仓'
                    )
                    logger.info(f"反向信号: 持多收到sell, 平多: {close_intent}")
                    intents.append(close_intent)

                # 平仓后反向开仓
                open_intent = TradeIntent(
                    direction='sell',
                    action='open',
                    confidence=confidence,
                    volume=1
                )
                logger.info(f"反向开仓: {open_intent}")
                intents.append(open_intent)
                return intents

            if has_short and signal == 1:
                # 持空收到buy信号 -> 先平空
                already_closing = any(i.action == 'close' and i.direction == 'buy' for i in intents)
                if not already_closing:
                    close_intent = TradeIntent(
                        direction='buy',
                        action='close',
                        confidence=confidence,
                        volume=position_manager.short_volume,
                        reason='反向信号平仓'
                    )
                    logger.info(f"反向信号: 持空收到buy, 平空: {close_intent}")
                    intents.append(close_intent)

                # 平仓后反向开仓
                open_intent = TradeIntent(
                    direction='buy',
                    action='open',
                    confidence=confidence,
                    volume=1
                )
                logger.info(f"反向开仓: {open_intent}")
                intents.append(open_intent)
                return intents

        # === 常规开仓逻辑 ===
        if signal == 1:
            intent = TradeIntent(
                direction='buy',
                action='open',
                confidence=confidence,
                volume=1
            )
            logger.info(f"生成看多交易意图: {intent}")
            intents.append(intent)
        elif signal == -1:
            intent = TradeIntent(
                direction='sell',
                action='open',
                confidence=confidence,
                volume=1
            )
            logger.info(f"生成看空交易意图: {intent}")
            intents.append(intent)
        else:
            if intents:
                logger.info("中性信号，仅执行已有平仓意图")
                return intents
            logger.info(f"中性信号 (signal={signal})，不交易")
            return None

        return intents if intents else None
