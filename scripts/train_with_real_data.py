"""
使用真实数据训练 ML 模型
从数据库读取历史日K线数据进行训练
"""
import sys
import os
import pandas as pd
import psycopg2

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.model_trainer import ModelTrainer


def load_real_data() -> pd.DataFrame:
    """从数据库加载真实日K线数据"""
    print("[DATA] 从数据库加载真实日K线数据...")
    
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='quant_trading',
        user='postgres',
        password='@Cmx1454697261'
    )
    
    query = """
        SELECT time as timestamp, open, high, low, close, volume
        FROM kline_daily
        WHERE symbol = 'AU'
        ORDER BY time ASC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # 转换时间戳
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"[OK] 加载完成！共 {len(df)} 条记录")
    print(f"     时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"     价格范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
    
    return df


def main():
    print("=" * 60)
    print("[TRAIN] 使用真实数据训练 ML 模型")
    print("=" * 60)
    
    # 1. 加载真实数据
    df = load_real_data()
    
    # 2. 特征工程
    print("\n" + "=" * 60)
    print("[STEP 1] 特征工程")
    print("=" * 60)
    
    feature_engineer = FeatureEngineer()
    X, y = feature_engineer.prepare_training_data(df)
    
    print(f"[OK] 特征提取完成！")
    print(f"     特征矩阵: {X.shape}")
    print(f"     目标变量: {y.shape}")
    print(f"     特征列表: {list(X.columns)}")
    
    # 3. 划分数据集
    print("\n" + "=" * 60)
    print("[STEP 2] 划分数据集")
    print("=" * 60)
    
    X_train, X_test, y_train, y_test = feature_engineer.train_test_split_time(
        X, y, test_size=0.2
    )
    
    print(f"[OK] 数据集划分完成！")
    print(f"     训练集: {len(X_train)} 样本")
    print(f"     测试集: {len(X_test)} 样本")
    print(f"     训练集目标均值: {y_train.mean():.6f}")
    print(f"     测试集目标均值: {y_test.mean():.6f}")
    
    # 4. 训练模型
    print("\n" + "=" * 60)
    print("[STEP 3] 训练 LightGBM 模型")
    print("=" * 60)
    
    trainer = ModelTrainer()
    model, metrics = trainer.train(X_train, y_train, X_test, y_test)
    
    # 5. 保存模型
    print("\n" + "=" * 60)
    print("[STEP 4] 保存模型")
    print("=" * 60)
    
    trainer.save_model()
    
    # 6. 验证模型
    print("\n" + "=" * 60)
    print("[STEP 5] 验证模型")
    print("=" * 60)
    
    new_trainer = ModelTrainer()
    new_trainer.load_model()
    y_pred = new_trainer.predict(X_test)
    
    print(f"[OK] 模型验证完成")
    print(f"     预测样本数: {len(y_pred)}")
    print(f"     预测均值: {y_pred.mean():.6f}")
    print(f"     预测标准差: {y_pred.std():.6f}")
    
    # 7. 总结
    print("\n" + "=" * 60)
    print("[SUMMARY] 训练总结")
    print("=" * 60)
    print(f"[OK] 数据来源: PostgreSQL kline_daily (AU)")
    print(f"[OK] 训练样本: {len(X_train)} 条")
    print(f"[OK] 测试样本: {len(X_test)} 条")
    print(f"[OK] 测试集 MSE:  {metrics['mse']:.6f}")
    print(f"[OK] 测试集 RMSE: {metrics['rmse']:.6f}")
    print(f"[OK] 模型路径: {trainer.model_path}")
    print("=" * 60)
    
    return metrics


if __name__ == "__main__":
    try:
        metrics = main()
        print("\n[SUCCESS] 模型训练完成！")
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
