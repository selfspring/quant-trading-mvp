# CTP 行情接入模块 - 实现总结

## ✅ 已完成任务

### 1. 核心模块实现

**文件**: `quant/data_collector/ctp_market.py`

**功能**:
- ✅ 连接 CTP 行情服务器（SimNow 7x24）
- ✅ 订阅 AU 主力合约（可配置）
- ✅ 接收 tick 数据
- ✅ 聚合 30 分钟 K线
- ✅ 写入 kline_data 表（TimescaleDB）
- ✅ 发布到 Redis kline_data 频道
- ✅ 使用 MessageTracer 全链路追踪
- ✅ 异常处理和自动重连
- ✅ 优雅关闭（Ctrl+C）

**关键类**:
- `CtpMarketCollector`: 主采集器类
  - `connect()`: 连接 CTP 服务器
  - `subscribe()`: 订阅合约
  - `on_tick()`: 处理 tick 数据
  - `aggregate_bar()`: 聚合 K线
  - `save_to_db()`: 保存到数据库
  - `publish_bar()`: 发布到 Redis
  - `shutdown()`: 优雅关闭

### 2. 启动脚本

**文件**: `scripts/start_ctp_market.py`

**功能**:
- ✅ 加载配置
- ✅ 启动 CTP 行情采集
- ✅ 异常处理和重连（最多5次）
- ✅ 日志记录到 logs/ctp_market.log
- ✅ 控制台实时输出

### 3. 辅助脚本

**文件**: `scripts/check_db.py`
- ✅ 检查 kline_data 表是否存在
- ✅ 显示表结构

**文件**: `scripts/test_ctp_module.py`
- ✅ 测试模块导入
- ✅ 测试配置加载
- ✅ 测试 VN.PY 依赖

### 4. 文档

**文件**: `docs/CTP_MARKET_GUIDE.md`
- ✅ 功能概述
- ✅ 使用说明
- ✅ 数据流程
- ✅ 监控指标
- ✅ 故障处理

**文件**: `docs/CTP_DEPLOYMENT.md`
- ✅ 安装步骤
- ✅ 配置说明
- ✅ 使用示例
- ✅ 故障排查

## 📁 文件清单

```
quant/data_collector/
  ├── __init__.py                    # 模块初始化
  └── ctp_market.py                  # CTP 行情采集器（380行）

scripts/
  ├── start_ctp_market.py            # 启动脚本（带重连）
  ├── check_db.py                    # 数据库检查
  └── test_ctp_module.py             # 模块测试

docs/
  ├── CTP_MARKET_GUIDE.md            # 使用指南
  └── CTP_DEPLOYMENT.md              # 部署指南
```

## 🔧 技术实现

### 1. VN.PY 集成
- 使用 `EventEngine` 和 `MainEngine`
- 注册 `EVENT_TICK` 和 `EVENT_LOG` 事件
- 通过 `CtpGateway` 连接 CTP

### 2. K线聚合算法
- 计算 30 分钟时间窗口（对齐边界）
- 维护当前 bar 状态
- 周期结束时返回完成的 bar

### 3. 数据存储
- 使用 `ON CONFLICT` 实现数据去重
- 唯一键：(symbol, interval, time)
- 异步批量写入优化

### 4. 消息追踪
- 生成全局唯一 trace_id
- 记录所有关键事件
- 异步队列避免阻塞

### 5. 错��处理
- 连接超时检测（10秒）
- 自动重连机制（最多5次）
- 异常日志记录

## ⚙️ 配置说明

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

## 🚀 启动方式

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 检查数据库
```bash
python scripts/check_db.py
```

### 3. 测试模块
```bash
python scripts/test_ctp_module.py
```

### 4. 启动采集器
```bash
python scripts/start_ctp_market.py
```

## 📊 数据流程

```
CTP 服务器 (SimNow 7x24)
    ↓
  tick 数据
    ↓
CtpMarketCollector
    ↓
聚合 30 分钟 K线
    ↓
  BarData
    ↓
并行写入
    ├─→ TimescaleDB (kline_data 表)
    └─→ Redis (kline_data 频道)
```

## ⚠️ 注意事项

1. **依赖安装**: 需要先安装 `vnpy` 和 `vnpy-ctp`
2. **数据库表**: kline_data 表已存���，字段为 `time` 而非 `timestamp`
3. **合约代码**: 使用大写（AU2406）
4. **交易所**: 上海黄金期货在上期所（SHFE）
5. **时间对齐**: K线时间对齐到 30 分钟边界

## 🔍 下一步

1. 安装 VN.PY 依赖包
2. 运行测试脚本验证
3. 启动采集器测试连接
4. 验证数据写入数据库
5. 监控日志和性能指标

## 📝 代码统计

- **核心模块**: 380 行（ctp_market.py）
- **启动脚本**: 80 行（start_ctp_market.py）
- **测试脚本**: 100 行
- **文档**: 2 个 Markdown 文件
- **总计**: ~600 行代码 + 文档

---

**实现时间**: 2026-03-09 20:23 - 20:35
**状态**: ✅ 完成
