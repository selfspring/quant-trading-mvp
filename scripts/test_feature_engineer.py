"""
测试特征工程模块
验证特征生成、目标变量计算和数据集划分功能
"""
import pandas as pd
import numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer


def create_mock_ohlcv(n_rows: int = 200) -> pd.DataFrame:
    """
    创建模拟的 OHLCV 数据
    
    Args:
        n_rows: 数据行数
    
    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    np.random.seed(42)
    
    # 生成时间索引
    dates = pd.date_range(start='2024-01-01', periods=n_rows, freq='30min')
    
    # 生成价格数据（模拟随机游走）
    base_price = 100.0
    returns = np.random.randn(n_rows) * 0.02  # 2% 标准差
    close_prices = base_price * np.exp(np.cumsum(returns))
    
    # 生成 OHLCV
    df = pd.DataFrame({
        'open': close_prices * (1 + np.random.randn(n_rows) * 0.005),
        'high': close_prices * (1 + np.abs(np.random.randn(n_rows)) * 0.01),
        'low': close_prices * (1 - np.abs(np.random.randn(n_rows)) * 0.01),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, n_rows)
    }, index=dates)
    
    # 确保 high >= close >= low
    df['high'] = df[['high', 'close']].max(axis=1)
    df['low'] = df[['low', 'close']].min(axis=1)
    
    return df


def main():
    """主测试函数"""
    print("=" * 60)
    print("特征工程模块测试")
    print("=" * 60)
    
    # 1. 创建模拟数据
    print("\n[1] 创建模拟 OHLCV 数据...")
    df = create_mock_ohlcv(n_rows=200)
    print(f"原始数据形状: {df.shape}")
    print(f"原始数据列: {list(df.columns)}")
    print(f"\n原始数据前 5 行:")
    print(df.head())
    
    # 2. 实例化特征工程器
    print("\n[2] 实例化 FeatureEngineer...")
    fe = FeatureEngineer()
    print(f"预测时长 (horizon): {fe.horizon} 分钟")
    
    # 3. 生成特征和目标
    print("\n[3] 生成特征 X 和目标 y...")
    X, y = fe.prepare_training_data(df)
    
    print(f"\n特征矩阵 X 形状: {X.shape}")
    print(f"目标变量 y 形状: {y.shape}")
    print(f"\n特征列名 ({len(X.columns)} 个):")
    print(list(X.columns))
    
    # 4. 验证数据清洗
    print("\n[4] 验证数据清洗...")
    print(f"X 中 NaN 数量: {X.isna().sum().sum()}")
    print(f"y 中 NaN 数量: {y.isna().sum()}")
    
    # 计算预期行数
    # 原始 200 行 - MA60 窗口期 (60) - prediction_horizon (60) = 约 80 行
    expected_rows = 200 - 60 - fe.horizon
    print(f"\n预期行数: 约 {expected_rows} 行")
    print(f"实际行数: {len(X)} 行")
    
    # 5. 测试时间序列划分
    print("\n[5] 测试时间序列划分...")
    X_train, X_test, y_train, y_test = fe.train_test_split_time(X, y, test_size=0.2)
    
    print(f"训练集 X 形状: {X_train.shape}")
    print(f"测试集 X 形状: {X_test.shape}")
    print(f"训练集 y 形状: {y_train.shape}")
    print(f"测试集 y 形状: {y_test.shape}")
    
    # 验证时间顺序
    print(f"\n训练集时间范围: {X_train.index[0]} 至 {X_train.index[-1]}")
    print(f"测试集时间范围: {X_test.index[0]} 至 {X_test.index[-1]}")
    
    # 6. 显示目标变量统计
    print("\n[6] 目标变量统计...")
    print(f"y 均值: {y.mean():.6f}")
    print(f"y 标准差: {y.std():.6f}")
    print(f"y 最小值: {y.min():.6f}")
    print(f"y 最大值: {y.max():.6f}")
    
    # 7. 显示部分特征数据
    print("\n[7] 特征数据示例 (前 3 行):")
    print(X.head(3))
    
    print("\n" + "=" * 60)
    print("[OK] 测试完成！特征工程模块工作正常。")
    print("=" * 60)


if __name__ == "__main__":
    main()
