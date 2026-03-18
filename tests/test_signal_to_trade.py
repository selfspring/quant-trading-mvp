"""
信号到交易集成测试 (Signal-to-Trade Integration Tests)
=====================================================

测试目标：验证 ML 预测信号如何正确转化为实际交易指令。
测试方法：使用真实的业务类（SignalProcessor, RiskManager, PositionManager），
         输入模拟的 ML 信号，验证完整链路的输出。

运行方式：
    python -m pytest tests/test_signal_to_trade.py -v
    或
    python -m unittest tests.test_signal_to_trade -v
"""

import unittest
from types import SimpleNamespace

from quant.risk_executor.position_manager import PositionManager
from quant.risk_executor.signal_processor import SignalProcessor, TradeIntent
from quant.risk_executor.risk_manager import RiskManager


# ============================================================================
# 辅助：构建轻量 config 对象，避免依赖 .env 和 pydantic-settings
# ============================================================================

def make_config(confidence_threshold: float = 0.65,
                max_position_ratio: float = 0.7,
                symbol: str = "au2606") -> SimpleNamespace:
    """构建测试用的最小 config 对象"""
    return SimpleNamespace(
        ml=SimpleNamespace(confidence_threshold=confidence_threshold),
        strategy=SimpleNamespace(
            symbol=symbol,
            max_position_ratio=max_position_ratio,
        ),
    )


# ============================================================================
# 测试用例
# ============================================================================

class TestSignalToTrade(unittest.TestCase):
    """ML 预测信号 → 交易指令 集成测试"""

    def setUp(self):
        """每个测试前初始化真实业务对象"""
        self.config = make_config(confidence_threshold=0.65)
        self.position_manager = PositionManager()
        self.signal_processor = SignalProcessor(self.config)
        self.risk_manager = RiskManager(self.position_manager, self.config)

    # ------------------------------------------------------------------
    # 测试 1：强看多信号 → 生成买入开仓意图
    # ------------------------------------------------------------------
    def test_strong_bullish_signal_generates_buy_open(self):
        """
        场景：ML 模型输出强看多信号，无持仓
        输入：prediction=0.02, confidence=0.8, signal=1
        预期：SignalProcessor 生成 buy/open 意图，RiskManager 放行
        """
        ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent, "高置信度看多信号应生成交易意图")

        adjusted = self.risk_manager.check_and_adjust(intent)
        self.assertIsNotNone(adjusted, "无持仓时 RiskManager 应放行")
        self.assertEqual(adjusted.direction, "buy")
        self.assertEqual(adjusted.action, "open")
        self.assertEqual(adjusted.volume, 1)

    # ------------------------------------------------------------------
    # 测试 2：强看空信号 → 生成卖出开仓意图
    # ------------------------------------------------------------------
    def test_strong_bearish_signal_generates_sell_open(self):
        """
        场景：ML 模型输出强看空信号，无持仓
        输入：prediction=-0.015, confidence=0.75, signal=-1
        预期：SignalProcessor 生成 sell/open 意图，RiskManager 放行
        """
        ml_output = {"prediction": -0.015, "confidence": 0.75, "signal": -1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent)

        adjusted = self.risk_manager.check_and_adjust(intent)
        self.assertIsNotNone(adjusted)
        self.assertEqual(adjusted.direction, "sell")
        self.assertEqual(adjusted.action, "open")
        self.assertEqual(adjusted.volume, 1)

    # ------------------------------------------------------------------
    # 测试 3：置信度不足 → 不生成交易意图
    # ------------------------------------------------------------------
    def test_low_confidence_signal_generates_no_intent(self):
        """
        场景：ML 模型输出看多信号，但置信度不足
        输入：prediction=0.005, confidence=0.25, signal=1
        预期：SignalProcessor 返回 None
        """
        ml_output = {"prediction": 0.005, "confidence": 0.25, "signal": 1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNone(intent, "置信度 0.25 < 阈值 0.65，不应生成交易意图")

    # ------------------------------------------------------------------
    # 测试 4：已有多头持仓 + 收到看空信号 → 转为平仓
    # ------------------------------------------------------------------
    def test_conflicting_signal_long_to_sell_triggers_close(self):
        """
        场景：当前持有多头 1 手，收到强看空信号
        预期：RiskManager 将 sell/open 拦截并转为 sell/close
        """
        # 模拟已有多头持仓
        self.position_manager.update_position('long', 1)

        ml_output = {"prediction": -0.015, "confidence": 0.75, "signal": -1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent)
        self.assertEqual(intent.direction, "sell")
        self.assertEqual(intent.action, "open")

        adjusted = self.risk_manager.check_and_adjust(intent)
        self.assertIsNotNone(adjusted, "持仓冲突时应生成平仓指令而非拦截")
        self.assertEqual(adjusted.direction, "sell", "平多头应使用 sell 方向")
        self.assertEqual(adjusted.action, "close", "应转为平仓指令")
        self.assertEqual(adjusted.volume, 1, "平仓手数应等于当前多头持仓")

    # ------------------------------------------------------------------
    # 测试 5：已有空头持仓 + 收到看多信号 → 转为平仓
    # ------------------------------------------------------------------
    def test_conflicting_signal_short_to_buy_triggers_close(self):
        """
        场景：当前持有空头 2 手，收到强看多信号
        预期：RiskManager 将 buy/open 拦截并转为 buy/close
        """
        self.position_manager.update_position('short', 2)

        ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent)

        adjusted = self.risk_manager.check_and_adjust(intent)
        self.assertIsNotNone(adjusted)
        self.assertEqual(adjusted.direction, "buy", "平空头应使用 buy 方向")
        self.assertEqual(adjusted.action, "close", "应转为平仓指令")
        self.assertEqual(adjusted.volume, 2, "平仓手数应等于当前空头持仓（2 手）")

    # ------------------------------------------------------------------
    # 测试 6：置信度恰好等于阈值 → 边界行为
    # ------------------------------------------------------------------
    def test_confidence_exactly_at_threshold(self):
        """
        边界条件：confidence == threshold (0.65)
        真实 SignalProcessor 使用 < 比较，所以 0.65 不小于 0.65，应生成意图
        """
        ml_output = {"prediction": 0.01, "confidence": 0.65, "signal": 1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent,
                             "置信度恰好等于阈值时应生成交易意图（< 比较）")

    # ------------------------------------------------------------------
    # 测试 7：同方向信号 + 已有持仓 → 放行（加仓）
    # ------------------------------------------------------------------
    def test_same_direction_signal_with_existing_position(self):
        """
        场景：已有多头 1 手，收到看多信号（同方向）
        预期：RiskManager 放行，不触发平仓
        """
        self.position_manager.update_position('long', 1)

        ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNotNone(intent)

        adjusted = self.risk_manager.check_and_adjust(intent)
        self.assertIsNotNone(adjusted, "同方向信号应放行")
        self.assertEqual(adjusted.action, "open", "同方向不应触发平仓")
        self.assertEqual(adjusted.direction, "buy")

    # ------------------------------------------------------------------
    # 测试 8：中性信号 → 不生成交易意图
    # ------------------------------------------------------------------
    def test_zero_signal_generates_no_intent(self):
        """
        边界条件：signal=0（中性信号）
        预期：SignalProcessor 返回 None
        """
        ml_output = {"prediction": 0.0, "confidence": 0.9, "signal": 0}

        intent = self.signal_processor.process_signal(ml_output)
        self.assertIsNone(intent, "中性信号（signal=0）不应生成交易意图")

    # ------------------------------------------------------------------
    # 测试 9：RiskManager 对 None 意图的处理
    # ------------------------------------------------------------------
    def test_risk_manager_handles_none_intent(self):
        """
        场景：SignalProcessor 返回 None（低置信度或中性信号）
        预期：RiskManager.check_and_adjust(None) 返回 None
        """
        adjusted = self.risk_manager.check_and_adjust(None)
        self.assertIsNone(adjusted, "None 意图应直接返回 None")


