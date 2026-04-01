"""
ML 预测器
使用 LightGBM 模型预测未来涨跌幅
"""
import os

import lightgbm as lgb
import pandas as pd

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

        # 只保留模型训练时使用的特征列，按模型期望的顺序排列
        model_feature_names = self.model.feature_name()
        missing_cols = [c for c in model_feature_names if c not in latest_features.columns]
        if missing_cols:
            raise ValueError(f"推理数据缺少模型所需特征: {missing_cols}")
        latest_features = latest_features[model_feature_names]

        # 3. 模型推理
        # lightgbm predict 返回一个 numpy 数组
        pred_value = self.model.predict(latest_features)[0]

        # 4. 生成看多/看空信号（先判断方向）
        # 4. 生成开仓/方向信号，判断方向
        # 新模型预测1小时收益率，std~0.0035，threshold调低
        threshold = 0.0008
        if pred_value > threshold:
            direction = "buy"
            signal = 1
        elif pred_value < -threshold:
            direction = "sell"
            signal = -1
        else:
            direction = None
            signal = 0

        # 5. 计算置信度（只对有方向信号计算）
        # 映射：0.0008->0.35, 0.002->0.6, 0.006+->0.9
        if signal == 0:
            confidence = 0.0
        else:
            abs_pred = abs(pred_value)
            if abs_pred <= threshold:
                confidence = 0.0
            elif abs_pred <= 0.003:
                # 低区间 [0.0015, 0.003] -> [0.35, 0.6]
                confidence = 0.35 + (abs_pred - threshold) / (0.002 - threshold) * 0.25
            elif abs_pred <= 0.008:
                # 中区间 [0.003, 0.008] -> [0.6, 0.9]
                confidence = 0.6 + (abs_pred - 0.002) / (0.006 - 0.002) * 0.3
            else:
                # 高区间 >0.8%，满分
                confidence = 0.9

        return {
            "prediction": float(pred_value),
            "confidence": float(confidence),
            "direction": direction,
            "signal": int(signal)
        }
