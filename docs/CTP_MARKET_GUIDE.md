# CTP 行情接入模块使用说明

## 功能概述

CTP 行情接入模块用于连接 SimNow 7x24 环境，订阅期货合约行情数据，聚合成 30 分钟 K线并存储到 TimescaleDB。

## 文件结构

```
quant/data_collector/
  ├── __init__.py              # 模块初始化
  └── ctp_market.py            # CTP 行情采集器

scripts/
  ├── start_ctp_market.py      # 启动脚本
  └── check_db.py              # 数据库检查脚本
```

## 配置说明

### .env 文件配置

CTP 配置在 `.env` 文件中：

**主账户配置（SimNow 官方仿真 - 256693）**：
```env
CTP__BROKER_ID=9999
CTP__ACCOUNT_ID=256693
CTP__PASSWORD=@Cmx1454697261
CTP__MD_ADDRESS=tcp://182.254.243.31:30011
CTP__TD_ADDRESS=tcp://182.254.243.31:30001
CTP__APP_ID=simnow_client_test
CTP__AUTH_CODE=0000000000000000
```

**备用账户配置（OpenCTP 7x24 - 17476）**：
```env
# 如需切换到 OpenCTP 账户，临时修改上面 CTP__ 配置为：
# CTP__ACCOUNT_ID=17476
# CTP__PASSWORD=123456
# CTP__MD_ADDRESS=tcp://trading.openctp.cn:30011
# CTP__TD_ADDRESS=tcp://trading.openctp.cn:30001
```

**配置说明**：
| 参数 | 说明 |
|------|------|
| BROKER_ID | 期货公司代码（SimNow 为 9999） |
| ACCOUNT_ID | 你的交易账户 |
| PASSWORD | 交易密码 |
| MD_ADDRESS | 行情服务器地址 |
| TD_ADDRESS | 交易服务器地址 |
| APP_ID | 应用 ID（固定值） |
| AUTH_CODE | 授权码（固定值） |

### 服务器地址说明

**SimNow 官方仿真服务器**（已测试可用）：
- 行情：`tcp://182.254.243.31:30011`
- 交易：`tcp://182.254.243.31:30001`

**OpenCTP 7x24 服务器**（备用）：
- 行情：`tcp://trading.openctp.cn:30011`
- 交易：`tcp://trading.openctp.cn:30001`

### 交易品种配置

交易品种配置：

```env
STRATEGY__SYMBOL=au2406
STRATEGY__INTERVAL=30m
```

### 配置更新记录

| 日期 | 账户 | 说明 |
|------|------|------|
| 2026-03-11 | 256693 | 切换到 SimNow 官方仿真账户（真实行情） |
| - | 17476 | 保留 OpenCTP 作为备用（7x24 可用） |

## 启动方式

### 1. 检查数据库表

```bash
python scripts/check_db.py
```

### 2. 启动行情采集

```bash
python scripts/start_ctp_market.py
```

### 3. 直接运行模块

```bash
python -m quant.data_collector.ctp_market
```

## 功能特性

### 1. 连接管理
- 自动连接 CTP 行情服务器
- 连接超时检测（10秒）
- 异常自动重连（最多5次）

### 2. 数据采集
- 订阅指定合约（默认 AU 主力合约）
- 接收实时 tick 数据
- 自动聚合 30 分钟 K线

### 3. 数据存储
- 写入 TimescaleDB kline_data 表
- 支持数据去重（ON CONFLICT）
- 发布到 Redis kline_data 频道

### 4. 消息追踪
- 使用 MessageTracer 记录所有操作
- trace_id 全链路追踪
- 异步批量写入 message_trace 表

### 5. 日志记录
- 结构化日志（structlog）
- 文件日志：logs/ctp_market.log
- 控制台实时输出

### 6. 优雅关闭
- 捕获 Ctrl+C 信号
- 关闭 VN.PY 引擎
- 刷新追踪器缓冲区
- 关闭数据库连接

## 数据流程

```
CTP 服务器
    ↓ tick 数据
CtpMarketCollector
    ↓ 聚合 30 分钟
BarData (K线)
    ↓ 并行写入
    ├─→ TimescaleDB (kline_data 表)
    └─→ Redis (kline_data 频道)
```

## 监控指标

采集器统计信息：

```python
collector.tracer.get_stats()
# {
#   'total_events': 1234,
#   'failed_events': 0,
#   'queue_full_count': 0,
#   'batch_writes': 12,
#   'dropped_events': 0,
#   'queue_size': 5
# }
```

## 故障处理

### 1. 连接失败
- 检查网络连接
- 验证 CTP 账号密码
- 确认 SimNow 服务器地址

### 2. 数据库错误
- 检查 PostgreSQL 服务状态
- 验证数据库连接配置
- 确认 kline_data 表存在

### 3. Redis 错误
- 检查 Redis 服务状态
- 验证 Redis 连接配置

## 注意事项

1. **SimNow 账号**：使用 SimNow 7x24 测试环境账号
2. **合约代码**：需要使用正确的合约代码（如 au2406）
3. **交易所**：上海黄金期货在上期所（SHFE）
4. **时间对齐**：K线时间对齐到 30 分钟边界
5. **数据去重**：使用 (symbol, interval, time) 作为唯一键

## 依赖包

```
openctp-ctp>=6.7.0
redis>=5.0.0
psycopg2-binary>=2.9.0
structlog>=24.0.0
```

## 下一步

- 添加更多合约订阅
- 支持多周期 K线（5m, 15m, 1h）
- 实现历史数据回补
- 添加行情监控告警
