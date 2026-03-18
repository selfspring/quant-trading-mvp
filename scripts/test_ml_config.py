"""测试 ML 配置加载"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.common.config import config

print("=" * 60)
print("ML 配置测试")
print("=" * 60)
print(f"模型路径：{config.ml.model_path}")
print(f"特征窗口：{config.ml.feature_window} 分钟")
print(f"预测时长：{config.ml.prediction_horizon} 分钟")
print(f"置信度阈值：{config.ml.confidence_threshold}")
print(f"学习率：{config.ml.learning_rate}")
print(f"叶子节点数：{config.ml.num_leaves}")
print(f"最大深度：{config.ml.max_depth}")
print("=" * 60)
print("Success: ML configuration loaded successfully!")
