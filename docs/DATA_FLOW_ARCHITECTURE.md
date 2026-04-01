# 量化交易系统数据流架构文档

**版本**: 1.0  
**日期**: 2026-03-12  
**基于**: PRD.md 产品需求文档

---

## 目录

1. [系统概览](#系统概览)
2. [第一层：数据采集层](#第一层数据采集层)
3. [第二层：信号生成层](#第二层信号生成层)
4. [第三层：信号融合层](#第三层信号融合层)
5. [第四层：风控层](#第四层风控层)
6. [第五层：交易执行层](#第五层交易执行层)
7. [第六层：监控告警层](#第六层监控告警层)
8. [完整数据流总结](#完整数据流总结)

---

## 系统概览

本系统采用六层架构，数据从外部数据源流入，经过信号生成、融合、风控、执行，最终通过监控界面反馈给用户。

```
外部数据源 
  → 采集脚本 
  → TimescaleDB/Chroma 
  → 信号生成 (技术指标 + ML + LLM) 
  → 信号融合 
  → 风控检查 
  → 交易执行 (CTP) 
  → 成交回报 
  → 监控告警 (Web + 邮件)
```

---

## 第一层：数据采集层

### 1.1 行情数据流

```
【数据源】
CTP 实时行情接口
  ↓
【采集脚本】
quant/data_collector/ctp_market.py
  ↓
【数据格式】
30分钟K线:
{
  "datetime": "2026-03-12 14:30:00",
  "open": 520.5,
  "high": 521.2,
  "low": 520.1,
  "close": 520.8,
  "volume": 12345,
  "open_interest": 67890
}
  ↓
【存储】
TimescaleDB
表名: kline_30m
索引: (datetime, symbol)
```

**实现文件**: `quant/data_collector/ctp_market.py`

---

### 1.2 基本面数据流

```
【数据源】
TuShare / AKShare (免费API)
  ↓
【采集脚本】
quant/data_collector/fundamental_collector.py (待实现)
  ↓
【数据格式】
基本面指标:
{
  "date": "2026-03-12",
  "fed_rate": 5.25,           # 美联储利率
  "non_farm": 250000,         # 非农就业人数
  "cpi": 3.2,                 # CPI通胀率
  "dollar_index": 103.5,      # 美元指数
  "treasury_yield_10y": 4.2   # 10年期美债收益率
}
  ↓
【存储】
TimescaleDB
表名: fundamentals
索引: (date)
```

**实现文件**: `quant/data_collector/fundamental_collector.py` (待实现)

---

### 1.3 新闻数据流

```
【数据源】
- 新浪财经 / 东方财富 / 金十数据 (实时快讯)
- 路透社 / 彭博 RSS
- Twitter/X (财经大V、美联储官员)
  ↓
【采集脚本】
quant/data_collector/news_collector.py (待实现)
  ↓
【数据格式】
新闻原文:
{
  "datetime": "2026-03-12 14:35:00",
  "source": "Reuters",
  "title": "Fed signals rate cut in Q2",
  "content": "The Federal Reserve...",
  "url": "https://..."
}
  ↓
【存储】
1. TimescaleDB (原文)
   表名: news_raw
   索引: (datetime, source)

2. Chroma (向量数据库)
   表名: news_embeddings
   用途: 相似度检索
```

**实现文件**: `quant/data_collector/news_collector.py` (待实现)

---

## 第二层：信号生成层

### 2.1 技术指标计算

```
【输入】
从 TimescaleDB 读取: kline_30m
  ↓
【处理模块】
quant/signal_generator/technical_indicators.py
  ↓
【计算指标】
- MA(5, 10, 20, 60)  # 移动平均线
- MACD               # 指数平滑异同移动平均线
- RSI                # 相对强弱指数
- Bollinger Bands    # 布林带
- ATR                # 平均真实波幅
  ↓
【输出格式】
{
  "datetime": "2026-03-12 14:30:00",
  "ma_5": 520.3,
  "ma_10": 519.8,
  "ma_20": 518.5,
  "ma_60": 515.2,
  "macd": 0.5,
  "macd_signal": 0.3,
  "macd_hist": 0.2,
  "rsi": 65.5,
  "bb_upper": 522.0,
  "bb_middle": 520.0,
  "bb_lower": 518.0,
  "atr": 1.5
}
  ↓
【存储】
TimescaleDB
表名: technical_signals
索引: (datetime, symbol)
```

**实现文件**: `quant/signal_generator/technical_indicators.py`

---

### 2.2 ML特征工程与预测

```
【输入】
从 TimescaleDB 读取:
- kline_30m (价格数据)
- fundamentals (基本面数据)
- technical_signals (技术指标)
  ↓
【特征工程】
quant/signal_generator/feature_engineer.py
  ↓
【生成18个特征】
1. 价格特征 (6个):
   - close, open, high, low, volume, open_interest
2. 技术指标特征 (10个):
   - ma_5, ma_10, ma_20, ma_60
   - macd, rsi, bb_upper, bb_lower, atr
3. 基本面特征 (2个):
   - dollar_index, treasury_yield_10y
  ↓
【ML模型预测】
quant/signal_generator/ml_predictor.py

模型: LightGBM (回归)
模型文件: models/lgbm_model.txt
  ↓
【预测目标】
未来2根30分钟K线 (1小时后) 的收益率
公式: (future_close - current_close) / current_close
  ↓
【输出格式】
{
  "datetime": "2026-03-12 14:30:00",
  "prediction": 0.008,      # 预测收益率 +0.8%
  "confidence": 0.75,       # 模型置信度
  "features": {...}         # 输入特征快照
}
  ↓
【存储】
TimescaleDB
表名: ml_predictions
索引: (datetime, symbol)
```

**实现文件**: 
- `quant/signal_generator/feature_engineer.py`
- `quant/signal_generator/ml_predictor.py`

---

### 2.3 LLM新闻解读

```
【输入】
从 TimescaleDB 读取: news_raw
  ↓
【LLM分析】
quant/signal_generator/llm_news_analyzer.py (待实现)

调用: Claude Opus 4 API
  ↓
【Prompt模板】
"分析以下新闻对黄金期货的影响:
标题: {title}
内容: {content}
请返回JSON格式:
{
  'importance': 'high|medium|low|irrelevant',
  'direction': 'bullish|bearish|neutral',
  'timeframe': 'immediate|short-term|long-term',
  'confidence': 0.0-1.0,
  'reasoning': '简短解释'
}"
  ↓
【输出格式】
{
  "datetime": "2026-03-12 14:35:00",
  "news_id": 12345,
  "importance": "high",
  "direction": "bullish",
  "timeframe": "immediate",
  "confidence": 0.85,
  "reasoning": "美联储暗示Q2降息，利好黄金"
}
  ↓
【触发条件】
- importance >= medium 且 confidence >= 0.6 → 记录
- importance == high 且 confidence >= 0.75 → 立即触发交易信号
  ↓
【存储】
TimescaleDB
表名: news_signals
索引: (datetime, news_id)
```

**实现文件**: `quant/signal_generator/llm_news_analyzer.py` (待实现)

---

## 第三层：信号融合层

```
【输入】
从 TimescaleDB 读取:
- technical_signals (技术指标信号)
- ml_predictions (ML预测信号)
- news_signals (LLM新闻信号)
  ↓
【融合模块】
quant/signal_generator/signal_fusion.py (待实现)
  ↓
【融合逻辑】
1. 加权综合:
   - ML预测: 50%
   - 技术指标: 30%
   - LLM新闻: 20%

2. 方向一致性检查:
   - 至少 2/3 的子信号方向一致才输出交易信号
   - 否则输出 "hold" (观望)

3. 信号强度计算:
   strength = (ml_confidence * 0.5) + 
              (technical_strength * 0.3) + 
              (llm_confidence * 0.2)
  ↓
【输出格式】
{
  "datetime": "2026-03-12 14:30:00",
  "direction": "buy",        # buy/sell/hold
  "strength": 0.78,          # 0.0-1.0
  "components": {
    "technical": {
      "signal": "buy",
      "strength": 0.65
    },
    "ml": {
      "prediction": 0.008,
      "confidence": 0.75
    },
    "llm": {
      "direction": "bullish",
      "confidence": 0.85
    }
  }
}
  ↓
【存储】
TimescaleDB
表名: fused_signals
索引: (datetime, symbol)
```

**实现文件**: `quant/signal_generator/signal_fusion.py` (待实现)

---

## 第四层：风控层

### 4.1 风控检查

```
【输入】
从 TimescaleDB 读取: fused_signals
  ↓
【风控模块】
quant/risk_executor/risk_manager.py
  ↓
【检查项】
1. 波动率过滤:
   - 计算 ATR
   - 如果 ATR > 近20日均值 * 2 → 降低仓位50% 或暂停交易

2. 信号强度阈值:
   - ML模型置信度 < 0.65 → 拒绝交易

3. 连败熔断:
   - 连续3笔交易亏损 → 暂停交易1小时

4. 最大仓位:
   - 当前仓位 + 新仓位 > 总资金70% → 拒绝交易

5. 单周最大亏损:
   - 本周累计亏损 > 总资金25% → 暂停交易，发送告警
  ↓
【决策输出】
- PASS: 通过风控，继续执行
- REJECT: 拒绝交易，记录原因
- ADJUST: 调整仓位后执行
```

**实现文件**: `quant/risk_executor/risk_manager.py`

---

### 4.2 仓位管理

```
【输入】
风控通过的信号 + 当前账户状态
  ↓
【仓位计算模块】
quant/risk_executor/position_manager.py
  ↓
【动态调仓规则】
根据信号强度 (strength) 计算仓位:
- 0.65 ≤ strength < 0.75 → 30% 仓位
- 0.75 ≤ strength < 0.85 → 50% 仓位
- strength ≥ 0.85 → 70% 仓位
  ↓
【止损止盈设定】
基于 ML 预测收益率:
- 预测收益率: +0.8%
- 止盈: +1.0% (预测值 * 1.25)
- 止损: -0.4% (预测值 * -0.5)
- 盈亏比: 2:1
  ↓
【输出格式】
{
  "datetime": "2026-03-12 14:30:00",
  "action": "open",          # open/close
  "direction": "buy",        # buy/sell
  "volume": 1,               # 手数
  "entry_price": 520.8,      # 入场价格
  "stop_loss": 518.7,        # 止损价格
  "take_profit": 525.8,      # 止盈价格
  "risk_reward_ratio": 2.0   # 盈亏比
}
  ↓
【存储】
TimescaleDB
表名: trade_orders
索引: (datetime, symbol)
```

**实现文件**: `quant/risk_executor/position_manager.py`

---

## 第五层：交易执行层

### 5.1 订单管理

```
【输入】
从 TimescaleDB 读取: trade_orders
  ↓
【订单管理模块】
quant/risk_executor/order_manager.py (待实现)
  ↓
【订单类型】
限价单 (避免滑点过大)
  ↓
【订单状态机】
待提交 → 已提交 → 部分成交 → 全部成交
                ↓
              已撤单 / 失败
  ↓
【异常处理】
- 下单失败 → 重试 (最多3次)
- 超时未成交 → 自动撤单
```

**实现文件**: `quant/risk_executor/order_manager.py` (待实现)

---

### 5.2 CTP交易接口

```
【输入】
订单管理模块的交易指令
  ↓
【CTP交易接口】
quant/data_collector/ctp_trade.py (待实现)
  ↓
【功能】
1. 下单 (开仓/平仓)
2. 订单状态跟踪
3. 成交回报处理
4. 持仓查询
  ↓
【发送到】
CTP 服务器 (上期所交易系统)
  ↓
【成交回报】
{
  "order_id": "20260312001",
  "status": "filled",        # filled/partial/rejected
  "filled_price": 520.8,
  "filled_volume": 1,
  "commission": 5.2,
  "datetime": "2026-03-12 14:30:05"
}
  ↓
【存储】
TimescaleDB
表名: trade_records
索引: (datetime, order_id)
```

**实现文件**: `quant/data_collector/ctp_trade.py` (待实现)

---

## 第六层：监控告警层

### 6.1 实时监控

```
【输入】
从 TimescaleDB 读取:
- 当前持仓
- 实时盈亏
- 最新信号状态
- 账户资金
  ↓
【监控服务】
quant/monitor/monitor_service.py (待实现)
  ↓
【Web界面】
quant/web_server/ (待实现)

技术: WebSocket 实时推送
  ↓
【展示内容】
- 持仓状态 (品种、方向、数量、成本价、当前价、盈亏)
- 盈亏曲线 (实时更新)
- 信号状态 (技术指标、ML预测、LLM解读)
- 交易记录 (最近10笔)
```

**实现文件**: 
- `quant/monitor/monitor_service.py` (待实现)
- `quant/web_server/` (待实现)

---

### 6.2 历史分析与回测

```
【输入】
从 TimescaleDB 读取:
- trade_records (交易记录)
- fused_signals (历史信号)
- ml_predictions (历史预测)
  ↓
【分析模块】
quant/monitor/analytics.py (待实现)
  ↓
【回测框架】
Backtrader 集成
  ↓
【评估指标】
- 年化收益率
- 夏普比率 (收益/风险比)
- 最大回撤
- 胜率 (盈利交易数 / 总交易数)
- 盈亏比 (平均盈利 / 平均亏损)
  ↓
【输出】
回测报告 (HTML/PDF)
```

**实现文件**: `quant/monitor/analytics.py` (待实现)

---

### 6.3 告警系统

```
【触发条件】
1. 触发交易 (开仓/平仓)
2. 连续亏损3次
3. 单周亏损超过20%
4. 系统异常 (数据源失效、模型推理失败等)
  ↓
【告警服务】
quant/monitor/alert_service.py (待实现)
  ↓
【邮件通知】
SMTP 发送
  ↓
【邮件内容】
- 事件类型
- 详细信息 (价格、仓位、原因等)
- 时间戳
- 建议操作
```

**实现文件**: `quant/monitor/alert_service.py` (待实现)

---

## 完整数据流总结

### 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                      外部数据源                              │
│  CTP行情 | TuShare/AKShare | 新浪财经/路透社/Twitter        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据采集层                              │
│  ctp_market.py | fundamental_collector.py | news_collector.py│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  数据存储 (TimescaleDB + Chroma)             │
│  kline_30m | fundamentals | news_raw | news_embeddings      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      信号生成层                              │
│  技术指标 | ML预测 (LightGBM) | LLM解读 (Claude Opus 4)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      信号融合层                              │
│  加权综合 (ML 50% + 技术 30% + LLM 20%) + 方向一致性检查    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        风控层                                │
│  波动率过滤 | 信号阈值 | 连败熔断 | 仓位管理 | 止损止盈     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      交易执行层                              │
│  订单管理 | CTP交易接口 | 成交回报处理                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      监控告警层                              │
│  Web实时监控 | 历史分析回测 | 邮件告警                      │
└─────────────────────────────────────────────────────────────┘
```

---

### 关键数据格式汇总

| 数据类型 | 格式 | 存储位置 |
|---------|------|---------|
| **30分钟K线** | `{datetime, open, high, low, close, volume, open_interest}` | `kline_30m` |
| **基本面数据** | `{date, fed_rate, non_farm, cpi, dollar_index, treasury_yield}` | `fundamentals` |
| **新闻原文** | `{datetime, source, title, content, url}` | `news_raw` |
| **新闻向量** | `{embedding: [768维向量]}` | `news_embeddings` (Chroma) |
| **技术指标** | `{datetime, ma_5, ma_10, ..., macd, rsi, bb_upper, bb_lower, atr}` | `technical_signals` |
| **ML预测** | `{datetime, prediction, confidence, features}` | `ml_predictions` |
| **LLM解读** | `{datetime, news_id, importance, direction, timeframe, confidence, reasoning}` | `news_signals` |
| **融合信号** | `{datetime, direction, strength, components}` | `fused_signals` |
| **交易指令** | `{datetime, action, direction, volume, entry_price, stop_loss, take_profit}` | `trade_orders` |
| **成交回报** | `{order_id, status, filled_price, filled_volume, commission, datetime}` | `trade_records` |

---

### 模块实现状态

| 模块 | 文件路径 | 状态 |
|-----|---------|------|
| **CTP行情** | `quant/data_collector/ctp_market.py` | ✅ 已实现 |
| **CTP长驻采集** | `scripts/run_ctp_collector.py` | ✅ 已实现 (2026-03-16) |
| **备用数据源** | `quant/data_collector/backup_data_source.py` | ✅ 已实现 |
| **基本面采集** | `quant/data_collector/fundamental_collector.py` | ❌ 待实现 |
| **新闻采集** | `quant/data_collector/news_collector.py` | ❌ 待实现 |
| **技术指标** | `quant/signal_generator/technical_indicators.py` | ✅ 已实现 |
| **特征工程** | `quant/signal_generator/feature_engineer.py` | ✅ 已实现 (47特征) |
| **ML预测** | `quant/signal_generator/ml_predictor.py` | ✅ 已实现 |
| **LLM解读** | `quant/signal_generator/llm_news_analyzer.py` | ❌ 待实现 |
| **信号融合** | `quant/signal_generator/signal_fusion.py` | ✅ 已实现 |
| **信号处理** | `quant/risk_executor/signal_processor.py` | ✅ 已实现 (含三种平仓) |
| **风控管理** | `quant/risk_executor/risk_manager.py` | ✅ 已实现 (含止损止盈) |
| **仓位管理** | `quant/risk_executor/position_manager.py` | ✅ 已实现 |
| **交易执行** | `quant/risk_executor/trade_executor.py` | ✅ 已实现 |
| **订单管理** | `quant/risk_executor/order_manager.py` | ❌ 待实现 |
| **CTP交易** | `quant/data_collector/ctp_trade.py` | ✅ 已实现 |
| **单次策略执行** | `scripts/run_single_cycle.py` | ✅ 已实现 (2026-03-16) |
| **监控服务** | `quant/monitor/monitor_service.py` | ❌ 待实现 |
| **Web界面** | `quant/web_server/` | ❌ 待实现 |
| **告警服务** | `quant/monitor/alert_service.py` | ❌ 待实现 |

---

## 重要更新 (2026-03-16)

### 数据采集架构升级

原架构依赖 SimNow 实时 Tick（不稳定），现已升级为：

```
CTP 长驻采集进程 (run_ctp_collector.py)
  → 交易时段持续运行
  → 收 Tick → 聚合 1 分钟 K 线 → 存入 kline_data 表
  → 交易时段结束自动退出

策略 Cron (run_single_cycle.py, 每 5 分钟)
  → 从数据库读 K 线 → ML 预测 → 风控 → 发单
  → 不足时回退到 AkShare
```

### ML 模型升级

- 特征数量: 18 → 47（增加动量、波动率、成交量、持仓量、时间等特征）
- 训练数据: 500 根模拟数据 → 10000 根真实 30 分钟线（天勤量化）
- 方向准确率: 44.93% → 64.01%
- 相关系数: -0.093 → 0.2109

### 平仓逻辑新增

1. **反向信号平仓**: 持多收到 sell 信号先平多再开空
2. **止损止盈平仓**: 盈亏比 2:1，持仓信息持久化到 strategy_state.json
3. **ML 预测反转平仓**: 预测方向反转立即平仓

### 置信度公式修正

旧公式 `min(abs(prediction) * 50, 1.0)` 导致置信度永远为 1.0。
新公式对异常预测值（>5%）降低置信度，防止无脑发单。

### 数据库新增数据

| 数据 | 来源 | 数量 |
|------|------|------|
| 30 分钟线 (au_main) | 天勤量化 | 10000 根 |
| 日线 (au_main) | 天勤量化 | 2474 根 |
| 1 分钟线 (au2606) | CTP 实时采集 | 持续增长 |

---

## 附录：PRD 关键约束

1. **AI不降级**: 在需求文档标注"AI"的位置，不使用启发式规则平替
2. **免费数据源**: 所有数据源必须免费，需要注册的由用户操作
3. **本地部署**: 系统运行在本地，不依赖云服务（除了LLM API）
4. **模拟盘先行**: 真实交易前必须通过模拟盘验证

---

**文档版本**: 1.0  
**最后更新**: 2026-03-12  
**维护者**: PM Agent
