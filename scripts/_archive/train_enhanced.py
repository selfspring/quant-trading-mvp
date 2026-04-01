"""
使用增强特征重新训练模型
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.model_trainer import ModelTrainer
from sklearn.metrics import mean_squared_error
import lightgbm as lgb

def evaluate_model(y_true, y_pred):
    """评估模型性能"""
    # 基础指标
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    
    # 方向准确率
    direction_true = (y_true > 0).astype(int)
    direction_pred = (y_pred > 0).astype(int)
    direction_accuracy = (direction_true == direction_pred).mean()
    
    # 相关系数
    correlation = np.corrcoef(y_true, y_pred)[0, 1]
    
    # 预测值分布
    pred_mean = y_pred.mean()
    pred_std = y_pred.std()
    
    # 高置信度预测的方向准确率
    pred_abs = np.abs(y_pred)
    high_conf_mask = pred_abs >= np.percentile(pred_abs, 65)
    if high_conf_mask.sum() > 0:
        high_conf_accuracy = (direction_true[high_conf_mask] == direction_pred[high_conf_mask]).mean()
    else:
        high_conf_accuracy = 0.0
    
    return {
        'mse': mse,
        'rmse': rmse,
        'direction_accuracy': direction_accuracy,
        'correlation': correlation,
        'pred_mean': pred_mean,
        'pred_std': pred_std,
        'high_conf_accuracy': high_conf_accuracy,
        'high_conf_count': high_conf_mask.sum()
    }

def main():
    print("=" * 60)
    print("使用增强特征重新训练模型")
    print("=" * 60)
    
    # 1. 读取数据
    data_path = 'E:/quant-trading-mvp/data/au_30m_combined.csv'
    print(f"\n[1/6] 读取数据: {data_path}")
    df = pd.read_csv(data_path)
    print(f"数据形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")
    
    # 2. 生成特征
    print("\n[2/6] 生成增强特征...")
    fe = FeatureEngineer()
    X, y = fe.prepare_training_data(df)
    print(f"特征数量: {X.shape[1]}")
    print(f"样本数量: {X.shape[0]}")
    print(f"特征列表: {X.columns.tolist()}")
    
    # 3. 划分训练集和测试集
    print("\n[3/6] 划分训练集和测试集 (80/20)...")
    X_train, X_test, y_train, y_test = fe.train_test_split_time(X, y, test_size=0.2)
    print(f"训练集: {X_train.shape[0]} 样本")
    print(f"测试集: {X_test.shape[0]} 样本")
    
    # 4. 训练模型
    print("\n[4/6] 训练 LightGBM 模型...")
    trainer = ModelTrainer()
    model, train_metrics = trainer.train(X_train, y_train, X_test, y_test)
    print("模型训练完成")
    
    # 5. 评估模型
    print("\n[5/6] 评估模型性能...")
    
    # 训练集评估
    y_train_pred = trainer.predict(X_train)
    train_metrics = evaluate_model(y_train, y_train_pred)
    
    print("\n训练集指标:")
    print(f"  MSE: {train_metrics['mse']:.6f}")
    print(f"  RMSE: {train_metrics['rmse']:.6f}")
    print(f"  方向准确率: {train_metrics['direction_accuracy']:.4f} ({train_metrics['direction_accuracy']*100:.2f}%)")
    print(f"  相关系数: {train_metrics['correlation']:.4f}")
    print(f"  预测均值: {train_metrics['pred_mean']:.6f}")
    print(f"  预测标准差: {train_metrics['pred_std']:.6f}")
    print(f"  高置信度方向准确率: {train_metrics['high_conf_accuracy']:.4f} ({train_metrics['high_conf_count']} 样本)")
    
    # 测试集评估
    y_test_pred = model.predict(X_test)
    test_metrics = evaluate_model(y_test, y_test_pred)
    
    print("\n测试集指标:")
    print(f"  MSE: {test_metrics['mse']:.6f}")
    print(f"  RMSE: {test_metrics['rmse']:.6f}")
    print(f"  方向准确率: {test_metrics['direction_accuracy']:.4f} ({test_metrics['direction_accuracy']*100:.2f}%)")
    print(f"  相关系数: {test_metrics['correlation']:.4f}")
    print(f"  预测均值: {test_metrics['pred_mean']:.6f}")
    print(f"  预测标准差: {test_metrics['pred_std']:.6f}")
    print(f"  高置信度方向准确率: {test_metrics['high_conf_accuracy']:.4f} ({test_metrics['high_conf_count']} 样本)")
    
    # 6. 保存模型
    print("\n[6/6] 保存模型...")
    model_path = 'E:/quant-trading-mvp/models/lgbm_model.txt'
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save_model(model_path)
    print(f"模型已保存到: {model_path}")
    
    print("\n" + "=" * 60)
    print("训练完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()
