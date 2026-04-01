"""
模型训练模块
使用 LightGBM 训练回归模型，预测未来收益率
"""
import os

import lightgbm as lgb
import numpy as np
from sklearn.metrics import mean_squared_error

from quant.common.config import config


class ModelTrainer:
    """LightGBM 模型训练器"""

    def __init__(self):
        """初始化训练器，从配置中读取模型路径和超参数"""
        self.model_path = config.ml.model_path
        self.params = {
            'learning_rate': config.ml.learning_rate,
            'num_leaves': config.ml.num_leaves,
            'max_depth': config.ml.max_depth,
            'min_data_in_leaf': config.ml.min_data_in_leaf,
            'objective': 'regression',
            'metric': 'rmse',
            'random_state': 42,
            'verbose': -1  # 减少训练日志输出
        }
        self.model = None

    def train(self, X_train, y_train, X_test, y_test):
        """
        训练 LightGBM 模型

        Args:
            X_train: 训练集特征
            y_train: 训练集目标
            X_test: 测试集特征
            y_test: 测试集目标

        Returns:
            (model, metrics) - 训练好的模型实例和评估指标 (MSE, RMSE)
        """
        print("[TRAIN] 开始训练 LightGBM 模型...")
        print(f"        训练集大小: {len(X_train)} 样本")
        print(f"        测试集大小: {len(X_test)} 样本")
        print(f"        特征数量: {X_train.shape[1]}")

        # 创建 LightGBM 回归器
        self.model = lgb.LGBMRegressor(**self.params)

        # 训练模型，使用 early stopping 防止过拟合
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            eval_metric='rmse',
            callbacks=[
                lgb.early_stopping(stopping_rounds=20, verbose=False),
                lgb.log_evaluation(period=0)  # 不打印每轮日志
            ]
        )

        print(f"[OK] 训练完成！最佳迭代轮数: {self.model.best_iteration_}")

        # 在测试集上评估
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)

        print("[EVAL] 测试集评估:")
        print(f"       MSE:  {mse:.6f}")
        print(f"       RMSE: {rmse:.6f}")

        return self.model, {"mse": mse, "rmse": rmse}

    def save_model(self):
        """保存模型到本地文件"""
        if self.model is None:
            raise ValueError("模型尚未训练，无法保存！")

        # 确保目录存在
        model_dir = os.path.dirname(self.model_path)
        if model_dir:  # 如果有目录路径
            os.makedirs(model_dir, exist_ok=True)

        # 保存模型
        self.model.booster_.save_model(self.model_path)
        print(f"[SAVE] 模型已保存至: {self.model_path}")

    def load_model(self):
        """从本地文件加载模型"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"找不到模型文件: {self.model_path}")

        # 加载 Booster 对象
        self.model = lgb.Booster(model_file=self.model_path)
        print(f"[LOAD] 成功加载模型: {self.model_path}")
        return self.model

    def predict(self, X):
        """
        使用训练好的模型进行预测

        Args:
            X: 特征数据 (DataFrame 或 numpy array)

        Returns:
            预测结果 (numpy array)
        """
        if self.model is None:
            raise ValueError("模型尚未训练或加载，无法预测！")

        # 如果是 LGBMRegressor，直接调用 predict
        if isinstance(self.model, lgb.LGBMRegressor):
            return self.model.predict(X)
        # 如果是 Booster，需要转换为 numpy array
        elif isinstance(self.model, lgb.Booster):
            if hasattr(X, 'values'):
                X = X.values
            return self.model.predict(X)
        else:
            raise TypeError(f"未知的模型类型: {type(self.model)}")
