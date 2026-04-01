"""
技术指标计算模块
使用纯 pandas 和 numpy 实现常用技术指标
"""
import numpy as np
import pandas as pd


def calculate_ma(df: pd.DataFrame, windows: list = [5, 10, 20, 60]) -> pd.DataFrame:
    """
    计算移动平均线 (Moving Average)

    Args:
        df: 包含 'close' 列的 DataFrame
        windows: 移动平均窗口列表

    Returns:
        添加了 MA 列的 DataFrame
    """
    df = df.copy()
    for window in windows:
        df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
    return df


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算 MACD (Moving Average Convergence Divergence)

    Args:
        df: 包含 'close' 列的 DataFrame
        fast: 快速 EMA 周期
        slow: 慢速 EMA 周期
        signal: 信号线周期

    Returns:
        添加了 MACD 相关列的 DataFrame
    """
    df = df.copy()

    # 计算快速和慢速 EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

    # MACD 线 = 快速 EMA - 慢速 EMA
    df['macd'] = ema_fast - ema_slow

    # 信号线 = MACD 的 EMA
    df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()

    # MACD 柱状图 = MACD - 信号线
    df['macd_hist'] = df['macd'] - df['macd_signal']

    return df


def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    计算 RSI (Relative Strength Index)

    Args:
        df: 包含 'close' 列的 DataFrame
        window: RSI 计算周期

    Returns:
        添加了 RSI 列的 DataFrame
    """
    df = df.copy()

    # 计算价格变化
    delta = df['close'].diff()

    # 分离涨跌
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # 计算平均涨跌幅
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    # 计算 RS 和 RSI
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df


def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: int = 2) -> pd.DataFrame:
    """
    计算布林带 (Bollinger Bands)

    Args:
        df: 包含 'close' 列的 DataFrame
        window: 移动平均窗口
        num_std: 标准差倍数

    Returns:
        添加了布林带列的 DataFrame
    """
    df = df.copy()

    # 中轨 = 移动平均
    df['bb_middle'] = df['close'].rolling(window=window).mean()

    # 标准差
    std = df['close'].rolling(window=window).std()

    # 上轨 = 中轨 + n * 标准差
    df['bb_upper'] = df['bb_middle'] + (num_std * std)

    # 下轨 = 中轨 - n * 标准差
    df['bb_lower'] = df['bb_middle'] - (num_std * std)

    # 布林带宽度 (可选，用于衡量波动性)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']

    return df


def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    计算 ATR (Average True Range - 真实波动幅度)

    Args:
        df: 包含 'high', 'low', 'close' 列的 DataFrame
        window: ATR 计算周期

    Returns:
        添加了 ATR 列的 DataFrame
    """
    df = df.copy()

    # 计算真实波动范围 (True Range)
    # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    # ATR = TR 的移动平均
    df['atr'] = true_range.rolling(window=window).mean()

    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术指标，用于特征工程主入口

    Args:
        df: 包含 OHLCV 数据的 DataFrame

    Returns:
        添加了所有技术指标的 DataFrame (已删除 NaN 行)
    """
    df = df.copy()

    # 依次计算各项指标
    df = calculate_ma(df)
    df = calculate_macd(df)
    df = calculate_rsi(df)
    df = calculate_bollinger_bands(df)
    df = calculate_atr(df)

    # 删除包含 NaN 的初始行
    df = df.dropna()

    return df