class TestMLPredictorOutputContract(unittest.TestCase):
    """验证 MLPredictor 输出格式契约"""

    def test_ml_output_has_required_keys(self):
        """MLPredictor 输出必须包含 prediction, confidence, signal 三个字段"""
        ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}
        required_keys = {"prediction", "confidence", "signal"}
        self.assertTrue(required_keys.issubset(ml_output.keys()))

    def test_ml_output_types_are_correct(self):
        """验证 ML 输出各字段的数据类型"""
        ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}
        self.assertIsInstance(ml_output["prediction"], float)
        self.assertIsInstance(ml_output["confidence"], float)
        self.assertIsInstance(ml_output["signal"], int)

    def test_confidence_is_bounded_0_to_1(self):
        """confidence 值应在 [0, 1] 范围内"""
        for conf in [0.0, 0.25, 0.5, 0.65, 0.8, 1.0]:
            self.assertTrue(0.0 <= conf <= 1.0)

    def test_signal_is_valid_value(self):
        """signal 值应为 -1, 0, 或 1"""
        valid_signals = {-1, 0, 1}
        for sig in [-1, 0, 1]:
            self.assertIn(sig, valid_signals)


class TestConfidenceThresholdConfig(unittest.TestCase):
    """验证置信度阈值配置的正确性"""

    def test_default_threshold_matches_config(self):
        """验证测试中使用的阈值与项目配置一致（0.65）"""
        config = make_config(confidence_threshold=0.65)
        processor = SignalProcessor(config)
        self.assertEqual(processor.confidence_threshold, 0.65)

    def test_threshold_boundary_values(self):
        """测试不同阈值下的信号过滤行为"""
        ml_output = {"prediction": 0.01, "confidence": 0.5, "signal": 1}

        # 阈值 0.3 → confidence 0.5 > 0.3 → 应生成意图
        config_low = make_config(confidence_threshold=0.3)
        processor_low = SignalProcessor(config_low)
        intent = processor_low.process_signal(ml_output)
        self.assertIsNotNone(intent, "阈值 0.3 时，confidence 0.5 应通过")

        # 阈值 0.8 → confidence 0.5 < 0.8 → 不应生成意图
        config_high = make_config(confidence_threshold=0.8)
        processor_high = SignalProcessor(config_high)
        intent = processor_high.process_signal(ml_output)
        self.assertIsNone(intent, "阈值 0.8 时，confidence 0.5 应被过滤")


class TestPositionManagerIntegration(unittest.TestCase):
    """验证 PositionManager 与风控链路的集成"""

    def test_position_manager_tracks_long(self):
        """PositionManager 正确追踪多头持仓"""
        pm = PositionManager()
        pm.update_position('long', 3)
        self.assertTrue(pm.has_long_position())
        self.assertFalse(pm.has_short_position())
        self.assertEqual(pm.get_position()['long_volume'], 3)

    def test_position_manager_tracks_short(self):
        """PositionManager 正确追踪空头持仓"""
        pm = PositionManager()
        pm.update_position('short', 2)
        self.assertFalse(pm.has_long_position())
        self.assertTrue(pm.has_short_position())
        self.assertEqual(pm.get_position()['short_volume'], 2)

    def test_position_manager_reset(self):
        """PositionManager 重置后无持仓"""
        pm = PositionManager()
        pm.update_position('long', 5)
        pm.update_position('short', 3)
        pm.reset()
        self.assertFalse(pm.has_any_position())


if __name__ == "__main__":
    unittest.main(verbosity=2)
