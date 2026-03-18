# 信号收集层数据库输出状态分析

## 📊 数据库表结构概览

根据 `scripts/init_db.py`，系统共有 **14 张表**：

### 数据层 (3 张)
1. ✅ **kline_data** - K 线数据
2. ✅ **fundamental_data** - 基本面数据
3. ✅ **news_raw** - 新闻原文

### 信号层 (5 张)
4. ✅ **news_analysis** - AI 新闻解读
5. ⚠️ **technical_indicators** - 技术指标
6. ❌ **ml_predictions** - ML 模型预测
7. ❌ **trading_signals** - 交易信号
8. ✅ **fused_signals** - 融合信号 (自定义表)

### 执行层 (3 张)
9. ✅ **orders** - 订单记录
10. ✅ **trades** - 成交记录
11. ✅ **positions** - 持仓记录

### 监控层 (3 张)
12. ✅ **account_snapshot** - 账户快照
13. ✅ **data_quality_log** - 数据质量监控
14. ✅ **signal_performance** - 信号回溯分析
15. ✅ **message_trace** - 消息流追踪

---

## 🔍 信号生成模块数据库输出情况

### 1. ✅ 技术信号 (Technical Signals)

**模块**: `quant/signal_generator/technical_signals.py`

**输出格式**:
```python
{
    "signal": "buy|sell|hold",
    "strength": 0.0-1.0,
    "indicators": {
        "ma_5": float,
        "ma_10": float,
        "ma_20": float,
        "ma_60": float,
        "macd": float,
        "macd_signal": float,
        "macd_hist": float,
        "rsi": float,
        "bb_upper": float,
        "bb_middle": float,
        "bb_lower": float,
        "atr": float,
        "close": float
    },
    "reasoning": str
}
```

**数据库写入**: ❌ **未实现**
- 代码中有 `CREATE TABLE technical_signals` 的 SQL 语句
- 但 **没有 `save_to_db()` 方法**
- 技术指标数据未持久化

**对应表**: `technical_signals` (设计中，未使用)

---

### 2. ❌ ML 预测 (ML Predictor)

**模块**: `quant/signal_generator/ml_predictor.py`

**输出格式**:
```python
{
    "prediction": float,      # 预测收益率
    "confidence": float,      # 置信度 0-1
    "signal": int            # 1=做多, -1=做空
}
```

**数据库写入**: ❌ **未实现**
- 没有 `save_to_db()` 方法
- ML 预测结果未持久化

**对应表**: `ml_predictions` (设计中，未使用)

**表结构**:
```sql
CREATE TABLE ml_predictions (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    predicted_return DECIMAL(8, 6) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    features JSONB,
    PRIMARY KEY (time, symbol)
)
```

---

### 3. ✅ LLM 新闻分析 (LLM News Analyzer)

**模块**: `quant/signal_generator/llm_news_analyzer.py`

**输出格式**:
```python
{
    "importance": "high|medium|low",
    "direction": "bullish|bearish|neutral",
    "timeframe": "short|medium|long",
    "confidence": float,
    "reasoning": str
}
```

**数据库写入**: ✅ **已实现**
- 有 `save_to_db()` 方法 (第 275 行)
- 写入到 `news_signals` 表 (自定义表)

**对应表**: `news_signals` (自定义，非标准表)

