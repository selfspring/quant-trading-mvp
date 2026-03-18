# ML 模块使用指南

## 概述

ML 模块使用 LightGBM 回归模型预测未来 2 根 K 线的对数收益率，基于 47 个技术特征。

## 模型信息

- **模型文件**: `models/lgbm_model.txt`
- **算法**: LightGBM 回归（regularized）
- **训练数据**: 天勤黄金主力合约 30 分钟线，10000 根（2023-12-22 ~ 2026-03-16）
- **特征数量**: 47 个
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

## 模型性能（2026-03-16）

| 指标 | 数值 |
|------|------|
| RMSE | 3.22% |
| 方向准确率 | 64.01% |
| 相关系数 | 0.2109 |

## 特征列表（47 个）

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
| CTP SimNow | 实时 Tick | 持续采集 | 实时预测 |

---

**文档版本**: 2.0
**最后更新**: 2026-03-16
