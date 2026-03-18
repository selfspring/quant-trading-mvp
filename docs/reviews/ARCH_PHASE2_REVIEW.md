# 架构阶段性审查 Phase 2 — signal_generator & risk_executor

> 审查日期: 2026-03-11 | 审查角色: 架构师

## 1. 模块解耦：基本合格，但有耦合点

- **职责划分清晰**：`technical_indicators.py`（纯函数计算）→ `feature_engineer.py`（特征+标签组装）→ `ml_predictor.py`（模型推理）三层分工明确。
- **问题**：`MLPredictor.predict()` 直接调用 `calculate_all_indicators()`，绕过了 `FeatureEngineer`。训练走 FeatureEngineer，推理走 MLPredictor 自己算——特征口径不一致的风险已经埋下。**必须统一入口**。
- **signal_processor → risk_manager 分层合理**：信号转意图 → 风控校验/调整 → 执行器生成订单，职责链清晰。`TradeIntent` 作为中间协议对象设计得当。

## 2. 数据流与性能：存在重复计算瓶颈

当前数据流：`CTP Tick → 30min Bar → Redis Pub → (消费端) 加载60根K线 → calculate_all_indicators() → 取最后一行预测`

- **每次信号触发都全量重算所有指标**（MA5/10/20/60、MACD、RSI、BB、ATR），60根K线×5类指标。当前30分钟级别尚可接受，但如果切到1分钟级别或多品种并行，会成为瓶颈。
- **建议**：引入增量计算缓存——维护一个滑动窗口 DataFrame，新 Bar 到达时只 append + 增量更新尾部指标值，而非每次 `df.copy()` + 全量 rolling。

## 3. 架构隐患 (Tech Debt) — 三个硬伤

### 3.1 持仓状态一致性（P0 级）
`PositionManager` 是纯内存 dict，与 CTP 实际持仓零同步。风险场景：
- 程序重启 → 内存持仓归零，但 CTP 仍有持仓 → 风控规则全部失效，可能反向开仓。
- 订单部分成交 → 本地未更新 → 持仓数量漂移。

### 3.2 CTP 断线无重连（P0 级）
`ctp_market.py` 的 `OnFrontConnected` 只做首次登录。`OnFrontDisconnected` 回调未实现——断线后行情静默丢失，无告警、无自动重连、无数据补全。

### 3.3 订单执行是空壳（P1 级）
`TradeExecutor.execute_order()` 只生成 Order 对象并打日志，未对接 CTP tdapi 发单。`# TODO` 标记仍在。无回报处理、无成交确认、无超时重试。

## 4. 下一步架构建议

| 优先级 | 隐患 | 方案 |
|--------|------|------|
| P0 | 持仓不一致 | 启动时调用 `ReqQryInvestorPosition` 同步 CTP 持仓初始化 `PositionManager`；每笔成交回报 (`OnRtnTrade`) 实时更新内存；每 N 分钟定时对账，不一致时告警+暂停交易 |
| P0 | 断线重连 | 实现 `OnFrontDisconnected` 回调，指数退避重连；重连成功后重新订阅行情 + 补拉缺失 Bar（从 DB 或 CTP 历史查询） |
| P1 | 订单空壳 | 对接 `tdapi.ReqOrderInsert`，实现 `OnRtnOrder`/`OnRtnTrade` 回调闭环；加入订单状态机（Pending→Filled/Rejected/Cancelled） |
| P2 | 特征口径 | `MLPredictor.predict()` 改为调用 `FeatureEngineer.generate_features()`，消除重复的 `calculate_all_indicators` 调用 |
| P2 | 指标重算 | 引入 `IndicatorCache` 类，维护滑动窗口，增量更新指标 |
