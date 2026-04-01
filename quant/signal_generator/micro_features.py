"""
微观特征生成：从多合约 1m K 线中提取微观结构特征，合并到 30m K 线数据中。

关键设计：
- 不做价差调整，不拼接价格序列
- 只提取统计特征（std, ratio, slope 等），这些特征本身不受绝对价格影响
- 换月点附近（前后各 1 天）的 1m 数据丢弃，微观特征置 NaN
"""
import logging

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sqlalchemy import text

from quant.common.db import db_engine

logger = logging.getLogger(__name__)

# 默认加载的合约列表
DEFAULT_SYMBOLS = ['au2504', 'au2506', 'au2508', 'au2510', 'au2512', 'au_main', 'au2606']


class MicroFeatureGenerator:
    """从多合约 1m K 线提取微观特征，附加到 30m K 线上"""

    MICRO_FEATURE_NAMES = [
        'micro_vol_std',
        'micro_vol_ratio',
        'micro_range_mean',
        'micro_range_std',
        'micro_up_ratio',
        'micro_close_slope',
        'micro_vwap_diff',
        'micro_max_vol_bar',
        'micro_oi_change',
        'micro_tail_momentum',
    ]

    def __init__(self, config, symbols=None):
        """
        Args:
            config: 配置对象
            symbols: 要加载 1m 数据的合约列表，默认 DEFAULT_SYMBOLS
        """
        self.config = config
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.df_1m = None          # 合并后的 1m 数据（带 symbol 列）
        self.roll_dates = set()    # 换月日期集合（date 对象）
        self._load_1m_data()
        self._detect_roll_dates()

    def _load_1m_data(self):
        """从数据库加载所有合约的 1m 数据"""
        frames = []
        placeholders = ', '.join(f"'{s}'" for s in self.symbols)
        sql = text(
            f"SELECT time AS timestamp, symbol, open, high, low, close, volume, open_interest "
            f"FROM kline_data "
            f"WHERE symbol IN ({placeholders}) AND interval='1m' "
            f"ORDER BY time"
        )
        with db_engine(self.config) as engine:
            self.df_1m = pd.read_sql(sql, engine)

        if self.df_1m.empty:
            logger.warning("No 1m data loaded for symbols: %s", self.symbols)
            return

        self.df_1m['timestamp'] = pd.to_datetime(self.df_1m['timestamp'], utc=True)
        logger.info(
            "Loaded %d 1m bars from %d symbols (%s ~ %s)",
            len(self.df_1m),
            self.df_1m['symbol'].nunique(),
            self.df_1m['timestamp'].min(),
            self.df_1m['timestamp'].max(),
        )

    def _detect_roll_dates(self):
        """
        检测换月日期：找到每个时间点活跃合约发生变化的日期。
        换月日期前后各 1 天的数据都标记为不可用。
        """
        if self.df_1m is None or self.df_1m.empty:
            return

        # 按日期分组，找出每天有哪些合约在交易
        df = self.df_1m.copy()
        df['date'] = df['timestamp'].dt.date
        daily_symbols = df.groupby('date')['symbol'].apply(set).reset_index()
        daily_symbols = daily_symbols.sort_values('date').reset_index(drop=True)

        raw_roll_dates = set()
        for i in range(1, len(daily_symbols)):
            prev_syms = daily_symbols.loc[i - 1, 'symbol']
            curr_syms = daily_symbols.loc[i, 'symbol']
            # 如果活跃合约集合发生变化（有新合约出现或旧合约消失）
            if prev_syms != curr_syms:
                raw_roll_dates.add(daily_symbols.loc[i, 'date'])

        # 扩展：每个换月日期前后各 1 天
        from datetime import timedelta
        for d in list(raw_roll_dates):
            self.roll_dates.add(d - timedelta(days=1))
            self.roll_dates.add(d)
            self.roll_dates.add(d + timedelta(days=1))

        logger.info("Detected %d raw roll dates, expanded to %d blackout dates",
                     len(raw_roll_dates), len(self.roll_dates))

    def _is_roll_period(self, ts) -> bool:
        """检查某个时间戳是否在换月黑名单期间"""
        return ts.date() in self.roll_dates

    def _compute_micro(self, bars_1m: pd.DataFrame) -> dict:
        """对一组 1m bars 计算 10 个微观特征"""
        n = len(bars_1m)
        if n < 5:
            return {name: np.nan for name in self.MICRO_FEATURE_NAMES}

        vol = bars_1m['volume'].values.astype(float)
        high = bars_1m['high'].values.astype(float)
        low = bars_1m['low'].values.astype(float)
        close = bars_1m['close'].values.astype(float)
        opn = bars_1m['open'].values.astype(float)
        oi = bars_1m['open_interest'].values.astype(float)

        # 1. micro_vol_std - 成交量标准差
        micro_vol_std = np.std(vol, ddof=1) if n > 1 else 0.0

        # 2. micro_vol_ratio - 尾部成交量 / 头部成交量
        tail_vol = vol[-5:].mean() if len(vol[-5:]) > 0 else 0.0
        head_vol = vol[:-5].mean() if len(vol[:-5]) > 0 and vol[:-5].mean() > 0 else 1.0
        micro_vol_ratio = tail_vol / head_vol

        # 3. micro_range_mean - 平均振幅
        ranges = high - low
        micro_range_mean = np.mean(ranges)

        # 4. micro_range_std - 振幅标准差
        micro_range_std = np.std(ranges, ddof=1) if n > 1 else 0.0

        # 5. micro_up_ratio - 阳线比例
        micro_up_ratio = np.sum(close > opn) / n

        # 6. micro_close_slope - 收盘价线性回归斜率
        x = np.arange(n)
        if n >= 2:
            slope, _, _, _, _ = scipy_stats.linregress(x, close)
            micro_close_slope = slope
        else:
            micro_close_slope = 0.0

        # 7. micro_vwap_diff - (VWAP - 最后收盘) / 最后收盘
        total_vol = vol.sum()
        if total_vol > 0:
            typical_price = (high + low + close) / 3.0
            vwap = np.sum(typical_price * vol) / total_vol
            last_close = close[-1]
            micro_vwap_diff = (vwap - last_close) / last_close if last_close > 0 else 0.0
        else:
            micro_vwap_diff = 0.0

        # 8. micro_max_vol_bar - 最大成交量位置（归一化）
        micro_max_vol_bar = np.argmax(vol) / n if n > 0 else 0.0

        # 9. micro_oi_change - 持仓量变化
        micro_oi_change = oi[-1] - oi[0]

        # 10. micro_tail_momentum - 尾部动量
        if n >= 6 and close[-6] > 0:
            micro_tail_momentum = (close[-1] / close[-6]) - 1.0
        elif n >= 2 and close[0] > 0:
            micro_tail_momentum = (close[-1] / close[0]) - 1.0
        else:
            micro_tail_momentum = 0.0

        return {
            'micro_vol_std': micro_vol_std,
            'micro_vol_ratio': micro_vol_ratio,
            'micro_range_mean': micro_range_mean,
            'micro_range_std': micro_range_std,
            'micro_up_ratio': micro_up_ratio,
            'micro_close_slope': micro_close_slope,
            'micro_vwap_diff': micro_vwap_diff,
            'micro_max_vol_bar': micro_max_vol_bar,
            'micro_oi_change': micro_oi_change,
            'micro_tail_momentum': micro_tail_momentum,
        }

    def generate_micro_features(self, df_30m: pd.DataFrame) -> pd.DataFrame:
        """
        为 30m DataFrame 的每一行，找到对应时间段的 1m 数据，
        计算微观特征并合并。

        换月期间的微观特征置 NaN。
        没有 1m 数据覆盖的行，微观特征也为 NaN。
        """
        df = df_30m.copy()

        time_col = 'timestamp' if 'timestamp' in df.columns else 'datetime'
        df[time_col] = pd.to_datetime(df[time_col], utc=True)

        # 初始化微观特征列
        for name in self.MICRO_FEATURE_NAMES:
            df[name] = np.nan

        if self.df_1m is None or self.df_1m.empty:
            logger.warning("No 1m data loaded, returning NaN micro features")
            return df

        min_1m = self.df_1m['timestamp'].min()
        max_1m = self.df_1m['timestamp'].max()

        matched = 0
        skipped_roll = 0
        for idx in df.index:
            bar_start = df.loc[idx, time_col]
            bar_end = bar_start + pd.Timedelta(minutes=30)

            # 跳过不在 1m 覆盖范围内的
            if bar_start < min_1m or bar_start > max_1m:
                continue

            # 换月检测：如果在黑名单日期内，跳过
            if self._is_roll_period(bar_start):
                skipped_roll += 1
                continue

            # 找到 [bar_start, bar_end) 的 1m 数据（所有合约）
            mask = (self.df_1m['timestamp'] >= bar_start) & (self.df_1m['timestamp'] < bar_end)
            bars_1m = self.df_1m.loc[mask]

            if bars_1m.empty:
                continue

            # 额外换月检测：如果该时间段内有多个合约的数据，
            # 选择数据量最多的那个合约（主力合约）
            symbols_in_window = bars_1m['symbol'].unique()
            if len(symbols_in_window) > 1:
                # 多合约同时存��，选数据量最多的
                counts = bars_1m.groupby('symbol').size()
                best_symbol = counts.idxmax()
                bars_1m = bars_1m[bars_1m['symbol'] == best_symbol]

            features = self._compute_micro(bars_1m)
            for name, val in features.items():
                df.loc[idx, name] = val
            matched += 1

        logger.info("Micro features: matched %d / %d 30m bars, skipped %d (roll period)",
                     matched, len(df), skipped_roll)
        return df