**表结构**:
```sql
CREATE TABLE news_signals (
    id SERIAL PRIMARY KEY,
    news_id INTEGER REFERENCES news_raw(id),
    datetime TIMESTAMPTZ NOT NULL,
    importance VARCHAR(20),
    direction VARCHAR(20),
    timeframe VARCHAR(20),
    confidence DECIMAL(3, 2),
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

---

### 4. ✅ 信号融合 (Signal Fusion)

**模块**: `quant/signal_generator/signal_fusion.py`

**输出格式**:
```python
{
    "direction": "buy|sell|hold",
    "strength": float,
    "components": {
        "technical": {...},
        "ml": {...},
        "llm": {...}
    },
    "timestamp": datetime,
    "symbol": str
}
```

**数据库写入**: ✅ **已实现**
- 有 `save_to_db()` 方法 (第 360 行)
- 写入到 `fused_signals` 表 (自定义表)

**对应表**: `fused_signals` (自定义，非标准表)

**表结构**:
```sql
CREATE TABLE fused_signals (
    id SERIAL PRIMARY KEY,
    datetime TIMESTAMP NOT NULL,
    symbol VARCHAR(20),
    direction VARCHAR(10),
    strength FLOAT,
    technical_signal VARCHAR(10),
    technical_strength FLOAT,
    ml_prediction FLOAT,
    ml_confidence FLOAT,
    llm_direction VARCHAR(20),
    llm_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
)
```

---

## 📋 缺失的数据库写入功能

### ❌ 1. 技术信号未持久化

**问题**: `TechnicalSignalGenerator.generate_signal()` 没有保存到数据库

**影响**:
- 无法回溯技术信号的历史表现
- 无法分析技术指标的有效性
- 无法做信号回测

**建议**: 添加 `save_to_db()` 方法，写入 `technical_signals` 表

---

### ❌ 2. ML 预测未持久化

**问题**: `MLPredictor.predict()` 没有保存到数据库

**影响**:
- 无法评估模型预测准确率
- 无法做预测回测
- 无法追踪模型性能变化

**建议**: 添加 `save_to_db()` 方法，写入 `ml_predictions` 表

---

### ⚠️ 3. 技术指标未持久化

**问题**: `calculate_all_indicators()` 计算的指标没有保存

**影响**:
- 每次都要重新计算指标
- 无法快速查询历史指标
- 增加计算开销

**建议**: 添加指标缓存机制，写入 `technical_indicators` 表

---

## 🎯 优先级建议

### 高优先级 (必须实现)

1. **ML 预测持久化**
   - 添加 `MLPredictor.save_to_db()`
   - 写入 `ml_predictions` 表
   - 记录预测值、置信度、模型版本

2. **技术信号持久化**
   - 添加 `TechnicalSignalGenerator.save_to_db()`
   - 写入 `technical_signals` 表 (需要创建)
   - 记录信号方向、强度、推理

### 中优先级 (建议实现)

3. **技术指标缓存**
   - 添加 `FeatureEngineer.save_indicators()`
   - 写入 `technical_indicators` 表
   - 减少重复计算

### 低优先级 (可选)

4. **统一信号表**
   - 考虑将 `news_signals` 和 `fused_signals` 合并到标准的 `trading_signals` 表
   - 统一信号格式和查询接口

---

## 📝 实现示例

### 1. ML 预测持久化

```python
# quant/signal_generator/ml_predictor.py

def save_to_db(self, prediction: dict, symbol: str, timestamp: datetime):
    """保存 ML 预测到数据库"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ml_predictions (
                        time, symbol, predicted_return, confidence, 
                        model_version, features
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, symbol) DO UPDATE SET
                        predicted_return = EXCLUDED.predicted_return,
                        confidence = EXCLUDED.confidence
                    """,
                    (
                        timestamp,
                        symbol,
                        prediction['prediction'],
                        prediction['confidence'],
                        'lgbm_v1',
                        None  # 可选：保存特征 JSON
                    )
                )
                conn.commit()
                logger.info(f"ML prediction saved: {symbol} @ {timestamp}")
    except Exception as e:
        logger.error(f"Failed to save ML prediction: {e}")
```

### 2. 技术信号持久化

```python
# quant/signal_generator/technical_signals.py

def save_to_db(self, signal: dict, symbol: str, timestamp: datetime):
    """保存技术信号到数据库"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO technical_signals (
                        time, symbol, signal, strength, 
                        ma_5, ma_10, ma_20, macd, rsi, reasoning
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        timestamp,
                        symbol,
                        signal['signal'],
                        signal['strength'],
                        signal['indicators']['ma_5'],
                        signal['indicators']['ma_10'],
                        signal['indicators']['ma_20'],
                        signal['indicators']['macd'],
                        signal['indicators']['rsi'],
                        signal['reasoning']
                    )
                )
                conn.commit()
                logger.info(f"Technical signal saved: {symbol} @ {timestamp}")
    except Exception as e:
        logger.error(f"Failed to save technical signal: {e}")
```

---

## 🔄 数据流总结

### 当前状态
```
K线数据 → ML预测 ❌ (未保存)
         ↓
K线数据 → 技术指标 → 技术信号 ❌ (未保存)
         ↓
新闻数据 → LLM分析 ✅ (已保存到 news_signals)
         ↓
三路信号 → 信号融合 ✅ (已保存到 fused_signals)
         ↓
融合信号 → 风控 → 交易执行
```

### 理想状态
```
K线数据 → ML预测 ✅ → ml_predictions
         ↓
K线数据 → 技术指标 ✅ → technical_indicators
         ↓
         技术信号 ✅ → technical_signals
         ↓
新闻数据 → LLM分析 ✅ → news_analysis
         ↓
三路信号 → 信号融合 ✅ → trading_signals (统一表)
         ↓
融合信号 → 风控 → 交易执行
```

---

## 📊 总结

### 已实现 (2/4)
- ✅ LLM 新闻分析 → `news_signals`
- ✅ 信号融合 → `fused_signals`

### 未实现 (2/4)
- ❌ ML 预测 → `ml_predictions`
- ❌ 技术信号 → `technical_signals`

### 建议
1. 优先实现 ML 预测和技术信号的持久化
2. 统一信号表结构，使用标准的 `trading_signals` 表
3. 添加信号回测和性能分析功能
