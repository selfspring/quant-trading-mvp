"""
pytest fixtures - 测试用 DataFrame、mock config 等
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class MockMLConfig:
    confidence_threshold = 0.65
    model_path = "models/lgbm_model.txt"
    feature_window = 60
    prediction_horizon = 2
    learning_rate = 0.05
    num_leaves = 31
    max_depth = 6
    min_data_in_leaf = 20


class MockStrategyConfig:
    symbol = "au2606"
    interval = "30m"
    max_position_ratio = 0.7
    max_weekly_drawdown = 0.25
    consecutive_loss_limit = 3
    atr_multiplier = 2.0


class MockConfig:
    ml = MockMLConfig()
    strategy = MockStrategyConfig()


@pytest.fixture
def mock_config():
    """模拟配置对象"""
    return MockConfig()


@pytest.fixture
def sample_ohlcv_df():
    """生成 100 行 OHLCV + open_interest 测试数据"""
    np.random.seed(42)
    n = 100
    base_price = 600.0
    close = base_price + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_price = close + np.random.randn(n) * 0.2

    timestamps = pd.date_range("2025-01-01 09:00", periods=n, freq="30min")

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(100, 10000, n).astype(float),
        "open_interest": np.random.randint(1000, 50000, n).astype(float),
    })


@pytest.fixture
def position_manager():
    """创建 PositionManager 实例"""
    from quant.risk_executor.position_manager import PositionManager
    return PositionManager()


@pytest.fixture
def risk_manager(position_manager, mock_config):
    """创建 RiskManager 实例"""
    from quant.risk_executor.risk_manager import RiskManager
    return RiskManager(position_manager, mock_config)


@pytest.fixture
def signal_processor(mock_config):
    """创建 SignalProcessor 实例"""
    from quant.risk_executor.signal_processor import SignalProcessor
    return SignalProcessor(mock_config)
