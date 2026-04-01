# 信号与交易集成测试用例 (QA)

## 编写的测试用例

### 核心场景（4 个）
- 测试 1: 强看多信号 → 生成买入开仓指令（BUY OPEN）
- 测试 2: 强看空信号 → 生成卖出开仓指令（SELL OPEN）
- 测试 3: 置信度不足（0.25 < 0.65）→ 忽略信号，不生成交易指令
- 测试 4: 已有多头持仓 + 看空信号 → 生成平仓指令（SELL CLOSE）

### 补充边界场景（6 个）
- 测试 5: 置信度恰好等于阈值（0.65）→ 生成指令（待开发团队确认 >= 还是 > 的边界行为）
- 测试 6: 同方向信号（已有多头 + 看多信号）→ 不触发平仓
- 测试 7: 空头持仓 + 看多信号 → 生成 BUY CLOSE 平空仓指令
- 测试 8: 中性信号（signal=0）→ 不生成交易指令

### 契约验证（4 个）
- 测试 9-11: MLPredictor 输出格式验证（必要字段、数据类型、值范围）
- 测试 12-13: 置信度阈值配置一致性验证、不同阈值下的过滤行为

## 测试运行结果

```
Ran 14 tests in 0.001s — OK
```

所有 14 个测试用例均通过（基于桩实现）。

## 发现的业务缺失（给开发团队的建议）

为了让这些测试从"桩实现"升级为"真实集成测试"，项目中还需要实现以下组件：

### 必须实现的类/模块

| 缺失组件 | 建议位置 | 职责 |
|---------|---------|------|
| `SignalProcessor` | `quant/risk_executor/signal_processor.py` | 核心：将 ML 信号转化为交易指令，包含置信度过滤、持仓冲突检测 |
| `TradeOrder` | `quant/risk_executor/models.py` | 交易指令数据结构（方向、开平、手数、合约） |
| `Position` | `quant/risk_executor/models.py` | 持仓信息数据结构 |
| `OrderDirection` / `OrderAction` | `quant/risk_executor/models.py` | 枚举：BUY/SELL、OPEN/CLOSE |
| `RiskManager` | `quant/risk_executor/risk_manager.py` | 风控管理器：仓位上限、回撤熔断、连败限制（config 中已有参数但无实现） |
| `TradeExecutor` | `quant/risk_executor/trade_executor.py` | 交易执行器：将 TradeOrder 提交到 CTP 接口 |

### 需要明确的业务决策

1. **阈值边界行为**：`confidence == threshold` 时是否交易？（当前测试假设 `>=` 通过）
2. **反向信号策略**：平仓后是否立即反向开仓？（当前测试假设保守策略：只平仓不反手）
3. **加仓规则**：同方向信号是否允许加仓？加仓上限是多少？
4. **中性信号处理**：`signal=0` 的场景是否可能出现？（当前 MLPredictor 只输出 1/-1）
5. **多合约支持**：当前测试仅覆盖单合约（au2606），是否需要多合约持仓管理？

### 现有代码可复用的部分

- `MLPredictor.predict()` 输出格式已确认：`{"prediction": float, "confidence": float, "signal": int}`
- `MLConfig.confidence_threshold` 默认值 0.65 已在 config.py 中定义
- `StrategyConfig` 中已有风控参数（`max_position_ratio`, `max_weekly_drawdown`, `consecutive_loss_limit`），但无对应实现
- `quant/risk_executor/` 目录已存在但为空，可直接在此目录下开发
