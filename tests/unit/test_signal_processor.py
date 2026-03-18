"""
SignalProcessor 单元测试
"""
import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quant.risk_executor.signal_processor import SignalProcessor, TradeIntent
from quant.risk_executor.position_manager import PositionManager


def test_low_confidence_no_trade(signal_processor):
    """置信度低于阈值不交易"""
    ml_output = {"prediction": 0.01, "confidence": 0.3, "signal": 1}
    result = signal_processor.process_signal(ml_output)
    assert result is None, "低置信度应返回 None"


def test_buy_signal_open(signal_processor):
    """买入信号生成开仓意图"""
    ml_output = {"prediction": 0.01, "confidence": 0.8, "signal": 1}
    result = signal_processor.process_signal(ml_output)
    assert result is not None
    assert len(result) == 1
    intent = result[0]
    assert intent.direction == "buy"
    assert intent.action == "open"
    assert intent.confidence == 0.8


def test_sell_signal_open(signal_processor):
    """卖出信号生成开仓意图"""
    ml_output = {"prediction": -0.01, "confidence": 0.8, "signal": -1}
    result = signal_processor.process_signal(ml_output)
    assert result is not None
    assert len(result) == 1
    intent = result[0]
    assert intent.direction == "sell"
    assert intent.action == "open"


def test_reverse_signal_close_and_open(signal_processor, position_manager):
    """反向信号先平后开"""
    # 模拟持有多头
    position_manager.long_volume = 1
    ml_output = {"prediction": -0.02, "confidence": 0.8, "signal": -1}
    result = signal_processor.process_signal(ml_output, position_manager)
    assert result is not None
    # 应有平仓 + 开仓（可能还有 ML 反转平仓）
    close_intents = [i for i in result if i.action == "close"]
    open_intents = [i for i in result if i.action == "open"]
    assert len(close_intents) >= 1, "应有至少一个平仓意图"
    assert len(open_intents) >= 1, "应有至少一个开仓意图"
    # 平仓方向应为 sell（平多）
    assert close_intents[0].direction == "sell"
    # 开仓方向应为 sell（开空）
    assert open_intents[0].direction == "sell"


def test_ml_reversal_close(signal_processor, position_manager):
    """ML 反转平仓：持多但预测看跌"""
    position_manager.long_volume = 1
    # 低置信度但预测为负 -> ML 反转平仓不需要置信度阈值
    ml_output = {"prediction": -0.01, "confidence": 0.3, "signal": 0}
    result = signal_processor.process_signal(ml_output, position_manager)
    assert result is not None
    # 应有平仓意图
    close_intents = [i for i in result if i.action == "close"]
    assert len(close_intents) >= 1, "ML 反转应生成平仓意图"
    assert close_intents[0].direction == "sell"
    assert "ML" in close_intents[0].reason or "反转" in close_intents[0].reason
