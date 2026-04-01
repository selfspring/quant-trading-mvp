"""
LLM 自动发现的因子库
每个因子经过 IC 评估验证有效（avg |IC| > 0.02）
"""
import numpy as np
import pandas as pd

# 自动发现的因子注册表
DISCOVERED_FACTORS = {}


def oi_price_momentum(df):
    """持仓价格联动：5期价格收益率与持仓量变化率的乘积
    avg |IC| = 0.0231, 4h IC=0.0381, 8h IC=0.0240
    """
    price_ret = df['close'].pct_change(5)
    oi_ret = df['open_interest'].pct_change(5)
    return price_ret * oi_ret * 1000

DISCOVERED_FACTORS['oi_price_momentum'] = oi_price_momentum


def oi_surprise(df):
    """持仓量意外：持仓量变化的z-score（相对20期均值和标准差）
    avg |IC| = 0.0206, 8h IC=0.0307
    """
    oi_change = df['open_interest'].diff()
    expected = oi_change.rolling(20).mean()
    std = oi_change.rolling(20).std()
    surprise = (oi_change - expected) / (std + 1e-8)
    return surprise

DISCOVERED_FACTORS['oi_surprise'] = oi_surprise


def oi_momentum_divergence(df):
    """持仓动量背离：10期价格动量z与持仓动量z的差
    avg |IC| = 0.0204, 4h IC=-0.0289
    """
    price_mom = df['close'].pct_change(10)
    oi_mom = df['open_interest'].pct_change(10)
    p_z = (price_mom - price_mom.rolling(20).mean()) / (price_mom.rolling(20).std() + 1e-8)
    o_z = (oi_mom - oi_mom.rolling(20).mean()) / (oi_mom.rolling(20).std() + 1e-8)
    return p_z - o_z

DISCOVERED_FACTORS['oi_momentum_divergence'] = oi_momentum_divergence


def realized_kurtosis(df):
    """已实现峰度取反：30期收益率峰度，高峰度看跌
    avg |IC| = 0.0292, 4h IC=-0.0317, 8h IC=-0.0289
    """
    import pandas as pd
    ret = np.log(df['close'] / df['close'].shift(1))
    kurt = ret.rolling(30).apply(lambda x: pd.Series(x).kurtosis(), raw=False)
    return -kurt

DISCOVERED_FACTORS['realized_kurtosis'] = realized_kurtosis


def oi_volume_ratio_change(df):
    """持仓量比变化：OI/Volume比值的5期变化率
    avg |IC| = 0.0227, 2h IC=0.0315
    """
    ratio = df['open_interest'] / (df['volume'] + 1e-8)
    ratio_change = ratio.pct_change(5)
    return ratio_change

DISCOVERED_FACTORS['oi_volume_ratio_change'] = oi_volume_ratio_change


def oi_regime(df):
    """持仓量状态：100期持仓量分位数*10期收益率
    avg |IC| = 0.0254, 4h IC=0.0323, 8h IC=0.0315
    """
    import pandas as pd
    oi_pct = df['open_interest'].rolling(100).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    price_ret = df['close'].pct_change(10)
    return oi_pct * price_ret * 100

DISCOVERED_FACTORS['oi_regime'] = oi_regime


def oi_concentration_momentum(df):
    """持仓集中度动量：OI/Volume比值偏离20期均值的z-score
    avg |IC| = 0.0241, 2h IC=0.0306
    """
    oi_ratio = df['open_interest'] / (df['volume'] + 1e-8)
    oi_ratio_ma = oi_ratio.rolling(20).mean()
    return (oi_ratio - oi_ratio_ma) / (oi_ratio.rolling(20).std() + 1e-8)

DISCOVERED_FACTORS['oi_concentration_momentum'] = oi_concentration_momentum


def volatility_asymmetry(df):
    """波动率不对称性：上行波动率与下行波动率之差/之和
    avg |IC| = 0.0276, 4h IC=0.0329
    """
    ret = np.log(df['close'] / df['close'].shift(1))
    up_vol = ret.where(ret > 0, 0).rolling(20).std()
    down_vol = ret.where(ret < 0, 0).rolling(20).std()
    return (up_vol - down_vol) / (up_vol + down_vol + 1e-8)

DISCOVERED_FACTORS['volatility_asymmetry'] = volatility_asymmetry


def volume_weighted_price_accel(df):
    """成交量加权价格加速度：量归一化收益的短期累积减长期均值
    avg |IC| = 0.0202, 8h IC=0.0390
    """
    ret = df['close'].pct_change()
    vol_norm = df['volume'] / df['volume'].rolling(20).mean()
    vw_ret = ret * vol_norm
    mom_short = vw_ret.rolling(5).sum()
    mom_long = vw_ret.rolling(20).sum()
    return mom_short - mom_long / 4

DISCOVERED_FACTORS['volume_weighted_price_accel'] = volume_weighted_price_accel


def volatility_cone_position(df):
    """波动率锥位置：多窗口波动率分位数均值
    avg |IC| = 0.0322, 8h IC=0.0389
    """
    ret = np.log(df['close'] / df['close'].shift(1))
    positions = []
    for w in [10, 20, 40, 60]:
        vol = ret.rolling(w).std()
        pct = vol.rolling(100).rank(pct=True)
        positions.append(pct)
    avg_pos = pd.concat(positions, axis=1).mean(axis=1)
    return avg_pos - 0.5

DISCOVERED_FACTORS['volatility_cone_position'] = volatility_cone_position


def oi_ma_cross_momentum(df):
    """OI均线交叉动量：OI短长均线差值的变化率
    avg |IC| = 0.0305, 8h IC=0.0558
    """
    oi_ma5 = df['open_interest'].rolling(5).mean()
    oi_ma20 = df['open_interest'].rolling(20).mean()
    diff = (oi_ma5 - oi_ma20) / (oi_ma20 + 1e-8)
    return diff.diff(3)

DISCOVERED_FACTORS['oi_ma_cross_momentum'] = oi_ma_cross_momentum


def volume_distribution_skew(df):
    """成交量分布偏度：30期量偏度乘以价格方向
    avg |IC| = 0.0227, 8h IC=0.0283
    """
    vol_skew = df['volume'].rolling(30).apply(lambda x: pd.Series(x).skew(), raw=False)
    price_dir = np.sign(df['close'].pct_change(10))
    return vol_skew * price_dir

DISCOVERED_FACTORS['volume_distribution_skew'] = volume_distribution_skew


def volatility_persistence(df):
    """波动率持续性：绝对收益率40期自相关
    avg |IC| = 0.0481, 8h IC=0.0689
    """
    ret = np.log(df['close'] / df['close'].shift(1))
    abs_ret = abs(ret)
    autocorr = abs_ret.rolling(40).apply(
    lambda x: pd.Series(x).autocorr(lag=1), raw=False)
    return autocorr

DISCOVERED_FACTORS['volatility_persistence'] = volatility_persistence


def oi_divergence_persistence(df):
    """OI背离持续性：OI与价格方向不一致的持续期数乘以OI方向
    avg |IC| = 0.0287, 4h IC=0.0359, 8h IC=0.0406
    """
    oi_dir = np.sign(df['open_interest'].diff())
    price_dir = np.sign(df['close'].diff())
    diverge = (oi_dir != price_dir).astype(float)
    return diverge.rolling(20).sum() * np.sign(df['open_interest'].diff(5))

DISCOVERED_FACTORS['oi_divergence_persistence'] = oi_divergence_persistence


def relative_vol_oi_ratio(df):
    """相对量仓比：Volume/OI的z-score
    avg |IC| = 0.0212, 2h IC=-0.0297
    """
    vol_oi = df['volume'] / (df['open_interest'] + 1e-8)
    vol_oi_ma = vol_oi.rolling(20).mean()
    vol_oi_std = vol_oi.rolling(20).std()
    return (vol_oi - vol_oi_ma) / (vol_oi_std + 1e-8)

DISCOVERED_FACTORS['relative_vol_oi_ratio'] = relative_vol_oi_ratio


def oi_trend_strength(df):
    """OI趋势强度：OI三均线排列方向乘以价格动量
    avg |IC| = 0.0353, 2h IC=0.0408, 4h IC=0.0489
    """
    oi_sma5 = df['open_interest'].rolling(5).mean()
    oi_sma20 = df['open_interest'].rolling(20).mean()
    oi_sma60 = df['open_interest'].rolling(60).mean()
    oi_aligned = ((oi_sma5 > oi_sma20) & (oi_sma20 > oi_sma60)).astype(float) - \
                 ((oi_sma5 < oi_sma20) & (oi_sma20 < oi_sma60)).astype(float)
    return oi_aligned * df['close'].pct_change(10)

DISCOVERED_FACTORS['oi_trend_strength'] = oi_trend_strength


def volume_weighted_oi_change(df):
    """成交量加权OI变化：OI变化乘以相对成交量的累积z-score
    avg |IC| = 0.0640, 4h IC=0.0781, 8h IC=0.0849
    """
    oi_chg = df['open_interest'].diff()
    vol_norm = df['volume'] / df['volume'].rolling(20).mean()
    raw = (oi_chg * vol_norm).rolling(10).sum()
    return (raw - raw.rolling(30).mean()) / (raw.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['volume_weighted_oi_change'] = volume_weighted_oi_change


def candle_body_accumulation(df):
    """K线实体累积：15期K线实体百分比之和
    avg |IC| = 0.0243, 4h IC=0.0339
    """
    body = (df['close'] - df['open']) / (df['open'] + 1e-8)
    return body.rolling(15).sum()

DISCOVERED_FACTORS['candle_body_accumulation'] = candle_body_accumulation


def vol_surprise_oi_interaction(df):
    """量意外与OI意外交互：成交量z-score乘以OI变化z-score
    avg |IC| = 0.0262, 4h IC=0.0390
    """
    vol_z = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-8)
    oi_diff = df['open_interest'].diff()
    oi_z = (oi_diff - oi_diff.rolling(20).mean()) / (oi_diff.rolling(20).std() + 1e-8)
    return vol_z * oi_z

DISCOVERED_FACTORS['vol_surprise_oi_interaction'] = vol_surprise_oi_interaction


def hour_of_day_momentum(df):
    """时段动量：夜盘和早盘加权收益的累积
    avg |IC| = 0.0319, 8h IC=0.0396
    """
    hour = df['timestamp'].dt.hour
    session_weight = pd.Series(0.0, index=df.index)
    session_weight[(hour >= 21) | (hour <= 1)] = 1.0
    session_weight[(hour >= 9) & (hour <= 10)] = 0.5
    ret = df['close'].pct_change()
    return (ret * session_weight).rolling(20).sum()

DISCOVERED_FACTORS['hour_of_day_momentum'] = hour_of_day_momentum


