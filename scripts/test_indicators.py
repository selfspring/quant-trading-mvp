"""
技术指标计算测试脚本
构造模拟数据并验证指标计算功能
"""
import sys
import os
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant.signal_generator.technical_indicators import calculate_all_indicators


def generate_mock_data(n_rows: int = 100) -> pd.DataFrame:
    """
    生成模拟的 OHLCV 数据
    
    Args:
        n_rows: 数据行数
    
    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    np.random.seed(42)
    
    # 生成基础价格序列 (随机游走)
    base_price = 100
    price_changes = np.random.randn(n_rows) * 2
    close_prices = base_price + np.cumsum(price_changes)
    
    # 确保价格为正
    close_prices = np.maximum(close_prices, 10)
    
    # 生成 OHLC 数据
    data = {
        'open': close_prices + np.random.randn(n_rows) * 0.5,
        'high': close_prices + np.abs(np.random.randn(n_rows)) * 1.5,
        'low': close_prices - np.abs(np.random.randn(n_rows)) * 1.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, n_rows)
    }
    
    df = pd.DataFrame(data)
    
    # 确保 high >= close >= low 和 high >= open >= low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def main():
    """主测试函数"""
    print("=" * 60)
    print("技术指标计算测试")
    print("=" * 60)
    
    # 生成模拟数据
    print("\n1. 生成模拟数据...")
    df = generate_mock_data(n_rows=100)
    print(f"   生成了 {len(df)} 行 OHLCV 数据")
    print(f"   原始数据列: {list(df.columns)}")
    
    # 计算所有指标
    print("\n2. 计算技术指标...")
    df_with_indicators = calculate_all_indicators(df)
    print(f"   计算完成，剩余 {len(df_with_indicators)} 行数据 (已删除 NaN)")
    print(f"   新增指标列: {[col for col in df_with_indicators.columns if col not in df.columns]}")
    
    # 显示结果
    print("\n3. 数据预览 (最后 5 行):")
    print("-" * 60)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:.2f}'.format)
    print(df_with_indicators.tail())
    
    # 验证指标范围
    print("\n4. 指标统计信息:")
    print("-" * 60)
    indicator_cols = [col for col in df_with_indicators.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
    print(df_with_indicators[indicator_cols].describe())
    
    # 检查是否有 NaN
    print("\n5. 数据完整性检查:")
    print("-" * 60)
    nan_count = df_with_indicators.isna().sum().sum()
    print(f"   NaN 总数: {nan_count}")
    if nan_count == 0:
        print("   [OK] 所有数据完整，无缺失值")
    else:
        print("   [ERROR] 存在缺失值，请检查")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
