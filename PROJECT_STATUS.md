# 量化交易系统 - 项目状态总结 (2026-03-12)

## ✅ 已完成的功能

### 1. 核心架构
- **CTP 行情采集**: `quant/data_collector/ctp_market.py` (openctp-ctp)
- **CTP 交易接口**: `quant/data_collector/ctp_trade.py`
- **ML 预测器**: `quant/signal_generator/ml_predictor.py` (LightGBM)
- **信号处理**: `quant/risk_executor/signal_processor.py` (置信度过滤)
- **风控管理**: `quant/risk_executor/risk_manager.py`
- **交易执行**: `quant/risk_executor/trade_executor.py`
- **K 线聚合**: `quant/data_collector/kline_aggregator.py`

### 2. 数据库
- PostgreSQL 已配置 (`localhost:5432/quant_trading`)
- 表结构：`kline_data`, `tick_data`, `orders`, `trades`, `positions` 等
- 测试数据：au2604 的 200 根 1 分钟 K 线

### 3. 策略验证
- ✅ 成功读取历史 K 线数据
- ✅ ML 模型正常预测 (LightGBM)
- ✅ 信号处理逻辑正常
- ✅ 置信度过滤工作正常
- ✅ CTP 交易接口已连接 (SimNow 256693)
- ✅ 持仓同步正常

## ❌ 未解决的问题

### 1. SimNow 实时行情 (关键)
**问题**: SimNow CTP 前置服务器连接成功、登录成功、订阅成功，但**不推送 Tick 数据**

**测试结果**:
| 前置地址 | 连接 | 登录 | 订阅 | Tick |
|---------|------|------|------|------|
| 182.254.243.31:30011 | ✅ | ✅ | ✅ | ❌ |
| 182.254.243.31:30012 | ✅ | ✅ | ✅ | ❌ |
| 182.254.243.31:30013 | ✅ | ✅ | ✅ | ❌ |
| vnpy_ctp | ❌ (error 4040 握手失败) | - | - | - |

**快期客户端**: 能看到实时行情，说明使用了**非 CTP 数据源**

**影响**: 无法获取实时 K 线，策略只能用历史数据测试

### 2. 日志编码问题
- Windows GBK 终端无法显示 emoji (✅❌⚠️)
- 不影响功能，仅日志显示问题

## 📋 下一步选项

### 选项 A: 使用替代数据源 (推荐)
- 接入 **Tushare**/**AkShare** 获取实时行情
- 写入数据库供策略使用
- 优点：不依赖 SimNow，可继续开发
- 缺点：数据可能有延迟

### 选项 B: 夜盘再测试
- SimNow 夜盘 (21:00-02:30) 可能推送行情
- 今晚再测试

### 选项 C: 用历史数据测试下单
- 降低置信度阈值 (0.65→0.50)
- 验证 ML 信号→风控→下单全流程
- 优点：验证逻辑完整性
- 缺点：不是真实行情

## 🔧 配置信息

```
SimNow 账户：256693
密码：@Cmx1454697261
BrokerID: 9999

行情前置：tcp://182.254.243.31:30011 (主用)
交易前置：tcp://182.254.243.31:30001

数据库：postgresql://postgres:@localhost:5432/quant_trading
策略品种：au2604
置信度阈值：0.65 (默认) / 0.50 (测试模式)
```

## 📁 关键文件

- 主策略：`scripts/main_strategy.py`
- 配置：`.env`
- 日志：`logs/main_strategy.log`
- 模型：`models/lgbm_model.txt`
- 测试数据生成：`generate_test_data.py`

## 💡 经验教训

1. **SimNow CTP 不提供实时行情推送** - 即使连接/登录/订阅都成功
2. **interval 字段大小写敏感** - 查询时用 '1m' 而非 '1min'
3. **symbol 大小写一致** - 数据库存小写，查询也要小写
4. **vnpy_ctp 与 SimNow 不兼容** - error 4040 握手解密失败
5. **openctp-ctp 可用** - 但需要修复回调问题

## 📝 待办事项

- [ ] 决定数据源方案 (Tushare/AkShare/夜盘测试)
- [ ] 测试完整下单流程 (降低置信度)
- [ ] 修复日志 emoji 编码问题
- [ ] 添加错误重试机制
- [ ] 完善文档 README.md
