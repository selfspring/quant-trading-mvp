# CTP 行情接入模块 - 安装和部署指南

## 当前状态

✅ **已完成**：
- CTP 行情采集模块：`quant/data_collector/ctp_market.py`
- 启动脚本：`scripts/start_ctp_market.py`
- 数据库检查脚本：`scripts/check_db.py`
- 模块测试脚本：`scripts/test_ctp_module.py`
- 使用文档：`docs/CTP_MARKET_GUIDE.md`

## 安装步骤

### 1. 安装依赖包

```bash
pip install -r requirements.txt
```

**注意**：如果 `vnpy` 和 `vnpy-ctp` 安装失败，需要单独安装：

```bash
pip install vnpy==3.9.0
pip install vnpy-ctp==6.6.9
```

### 2. 验证安装

```bash
python scripts/test_ctp_module.py
```

应该看到：
```
[PASS] Imports
[PASS] Config
[PASS] VN.PY
```

### 3. 检查数据库

```bash
python scripts/check_db.py
```

应该看到 kline_data 表结构。

### 4. 启动采集器

```bash
python scripts/start_ctp_market.py
```

## 功能说明

### 核心功能

1. **连接 CTP 行情服务器**
   - 使用 SimNow 7x24 测试环境
   - 自动重连机制

2. **订阅合约行情**
   - 默认订阅 AU2406（上海黄金期货）
   - 可配置其他合约

3. **聚合 K线数据**
   - 接收 tick 数据
   - 聚合成 30 分钟 K线
   - 时间对齐到 30 分钟边界

4. **数据存储**
   - 写入 TimescaleDB kline_data 表
   - 发布到 Redis kline_data 频道
   - 支持数据去重

5. **消息追踪**
   - 全链路 trace_id 追踪
   - 异步批量写入 message_trace 表
   - 性能统计

6. **日志记录**
   - 结构化日志（structlog）
   - 文件：logs/ctp_market.log
   - 控制台实时输出

## 配置说明

### CTP 配置（.env）

```env
CTP__BROKER_ID=9999
CTP__ACCOUNT_ID=17476
CTP__PASSWORD=123456
CTP__MD_ADDRESS=tcp://180.168.146.187:10211
CTP__TD_ADDRESS=tcp://180.168.146.187:10201
```

### 策略配置（.env）

```env
STRATEGY__SYMBOL=au2406
STRATEGY__INTERVAL=30m
```

## 数据库表结构

kline_data 表字段：
- `time`: 时间戳（主键之一）
- `symbol`: 合约代码（主键之一）
- `interval`: K线周期（主键之一）
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `open_interest`: 持仓量

## 使用示例

### 启动采集器

```bash
cd C:\Users\chen\.openclaw\workspace\quant-trading-mvp
python scripts\start_ctp_market.py
```

### 查看日志

```bash
tail -f logs/ctp_market.log
```

### 查询数据

```sql
SELECT * FROM kline_data 
WHERE symbol = 'AU2406' 
ORDER BY time DESC 
LIMIT 10;
```

## 故障排��

### 1. vnpy 未安装

```bash
pip install vnpy==3.9.0 vnpy-ctp==6.6.9
```

### 2. 连接失败

- 检查网络连接
- 验证 SimNow 账号密码
- 确认服务器地址正确

### 3. 数据库错误

- 检查 PostgreSQL 服务
- 验证数据库连接配置
- 确认 kline_data 表存在

### 4. Redis 错误

- 检查 Redis 服务
- 验证 Redis 连接配置

## 下一步开发

1. 添加更多合约订阅
2. 支持多周期 K线（5m, 15m, 1h）
3. 实现历史数据回补
4. 添加行情监控告警
5. 实现断线重连优化

## 文件清单

```
quant/data_collector/
  ├── __init__.py              # 模块初始化
  └── ctp_market.py            # CTP 行情采集器（主要实现）

scripts/
  ├── start_ctp_market.py      # 启动脚本（带重连）
  ├── check_db.py              # 数据库检查
  └── test_ctp_module.py       # 模块测试

docs/
  └── CTP_MARKET_GUIDE.md      # 使用指南
```

## 技术栈

- **VN.PY**: 交易接口框架
- **vnpy-ctp**: CTP 接口适配器
- **TimescaleDB**: 时序数据库
- **Redis**: 消息队列
- **structlog**: 结构化日志
- **psycopg2**: PostgreSQL 驱动

## 性能指标

- Tick 处理延迟: < 10ms
- K线聚合延迟: < 50ms
- 数据库写入: 批量异步
- 消息追踪: 异步队列

## 注意事项

1. SimNow 为测试环境，数据仅供测试使用
2. 生产环境需要使用真实 CTP 账号
3. K线时间对齐到 30 分钟边界（如 09:00, 09:30, 10:00）
4. 数据去重使用 (symbol, interval, time) 唯一键
5. 优雅关闭使用 Ctrl+C 信号

---

**完成时间**: 2026-03-09
**版本**: v1.0
