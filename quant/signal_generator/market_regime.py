"""
市场状态识别模块
使用 ATR+ADX 规则引擎 + HMM 隐马尔可夫模型识别市场状态
"""
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path


class MarketRegimeDetector:
    """市场状态检测器，结合规则引擎和 HMM 模型识别市场状态"""

    def __init__(self, model_path: str = 'models/hmm_model.pkl'):
        """
        初始化市场状态检测器

        Args:
            model_path: HMM 模型保存路径（相对于项目根目录）
        """
        # 解析项目根目录（假设脚本在 E:\quant-trading-mvp 下运行）
        project_root = Path(__file__).parent.parent.parent
        self.model_path = project_root / model_path
        
        # 规则引擎参数
        self.adx_trending_threshold = 25  # ADX > 25 为趋势市
        self.adx_ranging_threshold = 20   # ADX < 20 为震荡市
        self.atr_ratio_ranging_threshold = 0.005  # ATR/close < 0.005 为低波动
        self.atr_volatile_multiplier = 1.5  # ATR > 均值 1.5 倍为高波动
        self.atr_window = 20  # ATR 均值计算窗口
        
        # HMM 参数
        self.hmm_n_components = 3  # 3 个隐状态
        self.hmm_n_iter = 100  # 迭代次数
        self.hmm_window = 100  # 用于 HMM 特征计算的 K 线数量
        
        # HMM 模型
        self.hmm_model = None
        self.state_mapping = {}  # HMM 状态到市场状态的映射
        
        # 尝试加载现有模型
        self._load_model()

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ADX (Average Directional Index)

        Args:
            df: 包含 high, low, close 的 DataFrame
            period: ADX 计算周期

        Returns:
            ADX 值（最新一根的值）
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        n = len(df)
        if n < period * 2 + 1:
            # 数据不足，返回默认值
            return 15.0  # 默认中间值

        # 计算 +DM 和 -DM
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)

        for i in range(1, n):
            plus_move = high[i] - high[i-1]
            minus_move = low[i-1] - low[i]

            if plus_move > minus_move and plus_move > 0:
                plus_dm[i] = plus_move
            if minus_move > plus_move and minus_move > 0:
                minus_dm[i] = minus_move

        # 计算 TR (True Range)
        tr = np.zeros(n)
        for i in range(n):
            if i == 0:
                tr[i] = high[i] - low[i]
            else:
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                tr[i] = max(tr1, tr2, tr3)

        # 计算 ATR (使用 Welles Wilder 的平滑方法)
        atr = np.zeros(n)
        atr[period-1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        # 计算 +DI 和 -DI
        plus_di = np.zeros(n)
        minus_di = np.zeros(n)
        
        # 先计算平滑的 +DM 和 -DM
        plus_dm_smooth = np.zeros(n)
        minus_dm_smooth = np.zeros(n)
        plus_dm_smooth[period-1] = np.sum(plus_dm[:period])
        minus_dm_smooth[period-1] = np.sum(minus_dm[:period])
        
        for i in range(period, n):
            plus_dm_smooth[i] = plus_dm_smooth[i-1] - plus_dm_smooth[i-1]/period + plus_dm[i]
            minus_dm_smooth[i] = minus_dm_smooth[i-1] - minus_dm_smooth[i-1]/period + minus_dm[i]
        
        # 计算 +DI 和 -DI
        for i in range(period, n):
            if atr[i] > 0:
                plus_di[i] = 100 * plus_dm_smooth[i] / atr[i]
                minus_di[i] = 100 * minus_dm_smooth[i] / atr[i]

        # 计算 DX
        dx = np.zeros(n)
        for i in range(period, n):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / di_sum

        # 计算 ADX (DX 的平滑)
        adx = np.zeros(n)
        adx[period*2-1] = np.mean(dx[period:period*2])
        for i in range(period*2, n):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period

        # 返回最后一个有效值
        last_adx = adx[-1]
        if np.isnan(last_adx) or last_adx <= 0:
            return 15.0  # 默认中间值
        
        return float(last_adx)

    def _calculate_atr_ma(self, df: pd.DataFrame, atr_window: int = 20) -> float:
        """
        计算过去 N 根 K 线的 ATR 均值

        Args:
            df: 包含 atr 列的 DataFrame
            atr_window: ATR 均值计算窗口

        Returns:
            ATR 均值
        """
        return df['atr'].iloc[-atr_window:].mean()

    def _detect_rule_engine(self, df: pd.DataFrame) -> tuple:
        """
        使用 ATR+ADX 规则引擎检测市场状态

        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            (regime: str, adx: float, atr_ratio: float, params: dict)
        """
        # 计算 ADX
        adx = self._calculate_adx(df)
        
        # 计算当前 ATR 和归一化 ATR
        current_atr = df['atr'].iloc[-1]
        current_close = df['close'].iloc[-1]
        atr_ratio = current_atr / current_close if current_close > 0 else 0
        
        # 计算 ATR 均值（过去 20 根）
        atr_ma = self._calculate_atr_ma(df, self.atr_window)
        
        # 规则判断
        # 1. 检查是否为高波动状态（优先）
        if current_atr > atr_ma * self.atr_volatile_multiplier:
            regime = 'volatile'
            params = {
                'confidence_boost': 0.0,
                'stop_loss_multiplier': 1.0,
                'confidence_threshold': 0.7,
                'pause_trading': True,
                'reason': 'ATR 突然放大，波动率异常'
            }
        # 2. 检查是否为趋势市
        elif adx > self.adx_trending_threshold:
            regime = 'trending'
            params = {
                'confidence_boost': 0.1,  # 趋势明确时提高置信度
                'stop_loss_multiplier': 1.5,  # 放宽止损
                'confidence_threshold': 0.5,  # 降低开仓阈值
                'pause_trading': False,
                'reason': 'ADX 高于阈值，趋势明确'
            }
        # 3. 检查是否为震荡市
        elif adx < self.adx_ranging_threshold and atr_ratio < self.atr_ratio_ranging_threshold:
            regime = 'ranging'
            params = {
                'confidence_boost': 0.0,
                'stop_loss_multiplier': 1.0,
                'confidence_threshold': 0.6,  # 降低置信度阈值
                'pause_trading': False,
                'reason': 'ADX 低且 ATR 归一化值低，市场震荡'
            }
        else:
            # 默认状态，无明显特征
            regime = 'ranging'
            params = {
                'confidence_boost': 0.0,
                'stop_loss_multiplier': 1.0,
                'confidence_threshold': 0.7,
                'pause_trading': False,
                'reason': '无明显市场特征，默认震荡'
            }

        return regime, adx, atr_ratio, params

    def _prepare_hmm_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        准备 HMM 模型输入特征

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            特征矩阵 [returns, volatility, volume_ratio]
        """
        # 取最近 100 根 K 线
        recent_df = df.tail(self.hmm_window).copy()
        
        # 计算收益率
        returns = recent_df['close'].pct_change().fillna(0)
        
        # 计算波动率（滚动标准差）
        volatility = returns.rolling(window=5).std().fillna(0)
        
        # 计算成交量比率
        volume_ma = recent_df['volume'].rolling(window=5).mean()
        volume_ratio = (recent_df['volume'] / volume_ma).fillna(1).replace([np.inf, -np.inf], 1)
        
        # 组合特征
        features = pd.concat([returns, volatility, volume_ratio], axis=1).values
        
        return features

    def _train_hmm(self, features: np.ndarray):
        """
        训练 HMM 模型

        Args:
            features: 特征矩阵
        """
        try:
            from hmmlearn import hmm
        except ImportError:
            print("警告：hmmlearn 未安装，跳过 HMM 训练。请运行：pip install hmmlearn")
            return

        # 创建并训练 HMM 模型
        self.hmm_model = hmm.GaussianHMM(
            n_components=self.hmm_n_components,
            covariance_type='full',
            n_iter=self.hmm_n_iter,
            random_state=42
        )
        
        # 训练模型
        self.hmm_model.fit(features)
        
        # 保存模型
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.hmm_model, f)
        
        # 根据各状态的平均波动率映射到市场状态
        # 状态 0: 低波动 -> ranging
        # 状态 1: 中波动 -> trending  
        # 状态 2: 高波动 -> volatile
        self._map_hmm_states(features)

    def _map_hmm_states(self, features: np.ndarray):
        """
        根据各状态的平均波动率映射 HMM 状态到市场状态

        Args:
            features: 用于训练的特征矩阵
        """
        if self.hmm_model is None:
            return

        # 获取每个样本的预测状态
        states = self.hmm_model.predict(features)
        
        # 计算每个状态的平均波动率（volatility 是第 2 列）
        state_volatility = {}
        for state in range(self.hmm_n_components):
            state_mask = states == state
            if np.sum(state_mask) > 0:
                state_volatility[state] = features[state_mask, 1].mean()
            else:
                state_volatility[state] = 0
        
        # 按波动率排序
        sorted_states = sorted(state_volatility.items(), key=lambda x: x[1])
        
        # 映射：低波动 -> ranging, 中波动 -> trending, 高波动 -> volatile
        if len(sorted_states) >= 3:
            self.state_mapping = {
                sorted_states[0][0]: 'ranging',
                sorted_states[1][0]: 'trending',
                sorted_states[2][0]: 'volatile'
            }
        elif len(sorted_states) == 2:
            self.state_mapping = {
                sorted_states[0][0]: 'ranging',
                sorted_states[1][0]: 'volatile'
            }
        else:
            self.state_mapping = {0: 'ranging'}

    def _load_model(self):
        """加载已保存的 HMM 模型"""
        if not os.path.exists(self.model_path):
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                self.hmm_model = pickle.load(f)
            print(f"HMM 模型已加载：{self.model_path}")
        except Exception as e:
            print(f"加载 HMM 模型失败：{e}")
            self.hmm_model = None

    def _detect_hmm(self, df: pd.DataFrame) -> str:
        """
        使用 HMM 模型检测市场状态

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            市场状态：'trending' | 'ranging' | 'volatile'
        """
        if self.hmm_model is None:
            # 如果模型不存在，返回默认状态
            return 'ranging'
        
        try:
            # 准备特征
            features = self._prepare_hmm_features(df)
            
            # 预测最后一个状态
            last_state = self.hmm_model.predict(features[-1:])[0]
            
            # 映射到市场状态
            regime = self.state_mapping.get(last_state, 'ranging')
            
            return regime
        except Exception as e:
            print(f"HMM 预测失败：{e}")
            return 'ranging'

    def detect(self, df: pd.DataFrame) -> dict:
        """
        检测市场状态（主方法）

        输入带技术指标的 DataFrame（已经过 FeatureEngineer 处理）
        
        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            {
                'regime': 'trending' | 'ranging' | 'volatile',
                'regime_rule': 'trending' | 'ranging' | 'volatile',
                'regime_hmm': 'trending' | 'ranging' | 'volatile',
                'confidence': float,
                'adx': float,
                'atr_ratio': float,
                'params': dict
            }
        """
        # 1. 规则引擎检测
        regime_rule, adx, atr_ratio, params = self._detect_rule_engine(df)
        
        # 2. HMM 检测（如果模型不存在则自动训练）
        if self.hmm_model is None:
            print("HMM 模型不存在，正在训练...")
            features = self._prepare_hmm_features(df)
            self._train_hmm(features)
        
        regime_hmm = self._detect_hmm(df)
        
        # 3. 综合判断
        # 以规则引擎为准
        regime = regime_rule
        
        # 计算置信度
        base_confidence = 0.7  # 基础置信度
        
        if regime_rule == regime_hmm:
            # 两者一致，提高置信度
            confidence = base_confidence + 0.15
        else:
            # 不一致，降低置信度
            confidence = base_confidence - 0.05
        
        # 应用规则引擎的置信度调整
        confidence += params.get('confidence_boost', 0)
        
        # 确保置信度在合理范围
        confidence = max(0.1, min(1.0, confidence))
        
        return {
            'regime': regime,
            'regime_rule': regime_rule,
            'regime_hmm': regime_hmm,
            'confidence': round(confidence, 3),
            'adx': round(adx, 3),
            'atr_ratio': round(atr_ratio, 5),
            'params': params
        }
