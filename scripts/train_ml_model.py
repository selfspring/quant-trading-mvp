"""
模型训练验证脚本
测试 ModelTrainer 的训练、保存、加载功能
"""
import sys
import os
import pandas as pd
import numpy as np

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.model_trainer import ModelTrainer


def generate_mock_ohlcv(n_rows: int = 500) -> pd.DataFrame:
    """
    生成模拟的 OHLCV 数据
    
    Args:
        n_rows: 数据行数
    
    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    print(f"📊 生成 {n_rows} 行模拟 OHLCV 数据...")
    
    np.random.seed(42)
    
    # 生成时间序列
    dates = pd.date_range(start='2024-01-01', periods=n_rows, freq='30min')
    
    # 生成价格数据（带趋势和随机波动）
    base_price = 500.0
    trend = np.linspace(0, 50, n_rows)  # 上升趋势
    noise = np.random.randn(n_rows) * 5  # 随机波动
    close = base_price + trend + noise
    
    # 生成 OHLC
    high = close + np.abs(np.random.randn(n_rows) * 2)
    low = close - np.abs(np.random.randn(n_rows) * 2)
    open_price = close + np.random.randn(n_rows) * 1
    
    # 生成成交量
    volume = np.random.randint(1000, 10000, n_rows)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    print(f"✅ 数据生成完成！时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    return df


def main():
    """主函数：完整的训练流程"""
    print("=" * 60)
    print("🎯 ML 模型训练验证脚本")
    print("=" * 60)
    
    # 1. 生成模拟数据
    df = generate_mock_ohlcv(n_rows=500)
    
    # 2. 特征工程
    print("\n" + "=" * 60)
    print("🔧 步骤 1: 特征工程")
    print("=" * 60)
    
    feature_engineer = FeatureEngineer()
    X, y = feature_engineer.prepare_training_data(df)
    
    print(f"✅ 特征提取完成！")
    print(f"   特征矩阵形状: {X.shape}")
    print(f"   目标变量形状: {y.shape}")
    print(f"   特征列表 (前10个): {list(X.columns[:10])}")
    
    # 3. 划分训练集和测试集
    print("\n" + "=" * 60)
    print("📊 步骤 2: 划分数据集")
    print("=" * 60)
    
    X_train, X_test, y_train, y_test = feature_engineer.train_test_split_time(
        X, y, test_size=0.2
    )
    
    print(f"✅ 数据集划分完成！")
    print(f"   训练集: {len(X_train)} 样本")
    print(f"   测试集: {len(X_test)} 样本")
    print(f"   训练集目标均值: {y_train.mean():.6f}")
    print(f"   测试集目标均值: {y_test.mean():.6f}")
    
    # 4. 训练模型
    print("\n" + "=" * 60)
    print("🤖 步骤 3: 训练 LightGBM 模型")
    print("=" * 60)
    
    trainer = ModelTrainer()
    model, metrics = trainer.train(X_train, y_train, X_test, y_test)
    
    # 5. 保存模型
    print("\n" + "=" * 60)
    print("💾 步骤 4: 保存模型")
    print("=" * 60)
    
    trainer.save_model()
    
    # 6. 测试加载模型
    print("\n" + "=" * 60)
    print("📂 步骤 5: 测试模型加载")
    print("=" * 60)
    
    # 创建新的训练器实例
    new_trainer = ModelTrainer()
    loaded_model = new_trainer.load_model()
    
    # 使用加载的模型进行预测
    print("\n🔮 使用加载的模型进行预测测试...")
    y_pred_loaded = new_trainer.predict(X_test)
    
    # 验证预测结果一致性
    y_pred_original = trainer.predict(X_test)
    prediction_diff = np.abs(y_pred_loaded - y_pred_original).max()
    
    print(f"✅ 预测结果一致性检查:")
    print(f"   最大差异: {prediction_diff:.10f}")
    
    if prediction_diff < 1e-6:
        print(f"   ✅ 模型加载成功，预测结果一致！")
    else:
        print(f"   ⚠️  警告：预测结果存在差异！")
    
    # 7. 总结
    print("\n" + "=" * 60)
    print("📋 训练总结")
    print("=" * 60)
    print(f"✅ 模型训练完成")
    print(f"✅ 测试集 MSE:  {metrics['mse']:.6f}")
    print(f"✅ 测试集 RMSE: {metrics['rmse']:.6f}")
    print(f"✅ 模型已保存到: {trainer.model_path}")
    print(f"✅ 模型加载测试通过")
    print("=" * 60)
    
    return metrics


if __name__ == "__main__":
    try:
        metrics = main()
        print("\n🎉 所有测试通过！")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
