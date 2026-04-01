"""
集成预测器
使用 LightGBM + XGBoost + CatBoost 三模型加权投票
"""
import os
from typing import Optional

import pandas as pd
import numpy as np

from quant.common.config import config
from quant.signal_generator.feature_engineer import FeatureEngineer


class EnsemblePredictor:
    """
    三模型集成预测器
    
    加权策略：
    - LightGBM: 0.4
    - XGBoost: 0.3
    - CatBoost: 0.3
    
    置信度提升：三模型预测方向一致时 +0.1 bonus
    """
    
    def __init__(self):
        # 模型路径（与 train_ensemble.py 保持一致）
        self.base_model_dir = 'E:/quant-trading-mvp/models'
        self.lgb_path = os.path.join(self.base_model_dir, 'lgbm_model.txt')
        self.xgb_path = os.path.join(self.base_model_dir, 'xgb_model.json')
        self.cat_path = os.path.join(self.base_model_dir, 'catboost_model.cbm')
        
        self.lgb_model = None
        self.xgb_model = None
        self.cat_model = None
        self.lgb_weight = 0.4
        self.xgb_weight = 0.3
        self.cat_weight = 0.3
        self.load_models()
    
    def load_models(self):
        """加载三个模型，模型不可用时自动降级"""
        import lightgbm as lgb
        
        # 加载 LightGBM 模型
        if os.path.exists(self.lgb_path):
            try:
                self.lgb_model = lgb.Booster(model_file=self.lgb_path)
                print(f"[EnsemblePredictor] LightGBM 模型已加载：{self.lgb_path}")
            except Exception as e:
                print(f"[EnsemblePredictor] LightGBM 模型加载失败：{e}")
                self.lgb_model = None
        else:
            print(f"[EnsemblePredictor] LightGBM 模型不存在：{self.lgb_path}")
            self.lgb_model = None
        
        # 加载 XGBoost 模型
        if os.path.exists(self.xgb_path):
            try:
                import xgboost as xgb
                self.xgb_model = xgb.Booster()
                self.xgb_model.load_model(self.xgb_path)
                print(f"[EnsemblePredictor] XGBoost 模型已加载：{self.xgb_path}")
            except Exception as e:
                print(f"[EnsemblePredictor] XGBoost 模型加载失败：{e}")
                self.xgb_model = None
        else:
            print(f"[EnsemblePredictor] XGBoost 模型不存在：{self.xgb_path}")
            self.xgb_model = None
        
        # 加载 CatBoost 模型
        if os.path.exists(self.cat_path):
            try:
                from catboost import CatBoostRegressor
                self.cat_model = CatBoostRegressor()
                self.cat_model.load_model(self.cat_path)
                print(f"[EnsemblePredictor] CatBoost 模型已加载：{self.cat_path}")
            except Exception as e:
                print(f"[EnsemblePredictor] CatBoost 模型加载失败：{e}")
                self.cat_model = None
        else:
            print(f"[EnsemblePredictor] CatBoost 模型不存在：{self.cat_path}")
            self.cat_model = None
        
        # 检查是否有可用模型
        if self.lgb_model is None and self.xgb_model is None and self.cat_model is None:
            raise FileNotFoundError("没有可用的模型文件，请先运行训练脚本。")
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备特征数据，与训练保持一致（包括技术指标 + 微观特征 + 宏观特征）"""
        if len(df) < 60:
            raise ValueError("K 线数据不足 60 行，无法计算完整技术指标。")
        
        # 1. 通过 FeatureEngineer 统一生成特征（包含微观特征）
        fe = FeatureEngineer(include_micro=True)
        df_features = fe.generate_features(df)
        if df_features.empty:
            raise ValueError("特征计算后数据为空。")
        
        # 2. 添加宏观特征（与 train_ensemble.py 保持一致）
        df_features = self._add_macro_features_for_prediction(df_features)
        
        # 3. 取最新的一根 K 线特征
        latest_features = df_features.iloc[-1:].copy()
        
        # 4. 移除非数值列
        exclude_cols = ['timestamp', 'datetime', 'symbol', 'id', 'duration', 
                        'open', 'high', 'low', 'close', 'volume', 'open_interest']
        latest_features = latest_features.drop(columns=[c for c in exclude_cols if c in latest_features.columns], errors='ignore')
        
        return latest_features
    
    def _add_macro_features_for_prediction(self, df: pd.DataFrame) -> pd.DataFrame:
        """为预测添加宏观特征（简化版，只使用可用数据）"""
        from quant.common.db import db_engine
        
        df = df.copy()
        df['date'] = df['timestamp'].dt.date
        df['date'] = pd.to_datetime(df['date'])
        
        try:
            # 加载日频宏观数据
            with db_engine(config) as engine:
                macro_daily = pd.read_sql("SELECT date, indicator, value FROM macro_daily ORDER BY date", engine)
            
            if len(macro_daily) > 0:
                pivot = macro_daily.pivot_table(index='date', columns='indicator', values='value', aggfunc='first')
                pivot.index = pd.to_datetime(pivot.index)
                pivot = pivot.sort_index()
                
                key_daily = []
                for col in ['us_10y', 'us_2y', 'us_5y', 'shibor_on', 'shibor_1w']:
                    if col in pivot.columns:
                        key_daily.append(col)
                
                if key_daily:
                    macro_sub = pivot[key_daily].copy()
                    macro_sub.index.name = 'date'
                    macro_sub = macro_sub.reset_index()
                    macro_sub['date'] = pd.to_datetime(macro_sub['date'])
                    df = pd.merge_asof(df.sort_values('date'), macro_sub.sort_values('date'),
                                       on='date', direction='backward')
                    
                    if 'us_10y' in df.columns and 'us_2y' in df.columns:
                        df['us_spread_10y_2y'] = df['us_10y'] - df['us_2y']
            
            # 加载持仓排名
            with db_engine(config) as engine:
                fut_holding_raw = pd.read_sql("SELECT * FROM fut_holding ORDER BY trade_date", engine)
            
            if len(fut_holding_raw) > 0:
                holding = fut_holding_raw.groupby('trade_date').agg(
                    total_long=('long_hld', 'sum'),
                    total_short=('short_hld', 'sum'),
                    long_chg=('long_chg', 'sum'),
                    short_chg=('short_chg', 'sum'),
                ).reset_index()
                holding['long_short_ratio'] = holding['total_long'] / holding['total_short'].replace(0, 1)
                holding['trade_date'] = pd.to_datetime(holding['trade_date'], format='%Y%m%d')
                holding = holding.set_index('trade_date').sort_index()
                
                holding_df = holding.reset_index()
                holding_df.columns = ['date'] + [f'hold_{c}' for c in holding.columns]
                holding_df['date'] = pd.to_datetime(holding_df['date'])
                df = pd.merge_asof(df.sort_values('date'), holding_df.sort_values('date'),
                                   on='date', direction='backward')
            
            # 加载月频宏观数据
            with db_engine(config) as engine:
                macro_monthly = pd.read_sql("SELECT month, indicator, value FROM macro_monthly ORDER BY month", engine)
            
            if len(macro_monthly) > 0:
                key_indicators = ['nt_yoy', 'ppi_yoy', 'm2_yoy']
                df_filtered = macro_monthly[macro_monthly['indicator'].isin(key_indicators)]
                if len(df_filtered) > 0:
                    pivot = df_filtered.pivot_table(index='month', columns='indicator', values='value', aggfunc='first')
                    pivot.index = pd.to_datetime(pivot.index, format='%Y%m', errors='coerce')
                    pivot = pivot.dropna(how='all').sort_index()
                    
                    monthly_df = pivot.reset_index()
                    monthly_df.columns = ['date'] + [f'macro_{c}' for c in pivot.columns]
                    monthly_df['date'] = pd.to_datetime(monthly_df['date'])
                    monthly_df = monthly_df.dropna(subset=['date'])
                    
                    if len(monthly_df) > 0:
                        df = pd.merge_asof(df.sort_values('date'), monthly_df.sort_values('date'),
                                           on='date', direction='backward')
        except Exception as e:
            print(f"[EnsemblePredictor] 加载宏观特征失败：{e}，将继续使用已有特征")
        
        df = df.drop(columns=['date'], errors='ignore')
        return df
    
    def _predict_lgb(self, features: pd.DataFrame) -> Optional[float]:
        """LightGBM 预测"""
        if self.lgb_model is None:
            return None
        try:
            return float(self.lgb_model.predict(features)[0])
        except Exception as e:
            print(f"[EnsemblePredictor] LightGBM 预测失败：{e}")
            return None
    
    def _predict_xgb(self, features: pd.DataFrame) -> Optional[float]:
        """XGBoost 预测"""
        if self.xgb_model is None:
            return None
        try:
            import xgboost as xgb
            dmatrix = xgb.DMatrix(features)
            return float(self.xgb_model.predict(dmatrix)[0])
        except Exception as e:
            print(f"[EnsemblePredictor] XGBoost 预测失败：{e}")
            return None
    
    def _predict_cat(self, features: pd.DataFrame) -> Optional[float]:
        """CatBoost 预测"""
        if self.cat_model is None:
            return None
        try:
            return float(self.cat_model.predict(features)[0])
        except Exception as e:
            print(f"[EnsemblePredictor] CatBoost 预测失败：{e}")
            return None
    
    def predict(self, df: pd.DataFrame) -> dict:
        """
        输入最近的 K 线数据，输出预测信号
        
        Args:
            df: K 线数据 DataFrame，至少包含 60 行
        
        Returns:
            dict: {
                'signal': 'buy'/'sell'/'hold',
                'confidence': float,
                'predicted_return': float
            }
        """
        # 准备特征
        features = self._prepare_features(df)
        
        # 各模型预测
        pred_lgb = self._predict_lgb(features)
        pred_xgb = self._predict_xgb(features)
        pred_cat = self._predict_cat(features)
        
        # 收集可用预测结果
        predictions = []
        weights = []
        
        if pred_lgb is not None:
            predictions.append(pred_lgb)
            weights.append(self.lgb_weight)
        
        if pred_xgb is not None:
            predictions.append(pred_xgb)
            weights.append(self.xgb_weight)
        
        if pred_cat is not None:
            predictions.append(pred_cat)
            weights.append(self.cat_weight)
        
        if len(predictions) == 0:
            raise RuntimeError("没有可用的模型进行预测。")
        
        # 归一化权重
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # 加权平均预测
        predicted_return = sum(p * w for p, w in zip(predictions, weights))
        
        # 判断方向一致性（用于置信度 bonus）
        directions = [np.sign(p) for p in predictions]
        all_same_direction = len(set(directions)) == 1 and directions[0] != 0
        
        # 生成交易信号
        threshold = 0.005
        if predicted_return > threshold:
            signal = "buy"
        elif predicted_return < -threshold:
            signal = "sell"
        else:
            signal = "hold"
        
        # 计算置信度
        if signal == "hold":
            confidence = 0.0
        else:
            abs_pred = abs(predicted_return)
            if abs_pred <= threshold:
                confidence = 0.0
            elif abs_pred <= 0.02:
                # 合理范围 [0.005, 0.02] -> [0.4, 0.9]
                confidence = 0.4 + (abs_pred - threshold) / (0.02 - threshold) * 0.5
            elif abs_pred <= 0.05:
                # 偏高范围 [0.02, 0.05] -> [0.9, 0.5]
                confidence = 0.9 - (abs_pred - 0.02) / 0.03 * 0.4
            else:
                # 异常范围 >5%
                confidence = max(0.3 - (abs_pred - 0.05) * 2, 0.1)
            
            # 三模型方向一致时 +0.1 bonus
            if all_same_direction:
                confidence = min(confidence + 0.1, 1.0)
        
        return {
            'signal': signal,
            'confidence': float(confidence),
            'predicted_return': float(predicted_return)
        }
