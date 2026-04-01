"""
特征工程模块
连接原始数据、技术指标计算和机器学习模型训练的桥梁
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)
import pandas as pd

from quant.common.config import config
from quant.signal_generator.technical_indicators import calculate_all_indicators


class FeatureEngineer:
    """特征工程类，负责生成 ML 训练所需的特征和目标变量"""

    def __init__(self, include_micro=False, micro_symbols=None):
        """初始化特征工程器，从配置中读取预测时长

        Args:
            include_micro: 是否生成 1m 微观特征（需要数据库中有 1m 数据）
            micro_symbols: 微观特征使用的合约列表，默认 None（使用 DEFAULT_SYMBOLS）
        """
        self.horizon = config.ml.prediction_horizon
        self.include_micro = include_micro
        self._micro_gen = None
        if self.include_micro:
            from quant.signal_generator.micro_features import MicroFeatureGenerator
            self._micro_gen = MicroFeatureGenerator(config, symbols=micro_symbols)

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有特征（包括原生 OHLCV 及所有技术指标）

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            添加了所有技术指标的 DataFrame
        """
        # 调用指标计算模块
        df_features = calculate_all_indicators(df)

        # 添加价格动量特征
        df_features['returns_1'] = df_features['close'].pct_change(1)
        df_features['returns_5'] = df_features['close'].pct_change(5)
        df_features['returns_10'] = df_features['close'].pct_change(10)
        df_features['returns_20'] = df_features['close'].pct_change(20)

        # 添加波动率特征
        df_features['volatility_5'] = df_features['returns_1'].rolling(window=5).std()
        df_features['volatility_10'] = df_features['returns_1'].rolling(window=10).std()
        df_features['volatility_20'] = df_features['returns_1'].rolling(window=20).std()

        # 添加成交量特征
        volume_ma_5 = df_features['volume'].rolling(window=5).mean()
        volume_ma_10 = df_features['volume'].rolling(window=10).mean()
        df_features['volume_ratio_5'] = df_features['volume'] / volume_ma_5
        df_features['volume_ratio_10'] = df_features['volume'] / volume_ma_10
        df_features['volume_change'] = df_features['volume'].pct_change(1)

        # 添加价格位置特征
        high_20 = df_features['high'].rolling(window=20).max()
        low_20 = df_features['low'].rolling(window=20).min()
        # 处理除零问题
        price_range = high_20 - low_20
        df_features['price_position'] = np.where(
            price_range > 0,
            (df_features['close'] - low_20) / price_range,
            0.5  # 默认中间位置
        )
        df_features['distance_from_ma20'] = (df_features['close'] - df_features['ma_20']) / df_features['ma_20']

        # 添加K线形态特征
        candle_range = df_features['high'] - df_features['low']
        body = df_features['close'] - df_features['open']
        upper_wick = df_features['high'] - df_features[['open', 'close']].max(axis=1)
        lower_wick = df_features[['open', 'close']].min(axis=1) - df_features['low']

        # 处理除零问题
        df_features['body_ratio'] = np.where(
            candle_range > 0,
            body / candle_range,
            0
        )
        df_features['upper_shadow'] = np.where(
            candle_range > 0,
            upper_wick / candle_range,
            0
        )
        df_features['lower_shadow'] = np.where(
            candle_range > 0,
            lower_wick / candle_range,
            0
        )

        # 1. 持仓量相关（2个）
        # 支持 open_interest 或 close_oi 列名
        oi_col = None
        if 'open_interest' in df_features.columns:
            oi_col = 'open_interest'
        elif 'close_oi' in df_features.columns:
            oi_col = 'close_oi'

        if oi_col is not None:
            df_features['oi_change'] = df_features[oi_col].pct_change(1)
            # 持仓量/成交量比，处理除零
            df_features['oi_volume_ratio'] = np.where(
                df_features['volume'] > 0,
                df_features[oi_col] / df_features['volume'],
                0
            )

        # 2. 均线交叉信号（2个）
        df_features['ma_cross_5_20'] = (df_features['ma_5'] > df_features['ma_20']).astype(int)

        # MACD金叉死叉
        macd_diff = df_features['macd'] - df_features['macd_signal']
        macd_diff_prev = macd_diff.shift(1)
        df_features['macd_cross'] = np.where(
            (macd_diff > 0) & (macd_diff_prev <= 0), 1,  # 金叉
            np.where((macd_diff < 0) & (macd_diff_prev >= 0), -1, 0)  # 死叉
        )

        # 3. 价格形态（4个）
        # 是否创近20根新高
        high_20_max = df_features['high'].rolling(window=20).max()
        df_features['higher_high'] = (df_features['high'] >= high_20_max).astype(int)

        # 是否创近20根新低
        low_20_min = df_features['low'].rolling(window=20).min()
        df_features['lower_low'] = (df_features['low'] <= low_20_min).astype(int)

        # 连续上涨/下跌根数
        returns = df_features['close'].pct_change()
        df_features['consecutive_up'] = 0
        df_features['consecutive_down'] = 0
        for i in range(1, 11):
            df_features['consecutive_up'] += (returns.shift(i-1) > 0).astype(int)
            df_features['consecutive_down'] += (returns.shift(i-1) < 0).astype(int)

        # 4. 波动率相关（2个）
        # ATR标准化
        df_features['atr_ratio'] = np.where(
            df_features['close'] > 0,
            df_features['atr'] / df_features['close'],
            0
        )

        # 价格在布林带中的位置
        bb_range = df_features['bb_upper'] - df_features['bb_lower']
        df_features['bb_position'] = np.where(
            bb_range > 0,
            (df_features['close'] - df_features['bb_lower']) / bb_range,
            0.5
        )

        # 5. 时间特征（3个）
        # 支持 timestamp 或 datetime 列名
        time_col = None
        if 'timestamp' in df_features.columns:
            time_col = 'timestamp'
        elif 'datetime' in df_features.columns:
            time_col = 'datetime'

        if time_col is not None:
            dt = pd.to_datetime(df_features[time_col])
            df_features['hour_of_day'] = dt.dt.hour
            df_features['day_of_week'] = dt.dt.dayofweek
            # 夜盘标记（21:00-02:30）
            df_features['is_night_session'] = ((df_features['hour_of_day'] >= 21) | (df_features['hour_of_day'] <= 2)).astype(int)

        # 微观特征（可选）
        if self.include_micro and self._micro_gen is not None:
            df_features = self._micro_gen.generate_micro_features(df_features)

        # 接入发现的高 IC 因子（Top 15）
        try:
            from quant.factors.discovered_factors import DISCOVERED_FACTORS
            TOP_FACTORS = [
                'oi_rsi', 'vol_adj_oi_mom', 'volume_weighted_oi_change',
                'oi_norm_momentum', 'vol_weighted_oi_dir', 'oi_roc_momentum',
                'oi_relative_strength', 'oi_elasticity', 'range_expand_oi',
                'oi_flow_asymmetry', 'oi_curvature', 'bayesian_surprise_oi',
                'oi_volume_sync', 'oi_trend_reversal', 'oi_wavelet_energy'
            ]
            for fname in TOP_FACTORS:
                if fname in DISCOVERED_FACTORS:
                    try:
                        vals = DISCOVERED_FACTORS[fname](df_features)
                        if isinstance(vals, pd.Series) and len(vals) == len(df_features):
                            df_features[f'disc_{fname}'] = vals.values
                    except Exception as e:
                        logger.warning(f"Discovered factor '{fname}' 计算失败: {e}")
        except Exception as e:
            logger.warning(f"Discovered factors 模块加载失败: {e}")


        # === 归一化绝对价格特征 (使跨合约/跨时期可用) ===
        close_ref = df_features['close'].replace(0, float('nan'))
        for col in ['ma_5', 'ma_10', 'ma_20', 'ma_60']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref - 1.0
        for col in ['macd', 'macd_signal', 'macd_hist']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref
        for col in ['bb_upper', 'bb_lower', 'bb_middle']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref - 1.0
        for col in ['atr']:
            if col in df_features.columns:
                df_features[col] = df_features[col] / close_ref

        return df_features

    def prepare_training_data(self, df: pd.DataFrame):
        """
        根据输入的 OHLCV 原始数据，生成特征 X 和 目标 y

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            (X: pd.DataFrame, y: pd.Series) - 特征矩阵和目标变量
        """
        # 1. 生成特征
        df_feat = self.generate_features(df)

        # 2. 生成目标变量 y：未来 horizon 周期的对数收益率
        # 公式: log(close_{t+horizon} / close_t)
        # 注意: index 需要对齐
        df_feat['target_y'] = np.log(df_feat['close'].shift(-self.horizon) / df_feat['close'])

        # 3. 移除因为平移产生的 NaN 尾部数据
        df_clean = df_feat.dropna()

        # 4. 分离特征和目标
        y = df_clean.pop('target_y')
        X = df_clean

        # 5. 移除非数值列（如 timestamp, datetime, symbol），ML 模型只能处理数值特征
        # 保留 timestamp 作为索引，但不作为特征
        non_numeric_cols = []
        for col in ['timestamp', 'datetime', 'symbol', 'id', 'duration']:
            if col in X.columns:
                non_numeric_cols.append(col)

        if non_numeric_cols:
            X = X.drop(columns=non_numeric_cols)

        return X, y

    @staticmethod
    def train_test_split_time(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
        """
        按时间顺序划分数据集，保证不能打乱（TimeSeriesSplit 的简单实现）

        Args:
            X: 特征矩阵
            y: 目标变量
            test_size: 测试集比例，默认 0.2 (20%)

        Returns:
            (X_train, X_test, y_train, y_test) - 训练集和测试集
        """
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        return X_train, X_test, y_train, y_test
