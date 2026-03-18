# 调查结果汇总 (2026-03-18)

## 问题 1：策略日志文件为空 ✅ 已修复

### 现象
- `logs/strategy_2026-03-18.log` 文件存在但为 0 字节
- 脚本执行时控制台有日志输出，但文件没有内容

### 根本原因
Python 的 `logging.basicConfig()` 有个特性：**如果已经被调用过，后续调用会被静默忽略**。

测试验证：
```python
# 第一次调用
logging.basicConfig(handlers=[logging.FileHandler('file1.log')])
logger.info("Message 1")  # → 写入 file1.log

# 第二次调用（被忽略！）
logging.basicConfig(handlers=[logging.FileHandler('file2.log')])
logger.info("Message 2")  # → 仍然写入 file1.log，file2.log 为空
```

在 `run_single_cycle.py` 中，某个导入的模块（可能是 quant 子模块）先调用了 `basicConfig()`，导致脚本主体的配置被忽略。

### 解决方案
在 `run_single_cycle.py` 的 `basicConfig()` 中添加 `force=True` 参数：

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True  # 强制重新配置
)
```

### 修复文件
- `scripts/run_single_cycle.py` (第 29-36 行)

---

## 问题 2：SimNow 订单不成交 ⚠️ 待调查

### 现象
- 订单成功提交到 CTP：`报单已提交，OrderRef=1`
- 但 CTP 持仓始终为 0
- 每次策略执行都发现 "CTP 无持仓但 state 有记录，清空 state"

### 可能原因
1. **SimNow 仿真环境特性**：
   - SimNow 可能只在交易时段撮合成交
   - 非交易时段的订单会挂单但不成交
   
2. **订单类型问题**：
   - 市价单在 SimNow 可能需要对手盘
   - 仿真环境流动性不足

3. **交易时段限制**：
   - 当前时间 (10:15) 是交易时段（早盘 9:00-11:30）
   - 但 SimNow 可能只在特定时段撮合

4. **账户权限问题**：
   - SimNow 账户 256693 是否有交易权限
   - 是否需要先入金才能成交

### 下一步调查
1. 检查 SimNow 账户状态和权限
2. 查看 CTP 订单回报（OnRtnOrder）是否有成交回报
3. 确认 SimNow 撮合规则（是否需要对手盘）
4. 考虑在代码中添加订单状态跟踪，区分"已提交"和"已成交"

### 建议改进
1. **添加订单状态跟踪**：
   - 在 `ctp_trade.py` 中添加 `get_orders_by_day()` 和 `get_trades_by_day()` 方法
   - 或者注册回调函数处理 OnRtnTrade 回报

2. **改进 state 同步逻辑**：
   - 不在开仓时立即记录到 state
   - 等待成交回报后再更新 state

3. **添加成交确认日志**：
   - 在 `TradeSpi.OnRtnTrade` 中添加详细日志
   - 确认是否有成交回报

---

## 其他发现

### Windows 任务计划正常运行
- 6 个定时任务（3 个采集 + 3 个策略）都在运行
- 采集进程正常收集 K 线数据
- 策略每 5 分钟执行一次

### 数据库正常
- `kline_data` 表有 16543 条记录
- 今日已采集 31 根 1 分钟 K 线
- 最新数据到 09:29

### ML 模型正常
- 预测信号：buy (置信度 0.43-0.47)
- 预测收益率：~0.6%
- 置信度过滤正常工作

---

## 待办事项

1. ✅ 修复日志文件问题
2. ⏳ 调查 SimNow 成交问题
3. ⏳ 添加订单状态跟踪
4. ⏳ 改进 state 同步逻辑（等待成交后再记录）
