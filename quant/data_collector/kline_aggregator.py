"""
K 线聚合模块
将 Tick 数据聚合成不同周期的 K 线（1min, 5min, 15min, 1h）
输出标准 OHLCV 格式
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 支持的 K 线周期及其对应的分钟数
PERIOD_MINUTES = {
    '1min': 1,
    '5min': 5,
    '15min': 15,
    '1h': 60,
    '30m': 30,  # 兼容已有的 30 分钟周期
}


class KlineAggregator:
    """
    K 线聚合器
    
    功能：
    - 将 tick 数据列表聚合成指定周期的 K 线
    - 支持 1min / 5min / 15min / 1h / 30m 周期
    - 输出标准 OHLCV 格式（DataFrame 或 dict 列表）
    - 处理跨天、跨周边界
    """

    def __init__(self):
        # 实时聚合用的缓冲区：{symbol: {period: current_bar_dict}}
        self._bars: Dict[str, Dict[str, dict]] = defaultdict(dict)
        logger.info("kline_aggregator_initialized")

    # ------------------------------------------------------------------
    #  核心：批量聚合 —— tick list -> kline list
    # ------------------------------------------------------------------

    def aggregate_tick_to_kline(
        self,
        ticks: List[Dict],
        period: str = '1min',
    ) -> pd.DataFrame:
        """
        将 tick 数据列表按指定周期聚合为 K 线。

        Args:
            ticks: tick 数据列表，每条至少包含:
                   {
                       'symbol': str,
                       'last_price': float,
                       'volume': int/float,
                       'datetime': datetime,           # 必选
                       'open_interest': int/float,     # 可选
                   }
            period: K 线周期，可选 '1min', '5min', '15min', '1h', '30m'

        Returns:
            pd.DataFrame，列: timestamp, open, high, low, close, volume,
                              open_interest, symbol
            按 timestamp 升序排列。空输入返回空 DataFrame。
        """
        if period not in PERIOD_MINUTES:
            raise ValueError(
                f"不支持的周期 '{period}'，可选: {list(PERIOD_MINUTES.keys())}"
            )

        if not ticks:
            logger.warning(f"aggregate_tick_to_kline_empty_input period=period")
            return self._empty_kline_df()

        minutes = PERIOD_MINUTES[period]

        # 按 bar 起始时间分组
        grouped: Dict[tuple, list] = defaultdict(list)  # (symbol, bar_start) -> [tick, ...]
        for tick in ticks:
            try:
                tick_time = self._ensure_datetime(tick['datetime'])
                bar_start = self._align_time(tick_time, minutes)
                symbol = tick.get('symbol', 'UNKNOWN')
                grouped[(symbol, bar_start)].append(tick)
            except Exception as e:
                logger.warning(
                    "tick_parse_error",
                    tick=str(tick)[:200],
                    error=str(e),
                )
                continue

        # 聚合每组 ticks 成一根 K 线
        bars = []
        for (symbol, bar_start), group_ticks in sorted(grouped.items()):
            bar = self._aggregate_group(symbol, bar_start, group_ticks)
            bars.append(bar)

        df = pd.DataFrame(bars)
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(
            "aggregate_tick_to_kline_done",
            period=period,
            tick_count=len(ticks),
            bar_count=len(df),
        )
        return df

    # ------------------------------------------------------------------
    #  实时聚合 —— 逐条 tick 喂入，周期结束时返回完成的 bar
    # ------------------------------------------------------------------

    def on_tick(
        self,
        tick: Dict,
        period: str = '1min',
    ) -> Optional[dict]:
        """
        逐条 tick 实时聚合，返回「已完成」的 bar（未完成返回 None）。

        适合在 OnRtnDepthMarketData 回调中调用。

        Args:
            tick: 单条 tick 数据
            period: 聚合周期

        Returns:
            完成的 bar dict（含 timestamp/open/high/low/close/volume/open_interest/symbol），
            或 None。
        """
        if period not in PERIOD_MINUTES:
            raise ValueError(f"不支持的周期 '{period}'")

        minutes = PERIOD_MINUTES[period]
        symbol = tick.get('symbol', 'UNKNOWN')
        tick_time = self._ensure_datetime(tick['datetime'])
        bar_start = self._align_time(tick_time, minutes)
        bar_end = bar_start + timedelta(minutes=minutes)

        current = self._bars[symbol].get(period)

        finished_bar = None

        if current is not None:
            # 当前 tick 已经超过了正在构建的 bar 的时间窗口
            if tick_time >= current['_bar_end']:
                finished_bar = self._finalize_bar(current)
                current = None  # 强制新建

        if current is None:
            # 创建新 bar
            current = {
                'symbol': symbol,
                'timestamp': bar_start,
                '_bar_end': bar_end,
                'open': tick['last_price'],
                'high': tick['last_price'],
                'low': tick['last_price'],
                'close': tick['last_price'],
                'volume': tick.get('volume', 0),
                'open_interest': tick.get('open_interest', 0),
                '_first_volume': tick.get('volume', 0),
            }
            self._bars[symbol][period] = current
        else:
            # 更新当前 bar
            price = tick['last_price']
            current['high'] = max(current['high'], price)
            current['low'] = min(current['low'], price)
            current['close'] = price
            current['volume'] = tick.get('volume', 0)
            current['open_interest'] = tick.get('open_interest', 0)

        return finished_bar

    def flush(self, symbol: str = None, period: str = None) -> List[dict]:
        """
        强制输出当前正在构建的 bar（不等待周期结束）。
        用于收盘/停机时将未完成的 bar 保存下来。

        Args:
            symbol: 指定合约（None 表示全部）
            period: 指定周期（None 表示全部）

        Returns:
            完成的 bar 列表
        """
        flushed = []
        symbols = [symbol] if symbol else list(self._bars.keys())
        for sym in symbols:
            if sym not in self._bars:
                continue
            periods = [period] if period else list(self._bars[sym].keys())
            for p in periods:
                bar = self._bars[sym].pop(p, None)
                if bar:
                    flushed.append(self._finalize_bar(bar))
        return flushed

    # ------------------------------------------------------------------
    #  内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _align_time(dt: datetime, minutes: int) -> datetime:
        """
        将时间对齐到周期边界。
        例如 minutes=5 时，09:03:27 -> 09:00:00；09:07:15 -> 09:05:00
        ���于 1h (60min)，对齐到整点。
        """
        if minutes >= 60:
            # 按小时对齐
            hours = minutes // 60
            aligned_hour = (dt.hour // hours) * hours
            return dt.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
        else:
            total_minutes = dt.hour * 60 + dt.minute
            aligned_minutes = (total_minutes // minutes) * minutes
            aligned_hour = aligned_minutes // 60
            aligned_minute = aligned_minutes % 60
            return dt.replace(
                hour=aligned_hour,
                minute=aligned_minute,
                second=0,
                microsecond=0,
            )

    @staticmethod
    def _ensure_datetime(value) -> datetime:
        """将各种时间格式统一转成 datetime。"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, str):
            # 尝试几种常见格式
            for fmt in (
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
            ):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            # 最后尝试 pandas 解析
            return pd.Timestamp(value).to_pydatetime()
        raise TypeError(f"无法将 {type(value)} 转换为 datetime")

    @staticmethod
    def _aggregate_group(symbol: str, bar_start: datetime, ticks: List[Dict]) -> dict:
        """聚合一组属于同一 bar 的 ticks。"""
        prices = [t['last_price'] for t in ticks]
        volumes = [t.get('volume', 0) for t in ticks]
        open_interests = [t.get('open_interest', 0) for t in ticks]

        # 成交量处理：
        # CTP 的 volume 是累计值，取最后一条减第一条得到该 bar 区间增量；
        # 如果只有一条 tick 或看起来不是累计值（后面比前面小），就取最大值。
        first_vol = volumes[0]
        last_vol = volumes[-1]
        if last_vol >= first_vol and len(volumes) > 1:
            bar_volume = last_vol - first_vol
        else:
            bar_volume = max(volumes)

        return {
            'timestamp': bar_start,
            'symbol': symbol,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': bar_volume,
            'open_interest': open_interests[-1] if open_interests else 0,
        }

    @staticmethod
    def _finalize_bar(bar: dict) -> dict:
        """从内部 bar 结构生成干净的输出 dict，去掉内部字段。"""
        return {
            'timestamp': bar['timestamp'],
            'symbol': bar['symbol'],
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar['volume'],
            'open_interest': bar.get('open_interest', 0),
        }

    @staticmethod
    def _empty_kline_df() -> pd.DataFrame:
        """返回一个空的 K 线 DataFrame。"""
        return pd.DataFrame(
            columns=[
                'timestamp', 'symbol', 'open', 'high',
                'low', 'close', 'volume', 'open_interest',
            ]
        )
