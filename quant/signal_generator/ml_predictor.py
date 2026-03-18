"""
ML 预测器
使用 LightGBM 模型预测未来涨跌幅
"""
import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from quant.common.config import config
from quant.signal_generator.feature_engineer import FeatureEngineer


class MLPredictor:
    def __init__(self):
        self.model_path = config.ml.model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """加载训练好的 LightGBM 模型"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"找不到模型文件 {self.model_path}，请先运行训练脚本。"
            )
        self.model = lgb.Booster(model_file=self.model_path)

    def predict(self, df: pd.DataFrame) -> dict:
        """
        输入最近的 K 线数据，输出预测信号
        df 需要至少包含 60 行数据以计算长期 MA 指标
        """
        if len(df) < 60:
            raise ValueError("K 线数据不足 60 行，无法计算完整技术指标。")
            
        # 1. 通过 FeatureEngineer 统一生成特征（与训练保持同一口径）
        fe = FeatureEngineer()
        df_features = fe.generate_features(df)
        if df_features.empty:
            raise ValueError("特征计算后数据为空。")
            
        # 2. 取最新的一根 K 线特征进行预测
        latest_features = df_features.iloc[-1:]
        # 移除非数值列，与训练时 prepare_training_data 保持一致
        if 'timestamp' in latest_features.columns:
            latest_features = latest_features.drop(columns=['timestamp'])
        
        # 3. 模型推理
        # lightgbm predict 返回一个 numpy 数组
        pred_value = self.model.predict(latest_features)[0]
        
        # 4. 生成看多/看空信号（先判断方向）
        threshold = 0.005
        if pred_value > threshold:
            direction = "buy"
            signal = 1
        elif pred_value < -threshold:
            direction = "sell"
            signal = -1
        else:
            direction = None
            signal = 0
        
        # 5. 计算置信度（只对有方向的信号计算）
        # SimNow 模拟盘：放宽映射，让模型有机会交易
        # 映射：0.005 → 0.4, 0.008 → 0.65, 0.01 → 0.75, 0.02+ → 0.9
        if signal == 0:
            confidence = 0.0
        else:
            abs_pred = abs(pred_value)
            if abs_pred <= threshold:
                confidence = 0.0
            elif abs_pred <= 0.02:
                # 合理范围 [0.005, 0.02] -> [0.4, 0.9]
                confidence = 0.4 + (abs_pred - threshold) / (0.02 - threshold) * 0.5
            elif abs_pred <= 0.05:
                # 偏高范围 [0.02, 0.05] -> [0.9, 0.5]，越高越不可信
                confidence = 0.9 - (abs_pred - 0.02) / 0.03 * 0.4
            else:
                # 异常范围 >5%，模型预测不可信
                confidence = max(0.3 - (abs_pred - 0.05) * 2, 0.1)
        
        return {
            "prediction": float(pred_value),
            "confidence": float(confidence),
            "direction": direction,
            "signal": int(signal)
        }
