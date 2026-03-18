# 交易执行与风控核心类完成总结

## 实现内容
- 实现了 `PositionManager`: 管理多空持仓。
- 实现了 `SignalProcessor`: 将 ML 信号按置信度阈值转化为交易意图。
- 实现了 `RiskManager`: 处理持仓冲突，反向信号自动转平仓。
- 实现了 `TradeExecutor`: 封装最终订单，准备对接 CTP 接口。

## 模块整合状态
至此，"信号 -> 风控 -> 订单"的完整数据流结构已建立。

## 文件清单
```
quant/risk_executor/
├── __init__.py              # 模块导出
├── position_manager.py      # 持仓管理器
├── signal_processor.py      # 信号处理器
├── risk_manager.py          # 风控管理器
└── trade_executor.py        # 交易执行器
```

## 核心业务逻辑

### 1. PositionManager（持仓管理器）
- 记录多头和空头持仓数量
- 提供更新持仓的方法
- 提供查询持仓状态的方法

### 2. SignalProcessor（信号处理器）
- 输入：ML 模型输出 `{"prediction": 0.02, "confidence": 0.8, "signal": 1}`
- 逻辑：根据 `config.ml.confidence_threshold`（默认 0.65）过滤低置信度信号
- 输出：`TradeIntent` 对象，包含方向（buy/sell）和动作（open/close）

### 3. RiskManager（风控管理器）
- 规则 1：无持仓时，直接放行开仓指令
- 规则 2：已有多头持仓，收到看多���号，放行
- 规则 3：已有多头持仓，收到看空信号，**拦截开空并转为平多**
- 规则 4：已有空头持仓，收到看多信号，**拦截开多并转为平空**

### 4. TradeExecutor（交易执行器）
- 将 `TradeIntent` 转换为 CTP 接口订单
- 使用 `openctp-ctp` 的常量（`THOST_FTDC_D_Buy`, `THOST_FTDC_OF_Open` 等）
- 提供 `to_ctp_params()` 方法生成 CTP 接口参数
- 目前打印日志，后续可与 `ctp_market.py` 集成

## 数据流示例

```
ML 模型输出
  ↓
SignalProcessor (置信度过滤)
  ↓
TradeIntent (交易意图)
  ↓
RiskManager (持仓冲突检查)
  ↓
调整后的 TradeIntent
  ↓
TradeExecutor (生成 CTP 订单)
  ↓
Order (CTP 接口参数)
```

## 使用示例

```python
from quant.common.config import config
from quant.risk_executor import (
    PositionManager,
    SignalProcessor,
    RiskManager,
    TradeExecutor
)

# 初始化组件
position_mgr = PositionManager()
signal_proc = SignalProcessor(config)
risk_mgr = RiskManager(position_mgr, config)
executor = TradeExecutor(config)

# 处理 ML 信号
ml_output = {"prediction": 0.02, "confidence": 0.8, "signal": 1}
intent = signal_proc.process_signal(ml_output)

# 风控检查
adjusted_intent = risk_mgr.check_and_adjust(intent)

# 执行订单
if adjusted_intent:
    order = executor.execute_order(adjusted_intent)
    print(f"订单已生成: {order}")
```

## 后续集成点
- 与 `ctp_market.py` 集成，实际发送订单到 CTP 接口
- 订单回报处理，更新 `PositionManager` 的持仓状态
- 增加更多风控规则（最大仓位、止损止盈等）
