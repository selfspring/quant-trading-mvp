"""
主策略引擎测试 (Main Strategy Engine Tests)
==========================================

测试目标：验证 QuantTradingEngine 的完整生命周期和策略执行流程。
测试方法：使用 Mock 对象模拟外部依赖（CTP API、ML预测器等），
         验证引擎的初始化、策略循环、异常处理和优雅关闭。

运行方式：
    python -m pytest tests/test_main_strategy.py -v
    或
    python -m unittest tests.test_main_strategy -v
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import time
from types import SimpleNamespace

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock 所有导入，避免 main_strategy.py 的导入错误
sys.modules['quant.data_collector.ctp_market'] = MagicMock()
sys.modules['quant.data_collector.ctp_trade'] = MagicMock()
sys.modules['quant.signal_generator.ml_predictor'] = MagicMock()
sys.modules['quant.risk_executor.position_manager'] = MagicMock()
sys.modules['quant.risk_executor.signal_processor'] = MagicMock()
sys.modules['quant.risk_executor.risk_manager'] = MagicMock()
sys.modules['quant.risk_executor.trade_executor'] = MagicMock()

from scripts.main_strategy import QuantTradingEngine


# ============================================================================
# 辅助：构建测试用的 config 对象
# ============================================================================

def make_test_config():
    """构建测试用的最小 config 对象"""
    return SimpleNamespace(
        ctp=SimpleNamespace(
            broker_id="9999",
            account_id="test_account",
            password=SimpleNamespace(get_secret_value=lambda: "test_password"),
            md_address="tcp://test_md:41213",
            td_address="tcp://test_td:41205",
            app_id="test_app",
            auth_code="test_auth"
        ),
        strategy=SimpleNamespace(
            symbol="au2606",
            max_position_ratio=0.7
        ),
        ml=SimpleNamespace(
            confidence_threshold=0.65
        )
    )


# ============================================================================
# 测试用例
# ============================================================================

class TestEngineInitialization(unittest.TestCase):
    """测试引擎初始化"""
    
    @patch('quant.common.config.config', make_test_config())
    def test_engine_initialization(self):
        """测试所有组件能否正确实例化"""
        # Arrange
        engine = QuantTradingEngine()
        
        # Mock 所有组件的构造函数
        with patch('scripts.main_strategy.CTPMarketApi') as mock_market, \
             patch('scripts.main_strategy.CTPTradeApi') as mock_trade, \
             patch('scripts.main_strategy.MLPredictor') as mock_ml, \
             patch('scripts.main_strategy.PositionManager') as mock_position, \
             patch('scripts.main_strategy.SignalProcessor') as mock_signal, \
             patch('scripts.main_strategy.RiskManager') as mock_risk, \
             patch('scripts.main_strategy.TradeExecutor') as mock_executor:
            
            # Act
            result = engine.initialize()
            
            # Assert
            self.assertTrue(result, "初始化应该成功")
            self.assertIsNotNone(engine.market_api, "行情API应该被初始化")
            self.assertIsNotNone(engine.trade_api, "交易API应该被初始化")
            self.assertIsNotNone(engine.ml_predictor, "ML预测器应该被初始化")
            self.assertIsNotNone(engine.position_manager, "持仓管理器应该被初始化")
            self.assertIsNotNone(engine.signal_processor, "信号处理器应该被初始化")
            self.assertIsNotNone(engine.risk_manager, "风控管理器应该被初始化")
            self.assertIsNotNone(engine.trade_executor, "交易执行器应该被初始化")
            
            # 验证各组件被正确调用
            mock_market.assert_called_once()
            mock_trade.assert_called_once()
            mock_ml.assert_called_once()
            mock_position.assert_called_once()
            mock_signal.assert_called_once()
            mock_risk.assert_called_once()
            mock_executor.assert_called_once()
    
    @patch('quant.common.config.config', make_test_config())
    def test_initialization_failure(self):
        """测试初始化失败时的异常处理"""
        # Arrange
        engine = QuantTradingEngine()
        
        # Mock 行情API抛出异常
        with patch('scripts.main_strategy.CTPMarketApi', side_effect=Exception("连接失败")):
            # Act
            result = engine.initialize()
            
            # Assert
            self.assertFalse(result, "初始化失败应该返回 False")


class TestStrategyExecution(unittest.TestCase):
    """测试策略执行流程"""
    
    def setUp(self):
        """每个测试前初始化引擎和 Mock 对象"""
        self.engine = QuantTradingEngine()
        
        # Mock 所有依赖
        self.engine.market_api = Mock()
        self.engine.trade_api = Mock()
        self.engine.ml_predictor = Mock()
        self.engine.position_manager = Mock()
        self.engine.signal_processor = Mock()
        self.engine.risk_manager = Mock()
        self.engine.trade_executor = Mock()
    
    def test_strategy_cycle_with_strong_signal(self):
        """测试强信号的完整策略循环"""
        # Arrange - 模拟强信号（高置信度）
        ml_signal = {
            "prediction": 0.025,
            "confidence": 0.85,
            "signal": 1
        }
        
        trade_intent = {
            "symbol": "au2606",
            "direction": "BUY",
            "volume": 2,
            "reason": "ML强信号"
        }
        
        final_order = {
            "symbol": "au2606",
            "direction": "BUY",
            "volume": 1,  # 风控调整后
            "price_type": "MARKET"
        }
        
        # 配置 Mock 返回值
        self.engine.signal_processor.process.return_value = trade_intent
        self.engine.risk_manager.check.return_value = final_order
        
        # Act
        self.engine.run_strategy_cycle()
        
        # Assert - 验证完整链路
        self.engine.signal_processor.process.assert_called_once()
        self.engine.risk_manager.check.assert_called_once_with(trade_intent)
        self.engine.trade_executor.execute_order.assert_called_once_with(final_order)
    
    def test_strategy_cycle_with_weak_signal(self):
        """测试弱信号被过滤的情况"""
        # Arrange - 模拟弱信号（低置信度）
        ml_signal = {
            "prediction": 0.005,
            "confidence": 0.45,
            "signal": 1
        }
        
        # 信号处理器返回 None（置信度不足）
        self.engine.signal_processor.process.return_value = None
        
        # Act
        self.engine.run_strategy_cycle()
        
        # Assert - 验证信号被过滤，不执行后续步骤
        self.engine.signal_processor.process.assert_called_once()
        self.engine.risk_manager.check.assert_not_called()
        self.engine.trade_executor.execute_order.assert_not_called()
    
    def test_strategy_cycle_risk_rejection(self):
        """测试风控拦截的情况"""
        # Arrange
        trade_intent = {
            "symbol": "au2606",
            "direction": "BUY",
            "volume": 10,  # 超大仓位
            "reason": "ML信号"
        }
        
        # 信号处理器通过，但风控拦截
        self.engine.signal_processor.process.return_value = trade_intent
        self.engine.risk_manager.check.return_value = None  # 风控拒绝
        
        # Act
        self.engine.run_strategy_cycle()
        
        # Assert - 验证风控拦截，不执行交易
        self.engine.signal_processor.process.assert_called_once()
        self.engine.risk_manager.check.assert_called_once_with(trade_intent)
        self.engine.trade_executor.execute_order.assert_not_called()
    
    def test_strategy_cycle_exception_handling(self):
        """测试策略循环中的异常处理"""
        # Arrange - 模拟信号处理器抛出异常
        self.engine.signal_processor.process.side_effect = Exception("信号处理失败")
        
        # Act - 不应该抛出异常，应该被捕获
        try:
            self.engine.run_strategy_cycle()
            exception_caught = True
        except Exception:
            exception_caught = False
        
        # Assert
        self.assertTrue(exception_caught, "异常应该被捕获，不影响主循环")
        self.engine.trade_executor.execute_order.assert_not_called()


class TestPositionSync(unittest.TestCase):
    """测试持仓同步"""
    
    @patch('quant.common.config.config', make_test_config())
    def test_position_sync(self):
        """测试持仓同步功能"""
        # Arrange
        engine = QuantTradingEngine()
        engine.trade_api = Mock()
        engine.position_manager = Mock()
        
        # Mock CTP返回的持仓数据
        mock_positions = [
            {"symbol": "au2606", "direction": "LONG", "volume": 2},
            {"symbol": "ag2606", "direction": "SHORT", "volume": 1}
        ]
        engine.trade_api.query_positions.return_value = mock_positions
        
        # Act
        result = engine.connect()
        
        # Assert
        self.assertTrue(result, "连接应该成功")
        engine.position_manager.sync_from_ctp.assert_called_once_with(engine.trade_api)


class TestGracefulShutdown(unittest.TestCase):
    """测试优雅关闭"""
    
    def test_graceful_shutdown(self):
        """测试引擎能否优雅关闭"""
        # Arrange
        engine = QuantTradingEngine()
        engine.market_api = Mock()
        engine.trade_api = Mock()
        engine.running = True
        
        # Act
        engine.shutdown()
        
        # Assert
        self.assertFalse(engine.running, "running 标志应该被设置为 False")
        # 注意：由于代码中 disconnect 被注释，这里不验证断开连接
    
    @patch('time.sleep', return_value=None)  # 跳过等待
    def test_main_loop_interruption(self, mock_sleep):
        """测试主循环能否响应中断信号"""
        # Arrange
        engine = QuantTradingEngine()
        engine.market_api = Mock()
        engine.trade_api = Mock()
        engine.ml_predictor = Mock()
        engine.position_manager = Mock()
        engine.signal_processor = Mock()
        engine.risk_manager = Mock()
        engine.trade_executor = Mock()
        
        # 模拟信号处理返回 None（快速跳过）
        engine.signal_processor.process.return_value = None
        
        # 模拟运行 2 次循环后停止
        call_count = [0]
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] >= 2:
                engine.running = False
        
        mock_sleep.side_effect = side_effect
        
        # Act
        engine.main_loop()
        
        # Assert
        self.assertFalse(engine.running, "主循环应该能够正常退出")
        self.assertGreaterEqual(mock_sleep.call_count, 2, "应该至少执行了 2 次循环")


class TestSignalProcessingChain(unittest.TestCase):
    """测试信号处理链路"""
    
    def test_full_signal_chain(self):
        """测试从 ML 信号到最终发单的完整链路"""
        # Arrange
        engine = QuantTradingEngine()
        
        # Mock 所有组件
        engine.ml_predictor = Mock()
        engine.signal_processor = Mock()
        engine.risk_manager = Mock()
        engine.trade_executor = Mock()
        engine.position_manager = Mock()
        
        # 配置完整链路的返回值
        ml_signal = {"prediction": 0.02, "confidence": 0.8, "signal": 1}
        trade_intent = {"symbol": "au2606", "direction": "BUY", "volume": 2}
        final_order = {"symbol": "au2606", "direction": "BUY", "volume": 1}
        
        engine.signal_processor.process.return_value = trade_intent
        engine.risk_manager.check.return_value = final_order
        
        # Act
        engine.run_strategy_cycle()
        
        # Assert - 验证数据流转
        engine.signal_processor.process.assert_called_once()
        
        # 验证 risk_manager 收到了 signal_processor 的输出
        actual_call = engine.risk_manager.check.call_args
        self.assertEqual(actual_call[0][0], trade_intent)
        
        # 验证 trade_executor 收到了 risk_manager 的输出
        actual_call = engine.trade_executor.execute_order.call_args
        self.assertEqual(actual_call[0][0], final_order)
    
    def test_chain_break_at_signal_processor(self):
        """测试链路在信号处理器断开"""
        # Arrange
        engine = QuantTradingEngine()
        engine.signal_processor = Mock()
        engine.risk_manager = Mock()
        engine.trade_executor = Mock()
        
        # 信号处理器返回 None
        engine.signal_processor.process.return_value = None
        
        # Act
        engine.run_strategy_cycle()
        
        # Assert - 链路应该在此中断
        engine.signal_processor.process.assert_called_once()
        engine.risk_manager.check.assert_not_called()
        engine.trade_executor.execute_order.assert_not_called()
    
    def test_chain_break_at_risk_manager(self):
        """测试链路在风控管理器断开"""
        # Arrange
        engine = QuantTradingEngine()
        engine.signal_processor = Mock()
        engine.risk_manager = Mock()
        engine.trade_executor = Mock()
        
        trade_intent = {"symbol": "au2606", "direction": "BUY", "volume": 2}
        
        # 信号处理器通过，风控拒绝
        engine.signal_processor.process.return_value = trade_intent
        engine.risk_manager.check.return_value = None
        
        # Act
        engine.run_strategy_cycle()
        
        # Assert - 链路应该在风控处中断
        engine.signal_processor.process.assert_called_once()
        engine.risk_manager.check.assert_called_once()
        engine.trade_executor.execute_order.assert_not_called()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
