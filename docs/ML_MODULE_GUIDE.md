# ML 模块使用指南

## 概述

ML 模块使用 LightGBM 回归模型预测未来 2 根 K 线的对数收益率，基于 56 个技术特征（含 15 个高 IC 发现因子）。

## 模型信息

- **模型文件**: `models/lgbm_model.txt`
- **算法**: LightGBM 回归（regularized）
- **训练数据**: 天勤黄金主力合约 30 分钟线，10000 根（2023-12-22 ~ 2026-03-16）
- **特征数量**: 56 个（含 15 个高 IC 发现因子）
- **预测目标**: 未来 2 根 K 线的对数收益率 `log(close_{t+2} / close_t)`

## 模型参数

```python
{
    'learning_rate': 0.05,
    'num_leaves': 31,
    'max_depth': 6,
    'min_data_in_leaf': 20,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'objective': 'regression',
    'metric': 'rmse'
}
```

## 模型性能（2026-03-19）

| 指标 | 数值 | 备注 |
|------|------|------|
| RMSE | 3.21% | |
| 方向准确率 | 65.82% | 旧模型 64.01%，提升 1.81% |

## 特征列表（56 个）

### 基础 OHLCV（6 个）
open, high, low, close, volume, open_interest

### 技术指标（13 个）
ma_5, ma_10, ma_20, ma_60, macd, macd_signal, macd_hist, rsi, bb_middle, bb_upper, bb_lower, bb_width, atr

### 价格动量（4 个）
returns_1, returns_5, returns_10, returns_20

### 波动率（3 个）
volatility_5, volatility_10, volatility_20

### 成交量（3 个）
volume_ratio_5, volume_ratio_10, volume_change

### 价格位置（2 个）
price_position, distance_from_ma20

### K 线形态（3 个）
body_ratio, upper_shadow, lower_shadow

### 持仓量（2 个）
oi_change, oi_volume_ratio

### 均线交叉（2 个）
ma_cross_5_20, macd_cross

### 价格形态（4 个）
higher_high, lower_low, consecutive_up, consecutive_down

### 波动率衍生（2 个）
atr_ratio, bb_position

### 时间特征（3 个）
hour_of_day, day_of_week, is_night_session

### 高 IC 发现因子（15 个，2026-03-19 新增）
disc_oi_rsi, disc_vol_adj_oi_mom, disc_volume_weighted_oi_change, disc_oi_norm_momentum, disc_vol_weighted_oi_dir, disc_oi_roc_momentum, disc_oi_relative_strength, disc_oi_elasticity, disc_range_expand_oi, disc_oi_flow_asymmetry, disc_oi_curvature, disc_bayesian_surprise_oi, disc_oi_volume_sync, disc_oi_trend_reversal, disc_oi_wavelet_energy

## 置信度计算

```
预测值 0.5%~2%  → confidence 0.30~0.90（合理范围）
预测值 2%~5%    → confidence 0.90~0.50（偏高，降低信任）
预测值 >5%      → confidence < 0.30（异常，不交易）
```

阈值：confidence >= 0.65 才会生成交易信号。

## 平仓逻辑（2026-03-16 新增）

### 方式 1：反向信号平仓
- 持多收到 sell 信号 → 先平多再开空
- 持空收到 buy 信号 → 先平空再开多

### 方式 2：止损止盈平仓
- 止盈 = 开仓价 × (1 + 预测收益率 × 1.25)
- 止损 = 开仓价 × (1 - 预测收益率 × 0.5)
- 盈亏比 2:1

### 方式 3：ML 预测反转平仓
- 持多时 ML 预测看跌 → 立即平仓（不需要置信度阈值）
- 持空时 ML 预测看涨 → 立即平仓

## 使用方式

### 实时预测
```bash
cd E:\quant-trading-mvp
python scripts/monitor_ml.py
```

### 重新训练
```bash
python scripts/train_final_clean.py
```

### 超参数调优
```bash
python scripts/tune_hyperparams.py
```

### 模型评估
```bash
python scripts/evaluate_model.py
```

## 数据来源

| 来源 | 数据类型 | 数量 | 用途 |
|------|---------|------|------|
| 天勤量化 | 30 分钟线 | 10000 根 | 模型训练 |
| 天勤量化 | 1 分钟线 | 10000 根 | 备用 |
| AkShare | 日线 | 1499 天 | 备用 |
| 天勤采集器 | 实时 1m K 线 | 持续采集 | 实时预测（替代 CTP SimNow）|

## 重要更新 (2026-03-19)

### 数据采集切换
- 实时数据来源从 CTP SimNow Tick 切换为天勤 tqsdk `get_kline_serial(SHFE.au2606, 60)` 直接拿 1m K 线
- 采集器：`scripts/run_tq_collector.py`（替代 `run_ctp_collector.py`）

### 交易接口切换
- 放弃 SimNow CTP 交易，改用天勤快期模拟盘（TqKq）
- 新增 `quant/data_collector/tq_trade.py` 和 `quant/common/tq_factory.py`
- `trade_executor.py` 和 `execute_trade.py` 已切换到 `tq_trade_session`

### 置信度公式修正补充
- 异常预测值（>5%）进一步降低置信度，防止极端行情下无脑发单
- 预测值在合理范围（0.5%~2%）内线性映射到 0.30~0.90

## 重要更新 (2026-03-18) — Bug 修复

### logging 问题
- `logging.basicConfig()` 第二次调用被忽略，导致日志文件为空
- 修复：加 `force=True` 参数

### 发单后等待成交
- `execute_order()` 发完单立即返回，脚本退出后成交回报才到
- 修复：发单后 `time.sleep(5)` 等待成交回报

### SimNow 平仓经验
- 市价单(IOC)在非活跃时段被撤，必须用限价单
- 昨仓 CloseYesterday(`offset_flag='4'`)，今仓 CloseToday(`offset_flag='3'`)
- 必须分开各发一单，不能合并

---

**文档版本**: 3.0
**最后更新**: 2026-03-19
