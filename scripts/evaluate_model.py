"""评估 ML 模型质量"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from quant.signal_generator.feature_engineer import FeatureEngineer
from quant.signal_generator.ml_predictor import MLPredictor

print("=== 加载测试数据 ===")
df = pd.read_csv('E:/quant-trading-mvp/data/tq_au_30m.csv')
df['datetime'] = pd.to_datetime(df['datetime'], unit='ns')
df = df.rename(columns={'datetime': 'timestamp'})
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
df = df.sort_values('timestamp').reset_index(drop=True)

# 使用后 20% 作为测试集（训练时用的前 80%）
split_idx = int(len(df) * 0.8)
df_test = df[split_idx:].reset_index(drop=True)
print(f"测试集: {len(df_test)} 根 K 线")

print("\n=== 模型预测 ===")
predictor = MLPredictor()

predictions = []
actuals = []
confidences = []

# 滑动窗口预测
for i in range(60, len(df_test) - 2):  # 需要 60 根历史 + 2 根未来
    # 取历史数据
    window = df_test.iloc[max(0, i-100):i]
    if len(window) < 60:
        continue
    
    # 预测
    try:
        result = predictor.predict(window)
        pred = result['prediction']
        conf = result['confidence']
        
        # 实际收益率（未来 2 根 30 分钟 = 1 小时）
        actual = (df_test.iloc[i+2]['close'] - df_test.iloc[i]['close']) / df_test.iloc[i]['close']
        
        predictions.append(pred)
        actuals.append(actual)
        confidences.append(conf)
    except:
        continue

predictions = np.array(predictions)
actuals = np.array(actuals)
confidences = np.array(confidences)

print(f"有效预测: {len(predictions)} 次")

print("\n=== 1. 预测准确性 ===")
mse = np.mean((predictions - actuals) ** 2)
rmse = np.sqrt(mse)
mae = np.mean(np.abs(predictions - actuals))
print(f"MSE:  {mse:.6f}")
print(f"RMSE: {rmse:.6f} ({rmse*100:.2f}%)")
print(f"MAE:  {mae:.6f} ({mae*100:.2f}%)")

print("\n=== 2. 方向准确率 ===")
pred_direction = np.sign(predictions)
actual_direction = np.sign(actuals)
direction_correct = (pred_direction == actual_direction).sum()
direction_accuracy = direction_correct / len(predictions)
print(f"方向准确率: {direction_accuracy*100:.2f}% ({direction_correct}/{len(predictions)})")

print("\n=== 3. 高置信度预测表现 ===")
high_conf_mask = confidences >= 0.65
if high_conf_mask.sum() > 0:
    high_conf_preds = predictions[high_conf_mask]
    high_conf_actuals = actuals[high_conf_mask]
    high_conf_direction = (np.sign(high_conf_preds) == np.sign(high_conf_actuals)).sum()
    print(f"高置信度预测次数: {high_conf_mask.sum()}")
    print(f"高置信度方向准确率: {high_conf_direction/high_conf_mask.sum()*100:.2f}%")
    print(f"高置信度平均收益: {high_conf_actuals.mean()*100:.2f}%")
else:
    print("无高置信度预测（confidence >= 0.65）")

print("\n=== 4. 预测 vs 实际分布 ===")
print(f"预测值: 均值={predictions.mean()*100:.2f}%, 标准差={predictions.std()*100:.2f}%")
print(f"实际值: 均值={actuals.mean()*100:.2f}%, 标准差={actuals.std()*100:.2f}%")

print("\n=== 5. 相关性 ===")
correlation = np.corrcoef(predictions, actuals)[0, 1]
print(f"预测与实际的相关系数: {correlation:.4f}")
if correlation > 0.3:
    print("相关性较强，模型有预测能力")
elif correlation > 0.1:
    print("相关性一般，模型有一定预测能力")
else:
    print("相关性较弱，模型预测能力有限")

print("\n=== 6. 模型评级 ===")
score = 0
if rmse < 0.03:
    score += 2
    print("✓ RMSE < 3%: 优秀")
elif rmse < 0.05:
    score += 1
    print("✓ RMSE < 5%: 良好")
else:
    print("✗ RMSE >= 5%: 需改进")

if direction_accuracy > 0.55:
    score += 2
    print("✓ 方向准确率 > 55%: 优秀")
elif direction_accuracy > 0.50:
    score += 1
    print("✓ 方向准确率 > 50%: 良好")
else:
    print("✗ 方向准确率 <= 50%: 需改进")

if correlation > 0.2:
    score += 2
    print("✓ 相关系数 > 0.2: 优秀")
elif correlation > 0.1:
    score += 1
    print("✓ 相关系数 > 0.1: 良好")
else:
    print("✗ 相关系数 <= 0.1: 需改进")

print(f"\n总分: {score}/6")
if score >= 5:
    print("模型质量: 优秀，可以实盘")
elif score >= 3:
    print("模型质量: 良好，建议继续优化")
else:
    print("模型质量: 较差，需要重新训练")
