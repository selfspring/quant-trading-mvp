"""
FeatureEngineer 单元测试
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quant.signal_generator.feature_engineer import FeatureEngineer


@pytest.fixture
def feature_engineer():
    return FeatureEngineer()


@pytest.fixture
def large_ohlcv_df():
    """生成足够大的测试数据（200行，确保 dropna 后有足够数据）"""
    np.random.seed(42)
    n = 200
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


def test_generate_features_output_columns(feature_engineer, large_ohlcv_df):
    """测试 generate_features 输出列数 = 47 + 原始列"""
    df_feat = feature_engineer.generate_features(large_ohlcv_df)
    # 模型需要 47 个特征，generate_features 输出包含这些特征加上 timestamp
    expected_model_features = [
        'open', 'high', 'low', 'close', 'volume', 'open_interest',
        'ma_5', 'ma_10', 'ma_20', 'ma_60', 'macd', 'macd_signal', 'macd_hist',
        'rsi', 'bb_middle', 'bb_upper', 'bb_lower', 'bb_width', 'atr',
        'returns_1', 'returns_5', 'returns_10', 'returns_20',
        'volatility_5', 'volatility_10', 'volatility_20',
        'volume_ratio_5', 'volume_ratio_10', 'volume_change',
        'price_position', 'distance_from_ma20',
        'body_ratio', 'upper_shadow', 'lower_shadow',
        'oi_change', 'oi_volume_ratio',
        'ma_cross_5_20', 'macd_cross',
        'higher_high', 'lower_low', 'consecutive_up', 'consecutive_down',
        'atr_ratio', 'bb_position',
        'hour_of_day', 'day_of_week', 'is_night_session',
    ]
    for feat in expected_model_features:
        assert feat in df_feat.columns, f"缺少特征列: {feat}"


def test_generate_features_no_nan(feature_engineer, large_ohlcv_df):
    """测试 generate_features 后 dropna 无 NaN"""
    df_feat = feature_engineer.generate_features(large_ohlcv_df)
    df_clean = df_feat.dropna()
    # dropna 后不应有 NaN
    assert df_clean.isnull().sum().sum() == 0, "dropna 后仍有 NaN 值"
    # 且应有足够的行
    assert len(df_clean) > 0, "dropna 后无数据"


def test_prepare_training_data_shape(feature_engineer, large_ohlcv_df):
    """测试 prepare_training_data 返回的 X 和 y 形状正确"""
    X, y = feature_engineer.prepare_training_data(large_ohlcv_df)
    # X 和 y 行数相同
    assert len(X) == len(y), f"X 行数 {len(X)} != y 行数 {len(y)}"
    # X 应有 47 列（模型特征数）
    assert X.shape[1] == 47, f"X 列数 {X.shape[1]} != 47"
    # y 应为一维
    assert y.ndim == 1, "y 不是一维"
    # 数据量应大于 0
    assert len(X) > 0, "训练数据为空"


def test_feature_names_match_model(feature_engineer, large_ohlcv_df):
    """测试特征名与模型一致"""
    model_path = os.path.join(PROJECT_ROOT, "models", "lgbm_model.txt")
    if not os.path.exists(model_path):
        pytest.skip("模型���件不存在，跳过此测试")

    import lightgbm as lgb
    model = lgb.Booster(model_file=model_path)
    model_features = model.feature_name()

    X, y = feature_engineer.prepare_training_data(large_ohlcv_df)
    actual_features = list(X.columns)

    assert set(model_features) == set(actual_features), (
        f"特征不一致!\n"
        f"模型有但 FE 缺少: {set(model_features) - set(actual_features)}\n"
        f"FE 有但模型缺少: {set(actual_features) - set(model_features)}"
    )