def oi_elasticity(df):
    """OI弹性：OI变化率对价格变化率的弹性系数z-score
    avg |IC| = 0.0581, 4h IC=0.0700, 8h IC=0.0530
    """
    price_ret = df['close'].pct_change(5)
    oi_ret = df['open_interest'].pct_change(5)
    elasticity = (oi_ret / (price_ret + 1e-8)).clip(-10, 10)
    em = elasticity.rolling(10).mean()
    return (em - em.rolling(30).mean()) / (em.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_elasticity'] = oi_elasticity


def oi_relative_strength(df):
    """OI相对强弱：类RSI的OI强弱指标归一化
    avg |IC| = 0.0589, 4h IC=0.0657, 8h IC=0.0575
    """
    oi_diff = df['open_interest'].diff()
    oi_gain = oi_diff.clip(lower=0).rolling(14).mean()
    oi_loss = (-oi_diff.clip(upper=0)).rolling(14).mean()
    oi_rs = oi_gain / (oi_loss + 1e-8)
    oi_rsi = 100 - 100 / (1 + oi_rs)
    return (oi_rsi - 50) / 50

DISCOVERED_FACTORS['oi_relative_strength'] = oi_relative_strength


def weighted_volume_momentum(df):
    """加权量价动量：线性加权的量归一化收益
    avg |IC| = 0.0275, 4h IC=0.0335
    """
    weights = np.arange(1, 21, dtype=float)
    weights = weights / weights.sum()
    ret = df['close'].pct_change()
    vol_norm = df['volume'] / df['volume'].rolling(20).mean()
    weighted_ret = ret * vol_norm
    return weighted_ret.rolling(20).apply(lambda x: np.dot(x, weights), raw=True)

DISCOVERED_FACTORS['weighted_volume_momentum'] = weighted_volume_momentum


def oi_breakout_confirm(df):
    """OI突破确认：价格突破20期高低点时OI是否配合增仓
    avg |IC| = 0.0318, 4h IC=0.0489
    """
    price_high20 = df['close'].rolling(20).max()
    price_low20 = df['close'].rolling(20).min()
    price_breakout = (df['close'] >= price_high20).astype(float) - \
                     (df['close'] <= price_low20).astype(float)
    oi_increasing = (df['open_interest'].diff(3) > 0).astype(float) * 2 - 1
    return (price_breakout * oi_increasing).rolling(5).sum()

DISCOVERED_FACTORS['oi_breakout_confirm'] = oi_breakout_confirm


def multiscale_oi_divergence(df):
    """多尺度OI背离：短期与长期OI方向不一致时的短期OI变化
    avg |IC| = 0.0363, 4h IC=0.0385, 8h IC=0.0675
    """
    oi_5 = df['open_interest'].pct_change(5)
    oi_60 = df['open_interest'].pct_change(60)
    return (np.sign(oi_5) != np.sign(oi_60)).astype(float) * oi_5

DISCOVERED_FACTORS['multiscale_oi_divergence'] = multiscale_oi_divergence


def oi_momentum_persistence(df):
    """OI动量持续性：OI增加频率偏离50%乘以价格动量
    avg |IC| = 0.0396, 2h IC=0.0462, 4h IC=0.0516
    """
    oi_ret = df['open_interest'].pct_change()
    oi_pos = (oi_ret > 0).astype(float)
    oi_persist = oi_pos.rolling(20).mean()
    price_mom = df['close'].pct_change(10)
    return (oi_persist - 0.5) * 2 * price_mom

DISCOVERED_FACTORS['oi_momentum_persistence'] = oi_momentum_persistence


def oi_volume_sync(df):
    """OI量同步：OI和成交量同向变化的方向性累积
    avg |IC| = 0.0515, 4h IC=0.0584, 8h IC=0.0598
    """
    oi_dir = np.sign(df['open_interest'].diff())
    vol_dir = np.sign(df['volume'].diff())
    sync = (oi_dir == vol_dir).astype(float) * oi_dir
    return sync.rolling(15).sum()

DISCOVERED_FACTORS['oi_volume_sync'] = oi_volume_sync


def price_acceleration(df):
    """价格加速度z-score：短期动量超出长期动量的标准化偏离
    avg |IC| = 0.0245, 8h IC=0.0340
    """
    mom_5 = df['close'].pct_change(5)
    mom_20 = df['close'].pct_change(20)
    accel = mom_5 - mom_20 / 4
    return (accel - accel.rolling(30).mean()) / (accel.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['price_acceleration'] = price_acceleration


def return_entropy(df):
    """收益率信息熵：30期收益分布熵的z-score，低熵=趋势明确
    avg |IC| = 0.0443, 4h IC=-0.0433, 8h IC=-0.0561
    """
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    def _entropy(x):
        bins = np.histogram(x, bins=10)[0]
        p = bins / bins.sum()
        p = p[p > 0]
        return -np.sum(p * np.log2(p))
    ent = ret.rolling(30).apply(_entropy, raw=True)
    return (ent - ent.rolling(60).mean()) / (ent.rolling(60).std() + 1e-8)

DISCOVERED_FACTORS['return_entropy'] = return_entropy


def hurst_proxy(df):
    """Hurst指数代理：R/S法估计，>0.5趋势，<0.5均值回归
    avg |IC| = 0.0207, 8h IC=-0.0377
    """
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    def _hurst(x):
        n = len(x)
        if n < 10: return 0.5
        mean = np.mean(x)
        y = np.cumsum(x - mean)
        r = np.max(y) - np.min(y)
        s = np.std(x, ddof=1)
        if s < 1e-10: return 0.5
        return np.log(r / s + 1e-10) / np.log(n)
    h = ret.rolling(40).apply(_hurst, raw=True)
    return h - 0.5

DISCOVERED_FACTORS['hurst_proxy'] = hurst_proxy


def oi_dispersion(df):
    """OI变化离散度：OI变化率的变异系数z-score
    avg |IC| = 0.0361, 8h IC=0.0581
    """
    oi_ret = df['open_interest'].pct_change()
    disp = oi_ret.rolling(20).std() / (oi_ret.rolling(20).mean().abs() + 1e-8)
    return (disp - disp.rolling(60).mean()) / (disp.rolling(60).std() + 1e-8)

DISCOVERED_FACTORS['oi_dispersion'] = oi_dispersion


def oi_curvature(df):
    """OI曲率：OI三均线二阶差分z-score，检测OI拐点
    avg |IC| = 0.0559, 4h IC=0.0582, 8h IC=0.0736
    """
    ma10 = df['open_interest'].rolling(10).mean()
    ma20 = df['open_interest'].rolling(20).mean()
    ma40 = df['open_interest'].rolling(40).mean()
    curv = ma10 - 2 * ma20 + ma40
    return (curv - curv.rolling(30).mean()) / (curv.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_curvature'] = oi_curvature


def parkinson_vol_ratio(df):
    """Parkinson波动率比：高低价波动率/收盘价波动率，检测隐藏波动
    avg |IC| = 0.0482, 4h IC=-0.0518, 8h IC=-0.0526
    """
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    park = np.sqrt((np.log(df['high'] / df['low']) ** 2).rolling(20).mean() / (4 * np.log(2)))
    close_vol = ret.rolling(20).std()
    ratio = park / (close_vol + 1e-8)
    return (ratio - ratio.rolling(60).mean()) / (ratio.rolling(60).std() + 1e-8)

DISCOVERED_FACTORS['parkinson_vol_ratio'] = parkinson_vol_ratio


def vol_mom_divergence(df):
    """量价动量背离：价格动量z与成交量动量z的差
    avg |IC| = 0.0269, 4h IC=0.0303, 8h IC=0.0494
    """
    price_mom = df['close'].pct_change(10)
    vol_mom = df['volume'].pct_change(10)
    pm_z = (price_mom - price_mom.rolling(30).mean()) / (price_mom.rolling(30).std() + 1e-8)
    vm_z = (vol_mom - vol_mom.rolling(30).mean()) / (vol_mom.rolling(30).std() + 1e-8)
    return pm_z - vm_z

DISCOVERED_FACTORS['vol_mom_divergence'] = vol_mom_divergence


def oi_accumulation_speed(df):
    """OI累积速度：短期OI累积占长期累积的比例z-score
    avg |IC| = 0.0225, 8h IC=0.0464
    """
    oi_cum_5 = df['open_interest'].diff().rolling(5).sum()
    oi_cum_20 = df['open_interest'].diff().rolling(20).sum()
    speed = oi_cum_5 / (oi_cum_20.abs() + 1e-8)
    return (speed - speed.rolling(30).mean()) / (speed.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_accumulation_speed'] = oi_accumulation_speed


def oi_vel_accel(df):
    """OI速度加速度：OI二阶导的短长期差z-score乘以价格方向
    avg |IC| = 0.0257, 2h IC=-0.0445
    """
    import numpy as np
    oi_vel = df['open_interest'].diff()
    oi_accel = oi_vel.diff()
    oi_accel_z = (oi_accel.rolling(10).mean() - oi_accel.rolling(40).mean()) / (oi_accel.rolling(40).std() + 1e-8)
    price_mom = np.sign(df['close'].pct_change(5))
    return oi_accel_z * price_mom

DISCOVERED_FACTORS['oi_vel_accel'] = oi_vel_accel


def vol_weighted_oi_dir(df):
    """成交量加权OI方向：放量时OI方向的累积z-score
    avg |IC| = 0.0623, 4h IC=0.0683, 8h IC=0.0671
    """
    import numpy as np
    oi_dir = np.sign(df['open_interest'].diff())
    vol_w = df['volume'] / df['volume'].rolling(20).mean()
    vw_oi = (oi_dir * vol_w).rolling(15).sum()
    return (vw_oi - vw_oi.rolling(40).mean()) / (vw_oi.rolling(40).std() + 1e-8)

DISCOVERED_FACTORS['vol_weighted_oi_dir'] = vol_weighted_oi_dir


def oi_norm_momentum(df):
    """OI归一化动量：OI变化率乘以换手率
    avg |IC| = 0.0626, 4h IC=0.0746, 8h IC=0.0856
    """
    oi_pct = df['open_interest'].pct_change(10)
    vol_norm = df['volume'].rolling(10).mean() / (df['open_interest'] + 1e-8)
    oi_nm = oi_pct * vol_norm
    return (oi_nm - oi_nm.rolling(30).mean()) / (oi_nm.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_norm_momentum'] = oi_norm_momentum


def vp_corr_regime(df):
    """量价相关性regime变化：短长期量价相关性差的z-score
    avg |IC| = 0.0234, 8h IC=0.0421
    """
    corr_10 = df['close'].pct_change().rolling(10).corr(df['volume'].pct_change())
    corr_40 = df['close'].pct_change().rolling(40).corr(df['volume'].pct_change())
    regime = corr_10 - corr_40
    return (regime - regime.rolling(30).mean()) / (regime.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['vp_corr_regime'] = vp_corr_regime


def oi_trend_reversal(df):
    """OI趋势反转信号：OI均线交叉时的价格动量累积
    avg |IC| = 0.0510, 4h IC=0.0587, 8h IC=0.0658
    """
    import numpy as np
    oi_ma5 = df['open_interest'].rolling(5).mean()
    oi_ma20 = df['open_interest'].rolling(20).mean()
    oi_cross = np.sign(oi_ma5 - oi_ma20)
    oi_cross_change = oi_cross.diff().abs()
    price_at_cross = df['close'].pct_change(5) * oi_cross_change
    return price_at_cross.rolling(10).sum()

DISCOVERED_FACTORS['oi_trend_reversal'] = oi_trend_reversal


def volume_decay_rate(df):
    """成交量衰减率：5期成交量对数衰减率z-score
    avg |IC| = 0.0206, 2h IC=-0.0287
    """
    import numpy as np
    vol_ratio_5 = df['volume'] / df['volume'].shift(5)
    decay = np.log(vol_ratio_5 + 1e-8) / 5
    return (decay - decay.rolling(30).mean()) / (decay.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['volume_decay_rate'] = volume_decay_rate


def high_vol_bar_return(df):
    """高成交量K线收益：放量K线收益的累积
    avg |IC| = 0.0347, 4h IC=0.0401
    """
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    vol_threshold = df['volume'].rolling(20).quantile(0.8)
    is_high_vol = (df['volume'] > vol_threshold).astype(float)
    return (ret * is_high_vol).rolling(15).sum()

DISCOVERED_FACTORS['high_vol_bar_return'] = high_vol_bar_return


def oi_momentum_quality(df):
    """OI动量质量：OI变化率的夏普比
    avg |IC| = 0.0301, 2h IC=0.0337, 4h IC=0.0377
    """
    oi_ret = df['open_interest'].pct_change(5)
    oi_ret_mean = oi_ret.rolling(20).mean()
    oi_ret_std = oi_ret.rolling(20).std()
    return oi_ret_mean / (oi_ret_std + 1e-8)

DISCOVERED_FACTORS['oi_momentum_quality'] = oi_momentum_quality


def price_vol_oi_interact(df):
    """价格波动率与OI交互：波动率z乘以OI变化z
    avg |IC| = 0.0257, all horizons ~0.025
    """
    import numpy as np
    ret = np.log(df['close'] / df['close'].shift(1))
    price_vol = ret.rolling(20).std()
    price_vol_z = (price_vol - price_vol.rolling(60).mean()) / (price_vol.rolling(60).std() + 1e-8)
    oi_chg = df['open_interest'].diff(5)
    oi_chg_z = (oi_chg - oi_chg.rolling(20).mean()) / (oi_chg.rolling(20).std() + 1e-8)
    return price_vol_z * oi_chg_z

DISCOVERED_FACTORS['price_vol_oi_interact'] = price_vol_oi_interact


def oi_vol_trend_ratio(df):
    """OI与成交量趋势比：OI线性趋势/成交量线性趋势z-score
    avg |IC| = 0.0490, 4h IC=0.0579, 8h IC=0.0490
    """
    import numpy as np
    oi_trend = df['open_interest'].rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
    vol_trend = df['volume'].rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
    ratio = oi_trend / (vol_trend.abs() + 1e-8)
    return (ratio - ratio.rolling(30).mean()) / (ratio.rolling(30).std() + 1e-8)

DISCOVERED_FACTORS['oi_vol_trend_ratio'] = oi_vol_trend_ratio


def oi_roc_zscore_combo(df):
    """OI变化率多窗口z-score组合：3/5/10/20期加权
    avg |IC| = 0.0411, 4h IC=0.0414, 8h IC=0.0737
    """
    signals = []
    for w in [3, 5, 10, 20]:
        roc = df['open_interest'].pct_change(w)
        mu = roc.rolling(40).mean()
        std = roc.rolling(40).std()
        signals.append((roc - mu) / (std + 1e-10))
    return signals[0]*0.4 + signals[1]*0.3 + signals[2]*0.2 + signals[3]*0.1

DISCOVERED_FACTORS['oi_roc_zscore_combo'] = oi_roc_zscore_combo


def oi_price_elasticity_change(df):
    """OI价格弹性变化：短长期弹性差z-score
    avg |IC| = 0.0312, 4h IC=0.0315, 8h IC=0.0433
    """
    oi_r = df['open_interest'].pct_change()
    pr = np.log(df['close'] / df['close'].shift(1))
    es = oi_r.rolling(10).mean() / (pr.rolling(10).mean() + 1e-10)
    el = oi_r.rolling(40).mean() / (pr.rolling(40).mean() + 1e-10)
    d = es - el
    return ((d - d.rolling(60).mean()) / (d.rolling(60).std() + 1e-10)).clip(-5, 5)

DISCOVERED_FACTORS['oi_price_elasticity_change'] = oi_price_elasticity_change


def price_oi_beta_change(df):
    """价格OI Beta变化：短长期回归系数差z-score
    avg |IC| = 0.0327, 4h IC=-0.0434, 8h IC=-0.0207
    """
    pr = np.log(df['close'] / df['close'].shift(1))
    oi_r = df['open_interest'].pct_change()
    bs = pr.rolling(10).cov(oi_r) / (oi_r.rolling(10).var() + 1e-10)
    bl = pr.rolling(40).cov(oi_r) / (oi_r.rolling(40).var() + 1e-10)
    d = bs - bl
    return (d - d.rolling(40).mean()) / (d.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['price_oi_beta_change'] = price_oi_beta_change


def oi_price_corr_regime(df):
    """OI价格相关性regime：短长期相关性差z-score
    avg |IC| = 0.0265, 4h IC=-0.0401, 8h IC=-0.0102
    """
    oi_r = df['open_interest'].pct_change()
    pr = np.log(df['close'] / df['close'].shift(1))
    cs = oi_r.rolling(10).corr(pr)
    cl = oi_r.rolling(40).corr(pr)
    d = cs - cl
    return (d - d.rolling(60).mean()) / (d.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_price_corr_regime'] = oi_price_corr_regime


def oi_momentum_consistency_score(df):
    """OI动量一致性得分：多窗口方向一致性乘以幅度z-score
    avg |IC| = 0.0485, 4h IC=0.0475, 8h IC=0.0771
    """
    oi_chg = df['open_interest'].diff()
    dirs = [np.sign(df['open_interest'].diff(w)) for w in [3, 5, 10, 20]]
    consistency = sum(dirs) / len(dirs)
    oi_z = (oi_chg - oi_chg.rolling(20).mean()) / (oi_chg.rolling(20).std() + 1e-10)
    signal = consistency * abs(oi_z)
    return (signal - signal.rolling(40).mean()) / (signal.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_momentum_consistency_score'] = oi_momentum_consistency_score


def vol_price_oi_triple(df):
    """量价仓三重确认：放量+价格方向+OI方向一致的累积z-score
    avg |IC| = 0.0487, 4h IC=0.0561, 8h IC=0.0635
    """
    vol_up = df['volume'] > df['volume'].rolling(20).mean()
    price_up = df['close'] > df['close'].shift(1)
    oi_up = df['open_interest'] > df['open_interest'].shift(1)
    all_up = (vol_up & price_up & oi_up).astype(float)
    all_dn = (vol_up & ~price_up & ~oi_up).astype(float)
    signal = (all_up - all_dn).rolling(10).sum()
    return (signal - signal.rolling(40).mean()) / (signal.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['vol_price_oi_triple'] = vol_price_oi_triple


def oi_cumulative_flow(df):
    """OI累积流向：多头建仓减空头建仓的净流向z-score
    avg |IC| = 0.0397, 4h IC=0.0395, 8h IC=0.0595
    """
    oi_chg = df['open_interest'].diff()
    price_ret = np.log(df['close'] / df['close'].shift(1))
    bull_flow = oi_chg.where(price_ret > 0, 0).rolling(20).sum()
    bear_flow = oi_chg.where(price_ret < 0, 0).rolling(20).sum()
    net_flow = bull_flow - bear_flow
    return (net_flow - net_flow.rolling(40).mean()) / (net_flow.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_cumulative_flow'] = oi_cumulative_flow


def oi_price_rank_corr(df):
    """OI与价格排名差：40期内OI排名与价格排名差z-score
    avg |IC| = 0.0420, 4h IC=0.0481, 8h IC=0.0463
    """
    oi_rank = df['open_interest'].rolling(40).rank(pct=True)
    price_rank = df['close'].rolling(40).rank(pct=True)
    diff = oi_rank - price_rank
    return (diff - diff.rolling(40).mean()) / (diff.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_price_rank_corr'] = oi_price_rank_corr


def oi_price_mutual_info_proxy(df):
    """OI价格互信息代理：相关性强度乘以OI方向z-score
    avg |IC| = 0.0275, 4h IC=0.0327, 8h IC=0.0383
    """
    oi_ret = df['open_interest'].pct_change()
    price_ret = np.log(df['close'] / df['close'].shift(1))
    corr = oi_ret.rolling(20).corr(price_ret)
    abs_corr = abs(corr)
    oi_dir = np.sign(df['open_interest'].diff(5))
    signal = abs_corr * oi_dir
    return (signal - signal.rolling(40).mean()) / (signal.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_price_mutual_info_proxy'] = oi_price_mutual_info_proxy


def high_low_oi_interaction(df):
    """高低点OI交互：价格极值时OI反应的累积z-score
    avg |IC| = 0.0286, 4h IC=0.0370, 8h IC=0.0403
    """
    high_20 = df['high'].rolling(20).max()
    low_20 = df['low'].rolling(20).min()
    at_high = (df['high'] >= high_20 * 0.999).astype(float)
    at_low = (df['low'] <= low_20 * 1.001).astype(float)
    oi_chg_z = (df['open_interest'].diff() - df['open_interest'].diff().rolling(20).mean()) / (df['open_interest'].diff().rolling(20).std() + 1e-10)
    signal = (at_high - at_low) * oi_chg_z
    cum = signal.rolling(10).sum()
    return (cum - cum.rolling(40).mean()) / (cum.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['high_low_oi_interaction'] = high_low_oi_interaction


def kaufman_oi_signal(df, er_window=10, fast=2, slow=30):
    """Kaufman自适应OI信号：OI偏离KAMA的z-score，自适应速度跟踪OI趋势
    avg |IC| = 0.0340, 4h IC=0.0318, 8h IC=0.0685
    """
    oi = df['open_interest'].values.astype(float)
    n = len(oi)
    er = np.full(n, np.nan)
    for i in range(er_window, n):
        direction = abs(oi[i] - oi[i - er_window])
        volatility = np.sum(np.abs(np.diff(oi[i-er_window:i+1])))
        er[i] = direction / (volatility + 1e-10)
    er = np.clip(er, 0, 1)
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    kama = np.full(n, np.nan)
    kama[er_window] = oi[er_window]
    for i in range(er_window + 1, n):
        if np.isnan(kama[i-1]) or np.isnan(sc[i]):
            kama[i] = oi[i]
        else:
            kama[i] = kama[i-1] + sc[i] * (oi[i] - kama[i-1])
    kama_s = pd.Series(kama, index=df.index)
    oi_s = pd.Series(oi, index=df.index)
    dev = (oi_s - kama_s) / (oi_s.rolling(20).std() + 1e-10)
    dev_z = (dev - dev.rolling(60).mean()) / (dev.rolling(60).std() + 1e-10)
    return dev_z

DISCOVERED_FACTORS['kaufman_oi_signal'] = kaufman_oi_signal


def dema_oi_momentum(df, fast=5, slow=20):
    """DEMA OI动量：OI双指数均线交叉z-score乘以价格方向
    avg |IC| = 0.0291, 4h IC=0.0323, 8h IC=0.0500
    """
    oi = df['open_interest']
    def dema(s, p):
        ema1 = s.ewm(span=p, adjust=False).mean()
        ema2 = ema1.ewm(span=p, adjust=False).mean()
        return 2 * ema1 - ema2
    dema_fast = dema(oi, fast)
    dema_slow = dema(oi, slow)
    cross = (dema_fast - dema_slow) / (oi.rolling(20).std() + 1e-10)
    cross_z = (cross - cross.rolling(40).mean()) / (cross.rolling(40).std() + 1e-10)
    price_dir = np.sign(df['close'].pct_change(10))
    return cross_z * price_dir

DISCOVERED_FACTORS['dema_oi_momentum'] = dema_oi_momentum


def vidya_oi_trend(df, cmo_period=10, ema_period=20):
    """VIDYA OI趋势：OI偏离VIDYA自适应均线的z-score
    avg |IC| = 0.0292, 4h IC=0.0244, 8h IC=0.0594
    """
    oi = df['open_interest']
    oi_diff = oi.diff()
    up = oi_diff.clip(lower=0).rolling(cmo_period).sum()
    down = (-oi_diff.clip(upper=0)).rolling(cmo_period).sum()
    cmo = abs((up - down) / (up + down + 1e-10))
    sc = 2 / (ema_period + 1)
    vidya = pd.Series(np.nan, index=df.index)
    start = cmo_period + 1
    vidya.iloc[start] = oi.iloc[start]
    for i in range(start + 1, len(oi)):
        if np.isnan(vidya.iloc[i-1]) or np.isnan(cmo.iloc[i]):
            vidya.iloc[i] = oi.iloc[i]
        else:
            vidya.iloc[i] = vidya.iloc[i-1] + sc * cmo.iloc[i] * (oi.iloc[i] - vidya.iloc[i-1])
    dev = (oi - vidya) / (oi.rolling(20).std() + 1e-10)
    dev_z = (dev - dev.rolling(40).mean()) / (dev.rolling(40).std() + 1e-10)
    return dev_z

DISCOVERED_FACTORS['vidya_oi_trend'] = vidya_oi_trend


def tema_price_oi_spread(df, period=15):
    """TEMA价格OI价差：价格与OI的TEMA累积收益差z-score
    avg |IC| = 0.0424, 4h IC=-0.0513, 8h IC=-0.0368
    """
    def tema(s, p):
        e1 = s.ewm(span=p, adjust=False).mean()
        e2 = e1.ewm(span=p, adjust=False).mean()
        e3 = e2.ewm(span=p, adjust=False).mean()
        return 3*e1 - 3*e2 + e3
    price_tema = tema(df['close'].pct_change().cumsum(), period)
    oi_tema = tema(df['open_interest'].pct_change().cumsum(), period)
    spread = price_tema - oi_tema
    spread_z = (spread - spread.rolling(40).mean()) / (spread.rolling(40).std() + 1e-10)
    return spread_z

DISCOVERED_FACTORS['tema_price_oi_spread'] = tema_price_oi_spread


def bayesian_surprise_oi(df, prior_window=60, obs_window=10):
    """Bayesian惊喜OI：OI变化率的KL散度方向z-score
    avg |IC| = 0.0552, 4h IC=0.0638, 8h IC=0.0820
    """
    oi_ret = df['open_interest'].pct_change()
    prior_mean = oi_ret.rolling(prior_window).mean()
    prior_std = oi_ret.rolling(prior_window).std()
    obs_mean = oi_ret.rolling(obs_window).mean()
    kl = (obs_mean - prior_mean)**2 / (2 * prior_std**2 + 1e-10)
    kl_dir = kl * np.sign(obs_mean - prior_mean)
    kl_z = (kl_dir - kl_dir.rolling(40).mean()) / (kl_dir.rolling(40).std() + 1e-10)
    return kl_z

DISCOVERED_FACTORS['bayesian_surprise_oi'] = bayesian_surprise_oi


def spectral_coherence_poi(df, window=64):
    """频谱相干性：价格与OI低频相干度z-score乘以OI方向
    avg |IC| = 0.0445, 4h IC=0.0539, 8h IC=0.0479
    """
    ret = df['close'].pct_change().values
    oi_ret = df['open_interest'].pct_change().values
    n = len(df)
    vals = np.full(n, np.nan)
    for i in range(window, n):
        r = ret[i-window+1:i+1]
        o = oi_ret[i-window+1:i+1]
        if np.any(np.isnan(r)) or np.any(np.isnan(o)):
            continue
        fft_r = np.fft.rfft(r - np.mean(r))
        fft_o = np.fft.rfft(o - np.mean(o))
        cross = fft_r * np.conj(fft_o)
        psd_r = np.abs(fft_r)**2
        psd_o = np.abs(fft_o)**2
        denom = np.sqrt(psd_r * psd_o + 1e-20)
        coherence = np.abs(cross) / denom
        weights = psd_r[:8] + psd_o[:8]
        if np.sum(weights) < 1e-20:
            continue
            vals[i] = np.average(coherence[:8], weights=weights)
            s = pd.Series(vals, index=df.index)
            s_z = (s - s.rolling(60).mean()) / (s.rolling(60).std() + 1e-10)
            oi_dir = np.sign(df['open_interest'].diff(10))
            return s_z * oi_dir

DISCOVERED_FACTORS['spectral_coherence_poi'] = spectral_coherence_poi


def ewma_cross_oi_vol(df):
    """EWMA交叉OI量比：OI/Volume比的快慢EWMA交叉z乘以价格方向
    avg |IC| = 0.0321, 4h IC=-0.0377, 8h IC=-0.0331
    """
    ratio = df['open_interest'] / (df['volume'] + 1)
    fast = ratio.ewm(span=5, adjust=False).mean()
    slow = ratio.ewm(span=30, adjust=False).mean()
    cross = (fast - slow) / (ratio.rolling(20).std() + 1e-10)
    cross_z = (cross - cross.rolling(40).mean()) / (cross.rolling(40).std() + 1e-10)
    price_dir = np.sign(df['close'].pct_change(5))
    return cross_z * price_dir

DISCOVERED_FACTORS['ewma_cross_oi_vol'] = ewma_cross_oi_vol


def oi_wavelet_energy(df, window=32):
    """OI小波能量：Haar小波低频能量占比z-score乘以OI方向
    avg |IC| = 0.0266, 4h IC=-0.0254, 8h IC=-0.0344
    """
    oi_ret = df['open_interest'].pct_change().values
    n = len(df)
    vals = np.full(n, np.nan)
    for i in range(window, n):
        x = oi_ret[i-window+1:i+1]
        if np.any(np.isnan(x)) or len(x) < window:
            continue
        detail_energy = 0
        approx = x.copy()
        total_energy = np.sum(x**2)
        if total_energy < 1e-20:
            continue
        for level in range(3):
            if len(approx) < 2:
                break
            half = len(approx) // 2
            detail = np.array([(approx[2*j] - approx[2*j+1])/2 for j in range(half)])
            approx = np.array([(approx[2*j] + approx[2*j+1])/2 for j in range(half)])
            if level == 0:
                detail_energy = np.sum(detail**2)
        vals[i] = 1 - detail_energy / total_energy
        s = pd.Series(vals, index=df.index)
        s_z = (s - s.rolling(60).mean()) / (s.rolling(60).std() + 1e-10)
        oi_dir = np.sign(df['open_interest'].diff(10))
        return s_z * oi_dir

DISCOVERED_FACTORS['oi_wavelet_energy'] = oi_wavelet_energy


def granger_oi_price_v2(df, window=40, lag=5):
    """Granger因果OI->价格v2：OI预测价格的F统计量z乘以OI方向
    avg |IC| = 0.0232, 4h IC=0.0299, 8h IC=0.0300
    """
    ret = df['close'].pct_change().values
    oi_ret = df['open_interest'].pct_change().values
    n = len(df)
    vals = np.full(n, np.nan)
    for i in range(window + lag, n):
        y = ret[i-window+1:i+1]
        if np.any(np.isnan(y)):
            continue
        X_r = np.column_stack([ret[i-window+1-j:i+1-j] for j in range(1, lag+1)])
        X_u_oi = np.column_stack([oi_ret[i-window+1-j:i+1-j] for j in range(1, lag+1)])
        X_u = np.column_stack([X_r, X_u_oi])
        if np.any(np.isnan(X_r)) or np.any(np.isnan(X_u)):
            continue
        try:
            beta_r = np.linalg.lstsq(X_r, y, rcond=None)[0]
            rss_r = np.sum((y - X_r @ beta_r)**2)
            beta_u = np.linalg.lstsq(X_u, y, rcond=None)[0]
            rss_u = np.sum((y - X_u @ beta_u)**2)
            if rss_u > 1e-20:
                vals[i] = (rss_r - rss_u) / rss_u
        except:
            continue
    s = pd.Series(vals, index=df.index)
    s_z = (s - s.rolling(60).mean()) / (s.rolling(60).std() + 1e-10)
    oi_dir = np.sign(df['open_interest'].diff(5))
    return s_z * oi_dir

DISCOVERED_FACTORS['granger_oi_price_v2'] = granger_oi_price_v2


def oi_exp_decay_ret(df, halflife=10):
    """OI指数衰减加权收益：OI方向加权的指数衰减收益累积z
    avg |IC| = 0.0202, 4h IC=0.0208, 8h IC=0.0367
    """
    oi_chg = df['open_interest'].diff()
    ret = df['close'].pct_change()
    weights = np.exp(-np.log(2) * np.arange(20) / halflife)
    weighted_ret = pd.Series(0.0, index=df.index)
    for i, w in enumerate(weights):
        weighted_ret += w * (ret.shift(i) * np.sign(oi_chg.shift(i)))
        weighted_ret /= np.sum(weights)
        z = (weighted_ret - weighted_ret.rolling(40).mean()) / (weighted_ret.rolling(40).std() + 1e-10)
        return z

DISCOVERED_FACTORS['oi_exp_decay_ret'] = oi_exp_decay_ret


def oi_mom_dispersion_idx(df):
    """OI动量离散指数：多周期OI动量离散度乘以均值方向z
    avg |IC| = 0.0385, 4h IC=0.0417, 8h IC=0.0597
    """
    oi = df['open_interest']
    moms = []
    for w in [3, 5, 10, 20, 40]:
        m = oi.pct_change(w)
        m_z = (m - m.rolling(40).mean()) / (m.rolling(40).std() + 1e-10)
        moms.append(m_z)
    mom_df = pd.concat(moms, axis=1)
    dispersion = mom_df.std(axis=1)
    mean_dir = mom_df.mean(axis=1)
    signal = dispersion * np.sign(mean_dir)
    return (signal - signal.rolling(40).mean()) / (signal.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_mom_dispersion_idx'] = oi_mom_dispersion_idx


def vol_adj_oi_mom(df):
    """波动率调整OI动量：OI动量除以价格波动率
    avg |IC| = 0.0642, 4h IC=0.0837, 8h IC=0.0739
    """
    oi_mom10 = df['open_interest'].pct_change(10)
    ret = df['close'].pct_change()
    price_vol = ret.rolling(20).std()
    vol_adj = oi_mom10 / (price_vol + 1e-10)
    return (vol_adj - vol_adj.rolling(60).mean()) / (vol_adj.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['vol_adj_oi_mom'] = vol_adj_oi_mom


def range_expand_oi(df):
    """振幅扩张OI：振幅扩张时OI方向的15期累积z-score
    avg |IC| = 0.058, 2h IC=0.0574, 4h IC=0.0588, 8h IC=0.0577
    """
    oi_chg = df['open_interest'].pct_change()
    hl_range = (df['high'] - df['low']) / df['close']
    range_expanding = (hl_range > hl_range.rolling(20).mean()).astype(float)
    oi_dir_signal = np.sign(oi_chg) * range_expanding
    cum = oi_dir_signal.rolling(15).sum()
    return (cum - cum.rolling(60).mean()) / (cum.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['range_expand_oi'] = range_expand_oi


def cum_signed_oi_vel(df):
    """累积有符号OI速度：价格方向加权OI速度的20期累积z-score
    avg |IC| = 0.0496, 2h IC=0.0364, 4h IC=0.0575, 8h IC=0.0549
    """
    ret = df['close'].pct_change()
    oi_velocity = df['open_interest'].diff(3) / (df['open_interest'].rolling(20).std() + 1e-10)
    signed_oi_vel = oi_velocity * np.sign(ret.rolling(3).sum())
    cum_signed = signed_oi_vel.rolling(20).sum()
    return (cum_signed - cum_signed.rolling(60).mean()) / (cum_signed.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['cum_signed_oi_vel'] = cum_signed_oi_vel


def price_mom_oi_quality(df):
    """价格动量OI质量：OI确认的价格动量质量得分z-score
    avg |IC| = 0.0494, 4h IC=0.0537, 8h IC=0.0662
    """
    oi_chg = df['open_interest'].pct_change()
    price_mom = df['close'].pct_change(10)
    oi_confirm = (oi_chg.rolling(10).mean() > 0).astype(float)
    mom_quality = price_mom * oi_confirm.rolling(10).mean()
    return (mom_quality - mom_quality.rolling(60).mean()) / (mom_quality.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['price_mom_oi_quality'] = price_mom_oi_quality


def oi_price_mom_ratio(df):
    """OI价格动量比：OI动量/价格动量绝对值乘以价格方向z-score
    avg |IC| = 0.0387, 4h IC=0.0403, 8h IC=0.0467
    """
    oi_mom20 = df['open_interest'].pct_change(20)
    price_mom20 = df['close'].pct_change(20)
    mom_ratio = oi_mom20 / (price_mom20.abs() + 1e-10) * np.sign(price_mom20)
    return (mom_ratio - mom_ratio.rolling(60).mean()) / (mom_ratio.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_price_mom_ratio'] = oi_price_mom_ratio


def vol_surprise_dir(df):
    """成交量惊喜方向：异常放量时价格方向的15期累积z-score
    avg |IC| = 0.0325, 2h IC=0.0255, 4h IC=0.0323, 8h IC=0.0397
    """
    ret = df['close'].pct_change()
    vol_surprise = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-10)
    surprise_dir = vol_surprise * np.sign(ret)
    cum = surprise_dir.rolling(15).sum()
    return (cum - cum.rolling(60).mean()) / (cum.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['vol_surprise_dir'] = vol_surprise_dir


def oi_price_beta(df):
    """OI价格Beta：OI变化对价格变化的滚动回归斜率z-score
    avg |IC| = 0.0349, 8h IC=0.0632
    """
    oi_ret = df['open_interest'].pct_change()
    price_ret = df['close'].pct_change()
    cov_op = (oi_ret * price_ret).rolling(30).mean() - oi_ret.rolling(30).mean() * price_ret.rolling(30).mean()
    var_p = price_ret.rolling(30).var()
    oi_beta = cov_op / (var_p + 1e-10)
    return (oi_beta - oi_beta.rolling(60).mean()) / (oi_beta.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_price_beta'] = oi_price_beta


def oi_momentum_decay(df):
    """OI动量衰减：OI动量从峰值衰减程度乘以价格方向z-score
    avg |IC| = 0.0333, 4h IC=0.0405, 8h IC=0.0325
    """
    oi_mom5 = df['open_interest'].pct_change(5)
    oi_mom_peak = oi_mom5.abs().rolling(20).max()
    oi_decay = 1 - oi_mom5.abs() / (oi_mom_peak + 1e-10)
    price_dir = np.sign(df['close'].pct_change(10))
    factor = oi_decay * np.sign(oi_mom5) * price_dir
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_momentum_decay'] = oi_momentum_decay


def vp_cov_change(df):
    """量价协方差变化：短期与长期量价协方差差z-score
    avg |IC| = 0.0267, 4h IC=0.028, 8h IC=0.0466
    """
    ret = df['close'].pct_change()
    vol = df['volume']
    cov_short = (vol * ret).rolling(10).mean() - vol.rolling(10).mean() * ret.rolling(10).mean()
    cov_long = (vol * ret).rolling(40).mean() - vol.rolling(40).mean() * ret.rolling(40).mean()
    diff = cov_short - cov_long
    return (diff - diff.rolling(60).mean()) / (diff.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['vp_cov_change'] = vp_cov_change


def dir_oi_flow_imbal(df):
    """方向性OI资金流不平衡：上涨时OI增减vs下跌时OI增减差z-score
    avg |IC| = 0.0276, 2h IC=0.0193, 4h IC=0.0282, 8h IC=0.0352
    """
    ret = df['close'].pct_change()
    oi_chg = df['open_interest'].pct_change()
    up_bar = (ret > 0).astype(float)
    down_bar = (ret < 0).astype(float)
    oi_up_flow = (oi_chg * up_bar).rolling(20).sum()
    oi_down_flow = (oi_chg * down_bar).rolling(20).sum()
    diff = oi_up_flow - oi_down_flow
    return (diff - diff.rolling(60).mean()) / (diff.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['dir_oi_flow_imbal'] = dir_oi_flow_imbal


def oi_vol_squeeze(df):
    """OI 波动率挤压：低 OI 波动率时持仓量方向预示突破
    avg |IC| = 0.0257, 2h IC=0.0214, 4h IC=0.0302, 8h IC=0.0254
    """
    oi = df['open_interest'].values
    close = df['close'].values
    oi_pct = np.diff(oi, prepend=oi[0]) / (oi + 1e-10)
    oi_vol_short = pd.Series(oi_pct).rolling(10).std().values
    oi_vol_long = pd.Series(oi_pct).rolling(60).std().values
    vol_ratio = oi_vol_short / (oi_vol_long + 1e-10)
    squeeze = 1.0 / (vol_ratio + 0.1)
    oi_dir = np.sign(oi_pct)
    price_mom = close / np.maximum(pd.Series(close).rolling(10).mean().values, 1e-10) - 1
    signal = squeeze * oi_dir * np.sign(price_mom)
    signal = pd.Series(signal).fillna(0).values
    z_signal = (signal - np.nanmean(signal)) / (np.nanstd(signal) + 1e-10)
    return pd.Series(z_signal, index=df.index)

DISCOVERED_FACTORS['oi_vol_squeeze'] = oi_vol_squeeze


def vol_confirmed_oi_trend(df):
    """成交量确认的 OI 趋势：OI 趋势强度*成交量确认*价格方向
    avg |IC| = 0.0338, 2h IC=-0.0361, 4h IC=-0.0419, 8h IC=-0.0235
    """
    oi = df['open_interest']
    vol = df['volume']
    close = df['close']
    oi_ma5 = oi.rolling(5).mean()
    oi_ma20 = oi.rolling(20).mean()
    oi_trend = ((oi_ma5 - oi_ma20) / (oi_ma20 + 1e-10)).rolling(10).mean()
    vol_ratio = vol / vol.rolling(20).mean()
    vol_confirm = (vol_ratio > 1.0).astype(float) * 2 - 1
    price_dir = np.sign(close.pct_change(10))
    signal = oi_trend * vol_confirm * price_dir
    return (signal - signal.rolling(60).mean()) / (signal.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['vol_confirmed_oi_trend'] = vol_confirmed_oi_trend


def oi_ma_cross_signal(df):
    """OI 均线交叉信号：快慢 OI 均线差 z 乘以价格动量方向
    avg |IC| = 0.0495, 2h IC=0.0434, 4h IC=0.0602, 8h IC=0.0449
    """
    oi = df['open_interest']
    close = df['close']
    oi_ma5 = oi.rolling(5).mean()
    oi_ma20 = oi.rolling(20).mean()
    oi_cross = oi_ma5 - oi_ma20
    oi_cross_z = (oi_cross - oi_cross.rolling(60).mean()) / (oi_cross.rolling(60).std() + 1e-10)
    mom = close.pct_change(10)
    signal = oi_cross_z * np.sign(mom)
    return (signal - signal.rolling(20).mean()) / (signal.rolling(20).std() + 1e-10)

DISCOVERED_FACTORS['oi_ma_cross_signal'] = oi_ma_cross_signal


def oi_confirmed_breakout(df):
    """OI 确认突破：价格突破区间位置乘以 OI 变化方向
    avg |IC| = 0.038, 2h IC=0.0149, 4h IC=0.0458, 8h IC=0.0533
    """
    close = df['close']
    high_20 = close.rolling(20).max()
    low_20 = close.rolling(20).min()
    breakout = (close - low_20) / (high_20 - low_20 + 1e-10) - 0.5
    oi_change = df['open_interest'].pct_change(5)
    oi_confirm = np.sign(oi_change)
    factor = breakout * oi_confirm
    return (factor - factor.rolling(40).mean()) / (factor.rolling(40).std() + 1e-10)

DISCOVERED_FACTORS['oi_confirmed_breakout'] = oi_confirmed_breakout


def oi_flow_asymmetry(df):
    """OI 流向不对称：上涨 OI 流入减下跌 OI 流出
    avg |IC| = 0.057, 2h IC=0.0305, 4h IC=0.075, 8h IC=0.0655
    """
    oi_change = df['open_interest'].diff()
    up_oi = oi_change.where(df['close'] > df['open'], 0).rolling(10).sum()
    down_oi = (-oi_change).where(df['close'] < df['open'], 0).rolling(10).sum()
    factor = up_oi - down_oi
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_flow_asymmetry'] = oi_flow_asymmetry


def price_oi_corr_change(df):
    """价格 OI 相关性变化：短长期相关差 z-score
    avg |IC| = 0.0265, 2h IC=-0.0293, 4h IC=-0.04, 8h IC=-0.0103
    """
    ret = np.log(df['close'] / df['close'].shift(1))
    oi_ret = np.log(df['open_interest'] / df['open_interest'].shift(1))
    corr_short = ret.rolling(10).corr(oi_ret)
    corr_long = ret.rolling(40).corr(oi_ret)
    factor = corr_short - corr_long
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['price_oi_corr_change'] = price_oi_corr_change


def vol_cluster_intensity(df):
    """成交量聚集强度：放量聚集频率乘以价格方向
    avg |IC| = 0.0208, 2h IC=-0.0103, 4h IC=0.012, 8h IC=0.04
    """
    vol_ma = df['volume'].rolling(20).mean()
    vol_spike = (df['volume'] > vol_ma * 1.5).astype(float)
    cluster = vol_spike.rolling(5).sum() / 5.0
    price_dir = np.sign(df['close'].pct_change(5))
    factor = cluster * price_dir
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['vol_cluster_intensity'] = vol_cluster_intensity


def oi_rsi(df):
    """OI RSI 指标：OI 变化的 RSI 居中标准化
    avg |IC| = 0.0784, 2h IC=0.0635, 4h IC=0.0895, 8h IC=0.0821
    """
    oi_change = df['open_interest'].diff()
    gain = oi_change.where(oi_change > 0, 0).rolling(14).mean()
    loss = (-oi_change).where(oi_change < 0, 0).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    factor = (rsi - 50) / 50
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_rsi'] = oi_rsi


def oi_roc_momentum(df):
    """OI 变化率动量：10 期 OI 变化率的 5 期均值
    avg |IC| = 0.0607, 2h IC=0.0504, 4h IC=0.0815, 8h IC=0.0501
    """
    oi_roc = df['open_interest'].pct_change(10)
    factor = oi_roc.rolling(5).mean()
    return (factor - factor.rolling(60).mean()) / (factor.rolling(60).std() + 1e-10)

DISCOVERED_FACTORS['oi_roc_momentum'] = oi_roc_momentum


def oi_change_persistence(df):
    oi_change = df["open_interest"].diff()
    oi_direction = np.sign(oi_change)
    persistence = oi_direction.rolling(10).apply(lambda x: (x == x.iloc[-1]).sum() * x.iloc[-1], raw=False)
    result = pd.Series(index=df.index, data=persistence)
    result = (result - result.rolling(60).mean()) / (result.rolling(60).std() + 1e-8)
    return result

def price_oi_divergence_intensity(df):
    price_ret = df["close"].pct_change(10)
    price_z = (price_ret - price_ret.rolling(60).mean()) / (price_ret.rolling(60).std() + 1e-8)
    oi_ret = df["open_interest"].pct_change(10)
    oi_z = (oi_ret - oi_ret.rolling(60).mean()) / (oi_ret.rolling(60).std() + 1e-8)
    divergence = np.abs(price_z - oi_z)
    divergence = (divergence - divergence.rolling(60).mean()) / (divergence.rolling(60).std() + 1e-8)
    return divergence * -1

def oi_rsi_strength(df):
    oi_change = df["open_interest"].diff()
    gain = oi_change.clip(lower=0)
    loss = (-oi_change).clip(lower=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = 100 - (100 / (1 + rs))
    rsi_centered = rsi - 50
    signal = (rsi_centered - rsi_centered.rolling(60).mean()) / (rsi_centered.rolling(60).std() + 1e-8)
    return signal

def oi_vol_adj_momentum(df):
    oi_mom = df["open_interest"].pct_change(10)
    oi_vol = oi_mom.rolling(20).std()
    adj_mom = oi_mom / (oi_vol + 1e-8)
    signal = (adj_mom - adj_mom.rolling(60).mean()) / (adj_mom.rolling(60).std() + 1e-8)
    return signal

def zscore_vwap_deviation(df):
    """计算收盘价相对于成交量加权均价(VWAP)的滚动Z-score偏离度，捕捉价格偏离量价均衡位置后的均值回归机会
    avg |IC| = 0.0268
    """
    import numpy as np
    import pandas as pd
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    vwap = (typical_price * df['volume']).rolling(20, min_periods=10).sum() / df['volume'].rolling(20, min_periods=10).sum()
    deviation = df['close'] - vwap
    dev_mean = deviation.rolling(40, min_periods=20).mean()
    dev_std = deviation.rolling(40, min_periods=20).std(ddof=1)
    zscore = (deviation - dev_mean) / dev_std.replace(0, np.nan)
    factor = -zscore
    return factor

DISCOVERED_FACTORS['zscore_vwap_deviation'] = zscore_vwap_deviation


def oi_price_divergence_tension(df):
    """衡量持仓量变化方向与价格变化方向的持续背离张力——当OI累计变动与价格累计变动长期反向时，积累的"弹簧势能"越大，预示均值回归或趋势加速的概率越高。
    avg |IC| = 0.0463
    """
    import numpy as np
    import pandas as pd
    close = df['close']
    oi = df['open_interest']
    window = 20
    short_w = 5
    oi_chg = oi.diff().fillna(0)
    price_chg = close.diff().fillna(0)
    oi_cum = oi_chg.rolling(window).sum()
    price_cum = price_chg.rolling(window).sum()
    oi_std = oi_chg.rolling(window).std().replace(0, np.nan)
    price_std = price_chg.rolling(window).std().replace(0, np.nan)
    oi_z = oi_cum / oi_std
    price_z = price_cum / price_std
    divergence = oi_z * price_z
    tension = -divergence
    recent_oi_dir = np.sign(oi_chg.rolling(short_w).sum())
    recent_price_dir = np.sign(price_chg.rolling(short_w).sum())
    confirm = (recent_oi_dir != recent_price_dir).astype(float)
    factor = tension * (0.6 + 0.4 * confirm)
    factor.name = 'oi_price_divergence_tension'
    return factor

DISCOVERED_FACTORS['oi_price_divergence_tension'] = oi_price_divergence_tension


def multi_horizon_trend_projection(df):
    """将长周期（240根K线，约5个交易日）的线性回归斜率投影到短周期（30根K线），用短周期价格对长周期趋势线的偏离度衡量均值回归压力，偏离越大代表短周期过度偏离长期趋势，存在回归动力。
    avg |IC| = 0.0413
    """
    import numpy as np
    import pandas as pd
    close = df['close'].values
    n_long = 240
    n_short = 30
    factor = np.full(len(close), np.nan)
    for i in range(n_long - 1, len(close)):
            y_long = close[i - n_long + 1: i + 1]
            x_long = np.arange(n_long, dtype=np.float64)
            x_mean = x_long.mean()
            y_mean = y_long.mean()
            slope = np.sum((x_long - x_mean) * (y_long - y_mean)) / (np.sum((x_long - x_mean) ** 2) + 1e-12)
            intercept = y_mean - slope * x_mean
            projected_value = intercept + slope * (n_long - 1)
            actual = close[i]
            std_start = max(0, i - n_short + 1)
            rolling_std = np.std(close[std_start: i + 1], ddof=1) if (i - std_start + 1) > 1 else 1e-12
            deviation = (actual - projected_value) / (rolling_std + 1e-12)
            factor[i] = -deviation
    return pd.Series(factor, index=df.index, name='multi_horizon_trend_projection')

DISCOVERED_FACTORS['multi_horizon_trend_projection'] = multi_horizon_trend_projection


def volume_price_divergence_momentum(df):
    """衡量成交量变化率与价格变化率的背离程度的动量，当量增价滞或量缩价涨时产生极端信号，捕捉量价背离后的反转机会
    avg |IC| = 0.0227
    """
    import numpy as np
    import pandas as pd
    close = df['close']
    volume = df['volume']
    ret = close.pct_change()
    vol_ret = volume.pct_change()
    vol_ret_z = (vol_ret - vol_ret.rolling(20).mean()) / (vol_ret.rolling(20).std() + 1e-9)
    price_ret_z = (ret - ret.rolling(20).mean()) / (ret.rolling(20).std() + 1e-9)
    divergence = vol_ret_z - price_ret_z.abs() * np.sign(ret)
    div_ma_fast = divergence.rolling(5).mean()
    div_ma_slow = divergence.rolling(15).mean()
    factor = div_ma_fast - div_ma_slow
    return factor

DISCOVERED_FACTORS['volume_price_divergence_momentum'] = volume_price_divergence_momentum


def vwap_mean_reversion_zscore(df):
    """计算收盘价相对于成交量加权均价(VWAP)的滚动Z-Score偏离度，捕捉价格偏离量价均衡位置后的均值回归倾向，偏离越大回归动力越强
    avg |IC| = 0.0268
    """
    import numpy as np
    import pandas as pd
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    cum_tp_vol = (typical_price * df['volume']).rolling(window=20, min_periods=10).sum()
    cum_vol = df['volume'].rolling(window=20, min_periods=10).sum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    deviation = df['close'] - vwap
    dev_mean = deviation.rolling(window=40, min_periods=20).mean()
    dev_std = deviation.rolling(window=40, min_periods=20).std()
    zscore = (deviation - dev_mean) / dev_std.replace(0, np.nan)
    factor_series = -zscore
    factor_series.name = 'vwap_mean_reversion_zscore'
    return factor_series

DISCOVERED_FACTORS['vwap_mean_reversion_zscore'] = vwap_mean_reversion_zscore


def smart_money_absorption_ratio(df):
    """通过比较持仓量增加但价格波动收窄的区间，识别主力资金在窄幅震荡中悄然吸筹或派发的行为，吸筹比率越高说明主力控盘意图越强
    avg |IC| = 0.0247
    """
    import numpy as np
    import pandas as pd
    oi = df['open_interest']
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']
    oi_chg = oi.diff()
    price_range = high - low
    avg_range = price_range.rolling(20, min_periods=5).mean()
    range_ratio = price_range / avg_range.replace(0, np.nan)
    narrow_range = (range_ratio < 0.7).astype(float)
    oi_increase = (oi_chg > 0).astype(float)
    absorption_event = narrow_range * oi_increase
    vol_weight = volume / volume.rolling(20, min_periods=5).mean().replace(0, np.nan)
    weighted_absorption = absorption_event * vol_weight * oi_chg.abs() / oi.rolling(20, min_periods=5).mean().replace(0, np.nan)
    price_dir = np.sign(close.diff())
    signed_absorption = weighted_absorption * price_dir
    factor = signed_absorption.rolling(12, min_periods=3).sum() - signed_absorption.rolling(30, min_periods=8).sum() * (12.0 / 30.0)
    return factor

DISCOVERED_FACTORS['smart_money_absorption_ratio'] = smart_money_absorption_ratio


def oi_weighted_mean_reversion_z(df):
    """用持仓量加权的价格偏离其自适应均线的Z-score，持仓量越大时偏离越可信，捕捉超买超卖后的均值回归机会
    avg |IC| = 0.0215
    """
    import numpy as np
    import pandas as pd
    close = df['close']
    oi = df['open_interest']
    window = 20
    oi_w = oi / oi.rolling(window, min_periods=1).sum()
    oi_w = oi_w.fillna(1.0 / window)
    weighted_ma = (close * oi_w).rolling(window, min_periods=5).sum() / oi_w.rolling(window, min_periods=5).sum()
    deviation = close - weighted_ma
    dev_std = deviation.rolling(window, min_periods=5).std()
    z = deviation / dev_std.replace(0, np.nan)
    factor = -z
    factor.name = 'oi_weighted_mean_reversion_z'
    return factor

DISCOVERED_FACTORS['oi_weighted_mean_reversion_z'] = oi_weighted_mean_reversion_z


def multi_cycle_trend_pressure(df):
    """将长周期（120根K线，约5个交易日）的EMA趋势方向与强度映射到当前30分钟K线，通过计算短周期收益率与长周期趋势的一致性得分来衡量跨周期趋势压力，一致时为正向压力，背离时为负向压力。
    avg |IC| = 0.0632
    """
    import numpy as np
    import pandas as pd
    close = df['close']
    oi = df['open_interest']
    long_period = 120
    short_period = 10
    ema_long = close.ewm(span=long_period, adjust=False).mean()
    long_trend = (close - ema_long) / ema_long
    short_ret = close.pct_change(short_period)
    oi_chg = oi.pct_change(long_period)
    trend_sign = np.sign(long_trend)
    short_sign = np.sign(short_ret)
    consistency = (trend_sign * short_ret).rolling(short_period).mean()
    oi_confirm = np.sign(oi_chg) * trend_sign
    oi_weight = 1 + 0.5 * oi_confirm
    factor = consistency * oi_weight * long_trend.abs()
    factor.name = 'multi_cycle_trend_pressure'
    return factor

DISCOVERED_FACTORS['multi_cycle_trend_pressure'] = multi_cycle_trend_pressure


def smart_money_absorption(df):
    """通过检测价格波动收窄但持仓量持续增加的背离现象，捕捉主力资金在窄幅震荡中悄然吸筹或派发的行为，吸筹强度越高因子值越大
    avg |IC| = 0.0220
    """
    import numpy as np
    import pandas as pd
    price_range = (df['high'] - df['low']) / df['close']
    oi_change = df['open_interest'].diff()
    range_ma = price_range.rolling(12).mean()
    range_std = price_range.rolling(12).std().replace(0, np.nan)
    range_zscore = (price_range - range_ma) / range_std
    oi_chg_ma = oi_change.rolling(12).mean()
    oi_chg_std = oi_change.rolling(12).std().replace(0, np.nan)
    oi_zscore = (oi_change - oi_chg_ma) / oi_chg_std
    raw = oi_zscore - range_zscore
    vol_ratio = df['volume'] / df['volume'].rolling(12).mean().replace(0, np.nan)
    weight = 1.0 / (1.0 + np.exp(-2 * (vol_ratio - 1)))
    factor = (raw * weight).rolling(6).mean()
    return factor

DISCOVERED_FACTORS['smart_money_absorption'] = smart_money_absorption


def oi_price_divergence_intensity(df):
    """衡量持仓量变化方向与价格变化方向的背离强度，通过滚动窗口内OI变化率与收益率的标准化差值累积来捕捉多空分歧加剧的信号
    avg |IC| = 0.0300
    """
    import numpy as np
    import pandas as pd
    oi = df['open_interest']
    close = df['close']
    oi_ret = oi.pct_change().fillna(0)
    price_ret = close.pct_change().fillna(0)
    window = 12
    oi_z = (oi_ret - oi_ret.rolling(window, min_periods=1).mean()) / (oi_ret.rolling(window, min_periods=1).std().replace(0, np.nan)).fillna(1)
    price_z = (price_ret - price_ret.rolling(window, min_periods=1).mean()) / (price_ret.rolling(window, min_periods=1).std().replace(0, np.nan)).fillna(1)
    raw_div = oi_z - price_z * np.sign(oi_z)
    factor = raw_div.rolling(6, min_periods=1).sum()
    factor.name = 'oi_price_divergence_intensity'
    return factor

DISCOVERED_FACTORS['oi_price_divergence_intensity'] = oi_price_divergence_intensity


def smart_money_divergence(df):
    """通过比较大成交量K线（主力活跃）与小成交量K线（散户主导）的持仓变动方向差异，捕捉主力资金的真实意图——当主力放量时持仓增减方向与散户时段相反，说明主力在反向布局
    avg |IC| = 0.0334
    """
    import numpy as np
    import pandas as pd
    n = 20
    vol_ma = df['volume'].rolling(n).mean()
    vol_std = df['volume'].rolling(n).std()
    oi_change = df['open_interest'].diff()
    price_dir = np.sign(df['close'] - df['open'])
    signed_oi = oi_change * price_dir
    high_vol_mask = df['volume'] > (vol_ma + 0.8 * vol_std)
    low_vol_mask = df['volume'] < (vol_ma - 0.3 * vol_std)
    signed_oi_high = signed_oi.where(high_vol_mask, np.nan)
    signed_oi_low = signed_oi.where(low_vol_mask, np.nan)
    smart_flow = signed_oi_high.rolling(n, min_periods=3).mean()
    retail_flow = signed_oi_low.rolling(n, min_periods=3).mean()
    divergence = smart_flow - retail_flow
    factor = divergence / df['open_interest'].rolling(n).std().replace(0, np.nan)
    factor.name = 'smart_money_divergence'
    return factor

DISCOVERED_FACTORS['smart_money_divergence'] = smart_money_divergence


def long_cycle_trend_pressure(df):
    """将长周期（120根K线，约5个交易日）的趋势方向通过线性回归斜率量化，再与短周期（10根K线）价格偏离该趋势线的标准化残差相乘，捕捉长周期趋势对短周期回归压力的映射。
    avg |IC| = 0.0267
    """
    import numpy as np
    import pandas as pd

    close = df['close'].values
    n_long = 120
    n_short = 10
    n = len(close)
    factor = np.full(n, np.nan)

    for i in range(n_long - 1, n):
        seg = close[i - n_long + 1: i + 1]
        x = np.arange(n_long, dtype=np.float64)
        x_mean = x.mean()
        y_mean = seg.mean()
        slope = np.sum((x - x_mean) * (seg - y_mean)) / (np.sum((x - x_mean) ** 2) + 1e-18)
        intercept = y_mean - slope * x_mean
        trend_val = slope * (n_long - 1) + intercept
        if i >= n_short - 1:
            short_seg = close[i - n_short + 1: i + 1]
            short_mean = short_seg.mean()
            short_std = short_seg.std(ddof=1)
            if short_std > 1e-18:
                residual_z = (close[i] - trend_val) / short_std
            else:
                residual_z = 0.0
            norm_slope = slope / (short_mean + 1e-18)
            factor[i] = -norm_slope * residual_z

    return pd.Series(factor, index=df.index, name='long_cycle_trend_pressure')

DISCOVERED_FACTORS['long_cycle_trend_pressure'] = long_cycle_trend_pressure


def oi_weighted_mean_reversion_zscore(df):
    """用持仓量加权的价格偏离其自适应均线的Z-score，持仓量越大时偏离越可信，捕捉持仓确认下的超买超卖回归机会
    avg |IC| = 0.0219
    """
    import numpy as np
    import pandas as pd
    close = df['close'].copy()
    oi = df['open_interest'].copy()
    lookback = 20
    oi_weight = oi / oi.rolling(lookback, min_periods=1).sum()
    oi_weight = oi_weight.fillna(1.0 / lookback)
    weighted_ma = (close * oi_weight).rolling(lookback, min_periods=5).sum() / oi_weight.rolling(lookback, min_periods=5).sum()
    deviation = close - weighted_ma
    dev_std = deviation.rolling(lookback, min_periods=5).std()
    zscore = deviation / dev_std.replace(0, np.nan)
    oi_pct = oi.pct_change(5)
    oi_confirm = 1 + oi_pct.clip(-0.5, 0.5).fillna(0)
    factor = -zscore * oi_confirm
    factor.name = 'oi_weighted_mean_reversion_zscore'
    return factor

DISCOVERED_FACTORS['oi_weighted_mean_reversion_zscore'] = oi_weighted_mean_reversion_zscore


def smart_money_pressure(df):
    """通过成交量加权的持仓量变化与价格变动方向的非对称性，识别主力资金在放量时隐蔽建仓或减仓的方向性压力——当放量伴随持仓增加但价格未同向大幅波动时，暗示主力在对手盘中吸筹。
    avg |IC| = 0.0616
    """
    import numpy as np
    import pandas as pd
    
    close = df['close']
    volume = df['volume']
    oi = df['open_interest']
    high = df['high']
    low = df['low']
    
    # 价格变动与持仓变动
    ret = close.pct_change()
    oi_chg = oi.diff()
    
    # 成交量相对强度（相对于近期均值的倍数）
    vol_ma = volume.rolling(20, min_periods=5).mean()
    vol_ratio = volume / vol_ma.replace(0, np.nan)
    
    # 价格波动幅度归一化（用真实波幅衡量当根K线的价格效率）
    true_range = high - low
    tr_ma = true_range.rolling(20, min_periods=5).mean()
    price_efficiency = ret.abs() / (true_range / tr_ma.replace(0, np.nan)).replace(0, np.nan)
    
    # 核心逻辑：主力压力 = 放量时持仓变化的方向 × 成交量权重 ÷ 价格实际移动效率
    # 当放量+持仓增加但价格移动效率低（振幅大但净变动小），说明主力在震荡中吸筹
    # 符号由持仓变化方向与价格方向的组合决定
    
    # 持仓变化方向与价格方向的交互
    oi_chg_norm = oi_chg / oi.rolling(20, min_periods=5).std().replace(0, np.nan)
    
    # 大单信号：放量条件下，持仓变化强但价格效率低（主力隐蔽操作）
    raw_signal = oi_chg_norm * vol_ratio * (1 - price_efficiency.clip(0, 2) / 2)
    
    # 用指数加权累积近期主力压力方向
    window = 12
    weights = np.exp(-np.arange(window)[::-1] / 4.0)
    weights = weights / weights.sum()
    
    def weighted_sum(x):
        v = x.values
        if len(v) < window:
            w = np.exp(-np.arange(len(v))[::-1] / 4.0)
            w = w / w.sum()
            valid = ~np.isnan(v)
            if valid.sum() < 3:
                return np.nan
            return np.nansum(v * w)
        valid = ~np.isnan(v)
        if valid.sum() < 5:
            return np.nan
        return np.nansum(v * weights)
    
        pressure = raw_signal.rolling(window, min_periods=5).apply(weighted_sum, raw=False)
    
        # Z-score标准化
        mu = pressure.rolling(60, min_periods=20).mean()
        sigma = pressure.rolling(60, min_periods=20).std().replace(0, np.nan)
        factor = (pressure - mu) / sigma
    
        factor.name = 'smart_money_pressure'
        return factor

DISCOVERED_FACTORS['smart_money_pressure'] = smart_money_pressure

def daily_trend_intrabar_alpha(df):
    """将日线级别的趋势方向（通过多根30分钟K线聚合的日收益率均线）映射到每根30分钟K线上，计算短周期收益率与长周期趋势方向的一致性得分，捕捉顺势延续的alpha。
    avg |IC| = 0.0259
    """
    import numpy as np
    import pandas as pd
    
    close = df['close'].copy()
    volume = df['volume'].copy()
    
    # 30分钟K线，一个交易日约9根(黄金期货日盘+夜盘约4.5小时)
    # 用16根bar近似一个完整交易日，用80根bar近似5个交易日
    bars_per_day = 9
    short_window = bars_per_day  # ~1日
    long_window = bars_per_day * 5  # ~5日
    
    # 长周期趋势：用长窗口的指数加权移动平均斜率表征日线级别趋势
    ema_long = close.ewm(span=long_window, min_periods=long_window // 2).mean()
    ema_short = close.ewm(span=short_window, min_periods=short_window // 2).mean()
    
    # 日线级别趋势强度：短期EMA与长期EMA的偏离度（类似MACD思想）
    trend_signal = (ema_short - ema_long) / ema_long
    
    # 趋势方向的变化率，反映趋势加速/减速
    trend_momentum = trend_signal.diff(bars_per_day)
    
    # 短周期（单根bar）的标准化收益率
    bar_return = close.pct_change()
    bar_return_z = (bar_return - bar_return.rolling(long_window).mean()) / bar_return.rolling(long_window).std()
    
    # 跨周期因子：短周期收益率在长周期趋势方向上的映射
    # 趋势方向一致时放大，不一致时缩小/反转
    # 使用tanh对trend_signal归一化到[-1,1]避免极端值
    trend_direction = np.tanh(trend_signal * 100)  # 放大后压缩
    
    # 核心因子：趋势方向 * 短周期动量一致性 + 趋势加速项
    # 滚动相关：短周期收益与趋势方向的滚动一致性
    consistency = (bar_return_z * trend_direction).rolling(
        window=bars_per_day, min_periods=bars_per_day // 2
    ).mean()
    
    # 加入趋势加速项：趋势正在增强时给予额外权重
    trend_accel = np.tanh(trend_momentum * 500)
    
    # 用成交量加权的趋势确认度
    vol_ma = volume.rolling(long_window, min_periods=long_window // 2).mean()
    vol_ratio = volume / vol_ma.replace(0, np.nan)
    vol_weight = np.tanh(vol_ratio - 1)  # 成交量高于均值为正
    
    # 最终因子：一致性得分 + 趋势加速 * 成交量确认
    factor = consistency + 0.5 * trend_accel * vol_weight
    
    # 去极值
    factor = factor.clip(factor.quantile(0.005), factor.quantile(0.995))
    
    factor.name = 'daily_trend_intrabar_alpha'
    return factor

DISCOVERED_FACTORS['daily_trend_intrabar_alpha'] = daily_trend_intrabar_alpha

def oi_price_divergence_zscore(df):
    """计算持仓量变化率与价格变化率的滚动背离程度（两者标准化后的差值再取z-score），捕捉持仓量与价格走势不一致时的潜在反转或趋势加速信号
    avg |IC| = 0.0431
    """
    import numpy as np
    import pandas as pd
    
    close = df['close']
    oi = df['open_interest']
    
    # 持仓量和价格的短期变化率
    oi_ret = oi.pct_change(1)
    price_ret = close.pct_change(1)
    
    # 在滚动窗口内对两者分别标准化，然后计算差值（背离度）
    window = 48  # 48个30分钟bar ≈ 2个交易日
    
    oi_ret_mean = oi_ret.rolling(window, min_periods=20).mean()
    oi_ret_std = oi_ret.rolling(window, min_periods=20).std()
    price_ret_mean = price_ret.rolling(window, min_periods=20).mean()
    price_ret_std = price_ret.rolling(window, min_periods=20).std()
    
    # 标准化后的变化率
    oi_z = (oi_ret - oi_ret_mean) / (oi_ret_std + 1e-10)
    price_z = (price_ret - price_ret_mean) / (price_ret_std + 1e-10)
    
    # 背离度：OI标准化变化 - 价格标准化变化
    # 正值 = OI增速超过价格增速（增仓但价格未跟上，蓄力或即将反转）
    # 负值 = 价格增速超过OI增速（价格拉升但持仓未跟上，可能虚涨）
    raw_divergence = oi_z - price_z
    
    # 对背离度取累积均值进行平滑，再做z-score以增强信号稳定性
    smooth_window = 24  # 1个交易日
    div_smooth = raw_divergence.rolling(smooth_window, min_periods=10).mean()
    
    # 更长窗口做z-score归一化
    zscore_window = 96  # 4个交易日
    div_mean = div_smooth.rolling(zscore_window, min_periods=40).mean()
    div_std = div_smooth.rolling(zscore_window, min_periods=40).std()
    
    factor = (div_smooth - div_mean) / (div_std + 1e-10)
    
    # clip极端值
    factor = factor.clip(-4, 4)
    
    factor.name = 'oi_price_divergence_zscore'
    return factor

DISCOVERED_FACTORS['oi_price_divergence_zscore'] = oi_price_divergence_zscore

def big_order_flow_imbalance(df):
    """通过成交量与持仓量变化的非对称性捕捉主力大单方向——当价格上涨时成交量放大但持仓增加有限，暗示主力主动买入后平仓获利；反之则为主力打压，该因子度量这种资金流不对称强度。
    avg |IC| = 0.0311
    """
    import numpy as np
    import pandas as pd

    close = df['close']
    volume = df['volume']
    oi = df['open_interest']

    ret = close.pct_change()
    oi_chg = oi.diff()
    vol_ma = volume.rolling(20, min_periods=5).mean()
    vol_ratio = volume / vol_ma.replace(0, np.nan)

    # 主力行为信号：价格方向 × 成交量强度 × 持仓变化方向的背离
    # 大单买入：价格涨 + 放量 + 持仓减少（主力拉升后兑现）
    # 大单卖出：价格跌 + 放量 + 持仓减少（主力砸盘出货）
    # 用符号背离度量主力意图
    oi_chg_norm = oi_chg / oi.rolling(20, min_periods=5).std().replace(0, np.nan)
    signed_flow = ret.apply(np.sign) * vol_ratio * (-oi_chg_norm)

    # 短周期累积捕捉主力连续行为
    flow_fast = signed_flow.rolling(6, min_periods=3).sum()
    flow_slow = signed_flow.rolling(18, min_periods=6).sum()

    # 快慢差值反映主力近期加速行为
    raw = flow_fast - 0.5 * flow_slow

    # z-score 标准化
    mu = raw.rolling(40, min_periods=10).mean()
    sigma = raw.rolling(40, min_periods=10).std().replace(0, np.nan)
    factor = (raw - mu) / sigma

    factor.name = 'big_order_flow_imbalance'
    return factor

DISCOVERED_FACTORS['big_order_flow_imbalance'] = big_order_flow_imbalance


def oi_weighted_mean_reversion_pressure(df):
    """用持仓量加权的价格偏离度衡量均值回归压力——当价格大幅偏离持仓量加权均价且持仓量收缩时，回归压力更强，反之持仓扩张时趋势可能延续，因子值越极端表示超买超卖程度越高。
    avg |IC| = 0.0266
    """
    import numpy as np
    import pandas as pd

    close = df['close'].values
    volume = df['volume'].values
    oi = df['open_interest'].values

    # 持仓量加权的移动均价（20周期）
    window = 20
    oi_abs = np.abs(oi) + 1e-9
    weighted_price = close * oi_abs
    sum_wp = pd.Series(weighted_price).rolling(window, min_periods=5).sum().values
    sum_oi = pd.Series(oi_abs).rolling(window, min_periods=5).sum().values
    oi_vwap = sum_wp / sum_oi

    # 价格偏离持仓量加权均价的百分比
    deviation = (close - oi_vwap) / (oi_vwap + 1e-9)

    # 偏离度的z-score标准化（40周期滚动）
    z_window = 40
    dev_series = pd.Series(deviation)
    dev_mean = dev_series.rolling(z_window, min_periods=10).mean()
    dev_std = dev_series.rolling(z_window, min_periods=10).std()
    zscore = (dev_series - dev_mean) / (dev_std + 1e-9)

    # 持仓量变化率（缩仓放大回归信号，增仓抑制回归信号）
    oi_series = pd.Series(oi_abs)
    oi_ma = oi_series.rolling(window, min_periods=5).mean()
    oi_ratio = oi_series / (oi_ma + 1e-9)
    # oi_ratio < 1 表示缩仓，乘以 (2 - oi_ratio) 放大回归压力
    reversion_multiplier = 2.0 - oi_ratio

    factor = zscore * reversion_multiplier
    factor = factor.values

    return pd.Series(factor, index=df.index, name='oi_weighted_mean_reversion_pressure')

DISCOVERED_FACTORS['oi_weighted_mean_reversion_pressure'] = oi_weighted_mean_reversion_pressure


def price_zscore_adaptive(df):
    """使用自适应窗口（基于近期波动率regime）计算价格偏离移动均值的z-score，波动率高时缩短窗口加速均值回归信号，波动率低时延长窗口过滤噪音
    avg |IC| = 0.0217
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        high = df['high'].copy()
        low = df['low'].copy()
    
        # 计算真实波幅作为波动率代理
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
    
        # 短期和长期波动率
        vol_short = tr.rolling(10, min_periods=5).mean()
        vol_long = tr.rolling(60, min_periods=20).mean()
    
        # 波动率比率决定自适应权重: 高波动时偏向短窗口
        vol_ratio = (vol_short / vol_long).clip(0.5, 2.0)
    
        # 两个窗口的均值和标准差
        short_window = 20
        long_window = 80
    
        ma_short = close.rolling(short_window, min_periods=10).mean()
        std_short = close.rolling(short_window, min_periods=10).std()
        ma_long = close.rolling(long_window, min_periods=30).mean()
        std_long = close.rolling(long_window, min_periods=30).std()
    
        # z-score for each window
        z_short = (close - ma_short) / std_short.replace(0, np.nan)
        z_long = (close - ma_long) / std_long.replace(0, np.nan)
    
        # 自适应混合: vol_ratio高(高波动)时权重偏向短窗口z-score
        # 归一化权重到[0,1], vol_ratio范围[0.5, 2.0] -> w_short范围[0, 1]
        w_short = (vol_ratio - 0.5) / 1.5  # maps [0.5, 2.0] -> [0, 1]
    
        adaptive_z = w_short * z_short + (1 - w_short) * z_long
    
        # 用持仓量变化调整信号强度：持仓量下降时超买超卖信号更可靠（趋势衰竭）
        oi = df['open_interest'].copy()
        oi_change_pct = oi.pct_change(10)
        oi_modifier = 1.0 - oi_change_pct.clip(-0.5, 0.5)  # OI下降时放大信号
    
        # 最终因子：取负号使得超买为负、超卖为正（均值回归方向）
        factor = -adaptive_z * oi_modifier
    
        # 去极值
        factor = factor.clip(factor.quantile(0.01), factor.quantile(0.99))
    
        return factor

DISCOVERED_FACTORS['price_zscore_adaptive'] = price_zscore_adaptive


def rv_cone_term_skew(df):
    """多时间尺度已实现波动率在各自历史分位数上的斜率，捕捉波动率锥的期限结构倾斜方向，正值表示长周期波动率分位偏高（结构性波动率抬升），负值表示短周期波动率突刺（均值回复信号）。
    avg |IC| = 0.0442
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(close)
    
        # Use Parkinson volatility for efficiency (high-low based)
        log_hl = np.log(high / np.where(low > 0, low, np.nan))
        log_hl_sq = log_hl ** 2 / (4.0 * np.log(2.0))
    
        # Multiple timescales for realized vol
        windows = [6, 12, 24, 48]
        lookback = 240  # historical lookback for percentile ranking
    
        # Compute rolling realized vol at each timescale
        rv_dict = {}
        for w in windows:
            rv = pd.Series(log_hl_sq).rolling(window=w, min_periods=max(w // 2, 3)).mean().values
            rv = np.sqrt(rv) * np.sqrt(w)  # annualize-like scaling to same units
            rv_dict[w] = rv
    
        # Compute percentile rank of each RV within its own rolling history
        pct_ranks = {}
        for w in windows:
            rv_series = pd.Series(rv_dict[w])
            # Rolling percentile rank
            def rolling_pctrank(s, lb):
                result = np.full(len(s), np.nan)
                vals = s.values
                for i in range(lb, len(vals)):
                    window_vals = vals[i - lb:i + 1]
                    valid = window_vals[~np.isnan(window_vals)]
                    if len(valid) >= 20:
                        result[i] = np.searchsorted(np.sort(valid), vals[i]) / (len(valid) - 1)
                return result
        
            pct_ranks[w] = rolling_pctrank(rv_series, lookback)
    
        # Fit linear slope across timescales (x = log of window size for even spacing)
        x = np.log(np.array(windows, dtype=float))
        x_mean = x.mean()
        x_demean = x - x_mean
        ss_xx = np.sum(x_demean ** 2)
    
        factor = np.full(n, np.nan)
        for i in range(n):
            y = np.array([pct_ranks[w][i] for w in windows])
            if np.any(np.isnan(y)):
                continue
            y_mean = y.mean()
            y_demean = y - y_mean
            slope = np.sum(x_demean * y_demean) / ss_xx
            factor[i] = slope
    
        return pd.Series(factor, index=df.index, name='rv_cone_term_skew')

DISCOVERED_FACTORS['rv_cone_term_skew'] = rv_cone_term_skew


def vol_shock_price_elasticity(df):
    """衡量价格变动对成交量冲击的弹性（滚动回归斜率），弹性下降意味着大量成交无法推动价格，暗示筹码被吸收，预示反转或趋势衰竭
    avg |IC| = 0.0432
    """
        import numpy as np
        import pandas as pd
    
        close = df['close']
        volume = df['volume']
    
        # Rolling volume z-score as "volume shock" measure
        vol_ma = volume.rolling(40, min_periods=20).mean()
        vol_std = volume.rolling(40, min_periods=20).std()
        vol_zscore = (volume - vol_ma) / (vol_std.replace(0, np.nan) + 1e-10)
    
        # Signed return (to capture directional impact)
        ret = close.pct_change()
        abs_ret = ret.abs()
    
        # Rolling beta: abs_ret = alpha + beta * vol_zscore
        # High beta = price is elastic to volume shocks
        # Low/declining beta = volume absorbed without price impact
        window = 24  # 24 bars ~ 2 trading days on 30min
    
        cov_rv = abs_ret.rolling(window, min_periods=12).cov(vol_zscore)
        var_v = vol_zscore.rolling(window, min_periods=12).var()
        elasticity = cov_rv / (var_v.replace(0, np.nan) + 1e-10)
    
        # Rate of change in elasticity: declining = absorption regime
        elas_fast = elasticity.ewm(span=8, min_periods=4).mean()
        elas_slow = elasticity.ewm(span=30, min_periods=10).mean()
        elas_momentum = elas_fast - elas_slow
    
        # Combine with price direction:
        # Falling elasticity + rising price => stealth accumulation (bullish)
        # Falling elasticity + falling price => selling absorbed (bullish reversal)
        # Rising elasticity + rising price => easy gains, fragile (bearish)
        price_direction = close.ewm(span=20, min_periods=10).mean().pct_change(10)
    
        # Core factor: negative elasticity momentum adjusted by price context
        # Negative elas_momentum (absorption) with any price trend => contrarian signal
        factor = -elas_momentum * (1 + abs_ret.rolling(window, min_periods=12).mean() * 100)
    
        # Normalize by recent range for cross-regime stability
        factor_ma = factor.rolling(60, min_periods=20).mean()
        factor_std = factor.rolling(60, min_periods=20).std()
        factor = (factor - factor_ma) / (factor_std.replace(0, np.nan) + 1e-10)
    
        factor.name = 'vol_shock_price_elasticity'
        return factor

DISCOVERED_FACTORS['vol_shock_price_elasticity'] = vol_shock_price_elasticity


def cross_cycle_trend_residual_momentum(df):
    """用长周期(48根K线≈3个交易日)线性回归趋势外推的预期价格与实际短周期(8根K线)价格的偏差动量，捕捉短期价格对长期趋势轨迹的超调或滞后信号。
    avg |IC| = 0.0204
    """
        import numpy as np
        import pandas as pd

        close = df['close'].values
        n = len(close)
        long_window = 48   # ~3 trading days on 30min bars
        short_window = 8   # ~4 hours
        factor = np.full(n, np.nan)

        # Precompute linear regression components for long window
        x = np.arange(long_window, dtype=float)
        x_mean = x.mean()
        x_var = ((x - x_mean) ** 2).sum()

        for i in range(long_window + short_window - 1, n):
            # Long-period linear regression on [i - long_window - short_window + 1, i - short_window + 1)
            lr_start = i - long_window - short_window + 1
            lr_end = i - short_window + 1
            y = close[lr_start:lr_end]

            if np.any(np.isnan(y)):
                continue

            y_mean = y.mean()
            slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
            intercept = y_mean - slope * x_mean

            # Project trend forward by short_window bars
            # At end of LR window, x = long_window - 1; project to x = long_window - 1 + short_window
            projected_price = intercept + slope * (long_window - 1 + short_window)

            # Actual current price
            actual_price = close[i]

            # Price at the end of the LR window (start of short window)
            anchor_price = close[lr_end]

            if anchor_price == 0:
                continue

            # Residual: how much short-term deviates from long-term projection (normalized)
            projected_return = (projected_price - anchor_price) / anchor_price
            actual_return = (actual_price - anchor_price) / anchor_price

            residual = actual_return - projected_return

            # Weight by trend strength (R-squared of the long regression)
            y_hat = intercept + slope * x
            ss_res = ((y - y_hat) ** 2).sum()
            ss_tot = ((y - y_mean) ** 2).sum()
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

            # Strong long-trend makes the residual more meaningful
            factor[i] = residual * r_squared

        factor_series = pd.Series(factor, index=df.index, name='cross_cycle_trend_residual_momentum')

        # Standardize with rolling z-score to stabilize
        roll_mean = factor_series.rolling(96, min_periods=48).mean()
        roll_std = factor_series.rolling(96, min_periods=48).std()
        factor_series = (factor_series - roll_mean) / roll_std.replace(0, np.nan)

        return factor_series

DISCOVERED_FACTORS['cross_cycle_trend_residual_momentum'] = cross_cycle_trend_residual_momentum


def weekday_session_return_bias(df):
    """基于滚动历史统计每个(星期几×日内时段)组合的平均收益率，捕捉黄金因全球交易时段轮转产生的周内×时段交互季节性偏差
    avg |IC| = 0.0284
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['ret'] = df['close'].pct_change()
    
        # Extract weekday and intraday session identifier
        if hasattr(df.index, 'weekday'):
            df['weekday'] = df.index.weekday
            df['session'] = df.index.hour * 100 + df.index.minute
        else:
            df['weekday'] = pd.to_datetime(df.index).weekday
            df['session'] = pd.to_datetime(df.index).hour * 100 + pd.to_datetime(df.index).minute
    
        # Create a composite seasonal key: weekday * 100 + session_rank
        unique_sessions = sorted(df['session'].unique())
        session_map = {s: i for i, s in enumerate(unique_sessions)}
        df['session_rank'] = df['session'].map(session_map)
        df['seasonal_key'] = df['weekday'] * 100 + df['session_rank']
    
        # For each seasonal_key, compute expanding mean of historical returns
        # Use minimum 20 observations to have stable estimate, with exponential weighting
        # to adapt to regime changes
        min_obs = 20
        halflife = 60  # ~60 occurrences of same slot ≈ 12 weeks
    
        factor = pd.Series(np.nan, index=df.index)
    
        for key in df['seasonal_key'].unique():
            mask = df['seasonal_key'] == key
            subset_ret = df.loc[mask, 'ret']
        
            # Exponentially weighted expanding mean (shift to avoid lookahead)
            ewm_mean = subset_ret.shift(1).ewm(halflife=halflife, min_periods=min_obs).mean()
            ewm_std = subset_ret.shift(1).ewm(halflife=halflife, min_periods=min_obs).std()
        
            # Normalize: t-stat like score for stability
            score = ewm_mean / (ewm_std + 1e-10)
            factor.loc[mask] = score.values
    
        # Clip extreme values
        factor = factor.clip(-3, 3)
    
        # Fill initial NaN with 0 (no seasonal bias estimated yet)
        factor = factor.fillna(0.0)
    
        return factor

DISCOVERED_FACTORS['weekday_session_return_bias'] = weekday_session_return_bias


def adaptive_mean_reversion_zscore(df):
    """基于自适应窗口（波动率调整）的价格偏离VWAP均值的Z-score，捕捉价格相对于成交量加权公允价值的超买超卖程度，波动率越高则回看窗口越短以适应市场状态变化
    avg |IC| = 0.0264
    """
        import numpy as np
        import pandas as pd
    
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    
        # 计算滚动波动率用于自适应窗口
        ret = df['close'].pct_change()
        fast_vol = ret.rolling(window=10, min_periods=5).std()
        slow_vol = ret.rolling(window=40, min_periods=10).std()
    
        # 波动率比率：高波动时用短窗口，低波动时用长窗口
        vol_ratio = (fast_vol / slow_vol.replace(0, np.nan)).clip(0.5, 2.0)
    
        # 自适应窗口长度：基础窗口24（约2个交易日），根据波动率比率调整
        base_window = 24
        # vol_ratio高 -> 窗口短（快速适应），vol_ratio低 -> 窗口长（稳定估计）
        adaptive_window = (base_window / vol_ratio).fillna(base_window).astype(int).clip(8, 48)
    
        # 计算多个固定窗口的VWAP和标准差，然后根据自适应窗口插值选择
        windows = [8, 12, 16, 20, 24, 32, 40, 48]
        vwap_dict = {}
        std_dict = {}
    
        for w in windows:
            cum_vp = (typical_price * df['volume']).rolling(window=w, min_periods=w // 2).sum()
            cum_v = df['volume'].rolling(window=w, min_periods=w // 2).sum()
            vwap_dict[w] = cum_vp / cum_v.replace(0, np.nan)
            # 价格偏离VWAP的滚动标准差
            deviation = typical_price - vwap_dict[w]
            std_dict[w] = deviation.rolling(window=w, min_periods=w // 2).std()
    
        # 根据自适应窗口选择最近的VWAP和std
        n = len(df)
        selected_vwap = pd.Series(np.nan, index=df.index)
        selected_std = pd.Series(np.nan, index=df.index)
    
        for i in range(n):
            aw = adaptive_window.iloc[i]
            # 找最近的窗口
            best_w = min(windows, key=lambda w: abs(w - aw))
            selected_vwap.iloc[i] = vwap_dict[best_w].iloc[i]
            selected_std.iloc[i] = std_dict[best_w].iloc[i]
    
        # Z-score: 当前价格偏离自适应VWAP的标准化程度
        deviation = typical_price - selected_vwap
        zscore = deviation / selected_std.replace(0, np.nan)
    
        # 加入持仓量权重：持仓量增加时信号更可靠（取反表示均值回归方向）
        oi_change_pct = df['open_interest'].pct_change(5)
        oi_weight = 1.0 + oi_change_pct.clip(-0.1, 0.1) * 5  # 持仓增加放大信号
    
        # 负号：Z-score为正（超买）-> 因子为负（预期回落），反之亦然
        factor = -zscore * oi_weight
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
        factor.name = 'adaptive_mean_reversion_zscore'
    
        return factor

DISCOVERED_FACTORS['adaptive_mean_reversion_zscore'] = adaptive_mean_reversion_zscore


def oi_price_elastic_divergence(df):
    """计算持仓量变化率对价格变化率的弹性系数的滚动Z-score，捕捉OI对价格反应的异常偏离——当弹性系数极端偏高说明投机性建仓过度（价格小幅波动引发大量持仓变化），极端偏低则说明市场对价格变动漠然，两者均预示趋势转折。
    avg |IC| = 0.0232
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values.astype(float)
        oi = df['open_interest'].values.astype(float)
        n = len(close)
    
        # 价格收益率和OI变化率
        price_ret = np.empty(n)
        price_ret[0] = 0.0
        price_ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    
        oi_ret = np.empty(n)
        oi_ret[0] = 0.0
        oi_ret[1:] = (oi[1:] - oi[:-1]) / np.where(oi[:-1] == 0, 1.0, oi[:-1])
    
        # 计算滚动弹性系数: 用滚动回归 oi_ret ~ price_ret 的斜率
        # 弹性 = cov(oi_ret, price_ret) / var(price_ret)
        window = 20
    
        price_ret_s = pd.Series(price_ret)
        oi_ret_s = pd.Series(oi_ret)
    
        roll_cov = price_ret_s.rolling(window=window, min_periods=12).apply(
            lambda x: np.cov(x, oi_ret_s.iloc[x.index[0]:x.index[-1]+1].values[-len(x):])[0, 1] 
            if len(x) >= 12 else np.nan, raw=False
        )
    
        # 更高效的方式
        roll_mean_p = price_ret_s.rolling(window=window, min_periods=12).mean()
        roll_mean_o = oi_ret_s.rolling(window=window, min_periods=12).mean()
    
        cross = (price_ret_s * oi_ret_s).rolling(window=window, min_periods=12).mean()
        roll_cov2 = cross - roll_mean_p * roll_mean_o
    
        roll_var_p = price_ret_s.rolling(window=window, min_periods=12).var(ddof=0)
    
        # 弹性系数
        elasticity = roll_cov2 / roll_var_p.replace(0, np.nan)
    
        # 对弹性系数取滚动Z-score（较长窗口）以衡量当前弹性是否异常
        zscore_window = 60
        elas_mean = elasticity.rolling(window=zscore_window, min_periods=30).mean()
        elas_std = elasticity.rolling(window=zscore_window, min_periods=30).std(ddof=1)
    
        z_elasticity = (elasticity - elas_mean) / elas_std.replace(0, np.nan)
    
        # 用符号调整：结合近期OI方向，使因子有方向性
        # 如果OI在增加且弹性异常高 -> 投机建仓过度，可能反转（负信号）
        # 使用tanh压缩极端值
        oi_momentum = oi_ret_s.rolling(window=10, min_periods=5).mean()
        oi_direction = np.sign(oi_momentum)
    
        # 最终因子：弹性Z-score乘以OI方向的负值 -> 过度建仓为负信号
        factor = -z_elasticity * oi_direction
    
        # clip极端值
        factor = factor.clip(-5, 5)
    
        factor.index = df.index
        factor.name = 'oi_price_elastic_divergence'
    
        return factor

DISCOVERED_FACTORS['oi_price_elastic_divergence'] = oi_price_elastic_divergence


def price_vwap_reversion_z(df):
    """计算收盘价相对于成交量加权均价(VWAP)的标准化偏离度，当价格大幅偏离VWAP时预期均值回归，偏离越大反转概率越高
    avg |IC| = 0.0254
    """
        import numpy as np
        import pandas as pd
    
        # 使用典型价格 * 成交量来计算VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    
        # 滚动窗口计算VWAP（20根30分钟K线，约2.5个交易日）
        window = 20
        cum_tp_vol = (typical_price * df['volume']).rolling(window=window, min_periods=10).sum()
        cum_vol = df['volume'].rolling(window=window, min_periods=10).sum()
    
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    
        # 计算价格偏离VWAP的比率
        deviation = (df['close'] - vwap) / vwap
    
        # 使用更长窗口(40根)计算偏离度的均值和标准差，进行Z-score标准化
        z_window = 40
        dev_mean = deviation.rolling(window=z_window, min_periods=15).mean()
        dev_std = deviation.rolling(window=z_window, min_periods=15).std()
    
        z_score = (deviation - dev_mean) / dev_std.replace(0, np.nan)
    
        # 用持仓量变化率作为信号增强：持仓量减少时偏离更可能回归（多头/空头平仓）
        oi_change_rate = df['open_interest'].pct_change(5)
    
        # 当z_score极端且持仓量在减少时，回归信号更强
        # 负号表示均值回归方向：z_score高时预期下跌，z_score低时预期上涨
        oi_decay_factor = 1.0 + (-oi_change_rate.clip(-0.1, 0.1)) * 2  # 持仓减少时放大信号
    
        factor = -z_score * oi_decay_factor
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['price_vwap_reversion_z'] = price_vwap_reversion_z


def oi_price_elasticity_regime(df):
    """计算持仓量变化对价格变化的弹性系数在滚动窗口内的regime切换信号，当弹性由正转负表示市场从趋势跟随转向反转模式，捕捉持仓量驱动力的结构性变化。
    avg |IC| = 0.0323
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        oi = df['open_interest'].values
        n = len(close)
    
        # 价格和持仓量的对数收益率
        log_ret = np.log(close[1:] / close[:-1])
        log_oi_ret = np.log(oi[1:] / np.where(oi[:-1] > 0, oi[:-1], np.nan))
    
        log_ret = np.concatenate([[np.nan], log_ret])
        log_oi_ret = np.concatenate([[np.nan], log_oi_ret])
    
        s_ret = pd.Series(log_ret)
        s_oi_ret = pd.Series(log_oi_ret)
    
        # 短窗口弹性：OI变化率对价格变化率的回归斜率（滚动16根K线）
        short_window = 16
        # 长窗口弹性（滚动48根K线）
        long_window = 48
    
        def rolling_beta(x_series, y_series, window):
            """回归斜率 beta = cov(x,y)/var(x)，这里y=price_ret, x=oi_ret"""
            cov_xy = x_series.rolling(window, min_periods=window//2).cov(y_series)
            var_x = x_series.rolling(window, min_periods=window//2).var()
            beta = cov_xy / var_x.replace(0, np.nan)
            return beta
    
        # 弹性 = d(log_price) / d(log_oi) 的回归斜率
        beta_short = rolling_beta(s_oi_ret, s_ret, short_window)
        beta_long = rolling_beta(s_oi_ret, s_ret, long_window)
    
        # 弹性差异：短期弹性 vs 长期弹性的偏离
        elasticity_diff = beta_short - beta_long
    
        # 弹性的变化速度（动量）
        elasticity_momentum = beta_short.diff(4)
    
        # Regime信号：弹性差异标准化 + 弹性动量标准化的组合
        norm_window = 32
    
        def zscore_rolling(s, window):
            mu = s.rolling(window, min_periods=window//2).mean()
            sigma = s.rolling(window, min_periods=window//2).std()
            return (s - mu) / sigma.replace(0, np.nan)
    
        z_diff = zscore_rolling(elasticity_diff, norm_window)
        z_mom = zscore_rolling(elasticity_momentum, norm_window)
    
        # 组合信号：弹性regime切换强度
        # 当短期弹性急剧偏离长期弹性且动量加速时，信号更强
        raw_signal = 0.6 * z_diff + 0.4 * z_mom
    
        # 用持仓量变化的绝对幅度加权，OI变化大时信号更可信
        oi_activity = s_oi_ret.abs().rolling(short_window, min_periods=8).mean()
        oi_activity_z = zscore_rolling(oi_activity, norm_window)
        # sigmoid映射到[0.5, 1.5]作为置信度权重
        confidence = 1.0 / (1.0 + np.exp(-oi_activity_z)) + 0.5
    
        factor = raw_signal * confidence
    
        # 轻微平滑去噪
        factor = factor.ewm(span=3, adjust=False).mean()
    
        factor = factor.clip(-5, 5)
    
        return pd.Series(factor.values, index=df.index, name='oi_price_elasticity_regime')

DISCOVERED_FACTORS['oi_price_elasticity_regime'] = oi_price_elasticity_regime


def net_money_flow_intensity(df):
    """通过价格变动方向加权的成交量与持仓量变化交互，刻画主力资金净流入强度——价格上涨且持仓增加视为主力多头建仓，价格下跌且持仓增加视为主力空头建仓，持仓减少则为平仓离场，综合衡量主力净方向性资金流。
    avg |IC| = 0.0267
    """
        import numpy as np
        import pandas as pd
    
        close = df['close']
        volume = df['volume']
        oi = df['open_interest']
        high = df['high']
        low = df['low']
    
        # 典型价格
        typical_price = (high + low + close) / 3.0
    
        # 价格变动方向与幅度
        price_change = typical_price.diff()
    
        # 持仓量变化
        oi_change = oi.diff()
    
        # 资金流方向判定：
        # 价格上涨 + 持仓增加 → 主力多头开仓(+1权重)
        # 价格下跌 + 持仓增加 → 主力空头开仓(-1权重)  
        # 价格上涨 + 持仓减少 → 空头平仓(+0.5权重，偏多但力度弱)
        # 价格下跌 + 持仓减少 → 多头平仓(-0.5权重，偏空但力度弱)
    
        # 用持仓变化的绝对值作为主力参与程度的代理
        oi_abs = oi_change.abs()
        oi_participation = oi_abs / (oi_abs.rolling(20, min_periods=5).mean() + 1e-10)
    
        # 开仓/平仓区分：持仓增加为开仓，减少为平仓
        is_oi_increase = (oi_change > 0).astype(float)
        is_oi_decrease = (oi_change < 0).astype(float)
        is_oi_flat = (oi_change == 0).astype(float)
    
        # 价格方向
        price_dir = np.sign(price_change)
    
        # 主力资金流 = 方向 × 成交量 × 参与度权重
        # 开仓权重1.0，平仓权重0.5，持仓不变权重0.3
        weight = is_oi_increase * 1.0 + is_oi_decrease * 0.5 + is_oi_flat * 0.3
    
        # 单bar资金流
        raw_flow = price_dir * volume * weight * oi_participation
    
        # 短期累积净资金流（8根K线 = 4小时）
        short_flow = raw_flow.rolling(8, min_periods=3).sum()
    
        # 长期累积净资金流（40根K线 = 约一周）
        long_flow = raw_flow.rolling(40, min_periods=10).sum()
    
        # 净资金流强度 = 短期流入相对长期的偏离，标准化
        long_std = raw_flow.rolling(40, min_periods=10).std()
    
        factor = (short_flow - long_flow / 5.0) / (long_std * np.sqrt(8) + 1e-10)
    
        # 用tanh压缩极端值
        factor = np.tanh(factor / 3.0)
    
        factor.name = 'net_money_flow_intensity'
        return factor

DISCOVERED_FACTORS['net_money_flow_intensity'] = net_money_flow_intensity


def hour_of_day_momentum_regime(df):
    """基于交易日内不同时段（早盘开盘、午盘、夜盘）的历史动量特征，计算当前时段相对于其历史同时段收益均值的标准化偏离度，捕捉黄金期货日内时段效应的均值回归或动量延续特征
    avg |IC| = 0.0225
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['ret'] = df['close'].pct_change()
    
        # 从index或行号推断时段标签
        # SHFE黄金期货30分钟K线时段：
        # 夜盘: 21:00-23:00, 次日00:00-01:00 (约6根)
        # 早盘: 09:00-10:15, 10:30-11:30 (约5根)
        # 午盘: 13:30-15:00 (约3根)
        # 总计约14根/交易日
    
        if hasattr(df.index, 'hour'):
            hours = df.index.hour
        elif 'datetime' in df.columns:
            hours = pd.to_datetime(df['datetime']).dt.hour
        else:
            hours = None
    
        if hours is not None:
            # 基于小时划分时段
            conditions = [
                (hours >= 21) | (hours < 2),   # 夜盘
                (hours >= 9) & (hours < 12),    # 早盘
                (hours >= 12) & (hours < 16),   # 午盘
            ]
            choices = [0, 1, 2]
            df['session'] = np.select(conditions, choices, default=1)
        else:
            # 无时间信息时，用滚动位置模拟（假设每天约14根K线）
            bars_per_day = 14
            df['bar_pos'] = np.arange(len(df)) % bars_per_day
            conditions = [
                df['bar_pos'] < 6,    # 夜盘
                df['bar_pos'] < 11,   # 早盘
                df['bar_pos'] >= 11,  # 午盘
            ]
            choices = [0, 1, 2]
            df['session'] = np.select(conditions, choices, default=1)
    
        # 同时加入周内效应：星期几
        if hasattr(df.index, 'dayofweek'):
            df['dow'] = df.index.dayofweek
        elif 'datetime' in df.columns:
            df['dow'] = pd.to_datetime(df['datetime']).dt.dayofweek
        else:
            df['dow'] = 0
    
        # 构建复合时段标签: dow * 3 + session，最多 5*3=15 种组合
        df['regime_label'] = df['dow'] * 3 + df['session']
    
        # 对每个regime_label，计算该标签在过去N个同标签bar的收益均值和标准差
        lookback = 60  # 约60个同类bar（约4周同时段数据）
    
        grouped_mean = df.groupby('regime_label')['ret'].transform(
            lambda x: x.rolling(window=lookback, min_periods=10).mean()
        )
        grouped_std = df.groupby('regime_label')['ret'].transform(
            lambda x: x.rolling(window=lookback, min_periods=10).std()
        )
    
        # 当前收益相对于同regime历史分布的z-score
        zscore = (df['ret'] - grouped_mean) / (grouped_std + 1e-10)
    
        # 用历史同regime均值作为预期偏置，结合z-score构建因子
        # 正的regime_mean意味着该时段历史上倾向于上涨
        # 用EMA平滑regime_mean作为最终因子信号
        regime_bias = grouped_mean.ewm(span=20, min_periods=5).mean()
    
        # 将regime偏置与当前偏离度结合：偏置方向 + 均值回归信号
        factor = regime_bias * 1000 - zscore * 0.1  # regime动量 + 极端回归
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
        factor.name = 'hour_of_day_momentum_regime'
    
        return factor

DISCOVERED_FACTORS['hour_of_day_momentum_regime'] = hour_of_day_momentum_regime


def vol_shock_price_resilience(df):
    """衡量成交量突然放大（冲击）时价格的吸收能力，量大但价格变动小说明有大单被市场消化，反之则说明流动性不足导致价格剧烈波动，该比值的变化趋势反映市场微观结构的转变
    avg |IC| = 0.0449
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        high = df['high'].values
        low = df['low'].values
    
        n = len(close)
        factor = np.full(n, np.nan)
    
        # 价格变动幅度：用真实波幅(TR)衡量单根K线的价格波动
        tr = np.maximum(high - low, 
             np.maximum(np.abs(high - np.append(np.nan, close[:-1])),
                        np.abs(low - np.append(np.nan, close[:-1]))))
    
        # 成交量的滚动均值和标准差（20周期）
        lookback = 20
        vol_series = pd.Series(volume)
        vol_ma = vol_series.rolling(lookback, min_periods=10).mean().values
        vol_std = vol_series.rolling(lookback, min_periods=10).std().values
    
        # 成交量z-score：识别异常放量
        vol_zscore = (volume - vol_ma) / np.where(vol_std > 0, vol_std, np.nan)
    
        # 单位成交量的价格冲击：TR / volume（归一化）
        tr_series = pd.Series(tr)
        tr_ma = tr_series.rolling(lookback, min_periods=10).mean().values
    
        # 归一化价格冲击
        price_impact = tr / np.where(tr_ma > 0, tr_ma, np.nan)
        vol_norm = volume / np.where(vol_ma > 0, vol_ma, np.nan)
    
        # 核心指标：放量时的价格弹性 = 归一化价格波动 / 归一化成交量
        # 值小 -> 量大但价格稳（市场能吸收），值大 -> 量大价格也大波动（冲击显著）
        resilience = price_impact / np.where(vol_norm > 0, vol_norm, np.nan)
    
        # 只关注放量时刻（vol_zscore > 0.5），平时设为1（中性）
        resilience_cond = np.where(vol_zscore > 0.5, resilience, np.nan)
    
        # 用指数加权填充并平滑，得到连续信号
        res_series = pd.Series(resilience_cond)
        # 前向填充最多5根，然后做短期EMA
        res_filled = res_series.ffill(limit=5)
    
        # 短期均值 vs 长期均值的比值变化：趋势化
        short_window = 8
        long_window = 30
    
        res_short = res_filled.rolling(short_window, min_periods=3).mean()
        res_long = res_filled.rolling(long_window, min_periods=10).mean()
    
        # 最终因子：短期冲击弹性相对长期的偏离
        # 正值 -> 近期放量时价格波动相对更大（流动性恶化/趋势加速）
        # 负值 -> 近期放量时价格波动相对更小（大单被吸收/筹码交换充分）
        raw_factor = (res_short - res_long) / np.where(res_long > 0, res_long, np.nan)
    
        # 标准化
        factor_std = raw_factor.rolling(60, min_periods=20).std()
        factor_mean = raw_factor.rolling(60, min_periods=20).mean()
    
        final_factor = (raw_factor - factor_mean) / np.where(factor_std > 0, factor_std, np.nan)
    
        # 限制极端值
        final_factor = final_factor.clip(-3, 3)
    
        return final_factor

DISCOVERED_FACTORS['vol_shock_price_resilience'] = vol_shock_price_resilience


def smart_money_flow_intensity(df):
    """通过识别高成交量且持仓量显著变化的K线（视为主力大单行为），以成交量加权的持仓变化方向累积衡量主力资金净流入强度，正值表示主力建仓、负值表示主力撤退。
    avg |IC| = 0.0218
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        oi = df['open_interest'].values
        high = df['high'].values
        low = df['low'].values
    
        oi_change = np.diff(oi, prepend=oi[0])
    
        # 价格方向：用close相对于(high+low)/2的位置判断多空方向
        mid_price = (high + low) / 2.0
        price_direction = np.sign(close - mid_price)
        # 当close == mid时，用close变化方向替代
        close_diff = np.diff(close, prepend=close[0])
        mask_zero = price_direction == 0
        price_direction[mask_zero] = np.sign(close_diff[mask_zero])
    
        # 识别主力行为：成交量超过滚动中位数*1.5 且 持仓变化绝对值超过滚动中位数*1.5
        n = len(volume)
        lookback = 48  # 约2天的30分钟K线
    
        vol_series = pd.Series(volume)
        oi_chg_series = pd.Series(np.abs(oi_change))
    
        vol_median = vol_series.rolling(window=lookback, min_periods=8).median()
        oi_chg_median = oi_chg_series.rolling(window=lookback, min_periods=8).median()
    
        # 主力大单标识：成交量和持仓变化同时放大
        is_big_order = (vol_series > vol_median * 1.3) & (oi_chg_series > oi_chg_median * 1.3)
        is_big_order = is_big_order.values.astype(float)
    
        # 主力资金流方向：
        # 持仓增加+价格上涨 = 多头主力建仓(+)
        # 持仓增加+价格下跌 = 空头主力建仓(-)
        # 持仓减少+价格上涨 = 空头主力平仓(+)  
        # 持仓减少+价格下跌 = 多头主力平仓(-)
        # 综合方向 = sign(oi_change) * price_direction（建仓跟随方向）
        # 但平仓时方向相反，统一用 price_direction * |oi_change| 更合理
    
        # 用成交量归一化的持仓变化作为强度
        vol_safe = np.where(volume > 0, volume, 1.0)
        flow_intensity = (oi_change / vol_safe) * price_direction
    
        # 仅保留大单信号，小单置零
        smart_flow = flow_intensity * is_big_order
    
        # 指数加权累积，半衰期约16根K线（8小时）
        smart_flow_series = pd.Series(smart_flow, index=df.index)
    
        # 用EWM累积主力资金流
        decay = 16
        ewm_flow = smart_flow_series.ewm(halflife=decay, min_periods=8).mean()
    
        # 标准化：用滚动标准差归一化
        flow_std = ewm_flow.rolling(window=lookback * 2, min_periods=16).std()
        flow_std = flow_std.replace(0, np.nan)
    
        factor = ewm_flow / flow_std
    
        return factor

DISCOVERED_FACTORS['smart_money_flow_intensity'] = smart_money_flow_intensity


def intraday_hour_seasonality_zscore(df):
    """基于30分钟K线所处的日内时段（上午/下午/夜盘）与周内交易日的交互效应，计算该时段历史收益率的季节性Z-score，捕捉黄金期货在特定星期几特定时段的系统性动量或反转模式。
    avg |IC| = 0.0282
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['ret'] = df['close'].pct_change()
    
        # 从index或行号推断日内时段编号（每天约有多根30min K线）
        # 黄金期货交易时段：夜盘21:00-02:30(12根), 日盘09:00-10:15(3根), 10:30-11:30(2根), 13:30-15:00(3根)
        # 共约20根30min bar per day，用模运算近似分配时段ID
    
        # 构造日期列用于分组
        if isinstance(df.index, pd.DatetimeIndex):
            dt_index = df.index
        else:
            dt_index = pd.to_datetime(df.index)
    
        df['date'] = dt_index.date
        df['hour'] = dt_index.hour
        df['minute'] = dt_index.minute
        df['dow'] = dt_index.dayofweek  # 0=Mon ... 4=Fri
    
        # 划分时段：夜盘(21-02), 上午盘(9-11:30), 下午盘(13:30-15)
        def get_session(row):
            h = row['hour']
            if h >= 21 or h < 3:
                return 0  # 夜盘
            elif 9 <= h < 12:
                return 1  # 上午盘
            elif 13 <= h < 16:
                return 2  # 下午盘
            else:
                return -1  # 非交易时段（不应出现）
    
        df['session'] = df.apply(get_session, axis=1)
    
        # 构造交互键: dow * 3 + session -> 最多 5*3=15 个组合
        df['dow_session'] = df['dow'] * 10 + df['session']
    
        # 对每个 dow_session 组合，用expanding window计算历史均值和标准差
        # 然后计算当前收益相对历史的z-score
        lookback = 60  # 至少需要60个同类样本才有统计意义
    
        factor = pd.Series(np.nan, index=df.index)
    
        grouped = df.groupby('dow_session')
    
        for key, grp in grouped:
            if len(grp) < 10:
                continue
        
            ret_vals = grp['ret'].values
        
            # 使用expanding mean/std，但至少需要lookback个样本
            expanding_mean = pd.Series(ret_vals, index=grp.index).expanding(min_periods=20).mean()
            expanding_std = pd.Series(ret_vals, index=grp.index).expanding(min_periods=20).std()
        
            # 用滚动窗口替代expanding以适应regime变化
            rolling_mean = pd.Series(ret_vals, index=grp.index).rolling(window=lookback, min_periods=20).mean()
            rolling_std = pd.Series(ret_vals, index=grp.index).rolling(window=lookback, min_periods=20).std()
        
            # 季节性因子 = 历史同类时段的平均收益 / 波动率（即夏普化的季节性信号）
            # shift(1) 避免前视偏差
            seasonal_signal = rolling_mean.shift(1) / rolling_std.shift(1).replace(0, np.nan)
        
            factor.loc[grp.index] = seasonal_signal
    
        # 对因子做整体标准化
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        # 用全局rolling z-score进一步标准化，消除量纲差异
        overall_mean = factor.rolling(240, min_periods=60).mean()
        overall_std = factor.rolling(240, min_periods=60).std()
        factor = (factor - overall_mean) / overall_std.replace(0, np.nan)
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['intraday_hour_seasonality_zscore'] = intraday_hour_seasonality_zscore


def weekly_trend_intraday_alignment(df):
    """将周线级别趋势强度（通过120根30分钟K线约一周的线性回归斜率标准化）映射到短周期，衡量当前30分钟价格动量与长周期趋势方向的一致性程度，一致性越高因子值越大，捕捉顺势延续机会。
    avg |IC| = 0.0262
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 长周期参数：120根30min K线 ≈ 1周交易（约5天 * 24根/天，考虑夜盘）
        long_window = 120
        # 短周期参数：8根30min K线 ≈ 4小时
        short_window = 8
    
        # 长周期线性回归斜率（标准化）
        long_slope = np.full(n, np.nan)
        x_long = np.arange(long_window, dtype=float)
        x_long_demean = x_long - x_long.mean()
        x_long_var = np.sum(x_long_demean ** 2)
    
        for i in range(long_window - 1, n):
            y = close[i - long_window + 1: i + 1]
            y_demean = y - y.mean()
            slope = np.sum(x_long_demean * y_demean) / x_long_var
            # 用价格均值标准化斜率，得到无量纲趋势强度
            price_mean = y.mean()
            if price_mean != 0:
                long_slope[i] = slope / price_mean * long_window
            else:
                long_slope[i] = 0.0
    
        # 短周期动量：短窗口收益率（对数收益）
        short_mom = np.full(n, np.nan)
        for i in range(short_window, n):
            if close[i - short_window] > 0:
                short_mom[i] = np.log(close[i] / close[i - short_window])
    
        # 短周期成交量相对强度：当前短窗口均量 / 长窗口均量
        vol_ratio = np.full(n, np.nan)
        for i in range(long_window - 1, n):
            long_avg_vol = np.mean(volume[i - long_window + 1: i + 1])
            short_avg_vol = np.mean(volume[max(0, i - short_window + 1): i + 1])
            if long_avg_vol > 0:
                vol_ratio[i] = short_avg_vol / long_avg_vol
            else:
                vol_ratio[i] = 1.0
    
        # 核心因子：短周期动量与长周期趋势方向的一致性，用成交量放大
        # 当短周期动量方向与长周期趋势一致时，因子值为正且较大
        # 不一致时因子值为负（逆势信号）
        factor = np.full(n, np.nan)
        for i in range(long_window - 1, n):
            if np.isnan(long_slope[i]) or np.isnan(short_mom[i]) or np.isnan(vol_ratio[i]):
                continue
            # 一致性 = 短动量 * sign(长趋势) * 长趋势强度绝对值 * 成交量比率
            trend_strength = np.abs(long_slope[i])
            trend_sign = np.sign(long_slope[i])
            alignment = short_mom[i] * trend_sign
            factor[i] = alignment * trend_strength * vol_ratio[i]
    
        # 用滚动z-score标准化，避免量纲问题
        factor_series = pd.Series(factor, index=df.index)
        roll_mean = factor_series.rolling(window=240, min_periods=60).mean()
        roll_std = factor_series.rolling(window=240, min_periods=60).std()
        factor_series = (factor_series - roll_mean) / roll_std.replace(0, np.nan)
    
        return factor_series

DISCOVERED_FACTORS['weekly_trend_intraday_alignment'] = weekly_trend_intraday_alignment


def intraday_session_momentum_dispersion(df):
    """计算每日不同交易时段（早盘、午盘、夜盘）的动量离散度，捕捉黄金期货因时段流动性和参与者结构差异导致的日内动量分布不均衡效应
    avg |IC| = 0.2365
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['returns'] = df['close'].pct_change()
    
        # 提取时间信息，根据30分钟K线的时间戳判断交易时段
        # SHFE黄金期货交易时段：
        # 夜盘: 21:00-02:30 (次日)
        # 早盘: 09:00-11:30
        # 午盘: 13:30-15:00
    
        if hasattr(df.index, 'hour'):
            hour = df.index.hour
            minute = df.index.minute
        else:
            # 如果index不是datetime，尝试用位置推断
            # 假设每天有固定bar数，用模运算近似
            df['bar_idx'] = range(len(df))
            # 无法推断时段，退回到用bar在日内的相对位置
            hour = None
    
        if hour is not None:
            time_val = hour * 100 + minute
            # 夜盘: 21:00 - 02:30 => hour>=21 or hour<3
            # 早盘: 09:00 - 11:30 => 9<=hour<12 (含11:30的bar)
            # 午盘: 13:30 - 15:00 => 13<=hour<15
            conditions = [
                (hour >= 21) | (hour < 3),   # 夜盘
                (hour >= 9) & (hour < 12),    # 早盘
                (hour >= 13) & (hour < 16),   # 午盘
            ]
            choices = [0, 1, 2]
            df['session'] = np.select(conditions, choices, default=-1)
        
            # 构建交易日标识：夜盘归属下一个自然日
            trade_date = df.index.date
            df['trade_date'] = pd.Series(trade_date, index=df.index)
            # 夜盘的trade_date应该归到下一个交易日
            night_mask = df['session'] == 0
            df.loc[night_mask, 'trade_date'] = pd.to_datetime(
                df.loc[night_mask, 'trade_date']
            ) + pd.Timedelta(days=1)
            df['trade_date'] = df['trade_date'].astype(str)
        else:
            # fallback: 每天约16根30min bar，用rolling近似
            df['session'] = df['bar_idx'] % 16
            df['session'] = df['session'].apply(lambda x: 0 if x < 7 else (1 if x < 11 else 2))
            df['trade_date'] = (df['bar_idx'] // 16).astype(str)
    
        # 计算每个交易日每个时段的累计收益
        session_ret = df.groupby(['trade_date', 'session'])['returns'].sum()
        session_ret = session_ret.unstack(level='session')
    
        # 动量离散度 = 各时段收益的标准差 / (各时段收益绝对值的均值 + eps)
        # 高离散度意味着不同时段动量方向/幅度差异大
        eps = 1e-10
        dispersion = session_ret.std(axis=1) / (session_ret.abs().mean(axis=1) + eps)
    
        # 用符号加权：如果日内总收益为正，离散度取正；否则取负
        daily_total_ret = session_ret.sum(axis=1)
        signed_dispersion = dispersion * np.sign(daily_total_ret)
    
        # 映射回原始30min bar
        df['trade_date_str'] = df['trade_date'].astype(str)
        dispersion_map = signed_dispersion.to_dict()
        df['factor_daily'] = df['trade_date_str'].map(dispersion_map)
    
        # 用5日EMA平滑以增强信号稳定性
        daily_factor = df.groupby('trade_date_str')['factor_daily'].first().dropna()
        smoothed = daily_factor.ewm(span=5, min_periods=1).mean()
        smoothed_map = smoothed.to_dict()
        df['factor'] = df['trade_date_str'].map(smoothed_map)
    
        factor_series = df['factor'].copy()
        factor_series.index = df.index
        return factor_series

DISCOVERED_FACTORS['intraday_session_momentum_dispersion'] = intraday_session_momentum_dispersion


def gold_session_seasonality_score(df):
    """综合月份效应、星期效应和日内时段效应，基于历史收益率的季节性均值对当前K线进行评分，捕捉黄金期货在特定时间维度上的统计性价格偏差规律。
    avg |IC| = 0.0329
    """
        import numpy as np
        import pandas as pd

        # 确保索引为 DatetimeIndex
        idx = pd.to_datetime(df.index)

        close = df['close']
        ret = close.pct_change()

        # 提取时间维度特征
        month = idx.month          # 1~12，月份效应
        dayofweek = idx.dayofweek  # 0=周一 ... 4=周五，周内效应
        hour = idx.hour            # 小时，时段效应（30min K线）

        # 将时间特征打包进临时 DataFrame
        tmp = pd.DataFrame({
            'ret': ret.values,
            'month': month,
            'dayofweek': dayofweek,
            'hour': hour,
        }, index=idx)

        # ----------------------------------------------------------------
        # 1. 月份效应得分：用扩展窗口（expanding）计算各月历史平均收益率
        #    避免未来函数：先 shift(1) 再 groupby 累计均值
        # ----------------------------------------------------------------
        tmp['ret_lag'] = tmp['ret'].shift(1)

        # expanding 月均值：对每个月份，截止当前行之前的所有同月收益均值
        month_mean = (
            tmp.groupby('month')['ret_lag']
            .transform(lambda x: x.expanding().mean())
        )

        # ----------------------------------------------------------------
        # 2. 星期效应得分：同理，各星期几的历史平均收益率
        # ----------------------------------------------------------------
        dow_mean = (
            tmp.groupby('dayofweek')['ret_lag']
            .transform(lambda x: x.expanding().mean())
        )

        # ----------------------------------------------------------------
        # 3. 时段效应得分：各小时（30min K线取整点/半点）历史平均收益率
        # ----------------------------------------------------------------
        hour_mean = (
            tmp.groupby('hour')['ret_lag']
            .transform(lambda x: x.expanding().mean())
        )

        # ----------------------------------------------------------------
        # 4. 对三个分项分别做截面标准化（rolling zscore，窗口240根K线≈5个交易日）
        #    使三个维度量纲一致后合成综合得分
        # ----------------------------------------------------------------
        def rolling_zscore(s, window=240):
            m = s.rolling(window, min_periods=30).mean()
            sd = s.rolling(window, min_periods=30).std()
            return (s - m) / (sd + 1e-10)

        z_month = rolling_zscore(month_mean.fillna(0))
        z_dow   = rolling_zscore(dow_mean.fillna(0))
        z_hour  = rolling_zscore(hour_mean.fillna(0))

        # ----------------------------------------------------------------
        # 5. 加权合成：月份效应权重略高（持续性更强），时段效应其次
        #    权重可根据回测结果调整
        # ----------------------------------------------------------------
        factor = 0.40 * z_month + 0.30 * z_dow + 0.30 * z_hour

        factor = pd.Series(factor.values, index=df.index, name='gold_session_seasonality_score')
        return factor

DISCOVERED_FACTORS['gold_session_seasonality_score'] = gold_session_seasonality_score


def oi_entropy_regime(df):
    """用持仓量变化率的滚动信息熵衡量市场参与者行为的有序/无序程度，低熵意味着持仓变化集中于单一方向（趋势确认），高熵意味着多空博弈混乱（反转信号），结合价格动量方向生成复合信号
    avg |IC| = 0.0314
    """
        import numpy as np
        import pandas as pd
    
        oi = df['open_interest'].copy()
        close = df['close'].copy()
    
        # 持仓量变化
        oi_change = oi.diff()
    
        # 将OI变化离散化为若干bin，计算滚动窗口内的信息熵
        window = 20
        n_bins = 5
    
        def rolling_entropy(series, window, n_bins):
            entropy = pd.Series(np.nan, index=series.index)
            arr = series.values
            for i in range(window - 1, len(arr)):
                segment = arr[i - window + 1: i + 1]
                valid = segment[~np.isnan(segment)]
                if len(valid) < window // 2:
                    continue
                # 等频分箱
                counts, _ = np.histogram(valid, bins=n_bins)
                probs = counts / counts.sum()
                probs = probs[probs > 0]
                ent = -np.sum(probs * np.log2(probs))
                entropy.iloc[i] = ent
            return entropy
    
        oi_entropy = rolling_entropy(oi_change, window, n_bins)
    
        # 归一化熵到[0,1]，最大熵为log2(n_bins)
        max_entropy = np.log2(n_bins)
        norm_entropy = oi_entropy / max_entropy
    
        # 价格动量方向
        price_mom = close.pct_change(window)
    
        # OI净方向性：窗口内正变化占比 - 0.5，衡量持仓变化的偏向
        oi_pos_ratio = oi_change.rolling(window).apply(lambda x: np.nanmean(x > 0), raw=True) - 0.5
    
        # 复合因子逻辑：
        # 低熵 + OI方向与价格同向 → 趋势确认（正值）
        # 高熵 → 混乱状态，取反价格动量（反转信号）
        # 用 (1 - norm_entropy) 作为趋势确认权重，norm_entropy 作为反转权重
    
        trend_component = (1 - norm_entropy) * np.sign(price_mom) * np.sign(oi_pos_ratio) * np.abs(oi_pos_ratio)
        revert_component = norm_entropy * (-price_mom / close.rolling(window).std().replace(0, np.nan))
    
        factor = trend_component + revert_component
    
        # 标准化
        factor = (factor - factor.rolling(60, min_periods=20).mean()) / factor.rolling(60, min_periods=20).std().replace(0, np.nan)
    
        factor.name = 'oi_entropy_regime'
        return factor

DISCOVERED_FACTORS['oi_entropy_regime'] = oi_entropy_regime


def weekday_session_vol_anomaly(df):
    """计算当前周内日×盘中时段组合下的成交量相对于该组合历史均值的异常度，捕捉黄金期货在特定"星期几+时段"组合中流动性异常带来的价格预测信号
    avg |IC| = 0.0216
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['datetime'] = pd.to_datetime(df.index if isinstance(df.index, pd.DatetimeIndex) else df['datetime'] if 'datetime' in df.columns else df.index)
    
        # 提取周内日 (0=Monday, 4=Friday)
        df['weekday'] = df['datetime'].dt.weekday
    
        # 提取小时，划分盘中时段：
        # 0=夜盘(21-23,0-2), 1=早盘(9-10:15), 2=午前盘(10:30-11:30), 3=午后盘(13:30-15:00)
        hour = df['datetime'].dt.hour
        df['session'] = 0  # default夜盘
        df.loc[(hour >= 9) & (hour < 10), 'session'] = 1
        df.loc[(hour == 10), 'session'] = 2
        df.loc[(hour == 11), 'session'] = 2
        df.loc[(hour >= 13) & (hour < 15), 'session'] = 3
        df.loc[(hour >= 21) | (hour < 3), 'session'] = 0
    
        # 构造组合键
        df['wd_sess'] = df['weekday'].astype(str) + '_' + df['session'].astype(str)
    
        # 对每个组合计算滚动均值和标准差（用expanding with min 20 observations来避免前视偏差）
        # 为了效率，按组合分组后用expanding统计
        df['vol_log'] = np.log1p(df['volume'])
    
        # 使用groupby + expanding来计算历史均值和标准差
        grouped = df.groupby('wd_sess')['vol_log']
        df['hist_mean'] = grouped.transform(lambda x: x.expanding(min_periods=20).mean().shift(1))
        df['hist_std'] = grouped.transform(lambda x: x.expanding(min_periods=20).std().shift(1))
    
        # 成交量异常度 z-score
        vol_zscore = (df['vol_log'] - df['hist_mean']) / df['hist_std'].replace(0, np.nan)
    
        # 结合收益率方向：异常高成交量时的价格变动更有延续性
        ret = df['close'].pct_change()
    
        # 因子 = vol_zscore * sign(ret)，异常放量配合方向
        factor = vol_zscore * np.sign(ret)
    
        # 用短期EMA平滑避免噪声
        factor = factor.ewm(span=3, min_periods=1).mean()
    
        factor.index = df.index if not isinstance(df.index, pd.RangeIndex) else df.index
    
        return factor.rename('weekday_session_vol_anomaly')

DISCOVERED_FACTORS['weekday_session_vol_anomaly'] = weekday_session_vol_anomaly


def vwap_band_reversion_score(df):
    """计算价格相对于成交量加权均价(VWAP)的标准化偏离度，并结合持仓量变化方向判断偏离是否伴随筹码堆积，从而度量均值回归压力——价格大幅偏离VWAP且持仓量增加时，回归压力更强。
    avg |IC| = 0.0320
    """
        import numpy as np
        import pandas as pd
    
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    
        # 滚动VWAP（20根K线，即10小时窗口）
        window_vwap = 20
        cum_tp_vol = (typical_price * df['volume']).rolling(window=window_vwap, min_periods=10).sum()
        cum_vol = df['volume'].rolling(window=window_vwap, min_periods=10).sum()
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    
        # 价格偏离VWAP的百分比
        deviation = (df['close'] - vwap) / vwap.replace(0, np.nan)
    
        # 用更长窗口（40根K线）计算偏离度的z-score，标准化偏离幅度
        window_z = 40
        dev_mean = deviation.rolling(window=window_z, min_periods=20).mean()
        dev_std = deviation.rolling(window=window_z, min_periods=20).std()
        z_deviation = (deviation - dev_mean) / dev_std.replace(0, np.nan)
    
        # 持仓量变化率（短期5根 vs 中期20根均值）
        oi_short = df['open_interest'].rolling(window=5, min_periods=3).mean()
        oi_long = df['open_interest'].rolling(window=20, min_periods=10).mean()
        oi_expansion = (oi_short - oi_long) / oi_long.replace(0, np.nan)
    
        # 持仓扩张时偏离更有意义：用sigmoid函数将oi_expansion映射到[1, 2]作为权重
        oi_weight = 1.0 + 1.0 / (1.0 + np.exp(-50.0 * oi_expansion))
    
        # 均值回归得分：z_deviation取负（偏离越大，回归力越强），乘以持仓权重
        # 正值 -> 预期价格上涨（超卖回归）；负值 -> 预期价格下跌（超买回归）
        raw_score = -z_deviation * oi_weight
    
        # 最终用tanh压缩到[-1,1]区间，避免极端值
        factor = np.tanh(raw_score / 3.0)
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
        factor.name = 'vwap_band_reversion_score'
    
        return factor

DISCOVERED_FACTORS['vwap_band_reversion_score'] = vwap_band_reversion_score


def vol_surge_price_persistence(df):
    """衡量成交量异常放大时的价格变动在后续K线中的持续性，持续为正表示放量为知情交易（趋势延续），持续为负表示放量为噪音交易（价格回归）
    avg |IC| = 0.0296
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        vol_lookback = 20
        persist_window = 5
        factor_window = 30
    
        # Rolling volume mean and std for z-score
        vol_series = pd.Series(volume)
        vol_ma = vol_series.rolling(vol_lookback, min_periods=10).mean().values
        vol_std = vol_series.rolling(vol_lookback, min_periods=10).std().values
    
        # Volume z-score
        vol_z = np.full(n, np.nan)
        valid = vol_std > 0
        vol_z[valid] = (volume[valid] - vol_ma[valid]) / vol_std[valid]
    
        # Price return at each bar
        ret = np.full(n, np.nan)
        ret[1:] = close[1:] / close[:-1] - 1.0
    
        # Forward return over persist_window bars (does the move persist?)
        fwd_ret = np.full(n, np.nan)
        for i in range(n - persist_window):
            fwd_ret[i] = close[i + persist_window] / close[i] - 1.0
    
        # Persistence signal: sign agreement between surge-bar return and forward return
        # weighted by volume z-score magnitude (only consider surges z > 1)
        surge_threshold = 1.0
        persistence_raw = np.full(n, np.nan)
    
        for i in range(1, n - persist_window):
            if not np.isnan(vol_z[i]) and vol_z[i] > surge_threshold:
                if abs(ret[i]) > 1e-10:
                    # Normalize: forward return direction relative to surge bar direction
                    persistence_raw[i] = np.sign(ret[i]) * fwd_ret[i] * vol_z[i]
    
        # Rolling average of persistence signals over factor_window
        # Use expanding count to handle sparse surge events
        persistence_series = pd.Series(persistence_raw)
    
        # Exponentially weighted mean of non-NaN persistence values
        factor = np.full(n, np.nan)
        alpha = 2.0 / (factor_window + 1)
        ema_val = 0.0
        ema_weight = 0.0
        initialized = False
    
        for i in range(n):
            ema_val *= (1 - alpha)
            ema_weight *= (1 - alpha)
            if not np.isnan(persistence_raw[i]):
                ema_val += alpha * persistence_raw[i]
                ema_weight += alpha
                initialized = True
            if initialized and ema_weight > 1e-10:
                factor[i] = ema_val / ema_weight
    
        # Standardize with rolling z-score for stationarity
        factor_series = pd.Series(factor, index=df.index)
        f_ma = factor_series.rolling(60, min_periods=20).mean()
        f_std = factor_series.rolling(60, min_periods=20).std()
        result = (factor_series - f_ma) / f_std.replace(0, np.nan)
    
        return result

DISCOVERED_FACTORS['vol_surge_price_persistence'] = vol_surge_price_persistence


def long_short_trend_resonance(df):
    """长周期(120bar)线性回归趋势斜率与短周期(12bar)动量的共振强度，当短期动量与长期趋势方向一致且长期趋势高效时信号放大，捕捉跨周期趋势延续机会
    avg |IC| = 0.0238
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        n = len(close)
    
        long_win = 120   # ~10 trading days of 30-min bars
        short_win = 12   # ~1 trading session
    
        # Long-cycle: linear regression slope normalized by price level
        long_slope = np.full(n, np.nan)
        x_long = np.arange(long_win, dtype=float)
        x_long_demean = x_long - x_long.mean()
        x_long_var = np.sum(x_long_demean ** 2)
    
        for i in range(long_win - 1, n):
            y = close[i - long_win + 1: i + 1]
            y_demean = y - y.mean()
            slope = np.sum(x_long_demean * y_demean) / x_long_var
            # Normalize slope by average price to get relative trend strength
            long_slope[i] = slope / y.mean() * long_win  # total relative drift
    
        # Long-cycle trend efficiency: net move / total path (fractal efficiency)
        long_efficiency = np.full(n, np.nan)
        for i in range(long_win - 1, n):
            seg = close[i - long_win + 1: i + 1]
            net_move = abs(seg[-1] - seg[0])
            total_path = np.sum(np.abs(np.diff(seg)))
            long_efficiency[i] = net_move / total_path if total_path > 0 else 0
    
        # Short-cycle momentum: normalized return over short window
        short_mom = np.full(n, np.nan)
        for i in range(short_win, n):
            if close[i - short_win] != 0:
                short_mom[i] = (close[i] - close[i - short_win]) / close[i - short_win]
    
        # Resonance: short momentum * sign-aligned long slope * long efficiency
        # When short and long trends agree AND long trend is efficient, signal amplifies
        raw = np.full(n, np.nan)
        for i in range(n):
            if not (np.isnan(long_slope[i]) or np.isnan(short_mom[i]) or np.isnan(long_efficiency[i])):
                # Signed resonance: positive when short aligns with long
                raw[i] = short_mom[i] * np.sign(long_slope[i]) * long_efficiency[i] * abs(long_slope[i])
    
        # Rolling z-score for stationarity (60-bar window)
        z_win = 60
        factor = np.full(n, np.nan)
        raw_s = pd.Series(raw)
        roll_mean = raw_s.rolling(z_win, min_periods=30).mean()
        roll_std = raw_s.rolling(z_win, min_periods=30).std()
    
        for i in range(n):
            if not np.isnan(roll_std.iloc[i]) and roll_std.iloc[i] > 1e-12:
                factor[i] = (raw[i] - roll_mean.iloc[i]) / roll_std.iloc[i]
    
        return pd.Series(factor, index=df.index, name='long_short_trend_resonance')

DISCOVERED_FACTORS['long_short_trend_resonance'] = long_short_trend_resonance


def trend_projection_residual_mom(df):
    """用长周期(120bar)线性回归提取趋势后，计算短周期(8bar)残差动量并按趋势方向加权，捕捉长趋势框架下短期偏离的修复或加速信号
    avg |IC| = 0.0212
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        oi = df['open_interest'].values
        n = len(close)
    
        long_window = 120
        short_window = 8
    
        # Rolling linear regression over long window to extract trend
        trend_value = np.full(n, np.nan)
        trend_slope = np.full(n, np.nan)
    
        x = np.arange(long_window, dtype=float)
        x_mean = x.mean()
        x_var = ((x - x_mean) ** 2).sum()
    
        for i in range(long_window - 1, n):
            y = close[i - long_window + 1: i + 1]
            y_mean = y.mean()
            slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
            intercept = y_mean - slope * x_mean
            trend_value[i] = intercept + slope * (long_window - 1)
            trend_slope[i] = slope
    
        # Residual: deviation of price from long-term trend
        residual = close - trend_value
    
        # Short-term momentum of residual (8-bar rate of change)
        residual_mom = np.full(n, np.nan)
        for i in range(short_window, n):
            if not np.isnan(residual[i]) and not np.isnan(residual[i - short_window]):
                residual_mom[i] = residual[i] - residual[i - short_window]
    
        # Normalize residual momentum by rolling std of residuals (40-bar)
        norm_window = 40
        residual_series = pd.Series(residual)
        res_std = residual_series.rolling(window=norm_window, min_periods=20).std().values
        res_std = np.where(res_std < 1e-8, np.nan, res_std)
    
        norm_res_mom = residual_mom / res_std
    
        # Trend slope normalized
        slope_series = pd.Series(trend_slope)
        slope_std = slope_series.rolling(window=norm_window, min_periods=20).std().values
        slope_std = np.where(slope_std < 1e-8, np.nan, slope_std)
        norm_slope = trend_slope / slope_std
    
        # OI change confirmation: rising OI amplifies signal
        oi_change = pd.Series(oi).pct_change(short_window).values
        oi_factor = 1.0 + np.clip(oi_change * 10, -0.5, 0.5)
    
        # Final factor: residual momentum weighted by trend-alignment and OI
        # When residual_mom aligns with trend_slope direction -> amplified (trend continuation)
        # When they diverge -> dampened
        alignment = np.tanh(norm_slope * 0.5)  # soft trend direction [-1, 1]
    
        # Core signal: short-term residual momentum, modulated by long-term trend context
        # Positive alignment + positive residual_mom = strong buy (trend accel)
        # Positive alignment + negative residual_mom = dampened (pullback in uptrend, potential buy)
        raw_factor = norm_res_mom * (1.0 + alignment * np.sign(norm_res_mom) * 0.5) * oi_factor
    
        # Clip extremes
        factor = np.clip(raw_factor, -5, 5)
    
        return pd.Series(factor, index=df.index, name='trend_projection_residual_mom')

DISCOVERED_FACTORS['trend_projection_residual_mom'] = trend_projection_residual_mom


def multi_timeframe_trend_pressure(df):
    """将长周期（4小时/8根K线）的趋势方向和强度映射到短周期（30分钟），通过长周期EMA斜率与短周期价格偏离的交互来捕捉长短周期共振或背离的压力信号
    avg |IC| = 0.0359
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
        oi = df['open_interest'].copy()
    
        # 长周期参数：8根30分钟K线 = 4小时
        long_period = 8
        # 中周期参数：16根 = 8小时（日内趋势）
        mid_period = 16
    
        # 构造长周期EMA作为趋势锚点
        ema_long = close.ewm(span=mid_period, adjust=False).mean()
        ema_mid = close.ewm(span=long_period, adjust=False).mean()
    
        # 长周期趋势斜率（用长周期EMA的变化率衡量趋势方向和强度）
        long_trend_slope = ema_long.diff(long_period) / ema_long.shift(long_period)
    
        # 短周期价格相对长周期EMA的偏离（标准化）
        deviation = (close - ema_long) / ema_long
    
        # 短周期价格相对中周期EMA的偏离
        short_deviation = (close - ema_mid) / ema_mid
    
        # 长周期趋势强度：用rolling窗口内收盘价方向一致性
        close_diff = close.diff()
        trend_consistency = close_diff.rolling(long_period).apply(
            lambda x: np.sum(np.sign(x[~np.isnan(x)])) / len(x[~np.isnan(x)]) if len(x[~np.isnan(x)]) > 0 else 0,
            raw=True
        )
    
        # 持仓量在长周期内的变化方向（资金流入流出确认趋势）
        oi_change_long = (oi - oi.shift(long_period)) / (oi.shift(long_period) + 1e-10)
    
        # 成交量在长周期内的相对强度
        vol_ratio = volume / volume.rolling(mid_period).mean()
        vol_ratio = vol_ratio.fillna(1.0)
    
        # 核心因子：长周期趋势斜率 × 短周期偏离方向一致性 × 持仓确认
        # 当长短周期方向一致且持仓确认时，信号增强
        # 当长短周期背离时，信号减弱或反转
    
        # 长短周期共振信号
        trend_alignment = long_trend_slope * short_deviation
    
        # 持仓量确认权重：持仓变化方向与趋势一致时加权
        oi_confirm = np.sign(oi_change_long) * np.sign(long_trend_slope)
        oi_weight = 1.0 + 0.5 * oi_confirm  # 确认时1.5，不确认时0.5
    
        # 最终因子：趋势共振 × 一致性 × 持仓确认 × 成交量强度
        factor = trend_alignment * trend_consistency * oi_weight * np.log1p(vol_ratio)
    
        # Z-score标准化（rolling）
        roll_mean = factor.rolling(mid_period * 2, min_periods=long_period).mean()
        roll_std = factor.rolling(mid_period * 2, min_periods=long_period).std()
        factor_zscore = (factor - roll_mean) / (roll_std + 1e-10)
    
        # 截断极端值
        factor_zscore = factor_zscore.clip(-5, 5)
    
        return factor_zscore

DISCOVERED_FACTORS['multi_timeframe_trend_pressure'] = multi_timeframe_trend_pressure


def price_oi_centroid_dev(df):
    """当前价格偏离持仓量变化加权质心价格的标准化程度，质心代表新仓位建立的共识价值中枢，偏离越大越倾向均值回归
    avg |IC| = 0.0266
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        oi = df['open_interest'].values
        volume = df['volume'].values
    
        typical_price = (high + low + close) / 3.0
        oi_change = np.diff(oi, prepend=oi[0])
        oi_change_abs = np.abs(oi_change) + 1e-9  # avoid division by zero
    
        lookback = 48  # ~1.5 trading days on 30min bars
        n = len(close)
        factor = np.full(n, np.nan)
    
        for i in range(lookback, n):
            window_tp = typical_price[i - lookback:i + 1]
            window_oi_chg = oi_change_abs[i - lookback:i + 1]
            window_vol = volume[i - lookback:i + 1]
        
            # Composite weight: abs OI change * volume -> emphasize bars where positions are actively built with participation
            composite_w = window_oi_chg * (window_vol + 1e-9)
        
            # Exponential recency decay
            decay = np.exp(np.linspace(-2, 0, len(window_tp)))
            weights = composite_w * decay
            w_sum = weights.sum()
        
            if w_sum < 1e-12:
                continue
        
            # OI-volume weighted centroid price
            centroid = np.sum(weights * window_tp) / w_sum
        
            # Weighted std for normalization
            var = np.sum(weights * (window_tp - centroid) ** 2) / w_sum
            std = np.sqrt(var) if var > 0 else 1e-9
        
            # Standardized deviation from centroid
            z = (close[i] - centroid) / std
        
            # Apply soft saturation to avoid extreme outliers
            factor[i] = -np.tanh(z / 2.5)  # negative: high z -> expect reversion downward
    
        return pd.Series(factor, index=df.index, name='price_oi_centroid_dev')

DISCOVERED_FACTORS['price_oi_centroid_dev'] = price_oi_centroid_dev


def rv_term_structure_slope(df):
    """计算不同窗口（短5、中15、长40期）已实现波动率构成的波动率期限结构斜率，捕捉波动率锥的陡峭程度——正值表示短期波动率高于长期（波动率倒挂，预示均值回归），负值表示正常期限结构（趋势延续）。
    avg |IC| = 0.0215
    """
        import numpy as np
        import pandas as pd
    
        log_ret = np.log(df['close'] / df['close'].shift(1))
    
        # Parkinson estimator for more efficient realized vol at each window
        log_hl = np.log(df['high'] / df['low'])
        parkinson_var = log_hl ** 2 / (4.0 * np.log(2.0))
    
        # Realized vol at three horizons (annualized by sqrt of periods)
        rv_short = parkinson_var.rolling(window=5, min_periods=4).mean().apply(np.sqrt)
        rv_mid = parkinson_var.rolling(window=15, min_periods=10).mean().apply(np.sqrt)
        rv_long = parkinson_var.rolling(window=40, min_periods=25).mean().apply(np.sqrt)
    
        # Term structure slope via OLS-style: fit rv against horizon rank [0,1,2]
        # slope = weighted combination capturing curvature too
        # Normalized slope: (rv_short - rv_long) / rv_mid to capture relative steepness
        # This is more robust than raw difference
    
        raw_slope = (rv_short - rv_long) / rv_mid.replace(0, np.nan)
    
        # Add curvature info: is mid above or below interpolated midpoint?
        # curvature = rv_mid - 0.5*(rv_short + rv_long), normalized
        curvature = (rv_mid - 0.5 * (rv_short + rv_long)) / rv_mid.replace(0, np.nan)
    
        # Composite: slope dominates, curvature adds info about vol smile shape
        # Positive slope (short > long) with negative curvature = strong inversion signal
        factor = raw_slope - 0.5 * curvature
    
        # Smooth slightly to reduce noise (3-bar EMA)
        factor = factor.ewm(span=3, min_periods=2).mean()
    
        factor.name = 'rv_term_structure_slope'
        return factor

DISCOVERED_FACTORS['rv_term_structure_slope'] = rv_term_structure_slope


def weekly_hour_momentum_cycle(df):
    """基于周内效应与日内时段效应的交互，捕捉黄金期货在特定"星期几×盘中时段"组合下的历史动量模式，利用该组合的历史收益均值作为条件期望信号
    avg |IC| = 0.0255
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
    
        # 解析时间特征
        idx = pd.to_datetime(df.index) if not isinstance(df.index, pd.DatetimeIndex) else df.index
    
        # 星期几 (0=Monday, 4=Friday)
        dow = idx.dayofweek
    
        # 日内时段分桶: 将交易时间分为4个时段
        # 夜盘(21-23): 0, 夜盘(0-2:30): 1, 上午盘(9-11:30): 2, 下午盘(13:30-15): 3
        hour = idx.hour
        session = pd.Series(np.zeros(len(df), dtype=int), index=df.index)
        session[(hour >= 21) & (hour <= 23)] = 0
        session[(hour >= 0) & (hour < 3)] = 1
        session[(hour >= 9) & (hour < 12)] = 2
        session[(hour >= 12) & (hour < 16)] = 3
    
        # 构造组合键: dow * 4 + session, 共 5*4=20 个桶
        combo_key = pd.Series(dow * 4 + session.values, index=df.index)
    
        # 30分钟bar收益率
        ret = df['close'].pct_change()
    
        # 对每个combo_key，用过去60个交易日（约120根K线/天 * 但30min约8根/天, 60天≈480根同key约24次）
        # 的该key历史收益均值作为条件期望
        # 使用expanding + groupby的方式，但为避免前瞻偏差用shift
        lookback = 480  # 约60个交易日的30min bar数
    
        factor = pd.Series(np.nan, index=df.index)
    
        # 对每个combo key分组计算滚动均值（排除当前bar）
        for key in combo_key.unique():
            mask = combo_key == key
            key_ret = ret[mask]
            # 用expanding mean但shift(1)避免前瞻，同时限制窗口
            rolling_mean = key_ret.shift(1).rolling(window=60, min_periods=8).mean()
            # 用该key出现次数加权的标准化: 均值/标准差 -> t统计量形式
            rolling_std = key_ret.shift(1).rolling(window=60, min_periods=8).std()
            # 信号 = 条件均值 / 条件波动率 (类似Sharpe)
            signal = rolling_mean / (rolling_std + 1e-10)
            factor[mask] = signal
    
        # 再叠加一个"当前bar相对于条件期望的一致性"增强
        # 如果近期该combo的收益方向一致性高，信号更强
        consistency = pd.Series(np.nan, index=df.index)
        for key in combo_key.unique():
            mask = combo_key == key
            key_ret = ret[mask]
            # 近20次该key出现时正收益的比例 - 0.5，衡量方向一致性
            sign_ratio = key_ret.shift(1).rolling(window=20, min_periods=5).apply(
                lambda x: np.mean(x > 0) - 0.5, raw=True
            )
            consistency[mask] = sign_ratio
    
        # 最终因子: 条件Sharpe * (1 + 方向一致性) 
        final_factor = factor * (1 + 2 * consistency.fillna(0))
    
        # 整体zscore标准化（滚动）
        final_factor = (final_factor - final_factor.rolling(240, min_periods=60).mean()) / \
                       (final_factor.rolling(240, min_periods=60).std() + 1e-10)
    
        return final_factor

DISCOVERED_FACTORS['weekly_hour_momentum_cycle'] = weekly_hour_momentum_cycle


def oi_acceleration_price_divergence(df):
    """计算持仓量变化的加速度（二阶差分的均线）与价格动量之间的背离程度，捕捉持仓量加速增减但价格未同步响应的异常状态，预示趋势即将反转或加速。
    avg |IC| = 0.0227
    """
        import numpy as np
        import pandas as pd
    
        oi = df['open_interest'].copy()
        close = df['close'].copy()
    
        # 持仓量一阶变化率（归一化）
        oi_change = oi.diff()
        # 持仓量二阶变化（加速度）
        oi_accel = oi_change.diff()
    
        # 对加速度做EMA平滑，减少噪音，窗口8根K线（4小时）
        oi_accel_ema = oi_accel.ewm(span=8, min_periods=4).mean()
    
        # 用滚动标准差归一化加速度，得到加速度的z-score
        oi_accel_std = oi_accel_ema.rolling(window=24, min_periods=12).std()
        oi_accel_z = oi_accel_ema / oi_accel_std.replace(0, np.nan)
    
        # 价格动量：12根K线（6小时）的收益率
        price_mom = close.pct_change(12)
        # 价格动量z-score
        price_mom_std = price_mom.rolling(window=24, min_periods=12).std()
        price_mom_z = price_mom / price_mom_std.replace(0, np.nan)
    
        # 背离度 = OI加速度z-score - 价格动量z-score
        # 当OI加速增加但价格未涨（正背离），说明多头建仓但价格压制，蓄势待涨
        # 当OI加速增加但价格下跌（更强正背离），可能是空头主动建仓
        # 引入符号调整：考虑OI加速度方向与价格方向的交叉信息
        raw_divergence = oi_accel_z - price_mom_z
    
        # 再用滚动rank做截面标准化（时序rank归一化到-1,1）
        rank_div = raw_divergence.rolling(window=48, min_periods=24).apply(
            lambda x: (pd.Series(x).rank().iloc[-1] - 1) / (len(x) - 1) * 2 - 1 if len(x) > 1 else 0,
            raw=False
        )
    
        factor = rank_div
        factor.name = 'oi_acceleration_price_divergence'
    
        return factor

DISCOVERED_FACTORS['oi_acceleration_price_divergence'] = oi_acceleration_price_divergence


def volume_impulse_price_absorption(df):
    """衡量成交量脉冲后价格吸收能力，即短期成交量激增时价格变动幅度相对于成交量变化的弹性衰减，捕捉大量成交被市场吸收（量增价滞）的异常信号
    avg |IC| = 0.0347
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        high = df['high'].values
        low = df['low'].values
        n = len(close)
    
        # 成交量的短期均值和标准差（用于识别成交量脉冲）
        vol_ma_10 = pd.Series(volume).rolling(10, min_periods=5).mean().values
        vol_std_10 = pd.Series(volume).rolling(10, min_periods=5).std().values
    
        # 成交量z-score：衡量当前成交量相对于近期的异常程度
        vol_z = np.where(vol_std_10 > 0, (volume - vol_ma_10) / vol_std_10, 0.0)
    
        # 价格变动幅度：用真实波幅(TR)归一化
        price_change = np.abs(close - np.roll(close, 1))
        price_change[0] = 0.0
        tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        tr[0] = high[0] - low[0]
    
        # 价格变动相对于bar范围的比例（方向性效率）
        price_efficiency = np.where(tr > 0, price_change / tr, 0.0)
    
        # 成交量归一化变化率
        vol_change_ratio = np.where(vol_ma_10 > 0, volume / vol_ma_10, 1.0)
    
        # 核心逻辑：当成交量激增但价格吸收（价格变动小）时，说明市场在消化大单
        # 量价弹性 = 价格效率 / 成交量变化率，值越小说明量增价滞越明显
        raw_elasticity = np.where(vol_change_ratio > 0.01, price_efficiency / vol_change_ratio, np.nan)
    
        # 只在成交量显著放大时（vol_z > 0.5）计算有意义的信号
        # 对弹性取对数变换使分布更对称
        log_elasticity = np.where(
            (vol_z > 0.5) & (np.isfinite(raw_elasticity)) & (raw_elasticity > 0),
            np.log(raw_elasticity + 1e-8),
            np.nan
        )
    
        log_elasticity_series = pd.Series(log_elasticity, index=df.index)
    
        # 用扩展窗口前向填充，然后对近期脉冲事件做指数加权平均
        # 滚动窗口内的脉冲吸收信号均值
        factor_raw = log_elasticity_series.rolling(20, min_periods=3).mean()
    
        # 再做一次z-score标准化（滚动60期）
        factor_ma = factor_raw.rolling(60, min_periods=10).mean()
        factor_std = factor_raw.rolling(60, min_periods=10).std()
    
        factor = -((factor_raw - factor_ma) / factor_std.replace(0, np.nan))
        # 取负号：弹性越低（量增价滞）因子值越大，预示价格可能即将突破
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['volume_impulse_price_absorption'] = volume_impulse_price_absorption


def shadow_ratio_trend_divergence(df):
    """计算上下影线比率的趋势与价格趋势的背离，当价格上涨但上影线占比持续增大（抛压增强）或价格下跌但下影线占比持续增大（买盘托底）时，预示趋势反转。
    avg |IC| = 0.0218
    """
        import numpy as np
        import pandas as pd
    
        body = (df['close'] - df['open']).abs()
        full_range = df['high'] - df['low']
        full_range = full_range.replace(0, np.nan)
    
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
    
        # 上下影线比率：>1表示上影线主导，<1表示下影线主导
        shadow_ratio = (upper_shadow + 1e-8) / (lower_shadow + 1e-8)
        log_shadow_ratio = np.log(shadow_ratio)
    
        # 影线比率的短期趋势（用线性回归斜率衡量）
        window = 10
        def rolling_slope(series, w):
            x = np.arange(w, dtype=float)
            x_demean = x - x.mean()
            x_var = (x_demean ** 2).sum()
            slopes = series.rolling(w).apply(
                lambda y: np.sum(x_demean * (y - y.mean())) / x_var if x_var > 0 else 0,
                raw=True
            )
            return slopes
    
        shadow_trend = rolling_slope(log_shadow_ratio, window)
    
        # 价格趋势斜率
        price_trend = rolling_slope(df['close'], window)
    
        # 标准化两个趋势以便比较
        def rolling_zscore(series, w=20):
            m = series.rolling(w, min_periods=w // 2).mean()
            s = series.rolling(w, min_periods=w // 2).std()
            return (series - m) / (s + 1e-8)
    
        shadow_trend_z = rolling_zscore(shadow_trend, 20)
        price_trend_z = rolling_zscore(price_trend, 20)
    
        # 背离因子：影线趋势与价格趋势的交叉乘积取负
        # 价格上涨+上影线增大(shadow_trend>0) => 看空信号(负值)
        # 价格下跌+下影线增大(shadow_trend<0) => 看多信号(正值)
        divergence = -shadow_trend_z * price_trend_z
    
        # 用成交量加权平滑，高成交量时信号更可靠
        vol_weight = df['volume'] / df['volume'].rolling(20, min_periods=5).mean()
        vol_weight = vol_weight.clip(0.5, 3.0)
    
        factor = divergence * vol_weight
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['shadow_ratio_trend_divergence'] = shadow_ratio_trend_divergence


def multi_cycle_trend_alignment(df):
    """将4小时(8根K线)和日线(16根K线)级别的趋势方向通过线性回归斜率量化，再与当前30分钟K线的短周期动量交互，捕捉长周期趋势对短周期的驱动力和方向一致性
    avg |IC| = 0.0207
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
    
        # 短周期动量：3根K线(1.5小时)
        short_mom = close.pct_change(3)
    
        # 中周期趋势斜率：8根K线(4小时级别)，用线性回归斜率
        def rolling_slope(series, window):
            x = np.arange(window, dtype=float)
            x_mean = x.mean()
            x_var = ((x - x_mean) ** 2).sum()
            slopes = series.rolling(window).apply(
                lambda y: ((x - x_mean) * (y - y.mean())).sum() / x_var if x_var > 0 else 0,
                raw=True
            )
            return slopes
    
        mid_slope = rolling_slope(close, 8)
        # 标准化斜率：除以当前价格水平
        mid_slope_norm = mid_slope / close
    
        # 长周期趋势斜率：16根K线(日线级别)
        long_slope = rolling_slope(close, 16)
        long_slope_norm = long_slope / close
    
        # 超长周期趋势：32根K线(2日级别)的均线方向
        ma_32 = close.rolling(32).mean()
        ma_32_dir = ma_32.pct_change(4)  # 均线的4期变化率
    
        # 长周期趋势一致性：中周期和长周期斜率同号则放大
        trend_agreement = np.sign(mid_slope_norm) * np.sign(long_slope_norm)
    
        # 长周期趋势强度：取两个周期斜率的几何平均(保留符号)
        combined_trend_strength = np.sign(long_slope_norm) * np.sqrt(
            np.abs(mid_slope_norm) * np.abs(long_slope_norm)
        )
    
        # 成交量加权：用短周期成交量相对长周期的比值作为权重
        vol_ratio = volume.rolling(3).mean() / volume.rolling(16).mean()
        vol_ratio = vol_ratio.clip(0.5, 3.0)
    
        # 最终因子：长周期趋势映射到短周期
        # 当长周期趋势一致且短周期动量方向相同时，信号最强
        factor = (
            combined_trend_strength * 1000  # 放大到可读范围
            * (1 + trend_agreement) / 2     # 一致时为1，不一致时为0
            * vol_ratio                      # 成交量确认
            + short_mom * np.sign(long_slope_norm) * np.abs(ma_32_dir) * 100  # 短周期在长趋势方向上的贡献
        )
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['multi_cycle_trend_alignment'] = multi_cycle_trend_alignment


def shadow_momentum_divergence(df):
    """衡量影线隐含的方向性压力趋势与实际价格动量之间的背离程度，当上影线持续增大但价格仍上涨时暗示顶部卖压积聚，反之亦然
    avg |IC| = 0.0246
    """
        import numpy as np
        import pandas as pd
    
        high = df['high'].values
        low = df['low'].values
        open_ = df['open'].values
        close = df['close'].values
        volume = df['volume'].values
    
        body_top = np.maximum(open_, close)
        body_bot = np.minimum(open_, close)
    
        upper_shadow = high - body_top
        lower_shadow = body_bot - low
    
        full_range = high - low
        full_range = np.where(full_range < 1e-9, 1e-9, full_range)
    
        # Signed shadow pressure: positive = lower shadow dominant (buying support)
        # negative = upper shadow dominant (selling pressure)
        shadow_pressure = (lower_shadow - upper_shadow) / full_range
    
        # Weight by volume to emphasize high-activity bars
        vol_ma = pd.Series(volume).rolling(20, min_periods=1).mean().values
        vol_weight = np.where(vol_ma < 1e-9, 1.0, volume / vol_ma)
        vol_weight = np.clip(vol_weight, 0.2, 5.0)
    
        weighted_pressure = shadow_pressure * vol_weight
    
        # Trend of shadow pressure over rolling window (slope via linear regression)
        wp_series = pd.Series(weighted_pressure)
        window = 12
    
        def rolling_slope(s, w):
            x = np.arange(w, dtype=float)
            x_demean = x - x.mean()
            denom = (x_demean ** 2).sum()
            result = s.rolling(w, min_periods=w).apply(
                lambda y: np.sum((y - y.mean()) * x_demean) / denom if denom > 0 else 0,
                raw=True
            )
            return result
    
        shadow_trend = rolling_slope(wp_series, window)
    
        # Price momentum (normalized)
        price_ret = pd.Series(close).pct_change(window)
        ret_std = price_ret.rolling(60, min_periods=10).std().replace(0, np.nan)
        norm_ret = price_ret / ret_std
    
        # Shadow trend normalized
        st_std = shadow_trend.rolling(60, min_periods=10).std().replace(0, np.nan)
        norm_shadow = shadow_trend / st_std
    
        # Divergence: shadow pressure trend vs price momentum
        # When shadow_trend is negative (upper shadows growing) but price rising -> negative divergence
        # When shadow_trend is positive (lower shadows growing) but price falling -> positive divergence (bounce expected)
        divergence = norm_shadow - norm_ret
    
        # Smooth to reduce noise
        factor = divergence.rolling(5, min_periods=1).mean()
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return pd.Series(factor.values, index=df.index, name='shadow_momentum_divergence')

DISCOVERED_FACTORS['shadow_momentum_divergence'] = shadow_momentum_divergence


def seasonal_composite_edge(df):
    """基于历史同月份、同星期几、同时段的收益率均值加权合成季节性优势得分，捕捉黄金期货在特定时间维度上的重复性定价模式
    avg |IC| = 0.0269
    """
        import numpy as np
        import pandas as pd
    
        data = df.copy()
        data['ret'] = data['close'].pct_change()
    
        idx = data.index
        if isinstance(idx, pd.DatetimeIndex):
            ts = idx
        else:
            ts = pd.to_datetime(idx)
    
        data['month'] = ts.month
        data['weekday'] = ts.weekday
        data['hour'] = ts.hour
    
        # 用expanding窗口计算各维度的历史季节性收益均值（避免未来信息）
        # 为每个维度构建历史均值，使用滚动累计方式
    
        min_obs = 20
    
        # 月份效应：同月份历史平均收益
        month_mean = np.full(len(data), np.nan)
        # 星期效应：同星期几历史平均收益
        weekday_mean = np.full(len(data), np.nan)
        # 时段效应：同小时历史平均收益
        hour_mean = np.full(len(data), np.nan)
    
        ret_vals = data['ret'].values
        months = data['month'].values
        weekdays = data['weekday'].values
        hours = data['hour'].values
    
        # Expanding mean per group (strictly past data)
        for key_arr, out_arr in [(months, month_mean), (weekdays, weekday_mean), (hours, hour_mean)]:
            group_sum = {}
            group_cnt = {}
            for i in range(len(data)):
                k = key_arr[i]
                if k in group_sum and group_cnt[k] >= min_obs:
                    out_arr[i] = group_sum[k] / group_cnt[k]
                if not np.isnan(ret_vals[i]):
                    group_sum[k] = group_sum.get(k, 0.0) + ret_vals[i]
                    group_cnt[k] = group_cnt.get(k, 0) + 1
    
        # 加权合成：月份权重0.3，星期权重0.35，时段权重0.35
        month_s = pd.Series(month_mean, index=df.index)
        weekday_s = pd.Series(weekday_mean, index=df.index)
        hour_s = pd.Series(hour_mean, index=df.index)
    
        # Z-score标准化各维度后合成
        def rolling_zscore(s, window=480):
            m = s.rolling(window, min_periods=60).mean()
            st = s.rolling(window, min_periods=60).std()
            st = st.replace(0, np.nan)
            return (s - m) / st
    
        mz = rolling_zscore(month_s)
        wz = rolling_zscore(weekday_s)
        hz = rolling_zscore(hour_s)
    
        composite = 0.30 * mz.fillna(0) + 0.35 * wz.fillna(0) + 0.35 * hz.fillna(0)
    
        # 全部为nan的位置保持nan
        all_nan = mz.isna() & wz.isna() & hz.isna()
        composite[all_nan] = np.nan
    
        return composite

DISCOVERED_FACTORS['seasonal_composite_edge'] = seasonal_composite_edge


def vwap_zscore_mean_reversion(df):
    """计算当前收盘价相对于滚动VWAP的Z-score，捕捉价格偏离成交量加权均衡价格的程度，偏离越大越倾向于均值回归
    avg |IC| = 0.0253
    """
        import numpy as np
        import pandas as pd
    
        # 计算每根K线的VWAP近似值（用typical price加权）
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        dollar_volume = typical_price * df['volume']
    
        # 滚动窗口计算累积VWAP（20根30分钟K线 ≈ 2个交易日）
        window = 20
        rolling_dollar_volume = dollar_volume.rolling(window=window, min_periods=10).sum()
        rolling_volume = df['volume'].rolling(window=window, min_periods=10).sum()
        rolling_vwap = rolling_dollar_volume / rolling_volume.replace(0, np.nan)
    
        # 计算收盘价相对VWAP的偏离
        deviation = df['close'] - rolling_vwap
    
        # 用更长窗口（40根）计算偏离的标准差，构建Z-score
        long_window = 40
        dev_mean = deviation.rolling(window=long_window, min_periods=15).mean()
        dev_std = deviation.rolling(window=long_window, min_periods=15).std()
    
        zscore = (deviation - dev_mean) / dev_std.replace(0, np.nan)
    
        # 结合持仓量变化进行修正：持仓量减少时偏离更可能回归（多空平仓）
        oi_change_pct = df['open_interest'].pct_change(5)
        oi_decay_factor = 1.0 + (-oi_change_pct).clip(-0.5, 0.5)  # 持仓减少放大信号
    
        # 最终因子：取负号，使得超买为负（预期下跌），超卖为正（预期上涨）
        factor = -zscore * oi_decay_factor
    
        factor.name = 'vwap_zscore_mean_reversion'
        return factor

DISCOVERED_FACTORS['vwap_zscore_mean_reversion'] = vwap_zscore_mean_reversion


def weekly_trend_30m_projection(df):
    """将周线级别（40根30分钟K线≈1个交易日，200根≈一周）的趋势方向通过线性回归斜率映射到短周期，再用当前价格相对周线趋势线的偏离度衡量短周期的趋势跟随或背离强度
    avg |IC| = 0.0389
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        oi = df['open_interest'].values
        n = len(close)
    
        # 长周期参数：200根30min bar ≈ 一周（每天约8小时，16根/天*5天≈80，取200覆盖约2.5周作为趋势窗口）
        long_window = 200
        # 短周期参数：40根30min bar ≈ 1个交易日
        short_window = 40
    
        factor = np.full(n, np.nan)
    
        for i in range(long_window - 1, n):
            # 长周期线性回归：对close做OLS，得到趋势斜率和趋势线末端值
            y_long = close[i - long_window + 1: i + 1]
            x_long = np.arange(long_window, dtype=np.float64)
        
            x_mean = x_long.mean()
            y_mean = y_long.mean()
        
            slope_long = np.sum((x_long - x_mean) * (y_long - y_mean)) / (np.sum((x_long - x_mean) ** 2) + 1e-10)
            intercept_long = y_mean - slope_long * x_mean
        
            # 长周期趋势线在当前位置的预测值
            trend_value = intercept_long + slope_long * (long_window - 1)
        
            # 当前价格相对长周期趋势线的偏离（标准化）
            residuals_long = y_long - (intercept_long + slope_long * x_long)
            res_std = np.std(residuals_long) + 1e-10
            deviation = (close[i] - trend_value) / res_std
        
            # 短周期动量方向：用短窗口的回归斜率
            if i >= short_window - 1:
                y_short = close[i - short_window + 1: i + 1]
                x_short = np.arange(short_window, dtype=np.float64)
                xs_mean = x_short.mean()
                ys_mean = y_short.mean()
                slope_short = np.sum((x_short - xs_mean) * (y_short - ys_mean)) / (np.sum((x_short - xs_mean) ** 2) + 1e-10)
            else:
                slope_short = 0.0
        
            # 趋势一致性：长短周期斜率同号则趋势跟随，异号则背离
            # 用斜率归一化后的符号一致性加权
            slope_long_norm = slope_long / (np.abs(slope_long) + 1e-10)
            slope_short_norm = slope_short / (np.abs(slope_short) + 1e-10)
            consistency = slope_long_norm * slope_short_norm  # +1一致，-1背离
        
            # OI变化率作为确认信号：短周期OI增减
            oi_short = oi[i - short_window + 1: i + 1]
            oi_change = (oi_short[-1] - oi_short[0]) / (oi_short[0] + 1e-10)
        
            # 最终因子：偏离度 × 趋势一致性 × (1 + OI确认)
            # 偏离度带方向，一致性带方向，OI增加放大信号
            oi_confirm = np.sign(oi_change) * np.log1p(np.abs(oi_change) * 100)
        
            factor[i] = deviation * consistency * (1 + 0.3 * oi_confirm)
    
        return pd.Series(factor, index=df.index, name='weekly_trend_30m_projection')

DISCOVERED_FACTORS['weekly_trend_30m_projection'] = weekly_trend_30m_projection


def htf_trend_momentum_sync(df):
    """将120根30分钟K线合成为60分钟和240分钟的长周期趋势方向，通过EMA斜率对齐度加权映射到30分钟，衡量短周期动量与长周期趋势的同步强度。
    avg |IC| = 0.0613
    """
        import numpy as np
        import pandas as pd

        close = df['close'].copy()
        n = len(close)

        # ---------- 辅助：基于重采样构造长周期EMA斜率 ----------
        def resample_ema_slope(series, agg_bars, ema_period, slope_period):
            """
            将 series 按 agg_bars 根K线合并为高级别K线，
            计算 EMA，再将斜率插值回原始频率。
            """
            idx = np.arange(n)
            # 分组：每 agg_bars 根K线为一组
            group_id = idx // agg_bars

            # 用 groupby 取每组最后一根收盘价（模拟高级别收盘）
            s = pd.Series(series.values, index=idx)
            htf_close = s.groupby(group_id).last()

            # 计算高级别 EMA
            htf_ema = htf_close.ewm(span=ema_period, adjust=False).mean()

            # 高级别斜率：EMA的一阶差分 / EMA自身（归一化）
            htf_slope = htf_ema.diff(slope_period) / htf_ema.shift(slope_period)

            # 将高级别斜率映射回原始索引（前向填充）
            slope_reindexed = htf_slope.reindex(group_id).values
            return pd.Series(slope_reindexed, index=series.index)

        # ---------- 1. 60分钟级别（2根30min合1根）：趋势斜率 ----------
        # EMA周期=10（对应约20根30min），斜率窗口=3个高级别K线
        slope_60 = resample_ema_slope(close, agg_bars=2, ema_period=10, slope_period=3)

        # ---------- 2. 240分钟级别（8根30min合1根）：趋势斜率 ----------
        # EMA周期=8（对应约64根30min），斜率窗口=2个高级别K线
        slope_240 = resample_ema_slope(close, agg_bars=8, ema_period=8, slope_period=2)

        # ---------- 3. 短周期（30min）自身动量 ----------
        # 使用 EMA(5) 相对 EMA(20) 的偏离度作为短周期动量
        ema_fast = close.ewm(span=5, adjust=False).mean()
        ema_slow = close.ewm(span=20, adjust=False).mean()
        mom_30 = (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)

        # ---------- 4. 跨周期对齐权重 ----------
        # 当60min斜率与240min斜率方向一致时，长周期趋势可信度高，赋予更大权重
        # 对齐度 = sign一致时为1，否则为-1，再平滑
        align_raw = np.sign(slope_60) * np.sign(slope_240)
        # 平滑对齐信号（避免单根噪声）
        align_smooth = pd.Series(align_raw, index=close.index).rolling(4, min_periods=1).mean()

        # ---------- 5. 长周期综合趋势压力 ----------
        # 以 240min 斜率为主方向，60min 斜率为辅助，加权合并
        long_trend = 0.6 * slope_240 + 0.4 * slope_60

        # ---------- 6. 最终因子：短周期动量 × 长周期趋势强度 × 对齐权重 ----------
        # 物理含义：
        #   - long_trend 方向与 mom_30 同向 → 趋势延续信号增强
        #   - align_smooth 接近 1 → 多周期共振，信号更可靠
        #   - 反向则衰减或反转信号
        raw_factor = mom_30 * long_trend * (1 + align_smooth)

        # ---------- 7. 截面标准化（rolling z-score，窗口=120根，即2.5天） ----------
        roll_mean = raw_factor.rolling(120, min_periods=30).mean()
        roll_std  = raw_factor.rolling(120, min_periods=30).std().replace(0, np.nan)
        factor = (raw_factor - roll_mean) / roll_std

        # 极值截断，防止异常值干扰
        factor = factor.clip(-3, 3)

        factor.name = 'htf_trend_momentum_sync'
        return factor

DISCOVERED_FACTORS['htf_trend_momentum_sync'] = htf_trend_momentum_sync


def trend_projection_residual(df):
    """将长周期（如8小时/16根K线）的线性趋势投影到短周期（4根K线），计算短周期实际收益与长周期趋势预期收益的残差动量，捕捉短周期对长周期趋势的偏离与回归。
    avg |IC| = 0.0227
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
    
        long_window = 16  # 长周期：16根30min K线 = 8小时
        short_window = 4   # 短周期：4根30min K线 = 2小时
        decay_window = 8   # 残差动量的指数衰减窗口
    
        # 长周期线性回归斜率（每根K线的预期变动量）
        def rolling_linreg_slope(series, window):
            x = np.arange(window, dtype=float)
            x_mean = x.mean()
            x_var = ((x - x_mean) ** 2).sum()
        
            slopes = pd.Series(np.nan, index=series.index)
            vals = series.values
        
            for i in range(window - 1, len(vals)):
                y = vals[i - window + 1: i + 1]
                if np.any(np.isnan(y)):
                    continue
                y_mean = np.mean(y)
                slope = np.sum((x - x_mean) * (y - y_mean)) / x_var
                slopes.iloc[i] = slope
        
            return slopes
    
        # 长周期趋势斜率（标准化为每根K线的预期价格变动）
        long_slope = rolling_linreg_slope(close, long_window)
    
        # 长周期趋势对短周期的预期收益：斜率 * 短周期长度
        projected_return = long_slope * short_window
    
        # 短周期实际收益
        actual_return = close - close.shift(short_window)
    
        # 残差 = 实际短周期收益 - 长周期趋势预期收益
        residual = actual_return - projected_return
    
        # 用波动率标准化残差
        rolling_std = close.pct_change().rolling(long_window).std() * close
        rolling_std = rolling_std.replace(0, np.nan)
        norm_residual = residual / rolling_std
    
        # 对标准化残差取指数加权动量，捕捉残差的持续性（偏离后的均值回归信号）
        factor = norm_residual.ewm(span=decay_window, adjust=False).mean()
    
        # 取反：正残差表示短周期超涨于长周期趋势，预期回落
        factor = -factor
    
        factor.name = 'trend_projection_residual'
        return factor

DISCOVERED_FACTORS['trend_projection_residual'] = trend_projection_residual


def rv_skew_zscore(df):
    """计算已实现波动率的偏斜度（上行波动率与下行波动率之比）相对于其历史分布的Z-score，捕捉波动率非对称结构的异常变化，反映市场对上行与下行风险定价的失衡程度。
    avg |IC| = 0.0402
    """
        import numpy as np
        import pandas as pd
    
        log_ret = np.log(df['close'] / df['close'].shift(1))
    
        # 短周期窗口计算上行/下行已实现波动率
        window_short = 16  # 约1个交易日(30min K线, 8根/天, 2天)
        window_long = 80   # 约10个交易日
        zscore_window = 120  # Z-score回看窗口
    
        # 上行已实现波动率: 只取正收益的平方和
        up_ret_sq = (log_ret.clip(lower=0)) ** 2
        down_ret_sq = (log_ret.clip(upper=0)) ** 2
    
        rv_up_short = up_ret_sq.rolling(window=window_short, min_periods=8).sum().apply(np.sqrt)
        rv_down_short = down_ret_sq.rolling(window=window_short, min_periods=8).sum().apply(np.sqrt)
    
        rv_up_long = up_ret_sq.rolling(window=window_long, min_periods=40).sum().apply(np.sqrt)
        rv_down_long = down_ret_sq.rolling(window=window_long, min_periods=40).sum().apply(np.sqrt)
    
        # 波动率偏斜比: 上行RV / 下行RV
        # 比值>1表示上行波动主导, <1表示下行波动主导
        epsilon = 1e-10
        skew_ratio_short = rv_up_short / (rv_down_short + epsilon)
        skew_ratio_long = rv_up_long / (rv_down_long + epsilon)
    
        # 短周期偏斜相对长周期偏斜的偏离：捕捉偏斜结构的期限变化
        skew_diff = skew_ratio_short - skew_ratio_long
    
        # 对skew_diff做Z-score标准化，识别异常偏斜状态
        skew_mean = skew_diff.rolling(window=zscore_window, min_periods=60).mean()
        skew_std = skew_diff.rolling(window=zscore_window, min_periods=60).std()
    
        factor = (skew_diff - skew_mean) / (skew_std + epsilon)
    
        # 限制极端值
        factor = factor.clip(-4, 4)
    
        factor.name = 'rv_skew_zscore'
        return factor

DISCOVERED_FACTORS['rv_skew_zscore'] = rv_skew_zscore


def hour_volume_zscore(df):
    """计算当前30分钟K线所处交易时段的成交量相对于该时段历史均值的z-score，捕捉特定时段异常活跃度对后续价格的预测能力
    avg |IC| = 0.0216
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
    
        # 从索引或推断时段标签：用行号对每日bar数取模来标识时段
        # SHFE黄金期货30分钟K线：日盘+夜盘大约有多个时段
        # 我们用一种稳健方式：根据日期分组，给每天的bar编号作为时段ID
        if isinstance(df.index, pd.DatetimeIndex):
            df['date'] = df.index.date
            df['time'] = df.index.time
            # 用time直接作为时段标识
            df['slot'] = df['time'].astype(str)
        else:
            # 如果索引不是datetime，尝试用位置推断
            # 假设每天固定bar数，用差分检测日切换
            df['date'] = np.arange(len(df))
            df['slot'] = np.arange(len(df)) % 16  # fallback
            df['slot'] = df['slot'].astype(str)
    
        # 对每个时段，计算滚动的成交量均值和标准差（用过去20个同时段的数据）
        lookback = 20
    
        df['vol_log'] = np.log1p(df['volume'].values)
    
        # 为每个slot计算历史统计
        factor = pd.Series(np.nan, index=df.index)
    
        for slot_id, group in df.groupby('slot'):
            idx = group.index
            vol_vals = group['vol_log'].values
        
            roll_mean = pd.Series(vol_vals, index=idx).rolling(window=lookback, min_periods=5).mean()
            roll_std = pd.Series(vol_vals, index=idx).rolling(window=lookback, min_periods=5).std()
        
            # z-score
            current_vol = pd.Series(vol_vals, index=idx)
            z = (current_vol - roll_mean) / roll_std.replace(0, np.nan)
        
            factor.loc[idx] = z.values
    
        # 结合收益率方向：异常高成交量在上涨时段为正信号，下跌时段为负信号
        ret = df['close'].pct_change()
        ret_sign = np.sign(ret)
    
        # 最终因子：时段成交量z-score × 收益率符号，捕捉时段动量异常
        factor_series = factor * ret_sign
    
        factor_series.name = 'hour_volume_zscore'
        return factor_series

DISCOVERED_FACTORS['hour_volume_zscore'] = hour_volume_zscore


def oi_delta_price_lag_divergence(df):
    """捕捉持仓量变化（OI Delta）与价格变动之间的滞后背离——当OI大幅增加而价格滞后未跟随（或反向），往往预示主力建仓方向与短期价格走势的结构性分歧，具有反转或趋势加速信号。
    avg |IC| = 0.0217
    """
        import numpy as np
        import pandas as pd

        n_short = 3   # 短期窗口
        n_long = 12   # 长期窗口（约6小时）

        close = df['close']
        oi = df['open_interest']

        # 1. OI变化率（Delta OI / OI_lag）
        oi_chg = oi.diff(1)
        oi_chg_rate = oi_chg / oi.shift(1)  # 归一化OI变化率

        # 2. 价格变化率
        price_chg_rate = close.pct_change(1)

        # 3. 短期累积：OI变化率 vs 价格变化率 的"同向性"
        #    用rolling窗口内两者的差值累积，衡量背离程度
        divergence_raw = oi_chg_rate - price_chg_rate

        # 4. 短期背离动量（近期背离的方向和强度）
        div_short = divergence_raw.rolling(window=n_short, min_periods=n_short).sum()

        # 5. 长期背离基准（用于标准化，捕捉相对异常）
        div_long_mean = divergence_raw.rolling(window=n_long, min_periods=n_long).mean()
        div_long_std  = divergence_raw.rolling(window=n_long, min_periods=n_long).std()

        # 6. Z-score标准化：短期背离相对于长期分布的偏离程度
        #    正值：OI增速 > 价格增速（主力建仓但价格未跟随，潜在看多）
        #    负值：价格增速 > OI增速（价格超涨而OI未确认，潜在看空）
        factor = (div_short - div_long_mean * n_short) / (div_long_std * np.sqrt(n_short) + 1e-10)

        factor.name = 'oi_delta_price_lag_divergence'
        return factor

DISCOVERED_FACTORS['oi_delta_price_lag_divergence'] = oi_delta_price_lag_divergence


def weekly_momentum_intraday_reversion(df):
    """将周级别（240根30分钟K线）动量强度映射到日内尺度，计算短周期价格偏离长周期趋势均衡位置的回归压力，捕捉长周期趋势下短周期均值回复的交易机会。
    avg |IC| = 0.0386
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        high = df['high'].copy()
        low = df['low'].copy()
        volume = df['volume'].copy()
    
        # 周级别参数：240根30分钟K线 ≈ 1周（5天 * 48根/天，实际交易约8小时=16根，5天=80根，取近似）
        weekly_window = 80
        # 日级别参数
        daily_window = 16
        # 短周期窗口
        short_window = 8
    
        # 1. 周级别趋势方向与强度：用线性回归斜率标准化
        def rolling_linreg_slope(series, window):
            slopes = pd.Series(np.nan, index=series.index)
            x = np.arange(window, dtype=float)
            x_demean = x - x.mean()
            x_var = (x_demean ** 2).sum()
            for i in range(window - 1, len(series)):
                y = series.iloc[i - window + 1:i + 1].values
                if np.any(np.isnan(y)):
                    continue
                y_demean = y - y.mean()
                slope = (x_demean * y_demean).sum() / x_var
                # 用价格标准化斜率
                slopes.iloc[i] = slope / (series.iloc[i] + 1e-10)
            return slopes
    
        weekly_trend_slope = rolling_linreg_slope(close, weekly_window)
    
        # 2. 周级别趋势的均衡价格：成交量加权均价
        weekly_vwap = (close * volume).rolling(weekly_window).sum() / (volume.rolling(weekly_window).sum() + 1e-10)
    
        # 3. 短周期价格偏离度：当前价格相对周VWAP的偏离
        price_deviation = (close - weekly_vwap) / (weekly_vwap + 1e-10)
    
        # 4. 日内波动率（短周期）归一化
        daily_volatility = close.pct_change().rolling(daily_window).std()
        deviation_zscore = price_deviation / (daily_volatility + 1e-10)
    
        # 5. 短周期动量（8根K线）
        short_mom = close.pct_change(short_window)
    
        # 6. 核心因子：当周趋势强且短周期过度偏离时，产生回归压力信号
        # 若周趋势向上（slope>0）但短周期过度上冲（deviation_zscore很大），回归压力为负（做空信号）
        # 反之亦然
        # 用周趋势斜率的符号与偏离zscore的交互来衡量
    
        # 趋势方向一致性：短周期动量与长周期趋势的同向程度
        trend_alignment = np.sign(weekly_trend_slope) * short_mom
    
        # 回归压力 = 趋势强度 * 偏离程度的反向信号
        # 当偏离过大且与趋势同向时，预期回归；当偏离与趋势反向时，预期趋势延续
        reversion_pressure = weekly_trend_slope * 100 - deviation_zscore * 0.5
    
        # 结合趋势一致性调整
        factor = reversion_pressure - trend_alignment * deviation_zscore.abs()
    
        # 最终平滑
        factor = factor.rolling(4, min_periods=1).mean()
    
        return factor

DISCOVERED_FACTORS['weekly_momentum_intraday_reversion'] = weekly_momentum_intraday_reversion


def oi_price_lag_divergence_momentum(df):
    """捕捉持仓量变化与价格变化之间的滞后背离动量——当OI领先价格反转时，往往预示着主力资金的趋势反转意图，通过计算OI变化率与价格变化率的滚动互相关滞后结构，识别两者脱钩的加速信号。
    avg |IC| = 0.0385
    """
        import numpy as np
        import pandas as pd

        # 参数
        short_window = 8
        long_window = 24
        lag = 3

        close = df['close']
        oi = df['open_interest']

        # 价格收益率 & OI变化率
        price_ret = close.pct_change()
        oi_ret = oi.pct_change()

        # 滞后OI变化率（OI领先于价格）
        oi_ret_lagged = oi_ret.shift(lag)

        # 短期与长期的 OI变化率 - 价格变化率 背离值
        divergence = oi_ret_lagged - price_ret

        # 背离的短期动量：短窗口均值
        div_short = divergence.rolling(window=short_window, min_periods=short_window // 2).mean()

        # 背离的长期基准：长窗口均值
        div_long = divergence.rolling(window=long_window, min_periods=long_window // 2).mean()

        # 背离动量 = 短期背离均值偏离长期背离均值的程度
        div_momentum = div_short - div_long

        # 用长期标准差标准化，避免量纲问题
        div_std = divergence.rolling(window=long_window, min_periods=long_window // 2).std()
        div_std = div_std.replace(0, np.nan)

        factor = div_momentum / div_std

        factor.name = 'oi_price_lag_divergence_momentum'
        return factor

DISCOVERED_FACTORS['oi_price_lag_divergence_momentum'] = oi_price_lag_divergence_momentum


def oi_elasticity_shift(df):
    """衡量持仓量对价格变动的弹性（OI%变化/Price%变化）在短期与长期窗口间的差异，弹性突变意味着市场参与者对价格敏感度发生结构性转变，预示趋势启动或衰竭
    avg |IC| = 0.0278
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values.astype(float)
        oi = df['open_interest'].values.astype(float)
        n = len(close)
    
        # Percentage changes
        pct_close = np.empty(n)
        pct_close[0] = 0.0
        pct_close[1:] = (close[1:] - close[:-1]) / np.where(close[:-1] == 0, np.nan, close[:-1])
    
        pct_oi = np.empty(n)
        pct_oi[0] = 0.0
        pct_oi[1:] = (oi[1:] - oi[:-1]) / np.where(oi[:-1] == 0, np.nan, oi[:-1])
    
        # Rolling elasticity = cov(pct_oi, pct_close) / var(pct_close) over window
        def rolling_elasticity(pct_o, pct_c, window):
            elasticity = np.full(n, np.nan)
            for i in range(window - 1, n):
                pc = pct_c[i - window + 1: i + 1]
                po = pct_o[i - window + 1: i + 1]
                mask = np.isfinite(pc) & np.isfinite(po)
                if mask.sum() < window * 0.6:
                    continue
                pc_m = pc[mask]
                po_m = po[mask]
                var_pc = np.var(pc_m, ddof=1)
                if var_pc < 1e-14:
                    elasticity[i] = 0.0
                else:
                    cov_val = np.cov(po_m, pc_m, ddof=1)[0, 1]
                    elasticity[i] = cov_val / var_pc
            return elasticity
    
        # Short-term elasticity (8 bars ~ 4h) vs long-term (32 bars ~ 16h)
        short_window = 8
        long_window = 32
    
        elast_short = rolling_elasticity(pct_oi, pct_close, short_window)
        elast_long = rolling_elasticity(pct_oi, pct_close, long_window)
    
        # Elasticity shift: short-term minus long-term, normalized by long-term abs
        raw_shift = elast_short - elast_long
    
        # Normalize by rolling std of the shift for cross-temporal comparability
        shift_series = pd.Series(raw_shift)
        roll_mean = shift_series.rolling(window=48, min_periods=16).mean()
        roll_std = shift_series.rolling(window=48, min_periods=16).std()
    
        factor = (shift_series - roll_mean) / roll_std.replace(0, np.nan)
    
        # Clip extremes
        factor = factor.clip(-4, 4)
        factor.index = df.index
    
        return factor

DISCOVERED_FACTORS['oi_elasticity_shift'] = oi_elasticity_shift


def monthly_week_session_interaction(df):
    """捕捉月份×周内×日夜盘三维交互的季节性收益异常，利用历史同条件下的平均收益作为预测信号，反映黄金期货在特定月份的特定星期几的特定交易时段存在的系统性收益偏差。
    avg |IC| = 0.0262
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['datetime'] = pd.to_datetime(df.index) if not isinstance(df.index, pd.DatetimeIndex) else df.index
    
        # 30分钟收益率
        df['ret'] = df['close'].pct_change()
    
        # 提取月份和周内天
        df['month'] = df['datetime'].dt.month
        df['weekday'] = df['datetime'].dt.weekday  # 0=Mon, 4=Fri
    
        # 交易时段划分: 夜盘(21:00-02:30) -> 0, 早盘(09:00-11:30) -> 1, 午盘(13:30-15:00) -> 2
        hour = df['datetime'].dt.hour
        df['session'] = np.where(
            (hour >= 21) | (hour < 3), 0,
            np.where((hour >= 9) & (hour < 12), 1, 2)
        )
    
        # 构建三维交互键
        df['group_key'] = df['month'] * 100 + df['weekday'] * 10 + df['session']
    
        # 用扩展窗口计算历史同条件下的平均收益（避免未来信息泄漏）
        # 对每个group_key，计算截至当前的历史均值（不含当前值）
        factor = pd.Series(np.nan, index=df.index)
    
        # 为每个group_key计算expanding mean（shift(1)避免look-ahead）
        group_cum_sum = df.groupby('group_key')['ret'].cumsum().shift(1)
        group_cum_count = df.groupby('group_key').cumcount()  # 从0开始，即当前是第几个
    
        # 历史均值 = 累计和(不含当前) / 历史出现次数
        hist_mean = group_cum_sum / group_cum_count.replace(0, np.nan)
    
        # 需要足够的历史样本才有意义，至少出现过8次
        min_obs = 8
        hist_mean[group_cum_count < min_obs] = np.nan
    
        # 用历史均值的z-score标准化，使其跨时间可比
        # 滚动标准化：用过去252个bar（约1周多的交易数据对应的更长期窗口）
        roll_mean = hist_mean.rolling(window=480, min_periods=60).mean()
        roll_std = hist_mean.rolling(window=480, min_periods=60).std()
    
        factor = (hist_mean - roll_mean) / roll_std.replace(0, np.nan)
    
        # 极端值截断
        factor = factor.clip(-3, 3)
    
        return factor

DISCOVERED_FACTORS['monthly_week_session_interaction'] = monthly_week_session_interaction


def volume_absorption_ratio(df):
    """衡量高成交量K线的价格冲击效率与正常成交量K线的对比，当高量bars未能推动相应价格变动时，表明大资金在吸筹/派发，预示趋势反转
    avg |IC| = 0.0301
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
    
        returns_abs = np.abs(np.concatenate([[np.nan], np.diff(close) / close[:-1]]))
        bar_range = (high - low) / close
        # Combined price displacement: blend of return and range
        price_disp = 0.5 * returns_abs + 0.5 * bar_range
    
        lookback = 60  # 60 bars ~ roughly 5 trading days of 30min bars
        short_win = 10
    
        factor = pd.Series(np.nan, index=df.index)
    
        vol_series = pd.Series(volume, index=df.index)
        disp_series = pd.Series(price_disp, index=df.index)
    
        # Rolling volume percentile rank for each bar
        vol_rank = vol_series.rolling(lookback, min_periods=30).apply(
            lambda x: np.sum(x[:-1] <= x[-1]) / (len(x) - 1) if len(x) > 1 else np.nan,
            raw=True
        )
    
        # For each bar, compute rolling "expected" price impact per unit volume
        # normalized_impact = price_displacement / (volume / mean_volume)
        vol_ma = vol_series.rolling(lookback, min_periods=30).mean()
        relative_vol = vol_series / vol_ma.replace(0, np.nan)
    
        # Price impact efficiency: displacement per unit of relative volume
        impact_eff = disp_series / relative_vol.replace(0, np.nan)
    
        # Rolling median impact efficiency as baseline
        baseline_eff = impact_eff.rolling(lookback, min_periods=30).median()
    
        # Identify high-volume bars (top 30% in rolling window)
        is_high_vol = (vol_rank >= 0.70).astype(float)
    
        # Absorption = when high-vol bars have LOWER than expected impact
        # Compute average impact_eff for high-vol bars over recent window
        high_vol_impact = impact_eff * is_high_vol
        high_vol_impact = high_vol_impact.replace(0, np.nan)
    
        high_vol_avg = high_vol_impact.rolling(short_win, min_periods=3).mean()
    
        # Ratio: high-volume impact efficiency / baseline efficiency
        # < 1 means absorption (high vol, low impact) -> reversal signal
        # > 1 means impulse (high vol, high impact) -> continuation signal
        raw_ratio = high_vol_avg / baseline_eff.replace(0, np.nan)
    
        # Take log for symmetry and z-score for normalization
        log_ratio = np.log(raw_ratio.replace(0, np.nan))
    
        roll_mean = log_ratio.rolling(lookback, min_periods=20).mean()
        roll_std = log_ratio.rolling(lookback, min_periods=20).std()
    
        factor = (log_ratio - roll_mean) / roll_std.replace(0, np.nan)
    
        # Negative = absorption (high vol, low price move) -> bearish continuation weakening
        # Flip sign: absorption (negative) predicts reversal -> positive alpha
        factor = -factor
    
        factor.name = 'volume_absorption_ratio'
        return factor

DISCOVERED_FACTORS['volume_absorption_ratio'] = volume_absorption_ratio


def trend_projection_ratio(df):
    """将长周期（4小时/8根K线）的趋势斜率通过线性回归映射到短周期（30分钟），计算短周期价格偏离长周期趋势投影值的标准化比率，捕捉短周期对长周期趋势的回归或背离信号
    avg |IC| = 0.0204
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        n = len(close)
    
        # 长周期参数：8根30分钟K线 = 4小时
        long_period = 8
        # 中周期参数：16根 = 8小时（约一个交易日）
        mid_period = 16
        # 短周期波动窗口
        short_period = 4
    
        # 计算长周期线性回归斜率（滚动）
        def rolling_linreg_slope(arr, window):
            slopes = np.full(len(arr), np.nan)
            x = np.arange(window, dtype=float)
            x_mean = x.mean()
            x_var = ((x - x_mean) ** 2).sum()
            for i in range(window - 1, len(arr)):
                y = arr[i - window + 1: i + 1]
                if np.any(np.isnan(y)):
                    continue
                y_mean = y.mean()
                slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
                slopes[i] = slope
            return slopes
    
        # 长周期趋势斜率（16根K线窗口）
        long_slope = rolling_linreg_slope(close, mid_period)
    
        # 长周期趋势的投影值：从mid_period窗口末端向前投影short_period步
        # 即用当前长周期趋势预测未来short_period根K线后的价格
        # 投影价格 = 当前close + slope * short_period
        projected_price = close + long_slope * short_period
    
        # 实际short_period根K线后的价格变化方向（用过去的来做因子，避免未来数据）
        # 改为：当前价格相对于short_period根前的投影价格的偏离
        projected_price_shifted = np.full(n, np.nan)
        projected_price_shifted[short_period:] = projected_price[:-short_period]
    
        # 短周期实际价格 vs 长周期趋势投影价格的偏差
        deviation = close - projected_price_shifted
    
        # 用长周期波动率标准化
        rolling_std = pd.Series(close).rolling(mid_period).std().values
    
        # 标准化偏差
        factor = np.where(rolling_std > 1e-10, deviation / rolling_std, np.nan)
    
        # 再结合持仓量变化加权：持仓增加时趋势更可靠，偏离更有意义
        oi = df['open_interest'].values
        oi_change_ratio = np.full(n, np.nan)
        oi_ma = pd.Series(oi).rolling(long_period).mean().values
        oi_change_ratio = np.where(oi_ma > 0, oi / oi_ma, 1.0)
    
        # 最终因子：标准化偏差 * 持仓量相对强度
        factor = factor * oi_change_ratio
    
        factor_series = pd.Series(factor, index=df.index, name='trend_projection_ratio')
        return factor_series

DISCOVERED_FACTORS['trend_projection_ratio'] = trend_projection_ratio


def price_oi_weighted_mean_reversion(df):
    """以持仓量变化为权重计算加权VWAP，然后衡量当前价格对该加权均值的标准化偏离程度，持仓量增加时偏离更可信，捕捉超买超卖后的均值回归机会。
    avg |IC| = 0.0385
    """
        import numpy as np
        import pandas as pd
    
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        oi_change = df['open_interest'].diff().fillna(0)
        # 用持仓量变化的绝对值作为权重，持仓增加（新资金进入）时赋予更高权重
        oi_abs_change = oi_change.abs() + 1  # 加1避免零权重
    
        window = 48  # 约2天的30分钟K线
    
        # 计算持仓量加权的移动均价
        weighted_price = typical_price * oi_abs_change
        sum_weighted_price = weighted_price.rolling(window=window, min_periods=12).sum()
        sum_weights = oi_abs_change.rolling(window=window, min_periods=12).sum()
        oi_weighted_mean = sum_weighted_price / sum_weights
    
        # 价格偏离该加权均值
        deviation = df['close'] - oi_weighted_mean
    
        # 用滚动标准差标准化偏离
        dev_std = deviation.rolling(window=window, min_periods=12).std()
        zscore = deviation / dev_std.replace(0, np.nan)
    
        # 持仓量变化方向的确认：持仓增加且价格远离均值 -> 更强的回归信号
        # 用近期持仓净变化的符号来调整：持仓增加（多空博弈加剧）时偏离更有意义
        oi_net_change = oi_change.rolling(window=12, min_periods=4).sum()
        oi_confirmation = 1 + 0.5 * np.sign(oi_net_change) * (oi_net_change.abs() / oi_net_change.abs().rolling(window=window, min_periods=12).mean().replace(0, np.nan)).clip(0, 3)
        oi_confirmation = oi_confirmation.fillna(1)
    
        # 均值回归因子：取负号，偏离越大越可能回归
        factor = -zscore * oi_confirmation
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['price_oi_weighted_mean_reversion'] = price_oi_weighted_mean_reversion


def vol_price_impact_decay(df):
    """衡量成交量冲击对价格影响的衰减速度，即大成交量引发的价格变动在后续K线中被消化的快慢，衰减越快说明市场流动性越好、冲击为噪音，衰减越慢则冲击具有信息含量，可预示趋势延续。
    avg |IC| = 0.0211
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 计算收益率
        ret = np.empty(n)
        ret[0] = 0.0
        ret[1:] = close[1:] / close[:-1] - 1.0
    
        # 计算成交量的滚动均值和标准差，用于识别成交量冲击
        vol_ma = pd.Series(volume).rolling(window=20, min_periods=10).mean().values
        vol_std = pd.Series(volume).rolling(window=20, min_periods=10).std().values
    
        # 成交量Z-score
        vol_z = np.where(vol_std > 0, (volume - vol_ma) / vol_std, 0.0)
    
        # 成交量冲击时的价格变动（vol_z > 1视为冲击）
        # 计算冲击bar的带符号价格影响
        shock_signed_impact = np.where(vol_z > 1.0, ret * vol_z, 0.0)
    
        # 计算冲击后1~5根K线的累计收益（后续价格反应）
        # 如果后续收益方向与冲击方向一致，说明冲击有信息含量（衰减慢）
        # 如果后续收益方向与冲击方向相反，说明冲击为噪音被反转（衰减快）
    
        lookback = 30  # 回看窗口
        decay_periods = [1, 2, 3, 4, 5]
    
        # 计算各个decay period的前向收益
        fwd_ret_sum = np.zeros(n)
        for d in decay_periods:
            shifted_ret = np.empty(n)
            shifted_ret[:] = 0.0
            if d < n:
                # 使用过去的数据：shock发生在t-d位置，后续收益就是t-d+1到t
                # 为避免前瞻偏差，计算过去冲击后的后续反应
                pass
    
        # 重新设计：对于每个时间点t，回看lookback个bar
        # 找到其中的冲击bar，计算冲击bar收益方向与冲击后5bar累计收益方向的一致性
    
        shock_impact = pd.Series(shock_signed_impact)
        ret_series = pd.Series(ret)
    
        # 冲击后5bar累计收益
        post_shock_ret = ret_series.shift(-1).rolling(window=5, min_periods=1).sum().shift(5)
        # shift(5)确保在t时刻只用到t-5及之前的信息（无前瞻偏差）
        # 实际上用shift回到过去
    
        # 更简洁的方法：过去每个bar的冲击影响 * 后续反应的符号一致性
        post_cumret = np.zeros(n)
        for i in range(5, n):
            post_cumret[i] = np.sum(ret[i-4:i+1])  # i-4到i的5bar累计收益
    
        # 对于bar i，如果bar i-5是冲击bar，则冲击方向是ret[i-5]，后续反应是post_cumret[i]
        # 计算滚动窗口内的冲击延续比率
    
        shock_direction = np.sign(shock_signed_impact)
        continuation = np.zeros(n)
        for lag in range(1, 6):
            lagged_shock_dir = np.empty(n)
            lagged_shock_dir[:] = 0.0
            lagged_shock_dir[lag:] = shock_direction[:-lag]
            lagged_shock_mag = np.empty(n)
            lagged_shock_mag[:] = 0.0
            lagged_shock_mag[lag:] = np.abs(shock_signed_impact[:-lag])
            continuation += lagged_shock_dir * ret * lagged_shock_mag
    
        # 滚动求和：过去lookback个bar内冲击的价格延续度
        factor = pd.Series(continuation).rolling(window=lookback, min_periods=15).sum()
    
        factor.index = df.index
        return factor

DISCOVERED_FACTORS['vol_price_impact_decay'] = vol_price_impact_decay


def vol_skew_persistence_score(df):
    """通过比较上行波动率与下行波动率的滚动偏斜程度及其持续性，捕捉市场参与者对黄金价格下行风险的非对称定价结构，偏斜持续为负时暗示空头压力积累。
    avg |IC| = 0.0231
    """
        import numpy as np
        import pandas as pd

        # 参数
        short_window = 10   # 短期窗口（约5小时，捕捉当日结构）
        long_window = 40    # 长期窗口（约20小时，捕捉跨日结构）
        persist_window = 6  # 偏斜持续性观测窗口

        # 1. 计算每根K线的上行/下行实现波动率代理
        #    上行波动率：high - open（多头主导的波动空间）
        #    下行波动率：open - low（空头主导的波动空间）
        up_vol = df['high'] - df['open']
        dn_vol = df['open'] - df['low']

        # 2. 避免除零，计算上行/下行比率（>1 偏多，<1 偏空）
        epsilon = 1e-8
        raw_skew = up_vol / (dn_vol + epsilon)

        # 3. 对 raw_skew 取对数，使其关于1对称（log>0 偏多，log<0 偏空）
        log_skew = np.log(raw_skew + epsilon)

        # 4. 短期滚动均值偏斜（捕捉近期方向）
        short_skew = log_skew.rolling(window=short_window, min_periods=short_window // 2).mean()

        # 5. 长期滚动均值偏斜（捕捉背景结构）
        long_skew = log_skew.rolling(window=long_window, min_periods=long_window // 2).mean()

        # 6. 偏斜结构差：短期偏斜相对于长期偏斜的偏离
        #    正值：短期比长期更偏多头（上行波动扩张）
        #    负值：短期比长期更偏空头（下行波动扩张）
        skew_spread = short_skew - long_skew

        # 7. 持续性：统计近 persist_window 根K线中 skew_spread 符号一致的比例
        #    若持续同向，说明波动偏斜结构稳定，信号更可靠
        def sign_consistency(series):
            signs = np.sign(series.dropna())
            if len(signs) == 0:
                return np.nan
            return signs.sum() / len(signs)  # 范围 [-1, 1]

        persistence = skew_spread.rolling(window=persist_window, min_periods=persist_window // 2).apply(
            sign_consistency, raw=False
        )

        # 8. 最终因子：偏斜幅度 × 持续性
        #    幅度大且持续一致 → 因子绝对值大，方向性强
        #    幅度大但方向反复 → 因子被压缩，过滤噪声
        factor = skew_spread * persistence

        # 9. 滚动 Z-score 标准化（长期窗口），便于横截面/时序比较
        factor_mean = factor.rolling(window=long_window, min_periods=long_window // 2).mean()
        factor_std = factor.rolling(window=long_window, min_periods=long_window // 2).std()
        factor_z = (factor - factor_mean) / (factor_std + epsilon)

        factor_z.name = 'vol_skew_persistence_score'
        return factor_z

DISCOVERED_FACTORS['vol_skew_persistence_score'] = vol_skew_persistence_score


def large_order_price_impact_ratio(df):
    """通过识别成交量异常放大的K线（视为大单成交），计算大单K线上价格变动与成交量之比，再与普通K线对比，捕捉主力大单的价格冲击效率——大单推动价格的能力越强，说明主力控盘意愿越强。
    avg |IC| = 0.0211
    """
        import numpy as np
        import pandas as pd

        window = 20

        price_change = (df['close'] - df['open']).abs()
        vol = df['volume'].replace(0, np.nan)

        # 单根K线价格冲击效率：每单位成交量带来的价格变动
        price_impact = price_change / vol

        # 成交量的滚动均值与标准差，用于识别大单K线
        vol_mean = vol.rolling(window, min_periods=5).mean()
        vol_std = vol.rolling(window, min_periods=5).std()

        # 大单阈值：成交量超过均值 + 1倍标准差
        large_order_mask = vol > (vol_mean + vol_std)

        # 大单K线的方向：收涨为+1，收跌为-1
        direction = np.sign(df['close'] - df['open'])

        # 带方向的大单价格冲击
        signed_impact = price_impact * direction

        # 大单K线的有向冲击，非大单置为NaN
        large_order_impact = signed_impact.where(large_order_mask, other=np.nan)

        # 滚动窗口内大单冲击的累积均值（代表主力行为方向强度）
        large_order_impact_mean = large_order_impact.rolling(window, min_periods=3).mean()

        # 普通K线冲击均值（对比基准）
        normal_order_impact = signed_impact.where(~large_order_mask, other=np.nan)
        normal_order_impact_mean = normal_order_impact.rolling(window, min_periods=3).mean()

        # 因子值：大单冲击效率 相对于 普通冲击效率 的超额比率
        # 正值表示大单在推涨，负值表示大单在压价
        baseline = normal_order_impact_mean.abs().replace(0, np.nan)
        factor = (large_order_impact_mean - normal_order_impact_mean) / baseline

        factor = factor.replace([np.inf, -np.inf], np.nan)
        factor.name = 'large_order_price_impact_ratio'
        return factor

DISCOVERED_FACTORS['large_order_price_impact_ratio'] = large_order_price_impact_ratio


def bollinger_mean_reversion_intensity(df):
    """基于布林带位置与成交量萎缩的交互，捕捉价格触及极端偏离后在缩量环境下均值回归的强度信号
    avg |IC| = 0.0211
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
        high = df['high'].copy()
        low = df['low'].copy()
    
        # 多周期均值偏离度：用20期和40期两个窗口的z-score加权
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        zscore20 = (close - ma20) / std20.replace(0, np.nan)
    
        ma40 = close.rolling(40).mean()
        std40 = close.rolling(40).std()
        zscore40 = (close - ma40) / std40.replace(0, np.nan)
    
        # 加权z-score，短周期权重更大
        composite_zscore = 0.6 * zscore20 + 0.4 * zscore40
    
        # 成交量萎缩度：当前成交量相对近期均值的比值，缩量时回归概率更大
        vol_ma20 = volume.rolling(20).mean()
        vol_ratio = volume / vol_ma20.replace(0, np.nan)
        # 缩量因子：volume ratio越小，回归信号越强
        vol_decay = 1.0 / (1.0 + vol_ratio)  # 归一化到(0,1)，缩量时接近1
    
        # 真实波幅收窄度：ATR收窄意味着波动耗尽，回归概率上升
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean()
        atr28 = tr.rolling(28).mean()
        atr_contraction = atr14 / atr28.replace(0, np.nan)
        # ATR收窄时 < 1，波动扩张时 > 1
        volatility_exhaustion = 1.0 / (1.0 + atr_contraction)
    
        # 价格在近期高低范围中的位置（类似Williams %R的逻辑）
        hh20 = high.rolling(20).max()
        ll20 = low.rolling(20).min()
        price_position = (close - ll20) / (hh20 - ll20).replace(0, np.nan)
        # 转换为对称的-1到1：极端高位为正，极端低位为负
        price_position_symmetric = 2 * price_position - 1
    
        # 核心因子：composite_zscore的反转信号，被缩量和波动耗尽放大
        # 负号表示均值回归方向（zscore高时预期下跌，反之亦然）
        raw_signal = -composite_zscore * vol_decay * volatility_exhaustion
    
        # 用价格位置一致性加权：当zscore方向与price_position方向一致时，信号更可信
        consistency = composite_zscore * price_position_symmetric
        # consistency > 0 说明两者方向一致，信号更可靠
        consistency_weight = 1.0 + 0.5 * np.clip(consistency, 0, 3) / 3.0
    
        factor = raw_signal * consistency_weight
    
        # 平滑处理减少噪音
        factor = factor.rolling(3, min_periods=1).mean()
    
        factor.name = 'bollinger_mean_reversion_intensity'
        return factor

DISCOVERED_FACTORS['bollinger_mean_reversion_intensity'] = bollinger_mean_reversion_intensity


def weekly_trend_30min_alignment(df):
    """将周级别（240根30分钟K线）的趋势方向与强度映射到当前30分钟K线，通过计算长周期线性回归斜率与短周期动量的交互来捕捉长短周期共振信号
    avg |IC| = 0.0512
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 长周期参数：240根30min K线 ≈ 1周（黄金期货每天约16根30min K线，15天）
        long_window = 240
        # 短周期参数
        short_window = 16  # 约1个交易日
    
        # 长周期线性回归斜率（标准化）
        long_slope = np.full(n, np.nan)
        x_long = np.arange(long_window, dtype=float)
        x_long_demean = x_long - x_long.mean()
        x_long_var = np.sum(x_long_demean ** 2)
    
        for i in range(long_window - 1, n):
            y = close[i - long_window + 1: i + 1]
            y_demean = y - y.mean()
            slope = np.sum(x_long_demean * y_demean) / x_long_var
            # 用价格均值标准化斜率
            long_slope[i] = slope / y.mean() * long_window
    
        # 长周期趋势的R²（趋势质量）
        long_r2 = np.full(n, np.nan)
        for i in range(long_window - 1, n):
            y = close[i - long_window + 1: i + 1]
            y_mean = y.mean()
            y_demean = y - y_mean
            slope = np.sum(x_long_demean * y_demean) / x_long_var
            intercept = y_mean - slope * x_long.mean()
            y_pred = intercept + slope * x_long
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum(y_demean ** 2)
            if ss_tot > 1e-12:
                long_r2[i] = 1.0 - ss_res / ss_tot
            else:
                long_r2[i] = 0.0
    
        # 短周期动量（成交量加权）
        short_mom = np.full(n, np.nan)
        for i in range(short_window - 1, n):
            seg_close = close[i - short_window + 1: i + 1]
            seg_vol = volume[i - short_window + 1: i + 1].astype(float)
            ret = np.diff(seg_close) / seg_close[:-1]
            vol_w = seg_vol[1:]
            vol_sum = vol_w.sum()
            if vol_sum > 1e-12:
                short_mom[i] = np.sum(ret * vol_w) / vol_sum * short_window
            else:
                short_mom[i] = np.sum(ret)
    
        # 跨周期因子：长周期趋势强度 × 趋势质量 × 短周期同向确认
        # 当长短周期同向且长周期趋势质量高时，信号更强
        long_slope = pd.Series(long_slope)
        long_r2 = pd.Series(long_r2)
        short_mom = pd.Series(short_mom)
    
        # 核心：长周期方向加权的短周期动量，R²作为置信度
        factor = long_slope * long_r2 * np.sign(short_mom) * np.abs(short_mom)
    
        # 同向共振放大，反向抑制
        # 当long_slope和short_mom同号时factor自然放大，异号时信号减弱
    
        factor.index = df.index
        return factor

DISCOVERED_FACTORS['weekly_trend_30min_alignment'] = weekly_trend_30min_alignment


def vol_price_elasticity_decay(df):
    """计算成交量变化率对价格变化率的弹性系数（类似需求弹性），并用指数衰减加权近期窗口，捕捉量价响应关系的动态变化——弹性趋近零意味着放量不涨的背离信号，弹性绝对值放大则表示量价共振。
    avg |IC| = 0.0302
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values.astype(float)
        volume = df['volume'].values.astype(float)
        n = len(close)
    
        # 价格收益率和成交量变化率
        ret = np.empty(n)
        ret[0] = 0.0
        ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    
        vol_chg = np.empty(n)
        vol_chg[0] = 0.0
        vol_chg[1:] = (volume[1:] - volume[:-1]) / (volume[:-1] + 1e-10)
    
        # 滚动窗口计算量价弹性：elasticity = cov(vol_chg, ret) / var(ret)
        # 使用指数衰减权重，半衰期为8根bar（4小时）
        lookback = 20
        half_life = 8
        decay_weights = np.exp(-np.log(2) / half_life * np.arange(lookback)[::-1])
        decay_weights = decay_weights / decay_weights.sum()
    
        elasticity = np.full(n, np.nan)
    
        for i in range(lookback - 1, n):
            r_window = ret[i - lookback + 1: i + 1]
            v_window = vol_chg[i - lookback + 1: i + 1]
        
            w = decay_weights
        
            # 加权均值
            r_mean = np.sum(w * r_window)
            v_mean = np.sum(w * v_window)
        
            # 加权协方差和方差
            r_dev = r_window - r_mean
            v_dev = v_window - v_mean
        
            w_var_r = np.sum(w * r_dev ** 2)
            w_cov = np.sum(w * v_dev * r_dev)
        
            if abs(w_var_r) < 1e-14:
                elasticity[i] = 0.0
            else:
                elasticity[i] = w_cov / w_var_r
    
        # 对弹性取短期变化率，捕捉量价关系的突变
        elas_series = pd.Series(elasticity, index=df.index)
        elas_ma_fast = elas_series.ewm(span=5, min_periods=3).mean()
        elas_ma_slow = elas_series.ewm(span=15, min_periods=8).mean()
    
        # 快慢弹性差异：正值表示近期量价弹性增强（共振加强），负值表示背离加剧
        factor = elas_ma_fast - elas_ma_slow
    
        # 用当前成交量相对均量的比值做调制，放量时信号更可信
        vol_series = pd.Series(volume, index=df.index)
        vol_ratio = vol_series / vol_series.rolling(20, min_periods=5).mean()
        vol_ratio = vol_ratio.clip(0.2, 5.0)
    
        factor = factor * np.log1p(vol_ratio)
    
        factor.name = 'vol_price_elasticity_decay'
        return factor

DISCOVERED_FACTORS['vol_price_elasticity_decay'] = vol_price_elasticity_decay


def weekly_trend_intraday_deviation(df):
    """将周级别（40根30分钟K线≈5个交易日）的趋势方向与当前短周期动量的偏离度量化，捕捉短周期价格偏离长周期趋势后的均值回复或趋势延续信号
    avg |IC| = 0.0474
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
    
        # 长周期参数：40根30min K线 ≈ 5个交易日(周级别)
        long_window = 40
        # 短周期参数：8根30min K线 ≈ 1个交易日内半天
        short_window = 8
    
        # 长周期趋势：用线性回归斜率衡量周级别趋势强度和方向
        def rolling_linreg_slope(series, window):
            """计算滚动线性回归斜率，并用标准误归一化"""
            slopes = pd.Series(np.nan, index=series.index)
            x = np.arange(window, dtype=float)
            x_demean = x - x.mean()
            x_var = (x_demean ** 2).sum()
        
            for i in range(window - 1, len(series)):
                y = series.iloc[i - window + 1: i + 1].values
                if np.any(np.isnan(y)):
                    continue
                y_demean = y - y.mean()
                slope = (x_demean * y_demean).sum() / x_var
                # 用y的标准差归一化斜率，使其可比
                y_std = np.std(y)
                if y_std > 1e-10:
                    slopes.iloc[i] = slope / y_std * window
                else:
                    slopes.iloc[i] = 0.0
            return slopes
    
        # 长周期趋势斜率（归一化）
        long_trend = rolling_linreg_slope(close, long_window)
    
        # 短周期动量：短窗口收益率的z-score
        short_ret = close.pct_change(short_window)
        short_ret_mean = short_ret.rolling(long_window, min_periods=long_window).mean()
        short_ret_std = short_ret.rolling(long_window, min_periods=long_window).std()
        short_momentum_z = (short_ret - short_ret_mean) / short_ret_std.replace(0, np.nan)
    
        # 成交量加权的短周期位置：当前价格相对于长周期VWAP的偏离
        vwap_long = (close * volume).rolling(long_window, min_periods=long_window).sum() / \
                    volume.rolling(long_window, min_periods=long_window).sum().replace(0, np.nan)
        price_vwap_dev = (close - vwap_long) / vwap_long.replace(0, np.nan)
    
        # 核心因子：长周期趋势方向 × 短周期偏离的"一致性-背离"度量
        # 当短周期动量与长周期趋势方向一致时，因子为正（趋势延续）
        # 当短周期动量与长周期趋势方向背离时，因子为负（潜在反转）
        # 用VWAP偏离作为位置确认权重
    
        # 长周期趋势的tanh压缩，避免极端值
        trend_signal = np.tanh(long_trend * 0.5)
    
        # 短周期相对于长周期的偏离：正值=同向加速，负值=背离
        coherence = trend_signal * short_momentum_z
    
        # VWAP偏离方向与趋势的交互确认
        vwap_confirm = np.sign(trend_signal) * price_vwap_dev * 100
    
        # 综合因子
        factor = 0.6 * coherence + 0.4 * vwap_confirm
    
        # 最终做winsorize处理
        factor = factor.clip(-5, 5)
    
        factor.name = 'weekly_trend_intraday_deviation'
        return factor

DISCOVERED_FACTORS['weekly_trend_intraday_deviation'] = weekly_trend_intraday_deviation


def htf_trend_deviation_reversion(df):
    """计算长周期（4小时/8根K线）趋势方向与短周期（30分钟）价格偏离度，当短周期价格过度偏离长周期趋势均值时产生均值回归信号，捕捉短周期对长周期趋势锚定的回归效应。
    avg |IC| = 0.0237
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        high = df['high'].copy()
        low = df['low'].copy()
        volume = df['volume'].copy()
    
        # 长周期参数：8根30分钟K线 = 4小时
        long_period = 8
        # 超长周期：24根30分钟K线 = 12小时（约一个交易日）
        ultra_long_period = 24
    
        # 长周期趋势方向：用线性回归斜率表示
        def rolling_slope(series, window):
            x = np.arange(window, dtype=float)
            x_mean = x.mean()
            x_var = ((x - x_mean) ** 2).sum()
        
            slopes = series.rolling(window).apply(
                lambda y: np.sum((x - x_mean) * (y - y.mean())) / x_var if x_var > 0 else 0,
                raw=True
            )
            return slopes
    
        # 长周期趋势斜率（标准化）
        slope_long = rolling_slope(close, long_period)
        slope_ultra = rolling_slope(close, ultra_long_period)
    
        # 长周期VWAP作为趋势锚定价格
        vwap_long = (close * volume).rolling(long_period).sum() / volume.rolling(long_period).sum().replace(0, np.nan)
        vwap_ultra = (close * volume).rolling(ultra_long_period).sum() / volume.rolling(ultra_long_period).sum().replace(0, np.nan)
    
        # 短周期价格相对长周期VWAP的偏离（用ATR标准化）
        atr = (high - low).rolling(long_period).mean().replace(0, np.nan)
    
        deviation_long = (close - vwap_long) / atr
        deviation_ultra = (close - vwap_ultra) / atr
    
        # 长周期趋势强度：斜率标准化
        slope_long_norm = slope_long / atr
        slope_ultra_norm = slope_ultra / atr
    
        # 趋势一致性：长周期和超长周期趋势方向是否一致
        trend_agreement = np.sign(slope_long_norm) * np.sign(slope_ultra_norm)
    
        # 核心逻辑：当趋势一致时，偏离方向与趋势方向相反则产生回归信号
        # 当趋势不一致时，信号减弱
        # 因子 = 趋势方向 * 偏离度的反向（偏离越大，回归动力越强）
        # 正值表示预期上涨，负值表示预期下跌
    
        # 综合偏离度（加权）
        combined_deviation = 0.6 * deviation_long + 0.4 * deviation_ultra
    
        # 趋势方向一致且偏离方向与趋势相反时：强回归信号
        # 用趋势方向减去偏离来构造信号
        trend_direction = np.sign(0.5 * slope_long_norm + 0.5 * slope_ultra_norm)
    
        # 因子：趋势方向强度 - 短周期偏离（偏离过大时回归）
        # 当价格在趋势方向上过度延伸时为负（预期回调），反之为正
        factor = trend_direction * trend_agreement.clip(lower=0) - combined_deviation * 0.5
    
        # 用偏离度的极端程度加权
        deviation_extreme = combined_deviation.abs().rolling(ultra_long_period).rank(pct=True)
    
        factor = factor * deviation_extreme
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['htf_trend_deviation_reversion'] = htf_trend_deviation_reversion


def volume_disparity_price_divergence(df):
    """当成交量相对于其移动均值出现异常放大或缩小时，与同期价格变动方向进行对比，捕捉量价背离信号——量增价跌或量缩价涨往往预示趋势反转压力。
    avg |IC| = 0.0236
    """
        import numpy as np
        import pandas as pd

        # 参数
        vol_window = 20       # 成交量均值窗口
        price_window = 5      # 价格动量窗口
        smooth_window = 3     # 输出平滑窗口

        close = df['close']
        volume = df['volume']

        # 1. 成交量异常度：当前成交量偏离滚动均值的标准化程度
        vol_mean = volume.rolling(vol_window).mean()
        vol_std = volume.rolling(vol_window).std().replace(0, np.nan)
        vol_zscore = (volume - vol_mean) / vol_std  # 正值=放量，负值=缩量

        # 2. 价格动量：短窗口收益率，正值=上涨，负值=下跌
        price_return = close.pct_change(price_window)

        # 3. 量价背离核心逻辑：
        #    - 放量上涨（vol_zscore>0, price_return>0）：量价共振，顺势，factor > 0
        #    - 放量下跌（vol_zscore>0, price_return<0）：量增价跌，看空背离，factor < 0（空头信号）
        #    - 缩量上涨（vol_zscore<0, price_return>0）：量缩价涨，上涨不可持续，factor < 0
        #    - 缩量下跌（vol_zscore<0, price_return<0）：缩量下跌，下跌动能衰竭，factor > 0（潜在止跌）
        #    乘积：vol_zscore * price_return_sign
        #    同号（共振）为正，异号（背离）为负

        price_sign = np.sign(price_return)

        # 用 vol_zscore 幅度加权背离强度
        raw_factor = vol_zscore * price_sign

        # 4. 对背离进行二次强化：放量背离比缩量背离信号更强
        #    额外乘以 |vol_zscore| 的归一化权重，放大异常量时的信号强度
        vol_abs_norm = vol_zscore.abs() / (vol_zscore.abs().rolling(vol_window).mean().replace(0, np.nan))
        enhanced_factor = raw_factor * vol_abs_norm.clip(0.5, 3.0)

        # 5. 平滑输出，降低噪声
        factor = enhanced_factor.rolling(smooth_window).mean()

        factor.name = 'volume_disparity_price_divergence'
        return factor

DISCOVERED_FACTORS['volume_disparity_price_divergence'] = volume_disparity_price_divergence


def htf_trend_pulse_alignment(df):
    """将长周期（如240分钟，即8根30分钟K线）的趋势方向与强度映射到短周期，计算当前30分钟K线的价格动量与长周期趋势的对齐程度，对齐则放大信号，背离则衰减，捕捉趋势延续与反转的结构性机会。
    avg |IC| = 0.0371
    """
        import numpy as np
        import pandas as pd

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        open_interest = df['open_interest']

        # ---- 参数 ----
        htf_window = 8        # 长周期窗口：8根30min = 240min（4小时）
        ltf_window = 3        # 短周期动量窗口
        smooth_window = 4     # 对齐分数平滑窗口

        # ---- 长周期趋势方向与强度（用线性斜率归一化） ----
        def rolling_slope_zscore(series, window):
            """滚动线性回归斜率，并做Z-score标准化"""
            slopes = np.full(len(series), np.nan)
            arr = series.values
            x = np.arange(window, dtype=float)
            x -= x.mean()
            x_sq = (x ** 2).sum()
            for i in range(window - 1, len(arr)):
                y = arr[i - window + 1: i + 1]
                if np.any(np.isnan(y)):
                    continue
                y = y - y.mean()
                slopes[i] = (x * y).sum() / x_sq
            slope_series = pd.Series(slopes, index=series.index)
            # 对斜率做滚动Z-score，刻画趋势强度的相对水平
            slope_mean = slope_series.rolling(htf_window * 4, min_periods=htf_window).mean()
            slope_std  = slope_series.rolling(htf_window * 4, min_periods=htf_window).std().replace(0, np.nan)
            return (slope_series - slope_mean) / slope_std

        htf_slope_z = rolling_slope_zscore(close, htf_window)

        # ---- 长周期趋势方向（+1 / -1 / 0） ----
        htf_direction = np.sign(htf_slope_z)

        # ---- 长周期OI趋势：OI斜率方向，区分主动建仓/减仓 ----
        oi_slope_z = rolling_slope_zscore(open_interest, htf_window)
        oi_direction = np.sign(oi_slope_z)

        # 价格↑ + OI↑ → 主动多头建仓（趋势可信度高）
        # 价格↓ + OI↑ → 主动空头建仓（趋势可信度高）
        # 价格变动 + OI↓ → 平仓驱动，趋势可信度低
        trend_credibility = htf_direction * oi_direction  # +1:可信, -1:不可信

        # ---- 短周期价格动量（收益率） ----
        ltf_ret = close.pct_change(ltf_window)
        ltf_direction = np.sign(ltf_ret)

        # ---- 短周期成交量加权动量（VWAP偏离） ----
        typical_price = (high + low + close) / 3.0
        vwap = (typical_price * volume).rolling(htf_window, min_periods=htf_window // 2).sum() / \
               volume.rolling(htf_window, min_periods=htf_window // 2).sum().replace(0, np.nan)
        price_vwap_dev = (close - vwap) / vwap.replace(0, np.nan)

        # ---- 跨周期对齐分数 ----
        # 对齐分数 = 长周期趋势Z强度 × 短周期方向一致性 × 趋势可信度
        # 短周期方向与长周期方向一致 → +1，否则 → -1
        alignment = ltf_direction * htf_direction  # 方向一致性

        # 原始因子：长周期强度 × 对齐 × 可信度 × VWAP偏离方向修正
        raw_factor = (
            htf_slope_z                          # 长周期趋势强度（有方向）
            * alignment                          # 短周期是否顺趋势
            * trend_credibility                  # OI验证趋势真实性
            * (1 + price_vwap_dev.clip(-0.05, 0.05) * 10)  # VWAP偏离微调，限幅避免极值
        )

        # ---- 平滑处理，减少噪声 ----
        factor = raw_factor.rolling(smooth_window, min_periods=1).mean()

        # ---- 最终Z-score标准化，输出稳定 ----
        factor_mean = factor.rolling(240, min_periods=htf_window * 2).mean()
        factor_std  = factor.rolling(240, min_periods=htf_window * 2).std().replace(0, np.nan)
        factor = (factor - factor_mean) / factor_std

        factor.name = 'htf_trend_pulse_alignment'
        return factor

DISCOVERED_FACTORS['htf_trend_pulse_alignment'] = htf_trend_pulse_alignment


def realized_vol_asymmetry_skew(df):
    """用上行波动率与下行波动率之比衡量波动率的不对称性，捕捉市场对上涨与下跌恐慌程度的结构性偏斜，偏斜值高代表市场更恐惧下跌，具有均值回复预测能力。
    avg |IC| = 0.0290
    """
        import numpy as np
        import pandas as pd

        ret = df['close'].pct_change()

        window = 20  # 约10小时的30分钟K线

        def rolling_upside_vol(x):
            up = x[x > 0]
            return np.sqrt((up ** 2).mean()) if len(up) > 1 else np.nan

        def rolling_downside_vol(x):
            down = x[x < 0]
            return np.sqrt((down ** 2).mean()) if len(down) > 1 else np.nan

        upside_vol = ret.rolling(window).apply(rolling_upside_vol, raw=True)
        downside_vol = ret.rolling(window).apply(rolling_downside_vol, raw=True)

        # 波动率不对称偏斜比：上行vol / 下行vol
        # >1 表示上行波动更剧烈（偏多），<1 表示下行恐慌更强（偏空）
        raw_skew = upside_vol / downside_vol.replace(0, np.nan)

        # 对数化消除量纲偏差，正值偏多，负值偏空
        log_skew = np.log(raw_skew)

        # 对比自身历史水平做Z-Score标准化，提升跨时段可比性
        roll_mean = log_skew.rolling(window * 3).mean()
        roll_std = log_skew.rolling(window * 3).std()
        factor = (log_skew - roll_mean) / roll_std.replace(0, np.nan)

        factor.name = 'realized_vol_asymmetry_skew'
        return factor

DISCOVERED_FACTORS['realized_vol_asymmetry_skew'] = realized_vol_asymmetry_skew


def realized_vol_skew_asymmetry(df):
    """计算上行实现波动率与下行实现波动率的不对称性在不同时间窗口下的锥形结构斜率，捕捉波动率偏斜的期限结构变化，反映市场恐慌与贪婪的动态切换。
    avg |IC| = 0.0227
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(close)
    
        log_ret = np.log(close[1:] / close[:-1])
        log_ret = np.concatenate([[0.0], log_ret])
    
        # Parkinson volatility as realized vol proxy (more efficient than close-close)
        parkinson_var = (np.log(high / low)) ** 2 / (4.0 * np.log(2.0))
    
        # Separate upside and downside contributions
        up_mask = (log_ret > 0).astype(float)
        down_mask = (log_ret < 0).astype(float)
    
        # Upside realized vol: parkinson var weighted by positive return bars
        up_park = parkinson_var * up_mask
        down_park = parkinson_var * down_mask
    
        windows = [8, 16, 32, 64]
    
        up_park_s = pd.Series(up_park, index=df.index)
        down_park_s = pd.Series(down_park, index=df.index)
        up_mask_s = pd.Series(up_mask, index=df.index)
        down_mask_s = pd.Series(down_mask, index=df.index)
    
        skew_by_window = {}
        for w in windows:
            up_vol = np.sqrt(up_park_s.rolling(w, min_periods=w // 2).sum() / 
                             up_mask_s.rolling(w, min_periods=w // 2).sum().clip(lower=1))
            down_vol = np.sqrt(down_park_s.rolling(w, min_periods=w // 2).sum() / 
                               down_mask_s.rolling(w, min_periods=w // 2).sum().clip(lower=1))
        
            # Skew asymmetry: (down_vol - up_vol) / (down_vol + up_vol)
            total = down_vol + up_vol
            skew = (down_vol - up_vol) / total.replace(0, np.nan)
            skew_by_window[w] = skew
    
        skew_df = pd.DataFrame(skew_by_window)
    
        # Compute term structure slope: regress skew values against log(window)
        log_windows = np.log(np.array(windows, dtype=float))
        log_windows_dm = log_windows - log_windows.mean()
        denom = (log_windows_dm ** 2).sum()
    
        def row_slope(row):
            vals = row.values
            if np.any(np.isnan(vals)):
                return np.nan
            vals_dm = vals - np.nanmean(vals)
            return np.sum(vals_dm * log_windows_dm) / denom
    
        slope = skew_df.apply(row_slope, axis=1)
    
        # Normalize by rolling z-score for stationarity
        slope_mean = slope.rolling(64, min_periods=32).mean()
        slope_std = slope.rolling(64, min_periods=32).std().replace(0, np.nan)
    
        factor = (slope - slope_mean) / slope_std
    
        factor.name = 'realized_vol_skew_asymmetry'
        return factor

DISCOVERED_FACTORS['realized_vol_skew_asymmetry'] = realized_vol_skew_asymmetry


def oi_absorption_efficiency(df):
    """衡量每单位成交量所带来的持仓量净变化效率，高吸筹效率（OI大幅增加但成交量较小）暗示方向性建仓，低效率（高成交量但OI无变化）暗示对冲或平仓行为，捕捉主力资金吸筹/派发的隐蔽信号。
    avg |IC| = 0.0304
    """
        import numpy as np
        import pandas as pd

        # 参数设置
        short_window = 5
        long_window = 20
        smooth_window = 3

        # OI变化量（净持仓变化）
        delta_oi = df['open_interest'].diff()

        # 成交量（避免除零）
        vol = df['volume'].replace(0, np.nan)

        # 原始吸筹效率：每单位成交量带来的OI变化
        raw_efficiency = delta_oi / vol

        # 价格方向：用收盘价涨跌方向定义多空
        price_dir = np.sign(df['close'].diff())

        # 方向性吸筹效率：与价格方向对齐时为正（顺势建仓），背离时为负（逆势建仓/对冲）
        directional_efficiency = raw_efficiency * price_dir

        # 短期均值与长期均值的差（捕捉近期吸筹行为的异常程度）
        short_mean = directional_efficiency.rolling(window=short_window, min_periods=2).mean()
        long_mean = directional_efficiency.rolling(window=long_window, min_periods=5).mean()
        long_std = directional_efficiency.rolling(window=long_window, min_periods=5).std().replace(0, np.nan)

        # Z-score标准化：当前短期效率相对长期均值的偏离程度
        efficiency_zscore = (short_mean - long_mean) / long_std

        # 平滑处理，降低噪声
        factor = efficiency_zscore.rolling(window=smooth_window, min_periods=1).mean()

        factor.name = 'oi_absorption_efficiency'
        return factor

DISCOVERED_FACTORS['oi_absorption_efficiency'] = oi_absorption_efficiency


def oi_volume_pressure_imbalance(df):
    """通过比较持仓量增减与成交量的比值在上涨与下跌K线间的不对称性，识别主力资金在不同方向上的建仓/平仓力度差异，比值越高说明主力在该方向上越倾向于持仓而非短线交易
    avg |IC| = 0.0218
    """
        import numpy as np
        import pandas as pd
    
        oi_change = df['open_interest'].diff()
        price_change = df['close'] - df['open']
        volume = df['volume'].replace(0, np.nan)
    
        # 持仓变化与成交量的比值：衡量每单位成交量带来的持仓变化
        # 高比值意味着资金倾向于建仓（主力行为），低比值意味着日内短线交易为主
        oi_vol_ratio = oi_change / volume
    
        # 区分上涨和下跌K线
        is_up = price_change > 0
        is_down = price_change < 0
    
        # 上涨K线的持仓/成交比（主力做多建仓强度）
        up_ratio = oi_vol_ratio.where(is_up, np.nan)
        # 下跌K线的持仓/成交比（主力做空建仓强度）
        down_ratio = oi_vol_ratio.where(is_down, np.nan)
    
        window = 20
    
        # 用成交量加权的滚动均值，大成交量K线权重更大
        vol_up = volume.where(is_up, np.nan)
        vol_down = volume.where(is_down, np.nan)
    
        # 加权平均：sum(ratio * vol) / sum(vol) = sum(oi_change) / sum(vol) for each direction
        # 但我们用原始ratio的加权平均更精确
        up_oi_sum = (oi_change.where(is_up, 0)).rolling(window, min_periods=5).sum()
        up_vol_sum = (volume.where(is_up, 0)).rolling(window, min_periods=5).sum()
        down_oi_sum = (oi_change.where(is_down, 0)).rolling(window, min_periods=5).sum()
        down_vol_sum = (volume.where(is_down, 0)).rolling(window, min_periods=5).sum()
    
        up_pressure = up_oi_sum / up_vol_sum.replace(0, np.nan)
        down_pressure = down_oi_sum / down_vol_sum.replace(0, np.nan)
    
        # 不对称性：上涨时主力建仓强度 vs 下跌时主力建仓强度
        # 正值：主力在上涨时更倾向建仓（看多）
        # 负值：主力在下跌时更倾向建仓（看空）
        imbalance = up_pressure - down_pressure
    
        # 用短期与长期的差值捕捉边际变化
        window_long = 60
        up_oi_sum_l = (oi_change.where(is_up, 0)).rolling(window_long, min_periods=15).sum()
        up_vol_sum_l = (volume.where(is_up, 0)).rolling(window_long, min_periods=15).sum()
        down_oi_sum_l = (oi_change.where(is_down, 0)).rolling(window_long, min_periods=15).sum()
        down_vol_sum_l = (volume.where(is_down, 0)).rolling(window_long, min_periods=15).sum()
    
        up_pressure_l = up_oi_sum_l / up_vol_sum_l.replace(0, np.nan)
        down_pressure_l = down_oi_sum_l / down_vol_sum_l.replace(0, np.nan)
        imbalance_long = up_pressure_l - down_pressure_l
    
        # 短期imbalance相对长期的偏离：捕捉主力资金方向的边际变化
        factor = imbalance - imbalance_long
    
        # 标准化
        roll_std = factor.rolling(60, min_periods=15).std()
        factor = factor / roll_std.replace(0, np.nan)
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
    
        return factor

DISCOVERED_FACTORS['oi_volume_pressure_imbalance'] = oi_volume_pressure_imbalance


def htf_trend_alignment_score(df):
    """将日线级别（16根30分钟K线）的趋势强度与方向映射到30分钟周期，衡量短周期价格行为与长周期趋势的对齐程度，对齐越强信号越显著。
    avg |IC| = 0.0539
    """
        import numpy as np
        import pandas as pd

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        # ── 参数 ──────────────────────────────────────────────
        BARS_PER_DAY = 16          # 每个"长周期"窗口（约1个交易日）
        FAST_MA = 5                # 短周期MA（30min级别）
        SLOW_MA = 20               # 慢速MA（30min级别）
        HTF_TREND_WIN = 3          # 用多少个长周期窗口评估趋势斜率

        n = len(close)

        # ── Step 1: 构造长周期收盘价序列（滚动窗口末端值）─────
        # 每隔 BARS_PER_DAY 根K线采样一次，模拟日线收盘
        # 用滚动最后值作为"日线收盘"
        htf_close = close.rolling(window=BARS_PER_DAY, min_periods=BARS_PER_DAY).apply(
            lambda x: x.iloc[-1], raw=False
        )

        # ── Step 2: 长周期趋势方向（日线级EMA斜率）────────────
        # 对htf_close做短窗口EMA，计算斜率（一阶差分归一化）
        htf_ema_fast = htf_close.ewm(span=HTF_TREND_WIN * BARS_PER_DAY, adjust=False).mean()
        htf_ema_slow = htf_close.ewm(span=HTF_TREND_WIN * BARS_PER_DAY * 2, adjust=False).mean()

        # 长周期趋势方向：快线在慢线上方为多头，反之空头
        htf_trend_dir = np.sign(htf_ema_fast - htf_ema_slow)  # +1 / -1 / 0

        # 长周期趋势强度：快慢线偏离度（用ATR归一化）
        htf_spread = (htf_ema_fast - htf_ema_slow).abs()
        atr_30 = (high - low).rolling(window=BARS_PER_DAY).mean().replace(0, np.nan)
        htf_trend_strength = htf_spread / atr_30  # 无量纲强度

        # 归一化强度到 [0, 1]，用滚动分位数
        roll_win = BARS_PER_DAY * HTF_TREND_WIN * 4
        htf_strength_pct = htf_trend_strength.rolling(window=roll_win, min_periods=roll_win // 2).rank(pct=True)

        # ── Step 3: 短周期趋势对齐度──────────────────────────
        # 短周期MA交叉方向
        ma_fast = close.rolling(window=FAST_MA, min_periods=FAST_MA).mean()
        ma_slow = close.rolling(window=SLOW_MA, min_periods=SLOW_MA).mean()
        ltf_trend_dir = np.sign(ma_fast - ma_slow)

        # 短周期价格动量（相对自身N日前涨跌幅）
        ltf_momentum = close.pct_change(periods=FAST_MA)
        ltf_mom_dir = np.sign(ltf_momentum)

        # ── Step 4: 对齐得分合成──────────────────────────────
        # 规则：
        #   长周期趋势方向 × 短周期方向 → 同向=+1，反向=-1
        #   再乘以长周期趋势强度百分位，强趋势时放大信号
        dir_alignment = htf_trend_dir * ltf_trend_dir      # +1 对齐，-1 背离
        mom_alignment = htf_trend_dir * ltf_mom_dir        # 动量辅助确认

        # 综合对齐：方向+动量各占50%
        raw_alignment = 0.5 * dir_alignment + 0.5 * mom_alignment  # [-1, +1]

        # 用长周期强度百分位加权：强趋势时对齐/背离信号更可信
        # htf_strength_pct 在 [0,1]，转为 [-0.5, 1.5] 的增益 (弱趋势时压缩)
        strength_weight = 0.5 + htf_strength_pct  # [0.5, 1.5]

        factor = raw_alignment * strength_weight  # 范围约 [-1.5, +1.5]

        # ── Step 5: 滚动Z-score标准化，消除均值漂移────────────
        roll_std_win = BARS_PER_DAY * 10
        factor_mean = factor.rolling(window=roll_std_win, min_periods=roll_std_win // 2).mean()
        factor_std = factor.rolling(window=roll_std_win, min_periods=roll_std_win // 2).std().replace(0, np.nan)
        factor_zscore = (factor - factor_mean) / factor_std

        factor_zscore.name = 'htf_trend_alignment_score'
        return factor_zscore

DISCOVERED_FACTORS['htf_trend_alignment_score'] = htf_trend_alignment_score


def volume_shock_reversal_pressure(df):
    """捕捉成交量突发性冲击后价格未能持续突破的反转压力——当成交量出现异常放量（超过近期均值的若干倍标准差）但价格涨跌幅相对收缩时，意味着主力借量出货或吸筹完毕，后续存在反转驱动力。
    avg |IC| = 0.0263
    """
        import numpy as np
        import pandas as pd

        window = 20
        shock_mult = 2.0

        # 1. 成交量 Z-score：衡量当前成交量的异常程度
        vol_mean = df['volume'].rolling(window).mean()
        vol_std = df['volume'].rolling(window).std()
        vol_zscore = (df['volume'] - vol_mean) / (vol_std + 1e-10)

        # 2. 价格变动幅度（绝对收益率，归一化）
        price_range = (df['high'] - df['low']) / (df['close'].shift(1) + 1e-10)
        price_range_mean = price_range.rolling(window).mean()
        price_range_std = price_range.rolling(window).std()
        price_range_zscore = (price_range - price_range_mean) / (price_range_std + 1e-10)

        # 3. 量价冲击背离核心逻辑：
        #    - vol_zscore 高（异常放量）
        #    - price_range_zscore 低（价格波动相对收缩）
        #    => 两者之差越大，说明"量增价滞"，反转压力越强
        raw_signal = vol_zscore - price_range_zscore

        # 4. 方向修正：用收盘价相对于区间中点的位置判断偏向
        #    close 偏上 => 上方反转压力（做空信号为正）
        #    close 偏下 => 下方反转压力（做多信号为正）
        bar_mid = (df['high'] + df['low']) / 2.0
        close_position = (df['close'] - bar_mid) / ((df['high'] - df['low']) / 2.0 + 1e-10)
        # close_position in [-1, 1]，收盘偏上为正（看涨收盘）

        # 5. 仅在成交量冲击显著时激活因子（vol_zscore > shock_mult）
        shock_mask = (vol_zscore > shock_mult).astype(float)

        # 6. 最终因子：
        #    放量但收盘偏上 => 可能是出货 => 看跌压力 => 因子为负
        #    放量但收盘偏下 => 可能是洗盘/吸筹 => 看涨弹性 => 因子为正
        #    用 -close_position * raw_signal * shock_mask 构造
        factor_raw = -close_position * raw_signal * shock_mask

        # 7. 平滑（3期EMA）降低噪声
        factor = factor_raw.ewm(span=3, adjust=False).mean()

        factor.name = 'volume_shock_reversal_pressure'
        return factor

DISCOVERED_FACTORS['volume_shock_reversal_pressure'] = volume_shock_reversal_pressure


def oi_volume_price_pressure(df):
    """通过持仓量变化与成交量的比值（资金沉淀率）乘以价格方向，识别主力资金是在趋势方向上主动建仓（高沉淀率+顺势）还是短线投机（低沉淀率），高值表示主力顺势加仓的强压力信号
    avg |IC| = 0.0241
    """
        import numpy as np
        import pandas as pd
    
        # 持仓量变化
        delta_oi = df['open_interest'].diff()
    
        # 价格方向：用close相对于(high+low)/2的偏离度衡量bar内买卖压力
        mid_price = (df['high'] + df['low']) / 2.0
        price_pressure = (df['close'] - mid_price) / (df['high'] - df['low']).replace(0, np.nan)
    
        # 资金沉淀率：持仓变化占成交量的比例，反映有多少成交转化为持仓
        # 高沉淀率 = 主力建仓；低/负沉淀率 = 投机或平仓
        settling_rate = delta_oi / df['volume'].replace(0, np.nan)
    
        # 核心因子：沉淀率 × 价格压力方向
        # 正值大：主力顺势加仓（看多方向建仓+价格偏强，或看空方向建仓+价格偏弱取绝对值后也为正）
        raw_signal = settling_rate * price_pressure
    
        # 用滑动窗口平滑，减少噪音，取8根bar（4小时）的指数加权
        ema_signal = raw_signal.ewm(span=8, min_periods=4).mean()
    
        # 用更长周期的标准差做归一化，使因子值可比
        roll_std = raw_signal.rolling(window=40, min_periods=10).std()
    
        # 最终因子：短期EMA信号 / 长期波动率，类似z-score
        factor = ema_signal / roll_std.replace(0, np.nan)
    
        # 进一步用成交量加权的动量确认：大成交量时的信号更可信
        vol_weight = df['volume'] / df['volume'].rolling(window=20, min_periods=5).mean().replace(0, np.nan)
        vol_weight = vol_weight.clip(0.5, 3.0)  # 限制极端权重
    
        factor = factor * vol_weight
    
        factor.name = 'oi_volume_price_pressure'
        return factor

DISCOVERED_FACTORS['oi_volume_price_pressure'] = oi_volume_price_pressure


def smart_money_absorption_rate(df):
    """通过识别价格波动收窄但持仓量持续增加的"吸筹"模式，衡量主力资金在低波动区间悄然建仓的强度，吸筹越强烈因子值越高，预示后续趋势性行情启动
    avg |IC| = 0.0247
    """
        import numpy as np
        import pandas as pd
    
        # 价格波动率：用真实波幅ATR的滚动标准化衡量波动收窄程度
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
    
        # 短期ATR vs 长期ATR，比值越小说明波动越收窄
        atr_short = tr.rolling(6, min_periods=3).mean()
        atr_long = tr.rolling(24, min_periods=12).mean()
        volatility_contraction = atr_short / atr_long.replace(0, np.nan)
    
        # 持仓量变化：净增仓速率
        oi_change = df['open_interest'].diff()
        oi_change_ma = oi_change.rolling(6, min_periods=3).mean()
        oi_change_std = oi_change.rolling(24, min_periods=12).std().replace(0, np.nan)
        oi_accumulation = oi_change_ma / oi_change_std  # 标准化的增仓速率
    
        # 成交量集中度：大单行为往往表现为成交量脉冲（单根bar成交量远超均值）
        vol_ma = df['volume'].rolling(24, min_periods=12).mean().replace(0, np.nan)
        vol_spike = df['volume'] / vol_ma
        # 成交量脉冲但价格不动 => 主力对倒/吸筹
        price_return_abs = abs(df['close'].pct_change())
        price_return_ma = price_return_abs.rolling(6, min_periods=3).mean().replace(0, np.nan)
    
        # 单位价格变动消耗的成交量越大，说明有对手盘被吸收
        absorption_intensity = vol_spike / (price_return_abs / price_return_ma + 0.1)
        absorption_intensity_smooth = absorption_intensity.rolling(6, min_periods=3).mean()
    
        # 核心因子：波动收窄 × 增仓 × 吸收强度
        # 波动收窄用 (1 - contraction_ratio) 使收窄时值更大
        contraction_signal = (1 - volatility_contraction).clip(-2, 2)
    
        # 方向判断：用持仓增加时的价格方向累积判断多空
        price_dir = np.sign(df['close'].diff())
        oi_increase_mask = (oi_change > 0).astype(float)
        # 增仓时的价格方向累积
        directional_oi = (price_dir * oi_increase_mask).rolling(12, min_periods=6).sum()
    
        # 最终因子：吸筹强度 × 方向 × 波动收窄加成
        raw_factor = absorption_intensity_smooth * directional_oi * (1 + contraction_signal * 0.5)
    
        # Z-score标准化
        factor_mean = raw_factor.rolling(48, min_periods=24).mean()
        factor_std = raw_factor.rolling(48, min_periods=24).std().replace(0, np.nan)
        factor = (raw_factor - factor_mean) / factor_std
    
        factor = factor.replace([np.inf, -np.inf], np.nan)
        factor.name = 'smart_money_absorption_rate'
    
        return factor

DISCOVERED_FACTORS['smart_money_absorption_rate'] = smart_money_absorption_rate


def weekday_hour_momentum_interaction(df):
    """捕捉周内效应与日内时段效应的交互作用——不同星期几在不同交易时段（早盘/午盘/夜盘）呈现差异化的动量特征，利用历史滚动均值构建条件期望收益偏离作为因子信号
    avg |IC| = 0.0382
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
        df['ret'] = df['close'].pct_change()
    
        # 从index或推断时间信息
        if isinstance(df.index, pd.DatetimeIndex):
            timestamps = df.index
        else:
            timestamps = pd.to_datetime(df.index)
    
        df['weekday'] = timestamps.weekday  # 0=Mon, 4=Fri
        df['hour'] = timestamps.hour
    
        # 划分交易时段: 夜盘(21-23,0-2), 早盘(9-11), 午盘(13-15)
        def get_session(h):
            if h >= 21 or h <= 2:
                return 0  # night
            elif 9 <= h <= 11:
                return 1  # morning
            elif 13 <= h <= 15:
                return 2  # afternoon
            else:
                return -1
    
        df['session'] = df['hour'].apply(get_session)
    
        # 构建weekday-session组合键
        df['wd_sess'] = df['weekday'] * 10 + df['session']
    
        # 对每个weekday-session组合，计算滚动历史平均收益（过去60个交易日约120个同类bar）
        # 用expanding或rolling的方式，按组计算条件均值
        lookback = 480  # 约20个交易日 * 24 bars/day
    
        # 计算每个wd_sess组合的滚动平均收益
        df['group_mean_ret'] = np.nan
        df['group_mean_vol'] = np.nan
    
        # 使用高效的分组滚动方法
        for key in df['wd_sess'].unique():
            if key % 10 == 9:  # session == -1 mapped oddly, skip invalid
                continue
            mask = df['wd_sess'] == key
            idx = df.index[mask]
            if len(idx) < 10:
                continue
            # 滚动均值（过去同类bar的均值）
            group_ret = df.loc[idx, 'ret']
            rolling_mean = group_ret.expanding(min_periods=10).mean()
            rolling_std = group_ret.expanding(min_periods=10).std()
            df.loc[idx, 'group_mean_ret'] = rolling_mean
            df.loc[idx, 'group_mean_vol'] = rolling_std
    
        # 计算全局滚动均值作为基准
        global_rolling_mean = df['ret'].rolling(lookback, min_periods=60).mean()
        global_rolling_std = df['ret'].rolling(lookback, min_periods=60).std()
    
        # 因子 = 条件期望收益偏离全局均值，用波动率标准化
        # 即该weekday-session组合的历史均值超出全局均值的程度
        raw_signal = (df['group_mean_ret'] - global_rolling_mean)
    
        # 用条件波动率标准化，避免除零
        denom = df['group_mean_vol'].replace(0, np.nan)
        factor = raw_signal / denom
    
        # 对极端值做winsorize
        factor = factor.clip(-3, 3)
    
        # 用volume加权做平滑，增强信噪比
        factor_smooth = factor.ewm(span=8, min_periods=4).mean()
    
        factor_smooth.name = 'weekday_hour_momentum_interaction'
        return factor_smooth

DISCOVERED_FACTORS['weekday_hour_momentum_interaction'] = weekday_hour_momentum_interaction


def price_band_reversion_score(df):
    """计算收盘价相对于布林带的偏离程度，价格偏离上轨为超买（负值），偏离下轨为超卖（正值），捕捉均值回归潜力。
    avg |IC| = 0.0201
    """
        import numpy as np
        import pandas as pd

        close = df['close']
        window = 20
        bandwidth_mult = 2.0

        rolling_mean = close.rolling(window=window).mean()
        rolling_std = close.rolling(window=window).std(ddof=1)

        upper_band = rolling_mean + bandwidth_mult * rolling_std
        lower_band = rolling_mean - bandwidth_mult * rolling_std
        band_width = upper_band - lower_band

        # 价格在布林带中的相对位置：0=下轨，1=上轨
        pct_b = (close - lower_band) / band_width.replace(0, np.nan)

        # 将 %B 映射为均值回归信号：
        # pct_b > 0.5 超买区域 -> 负值（预期下跌）
        # pct_b < 0.5 超卖区域 -> 正值（预期上涨）
        reversion_raw = 0.5 - pct_b

        # 用偏离幅度加权：偏离越远，信号越强
        deviation_from_mean = (close - rolling_mean) / rolling_std.replace(0, np.nan)
        abs_dev = deviation_from_mean.abs().clip(lower=0)

        # 综合信号：方向 * 偏离强度的非线性放大
        factor = reversion_raw * (1 + abs_dev ** 1.5)

        # 滚动 z-score 标准化，消除量纲差异
        factor_mean = factor.rolling(window=window).mean()
        factor_std = factor.rolling(window=window).std(ddof=1)
        factor_zscore = (factor - factor_mean) / factor_std.replace(0, np.nan)

        factor_zscore.name = 'price_band_reversion_score'
        return factor_zscore

DISCOVERED_FACTORS['price_band_reversion_score'] = price_band_reversion_score


def weekly_trend_30m_deviation(df):
    """将长周期（以48根30分钟K线≈1个交易日×4天模拟周线级别）的趋势方向通过线性回归斜率量化，再计算当前短周期价格相对于该长周期趋势预期值的标准化偏离度，捕捉短周期价格回归长周期趋势的均值回复或趋势延续信号。
    avg |IC| = 0.0645
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 长周期窗口：48根30分钟K线 ≈ 4个交易日（黄金每日约12根30分钟K线）
        long_window = 48
        # 短周期窗口：用于计算短周期波动率
        short_window = 12
    
        factor = np.full(n, np.nan)
    
        for i in range(long_window - 1, n):
            # 长周期线性回归：对close做OLS回归，得到趋势斜率和截距
            y = close[i - long_window + 1: i + 1]
            x = np.arange(long_window, dtype=np.float64)
        
            x_mean = x.mean()
            y_mean = y.mean()
        
            ss_xx = np.sum((x - x_mean) ** 2)
            ss_xy = np.sum((x - x_mean) * (y - y_mean))
        
            if ss_xx == 0:
                continue
        
            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean
        
            # 长周期趋势在当前位置的预期价格
            trend_expected = intercept + slope * (long_window - 1)
        
            # 短周期局部波动率（用于标准化偏离度）
            if i >= short_window - 1:
                short_slice = close[i - short_window + 1: i + 1]
                local_std = np.std(short_slice, ddof=1)
            else:
                local_std = np.std(y, ddof=1)
        
            if local_std == 0 or np.isnan(local_std):
                continue
        
            # 当前价格相对长周期趋势预期值的标准化偏离
            deviation = (close[i] - trend_expected) / local_std
        
            # 用长周期斜率的符号加权：趋势方向上的偏离增强，反方向偏离减弱
            # 归一化斜率（相对于价格水平）
            norm_slope = slope * long_window / y_mean if y_mean != 0 else 0
        
            # 将成交量纳入：短周期相对于长周期的成交量比率作为信心权重
            vol_slice_long = volume[i - long_window + 1: i + 1]
            vol_slice_short = volume[i - short_window + 1: i + 1] if i >= short_window - 1 else vol_slice_long[-short_window:]
        
            vol_ratio = np.mean(vol_slice_short) / np.mean(vol_slice_long) if np.mean(vol_slice_long) > 0 else 1.0
        
            # 最终因子：偏离度 × 趋势强度符号 × 成交量信心
            # 正值表示价格在上升趋势中高于趋势线（趋势延续），负值表示下降趋势中低于趋势线
            factor[i] = deviation * np.sign(norm_slope) * np.log1p(vol_ratio)
    
        return pd.Series(factor, index=df.index, name='weekly_trend_30m_deviation')

DISCOVERED_FACTORS['weekly_trend_30m_deviation'] = weekly_trend_30m_deviation


def intraday_hour_momentum_bias(df):
    """基于30分钟K线所处的交易时段（上午/下午/夜盘）构建时段动量偏差因子，捕捉黄金期货在不同交易时段内系统性的收益率分布差异（夜盘受国际金价驱动往往动量更强，日盘则倾向于均值回复）
    avg |IC| = 0.0239
    """
        import numpy as np
        import pandas as pd
    
        # 计算每根K线的收益率
        returns = (df['close'] - df['open']) / df['open']
    
        # 通过K线在一天中的序号推断交易时段
        # SHFE黄金期货30分钟K线一个交易日约有如下时段:
        # 夜盘: 21:00-23:00, 次日00:00-01:00 (约6根)
        # 上午: 09:00-10:15, 10:30-11:30 (约5根)
        # 下午: 13:30-15:00 (约3根)
        # 用日内累计bar编号来区分时段
    
        dates = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.RangeIndex(len(df))
    
        # 使用价格变化幅度和成交量的日内模式来间接构建时段标签
        # 用bar在交易日内的序号（通过检测大间隔来分割交易日）
        price_gap = df['close'].pct_change().abs()
        vol_ratio = df['volume'] / df['volume'].rolling(14, min_periods=1).mean()
    
        # 构建周期性指标：利用bar序号模拟日内周期
        # 假设每个交易日约14根30分钟K线
        bars_per_day = 14
        bar_in_day = np.arange(len(df)) % bars_per_day
    
        # 更鲁棒的方法：用volume的周期性模式自适应检测
        # 计算滚动周期内各phase的平均收益
        lookback = bars_per_day * 20  # 20个交易日
    
        # 将bar_in_day分为3个时段
        # 时段0 (夜盘): bar 0-5, 时段1 (上午): bar 6-10, 时段2 (下午): bar 11-13
        session = np.where(bar_in_day <= 5, 0, np.where(bar_in_day <= 10, 1, 2))
        session_series = pd.Series(session, index=df.index)
    
        # 计算各时段滚动平均收益率
        session_mean_ret = pd.Series(np.nan, index=df.index, dtype=float)
        other_session_mean_ret = pd.Series(np.nan, index=df.index, dtype=float)
    
        for i in range(3):
            mask = session_series == i
            # 当前时段的滚动平均收益
            session_ret = returns.where(mask, np.nan)
            rolling_mean = session_ret.rolling(lookback, min_periods=bars_per_day * 3).mean()
            session_mean_ret = session_mean_ret.where(~mask, rolling_mean)
        
            # 其他时段的滚动平均收益
            other_ret = returns.where(~mask, np.nan)
            other_rolling_mean = other_ret.rolling(lookback, min_periods=bars_per_day * 3).mean()
            other_session_mean_ret = other_session_mean_ret.where(~mask, other_rolling_mean)
    
        # 时段动量偏差 = 当前时段历史平均收益 - 其他时段历史平均收益
        # 再乘以当前bar的成交量强度作为置信度权重
        bias = session_mean_ret - other_session_mean_ret
    
        # 用滚动标准差归一化
        bias_std = bias.rolling(lookback, min_periods=bars_per_day * 3).std()
        factor = bias / bias_std.replace(0, np.nan)
    
        # 结合当前量能异常程度增强信号
        vol_z = (df['volume'] - df['volume'].rolling(lookback, min_periods=10).mean()) / \
                df['volume'].rolling(lookback, min_periods=10).std().replace(0, np.nan)
    
        factor = factor * (1 + 0.3 * vol_z.clip(-2, 2))
    
        factor.name = 'intraday_hour_momentum_bias'
        return factor

DISCOVERED_FACTORS['intraday_hour_momentum_bias'] = intraday_hour_momentum_bias


def big_order_oi_divergence(df):
    """通过检测成交量突增（大单代理）时持仓量变化方向与价格变化方向的背离程度，识别主力资金隐蔽建仓或出货行为
    avg |IC| = 0.0404
    """
        import numpy as np
        import pandas as pd
    
        close = df['close']
        volume = df['volume']
        oi = df['open_interest']
    
        # 价格变化和持仓变化
        price_ret = close.pct_change()
        oi_change = oi.diff()
    
        # 识别大单：成交量超过过去20根K线均值1.5倍标准差
        vol_ma = volume.rolling(20, min_periods=5).mean()
        vol_std = volume.rolling(20, min_periods=5).std()
        big_order_flag = (volume > vol_ma + 1.5 * vol_std).astype(float)
    
        # 对所有bar计算：价格方向 vs 持仓变化方向的一致性
        # 主力建仓：价格微动但持仓大增（或反向）-> 背离
        # 用符号一致性衡量：price_ret * oi_change 同号=顺势，异号=背离
    
        # 标准化持仓变化和价格变化以使其可比
        oi_change_norm = oi_change / oi_change.rolling(20, min_periods=5).std().replace(0, np.nan)
        price_ret_norm = price_ret / price_ret.rolling(20, min_periods=5).std().replace(0, np.nan)
    
        # 背离度：大单时持仓变化幅度远超价格变化幅度的程度（主力吸筹信号）
        # 正值：持仓增加但价格未涨（主力多头建仓）或持仓减少但价格未跌（主力空头平仓）
        divergence = oi_change_norm - price_ret_norm * np.sign(oi_change_norm)
    
        # 仅在大单时加权，非大单时衰减
        weight = big_order_flag * 2.0 + (1 - big_order_flag) * 0.3
        weighted_div = divergence * weight
    
        # 滚动累积：过去10根K线的加权背离信号
        factor = weighted_div.rolling(10, min_periods=3).sum()
    
        # 再用较长窗口做z-score标准化，使因子平稳
        factor_ma = factor.rolling(40, min_periods=10).mean()
        factor_std = factor.rolling(40, min_periods=10).std().replace(0, np.nan)
        factor_z = (factor - factor_ma) / factor_std
    
        factor_z.name = 'big_order_oi_divergence'
        return factor_z

DISCOVERED_FACTORS['big_order_oi_divergence'] = big_order_oi_divergence


def adaptive_mean_reversion_intensity(df):
    """基于自适应布林带宽度归一化的价格偏离度，当价格偏离动态均值超过波动率调整阈值时捕捉均值回归机会，同时用持仓量变化确认反转信号强度
    avg |IC| = 0.0200
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
        oi = df['open_interest'].copy()
        high = df['high'].copy()
        low = df['low'].copy()
    
        # 多周期加权均值：用成交量加权的VWAP作为"真实均值"
        vwap_period = 20
        typical_price = (high + low + close) / 3.0
        cum_tp_vol = (typical_price * volume).rolling(vwap_period).sum()
        cum_vol = volume.rolling(vwap_period).sum()
        rolling_vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    
        # 价格偏离VWAP的程度
        deviation = close - rolling_vwap
    
        # 自适应波动率：用Garman-Klass估计器替代简单std，更精确
        log_hl = np.log(high / low.replace(0, np.nan))
        log_co = np.log(close / df['open'].replace(0, np.nan))
        gk_var = 0.5 * log_hl**2 - (2 * np.log(2) - 1) * log_co**2
        adaptive_vol = gk_var.rolling(vwap_period).mean().apply(lambda x: np.sqrt(abs(x)) if not np.isnan(x) else np.nan)
        adaptive_vol = adaptive_vol.replace(0, np.nan)
    
        # 归一化偏离度（Z-score形式）
        z_deviation = deviation / (adaptive_vol * close)
    
        # 持仓量确认：OI下降时偏离更可能回归（趋势衰竭）
        oi_change_pct = oi.pct_change(5)
        # OI下降 -> 回归信号增强（乘以负OI变化的sigmoid）
        oi_signal = 1.0 / (1.0 + np.exp(10 * oi_change_pct))  # OI下降时接近1，上升时接近0
    
        # 价格在近期range中的位置（Stochastic思想），极端位置增强信号
        period_high = high.rolling(20).max()
        period_low = low.rolling(20).min()
        range_width = period_high - period_low
        price_position = (close - period_low) / range_width.replace(0, np.nan)
        # 转换为对称的超买超卖指标 [-1, 1]
        extremity = 2 * price_position - 1
    
        # 综合因子：偏离度 * OI确认 * 极端度确认，取负号使其为均值回归方向
        # 价格高于均值且处于超买 -> 因子为负（预期下跌）
        # 价格低于均值且处于超卖 -> 因子为正（预期上涨）
        raw_factor = -z_deviation * (0.5 + 0.5 * oi_signal) * (0.5 + 0.5 * abs(extremity))
    
        # 用短期动量衰减过滤：近3根K线的动量减弱才确认回归
        mom_3 = close.pct_change(3)
        mom_10 = close.pct_change(10)
        # 动量衰减：短期动量弱于长期动量方向
        momentum_decay = np.where(
            np.sign(mom_3) == np.sign(mom_10),
            np.where(abs(mom_3) < abs(mom_10) * 0.3, 1.5, 0.7),  # 动量衰减增强信号
            1.2  # 动量反转也增强
        )
    
        factor = raw_factor * momentum_decay
    
        # 最终平滑避免噪音
        factor = pd.Series(factor, index=df.index).rolling(3, min_periods=1).mean()
    
        return factor

DISCOVERED_FACTORS['adaptive_mean_reversion_intensity'] = adaptive_mean_reversion_intensity


def weekly_trend_halfhour_projection(df):
    """将周级别(240根30分钟K线约5个交易日)的趋势强度通过线性回归斜率标准化后，投影到短周期动量上，捕捉长周期趋势对短周期价格运动的放大或抑制效应
    avg |IC| = 0.0540
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 长周期参数：240根30min bar ≈ 5个交易日(一周)
        long_window = 240
        # 短周期参数：16根30min bar ≈ 1个交易日
        short_window = 16
    
        # 计算长周期趋势：用线性回归斜率标准化为t-stat
        def rolling_trend_tstat(arr, window):
            result = np.full(len(arr), np.nan)
            x = np.arange(window, dtype=float)
            x_demean = x - x.mean()
            ss_x = np.sum(x_demean ** 2)
            for i in range(window - 1, len(arr)):
                y = arr[i - window + 1: i + 1]
                if np.any(np.isnan(y)):
                    continue
                y_demean = y - np.mean(y)
                slope = np.sum(x_demean * y_demean) / ss_x
                y_hat = np.mean(y) + slope * x_demean
                residuals = y - (np.mean(y) + slope * x)
                # 修正：用正确的x
                y_pred = slope * x + (np.mean(y) - slope * np.mean(x))
                resid = y - y_pred
                sse = np.sum(resid ** 2)
                mse = sse / max(window - 2, 1)
                se_slope = np.sqrt(mse / ss_x) if mse > 0 else np.nan
                if se_slope and se_slope > 1e-12:
                    result[i] = slope / se_slope
                else:
                    result[i] = 0.0
            return result
    
        # 长周期趋势t统计量（归一化的趋势强度）
        log_close = np.log(close, where=close > 0, out=np.full(n, np.nan))
        long_tstat = rolling_trend_tstat(log_close, long_window)
    
        # 短周期动量：短窗口收益率
        short_ret = np.full(n, np.nan)
        for i in range(short_window, n):
            if close[i - short_window] > 0:
                short_ret[i] = (close[i] - close[i - short_window]) / close[i - short_window]
    
        # 短周期波动率用于标准化短周期动量
        short_vol = np.full(n, np.nan)
        log_ret = np.full(n, np.nan)
        for i in range(1, n):
            if close[i - 1] > 0 and close[i] > 0:
                log_ret[i] = np.log(close[i] / close[i - 1])
    
        for i in range(short_window, n):
            window_rets = log_ret[i - short_window + 1: i + 1]
            valid = window_rets[~np.isnan(window_rets)]
            if len(valid) > 2:
                short_vol[i] = np.std(valid) * np.sqrt(short_window)
    
        # 投影因子：长周期趋势强度 × 短周期标准化动量
        # 金融逻辑：当长周期趋势强时，顺趋势的短周期动量被放大（趋势延续）
        factor = np.full(n, np.nan)
        for i in range(n):
            if (not np.isnan(long_tstat[i]) and not np.isnan(short_ret[i]) 
                and not np.isnan(short_vol[i]) and short_vol[i] > 1e-10):
                norm_short_mom = short_ret[i] / short_vol[i]
                # 用tanh压缩长周期趋势避免极端值
                trend_signal = np.tanh(long_tstat[i] / 3.0)
                factor[i] = trend_signal * norm_short_mom
    
        return pd.Series(factor, index=df.index, name='weekly_trend_halfhour_projection')

DISCOVERED_FACTORS['weekly_trend_halfhour_projection'] = weekly_trend_halfhour_projection


def oi_volume_directional_conviction(df):
    """通过持仓量变化与成交量的比值（沉淀率）在价格上涨和下跌时的不对称性，捕捉主力资金在多空方向上的建仓conviction差异，高值表示主力倾向于在上涨时沉淀资金（看多conviction强于看空）
    avg |IC| = 0.0266
    """
        import numpy as np
        import pandas as pd
    
        ret = df['close'].pct_change()
        oi_chg = df['open_interest'].diff()
        vol = df['volume'].replace(0, np.nan)
    
        # 沉淀率：每单位成交量带来的持仓变化，反映资金是沉淀（建仓）还是流出（平仓）
        settle_rate = oi_chg / vol
    
        # 区分上涨bar和下跌bar
        up_mask = ret > 0
        down_mask = ret < 0
    
        window = 20
    
        # 上涨时的平均沉淀率（主力在上涨中建仓的意愿）
        up_settle = settle_rate.where(up_mask, np.nan)
        down_settle = settle_rate.where(down_mask, np.nan)
    
        # 使用指数加权，给近期更多权重
        up_mean = up_settle.ewm(span=window, min_periods=5).mean()
        down_mean = down_settle.ewm(span=window, min_periods=5).mean()
    
        # 上涨时沉淀率高（主力建多仓）且下跌时沉淀率低或为负（主力不建空仓/平仓）
        # 二者之差反映主力方向性conviction
        raw_factor = up_mean - down_mean
    
        # 用成交量加权的波动率做标准化，使因子在不同波动环境下可比
        vol_ma = vol.rolling(window, min_periods=5).mean()
        oi_ma = df['open_interest'].rolling(window, min_periods=5).mean()
        norm_factor = (oi_ma / vol_ma).replace(0, np.nan)
    
        factor = raw_factor / norm_factor
    
        # 去极值
        factor = factor.clip(factor.quantile(0.005), factor.quantile(0.995))
    
        return factor

DISCOVERED_FACTORS['oi_volume_directional_conviction'] = oi_volume_directional_conviction


def smart_money_pressure_index(df):
    """通过识别成交量萎缩但持仓量显著变化的K线（静默建仓/减仓），结合价格方向构建主力资金压力指标，捕捉机构在低成交量环境下的隐蔽方向性操作
    avg |IC| = 0.0204
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
    
        # 价格变动方向与幅度
        price_return = df['close'].pct_change()
    
        # 持仓量变化
        oi_change = df['open_interest'].diff()
    
        # 成交量的滚动中位数，用于判断"低量"环境
        vol_median_20 = df['volume'].rolling(20, min_periods=5).median()
        vol_ratio = df['volume'] / vol_median_20.replace(0, np.nan)
    
        # 识别低量环境：成交量低于中位数的60%
        low_vol_mask = vol_ratio < 0.6
    
        # 单位成交量的持仓变化强度（主力静默操作信号）
        # 高OI变化/低成交量 = 主力在悄悄建仓或平仓
        oi_per_vol = oi_change / df['volume'].replace(0, np.nan)
    
        # 用价格方向给持仓变化签名：
        # 价格上涨 + OI增加 = 多头主力建仓（正向压力）
        # 价格下跌 + OI增加 = 空头主力建仓（负向压力）
        # 价格上涨 + OI减少 = 空头平仓（正向但力度弱，打折）
        # 价格下跌 + OI减少 = 多头平仓（负向但力度弱，打折）
    
        sign_price = np.sign(price_return)
        sign_oi = np.sign(oi_change)
    
        # 建仓行为权重1.0，平仓行为权重0.5
        action_weight = np.where(sign_oi * sign_price > 0, 1.0,   # 顺向建仓
                        np.where(sign_oi * sign_price < 0, 0.5,    # 逆向（平仓驱动）
                        0.3))                                       # 中性
    
        # 核心信号：在低量环境下放大，高量环境下衰减
        vol_amplifier = np.where(low_vol_mask, 2.0, 1.0 / (vol_ratio.clip(lower=0.5)))
    
        # 带符号的主力压力原始值
        raw_pressure = sign_price * np.abs(oi_per_vol) * action_weight * vol_amplifier
    
        # 处理异常值
        raw_pressure = pd.Series(raw_pressure, index=df.index)
        raw_pressure = raw_pressure.replace([np.inf, -np.inf], np.nan)
    
        # 滚动累积：短期（6根=3小时）主力行为累积方向
        cum_pressure_short = raw_pressure.rolling(6, min_periods=3).sum()
        # 中期（20根=10小时≈2.5交易日）趋势
        cum_pressure_long = raw_pressure.rolling(20, min_periods=8).mean()
    
        # 短期累积与中期趋势的交叉强度
        factor = cum_pressure_short - cum_pressure_long * 6  # 尺度对齐
    
        # Z-score标准化（滚动60根窗口）
        factor_mean = factor.rolling(60, min_periods=20).mean()
        factor_std = factor.rolling(60, min_periods=20).std().replace(0, np.nan)
        factor_z = (factor - factor_mean) / factor_std
    
        # clip极端值
        factor_z = factor_z.clip(-4, 4)
    
        return factor_z

DISCOVERED_FACTORS['smart_money_pressure_index'] = smart_money_pressure_index


def multi_horizon_trend_pressure(df):
    """将长周期（日线级别~8根30min bar）的趋势方向与强度映射到短周期，通过长周期趋势斜率对短周期价格偏离的加权，捕捉长周期趋势对短周期回调/延续的压制或助推效应。
    avg |IC| = 0.0334
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].copy()
        volume = df['volume'].copy()
    
        # 长周期参数：8根30min bar ≈ 1个交易日(4h)，48根 ≈ 约3个交易日
        long_window = 48  # 长周期趋势窗口
        short_window = 8   # 短周期偏离窗口
    
        # 1. 长周期趋势：用线性回归斜率衡量趋势方向和强度
        def rolling_slope(series, window):
            """计算滚动线性回归斜率，并用标准差归一化"""
            slopes = pd.Series(np.nan, index=series.index)
            x = np.arange(window, dtype=float)
            x_demean = x - x.mean()
            x_var = (x_demean ** 2).sum()
        
            for i in range(window - 1, len(series)):
                y = series.iloc[i - window + 1: i + 1].values
                if np.any(np.isnan(y)):
                    continue
                y_demean = y - y.mean()
                slope = (x_demean * y_demean).sum() / x_var
                # 用价格标准差归一化斜率
                y_std = np.std(y)
                if y_std > 1e-10:
                    slopes.iloc[i] = slope / y_std
                else:
                    slopes.iloc[i] = 0.0
            return slopes
    
        long_trend_slope = rolling_slope(close, long_window)
    
        # 2. 长周期趋势的R²：衡量趋势的可靠性/线性程度
        r_squared = pd.Series(np.nan, index=close.index)
        x = np.arange(long_window, dtype=float)
        x_demean = x - x.mean()
        x_var = (x_demean ** 2).sum()
    
        for i in range(long_window - 1, len(close)):
            y = close.iloc[i - long_window + 1: i + 1].values
            if np.any(np.isnan(y)):
                continue
            y_demean = y - y.mean()
            slope = (x_demean * y_demean).sum() / x_var
            y_hat = slope * x_demean
            ss_res = ((y_demean - y_hat) ** 2).sum()
            ss_tot = (y_demean ** 2).sum()
            if ss_tot > 1e-10:
                r_squared.iloc[i] = 1.0 - ss_res / ss_tot
            else:
                r_squared.iloc[i] = 0.0
    
        # 3. 短周期价格偏离：当前价格相对短周期均线的偏离（z-score化）
        short_ma = close.rolling(short_window, min_periods=short_window).mean()
        short_std = close.rolling(short_window, min_periods=short_window).std()
        short_deviation = (close - short_ma) / short_std.replace(0, np.nan)
    
        # 4. 短周期成交量相对强度（短/长），作为映射的权重调节
        vol_short_ma = volume.rolling(short_window, min_periods=short_window).mean()
        vol_long_ma = volume.rolling(long_window, min_periods=long_window).mean()
        vol_ratio = vol_short_ma / vol_long_ma.replace(0, np.nan)
    
        # 5. 因子合成：长周期趋势强度 × R² × 短周期顺/逆趋势偏离 × 成交量配合度
        # 正值：短周期偏离方向与长周期趋势一致且有量配合 → 趋势延续信号
        # 负值：短周期偏离方向与长周期趋势相反 → 回调受压信号
        factor = long_trend_slope * r_squared * short_deviation * vol_ratio
    
        # 对极端值做winsorize
        factor = factor.clip(factor.quantile(0.005), factor.quantile(0.995))
    
        factor.name = 'multi_horizon_trend_pressure'
        return factor

DISCOVERED_FACTORS['multi_horizon_trend_pressure'] = multi_horizon_trend_pressure


def session_volatility_anomaly(df):
    """计算当前30分钟K线所处交易时段（上午/下午/夜盘）的已实现波动率相对于该时段历史滚动均值的偏离度，捕捉特定时段波动率异常放大或收缩带来的均值回归机会
    avg |IC| = 0.0211
    """
        import numpy as np
        import pandas as pd
    
        df = df.copy()
    
        # 从索引或行号推断时段信息
        # SHFE黄金期货30分钟K线时段：
        # 夜盘: 21:00-02:30 (大致bar序号)
        # 上午: 09:00-11:30
        # 下午: 13:30-15:00
        # 用bar在当日内的序号来判断时段
    
        # 计算每根K线的已实现波动率（用log return的绝对值作为瞬时波动率代理）
        log_ret = np.log(df['close'] / df['open']).abs()
        hl_vol = np.log(df['high'] / df['low'])  # 高低波动幅度
    
        # 构建日内bar序号：通过检测日切换（close价格大幅跳变或volume模式重置）
        # 更稳健的方法：用累计volume重置检测新交易日
        # 简化：用索引如果是datetime，否则用volume pattern
    
        if isinstance(df.index, pd.DatetimeIndex):
            hour = df.index.hour
            # 夜盘: 21,22,23,0,1,2
            # 上午: 9,10,11
            # 下午: 13,14
            session = pd.Series(0, index=df.index)
            session[hour.isin([21, 22, 23, 0, 1, 2])] = 0  # 夜盘
            session[hour.isin([9, 10, 11])] = 1              # 上午
            session[hour.isin([13, 14, 15])] = 2              # 下午
        else:
            # 无时间索引时，用bar序号对每日bar数取模模拟时段
            # 假设每天约14根30分钟bar
            bars_per_day = 14
            bar_idx = np.arange(len(df)) % bars_per_day
            session = pd.Series(0, index=df.index)
            session[bar_idx < 6] = 0    # 夜盘（前6根）
            session[(bar_idx >= 6) & (bar_idx < 11)] = 1  # 上午
            session[bar_idx >= 11] = 2  # 下午
    
        df['session'] = session.values
        df['hl_vol'] = hl_vol.values
    
        # 对每个时段，计算滚动历史均值和标准差（过去20个同时段bar）
        lookback = 20
    
        factor = pd.Series(np.nan, index=df.index)
    
        for s in [0, 1, 2]:
            mask = df['session'] == s
            session_vol = df.loc[mask, 'hl_vol']
        
            if len(session_vol) < lookback + 1:
                continue
        
            roll_mean = session_vol.rolling(window=lookback, min_periods=10).mean()
            roll_std = session_vol.rolling(window=lookback, min_periods=10).std()
        
            # Z-score: 当前时段波动率相对历史的偏离
            z = (session_vol - roll_mean) / (roll_std + 1e-10)
        
            factor.loc[mask] = z.values
    
        # 前向填充，使非该时段的bar也有值（用最近一次的异常度）
        factor = factor.ffill()
    
        # 取负号：波动率异常高时预期均值回归（做空波动方向）
        factor = -factor
    
        return factor

DISCOVERED_FACTORS['session_volatility_anomaly'] = session_volatility_anomaly


def volume_impulse_price_elasticity(df):
    """衡量成交量脉冲（突发放量）对价格变动的弹性系数，当单位成交量冲击引起的价格变动逐渐减小时，表明市场吸收能力增强，价格趋势可能反转
    avg |IC| = 0.0345
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        high = df['high'].values
        low = df['low'].values
        n = len(close)
    
        # 价格变动幅度（用high-low捕捉bar内波动）
        price_range = high - low
        ret_abs = np.abs(np.concatenate([[np.nan], np.diff(close)]))
    
        # 成交量相对于近期均值的倍数（量冲击强度）
        vol_ma = pd.Series(volume).rolling(20, min_periods=5).mean().values
        vol_ratio = volume / np.where(vol_ma > 0, vol_ma, np.nan)
    
        # 识别成交量脉冲：vol_ratio > 1.5 的bar视为放量冲击
        # 计算每根bar的"价格弹性" = 价格变动 / 成交量冲击强度
        # 用price_range + ret_abs综合衡量价格响应
        price_response = (price_range + ret_abs) / 2.0
    
        # 价格弹性：单位量冲击带来的价格响应
        elasticity = price_response / np.where(vol_ratio > 0.01, vol_ratio, np.nan)
    
        # 对弹性做标准化：用近期弹性的均值和标准差
        elasticity_s = pd.Series(elasticity)
        elas_ma = elasticity_s.rolling(30, min_periods=10).mean()
        elas_std = elasticity_s.rolling(30, min_periods=10).std()
    
        # 只在放量bar上计算有效弹性变化，其余用NaN
        vol_ratio_s = pd.Series(vol_ratio)
        is_impulse = vol_ratio_s > 1.3
    
        # 放量时弹性相对历史的z-score
        elas_z = (elasticity_s - elas_ma) / elas_std.replace(0, np.nan)
    
        # 核心信号：近期放量bar的弹性z均值（滚动窗口）
        # 弹性下降（z<0）说明放量但价格不动 -> 趋势衰竭信号
        impulse_elas = elas_z.where(is_impulse, np.nan)
    
        # 用expanding forward-fill + rolling来获取近期放量事件的平均弹性
        # 采用指数加权方式聚合最近的放量弹性信号
        factor = impulse_elas.rolling(window=20, min_periods=3).mean()
    
        # 叠加量价背离维度：价格创新高/新低但弹性走低
        close_s = pd.Series(close)
        price_pctile = close_s.rolling(20, min_periods=5).apply(
            lambda x: np.sum(x[-1] >= x) / len(x), raw=True
        )
    
        # 价格在高位但弹性低 -> 负信号（顶部吸收）
        # 价格在低位但弹性低 -> 正信号（底部吸收）
        price_position = 2 * (price_pctile - 0.5)  # [-1, 1]
    
        # 最终因子：弹性信号 * (-价格位置) 
        # 高位+低弹性=负值（看跌），低位+低弹性=正值（看涨）
        combined = -factor * price_position
    
        result = pd.Series(combined, index=df.index, name='volume_impulse_price_elasticity')
        return result

DISCOVERED_FACTORS['volume_impulse_price_elasticity'] = volume_impulse_price_elasticity


def vwap_deviation_mean_reversion_z(df):
    """计算当前收盘价相对于多周期自适应VWAP的标准化偏离度，并结合偏离度的均值回归速度（一阶差分）来捕捉超买超卖后的回归信号
    avg |IC| = 0.0252
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
    
        typical_price = (high + low + close) / 3.0
    
        # 计算多周期VWAP偏离并融合
        windows = [24, 48, 96]  # 对应约半天、一天、两天的30分钟K线
    
        z_scores = []
        for w in windows:
            cum_tp_vol = pd.Series(typical_price * volume).rolling(w, min_periods=int(w * 0.7)).sum().values
            cum_vol = pd.Series(volume, dtype=float).rolling(w, min_periods=int(w * 0.7)).sum().values
        
            vwap = cum_tp_vol / np.where(cum_vol > 0, cum_vol, np.nan)
        
            # 偏离度
            deviation = close - vwap
        
            # 用滚动标准差标准化
            dev_series = pd.Series(deviation)
            dev_mean = dev_series.rolling(w, min_periods=int(w * 0.7)).mean().values
            dev_std = dev_series.rolling(w, min_periods=int(w * 0.7)).std().values
        
            z = (deviation - dev_mean) / np.where(dev_std > 1e-10, dev_std, np.nan)
            z_scores.append(z)
    
        z_scores = np.array(z_scores)
        # 多周期加权平均，短周期权重更高以捕捉即时超买超卖
        weights = np.array([0.5, 0.3, 0.2]).reshape(-1, 1)
        composite_z = np.nansum(z_scores * weights, axis=0) / np.nansum(weights * (~np.isnan(z_scores)).astype(float), axis=0)
    
        # 计算z-score的一阶差分（均值回归速度）：当z很高但开始下降时，回归信号更强
        composite_z_series = pd.Series(composite_z)
        z_velocity = composite_z_series.diff(3).values  # 3根K线的变化
    
        # 最终因子：z-score的绝对水平 * 回归方向信号
        # 当z>0且velocity<0（超买开始回落）-> 负值（看空）
        # 当z<0且velocity>0（超卖开始回升）-> 正值（看多）
        # 用 -z * |velocity| 的符号一致性来增强信号
    
        # 简化：当偏离和速度方向相反时，取反向信号强度
        reversion_signal = -composite_z * np.abs(z_velocity)
    
        # 当偏离和速度同向时（趋势仍在加强），信号减弱
        same_direction = np.sign(composite_z) == np.sign(z_velocity)
        reversion_signal[same_direction] = reversion_signal[same_direction] * 0.3
    
        factor = pd.Series(reversion_signal, index=df.index, name='vwap_deviation_mean_reversion_z')
    
        return factor

DISCOVERED_FACTORS['vwap_deviation_mean_reversion_z'] = vwap_deviation_mean_reversion_z


def smart_money_volume_divergence(df):
    """通过识别价格变动幅度与成交量不匹配的"聪明钱"行为——大资金在低量时悄然建仓（价格小幅波动但持仓量显著增加）或在高量时反向出货（放量但价格未能有效突破），衡量主力资金的真实方向与市场表面走势的背离程度。
    avg |IC| = 0.0219
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        oi = df['open_interest'].values
        high = df['high'].values
        low = df['low'].values
    
        n = len(close)
        factor = pd.Series(np.nan, index=df.index)
    
        # 价格变动率（绝对值）
        price_ret = np.zeros(n)
        price_ret[1:] = (close[1:] - close[:-1]) / np.where(close[:-1] != 0, close[:-1], 1)
    
        # 价格方向
        price_dir = np.sign(price_ret)
    
        # OI变化率
        oi_change = np.zeros(n)
        oi_change[1:] = oi[1:] - oi[:-1]
    
        # 成交量标准化（rolling z-score，窗口20）
        vol_series = pd.Series(volume, index=df.index)
        vol_ma = vol_series.rolling(20, min_periods=5).mean()
        vol_std = vol_series.rolling(20, min_periods=5).std()
        vol_zscore = ((vol_series - vol_ma) / vol_std.replace(0, np.nan)).values
    
        # 价格波动幅度标准化
        price_range = (high - low) / np.where(close != 0, close, 1)
        pr_series = pd.Series(price_range, index=df.index)
        pr_ma = pr_series.rolling(20, min_periods=5).mean()
        pr_std = pr_series.rolling(20, min_periods=5).std()
        pr_zscore = ((pr_series - pr_ma) / pr_std.replace(0, np.nan)).values
    
        # 聪明钱信号：低波动+低量+OI大幅变化 → 主力悄然建仓/减仓
        # 用OI变化方向作为主力真实意图的代理
        # 背离度 = OI变化方向 * (OI变化幅度归一化) * (1 - 量价匹配度)
    
        oi_change_series = pd.Series(oi_change, index=df.index)
        oi_ma = oi_change_series.abs().rolling(20, min_periods=5).mean()
        oi_std = oi_change_series.abs().rolling(20, min_periods=5).std()
        oi_intensity = (oi_change_series.abs() / oi_ma.replace(0, np.nan)).values
    
        # 量价匹配度：高量应对应高波动，低量对应低波动
        # 不匹配时说明有主力操控
        vol_price_mismatch = np.abs(vol_zscore - pr_zscore)
    
        # 主力方向信号：OI增加且价格上涨→多头建仓(+)，OI增加且价格下跌→空头建仓(-)
        # OI减少且价格上涨→空头平仓(+弱)，OI减少且价格下跌→多头平仓(-弱)
        raw_signal = np.sign(oi_change) * price_dir * oi_intensity * (1 + vol_price_mismatch)
    
        # 当OI增加（新仓位）时信号更强，给予额外权重
        oi_adding = (oi_change > 0).astype(float)
        weighted_signal = raw_signal * (1 + 0.5 * oi_adding)
    
        # 滚动累积（8根K线 = 4小时）捕捉主力持续行为
        sig_series = pd.Series(weighted_signal, index=df.index)
        factor = sig_series.rolling(8, min_periods=3).sum()
    
        # 再做一次标准化以稳定因子分布
        f_ma = factor.rolling(40, min_periods=10).mean()
        f_std = factor.rolling(40, min_periods=10).std()
        factor = (factor - f_ma) / f_std.replace(0, np.nan)
    
        return factor

DISCOVERED_FACTORS['smart_money_volume_divergence'] = smart_money_volume_divergence


def weekly_trend_bar_resonance(df):
    """将周线级别（120根30分钟K线≈一周）的趋势强度通过线性回归斜率量化，再与当前短周期（10根K线）动量方向对齐度加权，捕捉长周期趋势对短周期的共振放大效应
    avg |IC| = 0.0503
    """
        import numpy as np
        import pandas as pd
    
        close = df['close'].values
        volume = df['volume'].values
        n = len(close)
    
        # 长周期参数：120根30min bar ≈ 1周(每天约8个交易时段*5天*3根=120)
        long_window = 120
        # 中周期参数：40根 ≈ 约2天
        mid_window = 40
        # 短周期参数
        short_window = 10
    
        factor = np.full(n, np.nan)
    
        # 预计算对数收盘价
        log_close = np.log(close)
    
        def linreg_slope_normalized(y_arr):
            """计算线性回归斜率并用标准差归一化，得到趋势强度"""
            m = len(y_arr)
            x = np.arange(m, dtype=np.float64)
            x_mean = x.mean()
            y_mean = y_arr.mean()
            ss_xx = np.sum((x - x_mean) ** 2)
            if ss_xx < 1e-15:
                return 0.0
            ss_xy = np.sum((x - x_mean) * (y_arr - y_mean))
            slope = ss_xy / ss_xx
            y_std = np.std(y_arr)
            if y_std < 1e-15:
                return 0.0
            # R-squared作为趋势的可信度
            y_hat = slope * x + (y_mean - slope * x_mean)
            ss_res = np.sum((y_arr - y_hat) ** 2)
            ss_tot = np.sum((y_arr - y_mean) ** 2)
            if ss_tot < 1e-15:
                return 0.0
            r_sq = 1.0 - ss_res / ss_tot
            # 斜率归一化 * sqrt(R^2) 作为趋势质量
            return (slope / y_std) * m * np.sqrt(max(r_sq, 0.0))
    
        for i in range(long_window - 1, n):
            # 长周期趋势强度（方向+质量）
            long_seg = log_close[i - long_window + 1: i + 1]
            long_trend = linreg_slope_normalized(long_seg)
        
            # 中周期趋势强度
            if i >= mid_window - 1:
                mid_seg = log_close[i - mid_window + 1: i + 1]
                mid_trend = linreg_slope_normalized(mid_seg)
            else:
                mid_trend = 0.0
        
            # 短周期动量（简单收益率归一化）
            if i >= short_window - 1:
                short_seg = log_close[i - short_window + 1: i + 1]
                short_mom = short_seg[-1] - short_seg[0]
                short_std = np.std(np.diff(short_seg))
                if short_std > 1e-15:
                    short_mom_norm = short_mom / (short_std * np.sqrt(short_window))
                else:
                    short_mom_norm = 0.0
            else:
                short_mom_norm = 0.0
        
            # 成交量加权：近期成交量相对均值的比率，放大活跃时段信号
            vol_seg = volume[i - short_window + 1: i + 1] if i >= short_window - 1 else volume[max(0, i-4): i+1]
            vol_ratio = vol_seg[-1] / (np.mean(vol_seg) + 1e-15)
            vol_weight = np.clip(vol_ratio, 0.5, 3.0)
        
            # 共振度：长周期与短周期方向一致时放大，不一致时压缩
            # 同时融入中周期形成三级共振
            long_sign = np.sign(long_trend)
            mid_sign = np.sign(mid_trend)
            short_sign = np.sign(short_mom_norm)
        
            # 三级共振系数：全同向=1.5，两级同向=1.0，全不同=-0.5
            alignment = (long_sign * short_sign + long_sign * mid_sign + mid_sign * short_sign) / 3.0
            resonance = 0.5 + alignment  # 范围 [-0.5, 1.5]
        
            # 最终因子 = 长周期趋势强度 * 短周期动量 * 共振系数 * 成交量权重
            factor[i] = long_trend * abs(short_mom_norm) * resonance * vol_weight * np.sign(short_mom_norm)
    
        return pd.Series(factor, index=df.index, name='weekly_trend_bar_resonance')

DISCOVERED_FACTORS['weekly_trend_bar_resonance'] = weekly_trend_bar_resonance


def volume_price_impact_decay(df):
    """衡量成交量冲击对价格的边际影响随时间衰减的速率，若单位成交量驱动的价格变动持续缩小则表明市场吸收能力增强，反之则暗示流动性枯竭下的价格脆弱性
    avg |IC| = 0.0318
    """
        import numpy as np
        import pandas as pd
    
        # 每根K线的价格变动幅度（绝对值）
        price_move = (df['close'] - df['open']).abs()
    
        # 单位成交量的价格冲击力（避免除零）
        vol_safe = df['volume'].replace(0, np.nan)
        unit_impact = price_move / vol_safe
    
        # 计算短期和长期的单位成交量价格冲击均值
        short_window = 6   # 3小时
        long_window = 24    # 12小时（约2.5个交易日）
    
        impact_short = unit_impact.rolling(window=short_window, min_periods=3).mean()
        impact_long = unit_impact.rolling(window=long_window, min_periods=12).mean()
    
        # 冲击衰减比率：短期冲击/长期冲击
        # >1 表示近期单位成交量推动价格能力增强（流动性变差/趋势加速）
        # <1 表示近期单位成交量推动价格能力减弱（流动性改善/趋势衰竭）
        impact_ratio = impact_short / impact_long
    
        # 结合成交量异常度进行加权：成交量越异常，信号越强
        vol_ma = df['volume'].rolling(window=long_window, min_periods=12).mean()
        vol_std = df['volume'].rolling(window=long_window, min_periods=12).std()
        vol_z = (df['volume'] - vol_ma) / vol_std.replace(0, np.nan)
        vol_z_smooth = vol_z.rolling(window=short_window, min_periods=3).mean()
    
        # 用价格方向给因子赋方向性
        price_direction = np.sign(df['close'] - df['open']).rolling(window=short_window, min_periods=3).mean()
    
        # 最终因子：方向性 × 冲击衰减比率的对数 × 成交量异常度
        # 对数化使分布更对称
        log_impact_ratio = np.log(impact_ratio.replace(0, np.nan))
    
        # 成交量异常时冲击力增强 → 趋势可能加速（同向信号）
        # 成交量异常时冲击力衰减 → 大量成交但价格不动（反转信号）
        factor = log_impact_ratio * (1 + vol_z_smooth.clip(-2, 2)) * price_direction
    
        # 标准化处理
        factor_ma = factor.rolling(window=48, min_periods=24).mean()
        factor_std = factor.rolling(window=48, min_periods=24).std()
        factor_z = (factor - factor_ma) / factor_std.replace(0, np.nan)
    
        factor_z = factor_z.clip(-3, 3)
    
        return factor_z

DISCOVERED_FACTORS['volume_price_impact_decay'] = volume_price_impact_decay
