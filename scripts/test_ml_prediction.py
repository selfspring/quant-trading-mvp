"""
测试 ML 预测脚本
"""
import sys
import os
import pandas as pd
import numpy as np

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant.signal_generator.ml_predictor import MLPredictor


def generate_mock_ohlcv(n_rows=100):
    """生成模拟的 OHLCV 数据"""
    np.random.seed(42)
    
    # 生成基础价格序列（随机游走）
    base_price = 100.0
    price_changes = np.random.randn(n_rows) * 0.5
    close_prices = base_price + np.cumsum(price_changes)
    
    # 生成 OHLCV 数据
    data = {
        'open': close_prices + np.random.randn(n_rows) * 0.2,
        'high': close_prices + np.abs(np.random.randn(n_rows)) * 0.5,
        'low': close_prices - np.abs(np.random.randn(n_rows)) * 0.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, n_rows)
    }
    
    df = pd.DataFrame(data)
    
    # 确保 high >= close >= low 和 high >= open >= low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def main():
    print("=" * 60)
    print("测试 ML 预测器")
    print("=" * 60)
    
    # 1. 生成模拟数据
    print("\n1. 生成 100 行模拟 OHLCV 数据...")
    df = generate_mock_ohlcv(100)
    print(f"   数据形状: {df.shape}")
    print(f"   数据预览:\n{df.head()}")
    
    # 2. 实例化预测器
    print("\n2. 实例化 MLPredictor...")
    try:
        predictor = MLPredictor()
        print("   [OK] 模型加载成功")
    except FileNotFoundError as e:
        print(f"   [ERROR] 错误: {e}")
        print("   请先运行 scripts/train_ml_model.py 训练模型")
        return
    except Exception as e:
        print(f"   [ERROR] 加载失败: {e}")
        return
    
    # 3. 执行预测
    print("\n3. 执行预测...")
    try:
        result = predictor.predict(df)
        print("   [OK] 预测成功")
        print(f"\n   预测结果:")
        print(f"   - prediction (预测收益率): {result['prediction']:.6f}")
        print(f"   - confidence (置信度): {result['confidence']:.4f}")
        print(f"   - signal (信号): {result['signal']} ({'看多' if result['signal'] == 1 else '看空'})")
        
        # 4. 验证结果
        print("\n4. 验证结果...")
        assert 0.0 <= result['confidence'] <= 1.0, "置信度应在 0-1 之间"
        assert result['signal'] in [1, -1], "信号应为 1 或 -1"
        assert isinstance(result['prediction'], float), "预测值应为浮点数"
        print("   [OK] 所有验证通过")
        
    except ValueError as e:
        print(f"   [ERROR] 预测失败: {e}")
        return
    except Exception as e:
        print(f"   [ERROR] 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
