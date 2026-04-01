"""
RiskManager 单元测试
"""
import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quant.risk_executor.risk_manager import RiskManager
from quant.risk_executor.signal_processor import TradeIntent


def test_stop_loss_triggered(risk_manager):
    """止损触发：多头持仓，价格跌破止损"""
    open_positions = [{
        "direction": "buy",
        "entry_price": 600.0,
        "stop_loss": 595.0,
        "take_profit": 610.0,
        "volume": 1,
    }]
    # 当前价 594 < 止损 595
    intents = risk_manager.check_stop_loss_take_profit(594.0, open_positions)
    assert len(intents) == 1
    assert intents[0].action == "close"
    assert intents[0].direction == "sell"  # 平多


def test_take_profit_triggered(risk_manager):
    """止盈触发：多头持仓，价格突破止盈"""
    open_positions = [{
        "direction": "buy",
        "entry_price": 600.0,
        "stop_loss": 595.0,
        "take_profit": 610.0,
        "volume": 1,
    }]
    # 当前价 611 >= 止盈 610
    intents = risk_manager.check_stop_loss_take_profit(611.0, open_positions)
    assert len(intents) == 1
    assert intents[0].action == "close"
    assert intents[0].direction == "sell"


def test_no_stop_triggered(risk_manager):
    """未触发止损止盈：价格在止损止盈之间"""
    open_positions = [{
        "direction": "buy",
        "entry_price": 600.0,
        "stop_loss": 595.0,
        "take_profit": 610.0,
        "volume": 1,
    }]
    # 当前价 602，在 595~610 之间
    intents = risk_manager.check_stop_loss_take_profit(602.0, open_positions)
    assert len(intents) == 0


def test_calc_stop_loss_take_profit_buy():
    """多头止损止盈计算"""
    result = RiskManager.calc_stop_loss_take_profit("buy", 600.0, 0.02)
    # 止盈 = 600 * (1 + 0.02 * 1.25) = 600 * 1.025 = 615.0
    assert result["take_profit"] == 615.0
    # 止损 = 600 * (1 - 0.02 * 0.5) = 600 * 0.99 = 594.0
    assert result["stop_loss"] == 594.0
    # 盈亏比应约为 2:1
    profit = result["take_profit"] - 600.0
    loss = 600.0 - result["stop_loss"]
    assert abs(profit / loss - 2.5) < 0.01, f"盈亏比 {profit/loss:.2f} 不符合预期 2.5"


def test_calc_stop_loss_take_profit_sell():
    """空头止损止盈计算"""
    result = RiskManager.calc_stop_loss_take_profit("sell", 600.0, 0.02)
    # 止盈 = 600 * (1 - 0.02 * 1.25) = 600 * 0.975 = 585.0
    assert result["take_profit"] == 585.0
    # 止损 = 600 * (1 + 0.02 * 0.5) = 600 * 1.01 = 606.0
    assert result["stop_loss"] == 606.0
    # 空头：止损在上方，止盈在下方
    assert result["stop_loss"] > 600.0
    assert result["take_profit"] < 600.0
