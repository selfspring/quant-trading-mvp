# TradeExecutor 与 CTP 交易 API 对接总结

> 日期: 2026-03-11

## 1. 完成的工作

### 1.1 新建 `quant/data_collector/ctp_trade.py` — CTP 交易接口封装

项目中原本只有行情接口 (`ctp_market.py` 中的 `MdSpi`)，没有封装好的交易接口类。因此新建了 `CTPTradeApi` 类，提供两个核心方法：

| 方法 | 签名 | 说明 |
|------|------|------|
| `send_order()` | `(instrument_id, direction, offset_flag, volume, price, exchange_id, order_price_type)` | 发送报单到 CTP |
| `get_current_position()` | `(instrument_id="") -> {"long_volume": int, "short_volume": int}` | 查询当前持仓 |

内部完整实现了：
- 连接管理（`connect` / `disconnect`）
- 客户端认证 → 登录 → 结算单确认 的完整流程
- `TradeSpi` 回调类处理委托回报 (`OnRtnOrder`)、成交回报 (`OnRtnTrade`)、报单拒绝等
- 线程安全的 `OrderRef` 自增
- 持仓查询的异步缓冲与同步等待

### 1.2 修改 `quant/risk_executor/trade_executor.py`

**构造函数变更：**
```python
# 之前
def __init__(self, config):

# 之后
def __init__(self, config, td_api=None):
```

- `td_api=None` 时为 dry-run 模式（仅生成订单对象，不实际发单）
- `td_api` 传入 `CTPTradeApi` 实例时为实盘模式

**`execute_order()` 方法变更：**
1. 将 `TradeIntent` 转换为 `Order` 对象（方向/开平映射）
2. 调用 `order.to_ctp_params()` 获取参数字典
3. **调用 `self.td_api.send_order(**params)` 真实发单**
4. 将返回的 `order_ref` 保存到 `order.order_ref`
5. 记录详细日志

**`Order.to_ctp_params()` 输出变更：**

旧版使用 CTP 原始字段名（如 `InstrumentID`, `CombOffsetFlag`），新版输出与 `CTPTradeApi.send_order()` 的 Python 参数名完全对齐：

```python
{
    'instrument_id': 'au2606',
    'direction': '0',       # THOST_FTDC_D_Buy
    'offset_flag': '0',     # THOST_FTDC_OF_Open
    'volume': 1,
    'price': 680.0,
}
```

## 2. 参数映射对照表

| TradeIntent 字段 | CTP 常量 | send_order 参数 |
|---|---|---|
| `direction='buy'` | `THOST_FTDC_D_Buy` (`'0'`) | `direction='0'` |
| `direction='sell'` | `THOST_FTDC_D_Sell` (`'1'`) | `direction='1'` |
| `action='open'` | `THOST_FTDC_OF_Open` (`'0'`) | `offset_flag='0'` |
| `action='close'` | `THOST_FTDC_OF_Close` (`'1'`) | `offset_flag='1'` |
| `volume` | — | `volume` (整数) |
| `config.strategy.symbol` | — | `instrument_id` (字符串) |

映射链路：`TradeIntent → Order → to_ctp_params() → td_api.send_order(**params)`

## 3. 验证脚本结果

脚本位置：`scripts/verify_trade_flow.py`

```
✅ PASS  test_strong_bull_signal_opens_long        — 强多头信号 → 买入开仓
✅ PASS  test_bear_signal_with_long_position_closes — 已有多头+看空 → RiskManager 转平仓
✅ PASS  test_low_confidence_signal_rejected         — 低置信度 → 不交易
✅ PASS  test_dry_run_mode                           — td_api=None → 仅生成订单
✅ PASS  test_order_param_mapping                    — to_ctp_params() 参数名与 send_order() 完全匹配

🎉 所有 5 个测试全部通过
```

## 4. 结论

| 检查项 | 状态 |
|--------|------|
| TradeExecutor 是否具备发单能力 | ✅ 是 — 通过 `td_api.send_order()` 真实发单 |
| 参数映射是否正确 | ✅ 是 — `to_ctp_params()` 输出与 `send_order()` 签名完全匹配 |
| 验证脚本是否跑通 | ✅ 是 — 5/5 测试通过 |
| 向后兼容 | ✅ 是 — `td_api=None` 时为 dry-run，不影响现有使用 |

## 5. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `quant/data_collector/ctp_trade.py` | **新建** | CTP 交易接口封装（`CTPTradeApi` + `TradeSpi`） |
| `quant/risk_executor/trade_executor.py` | **修改** | 接入 `td_api`，实现真实发单 |
| `scripts/verify_trade_flow.py` | **新建** | Mock 集成验证脚本（5 个测试用例） |
| `trade_integration_summary.md` | **新建** | 本文件 |
