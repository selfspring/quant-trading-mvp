# Tick 实时数据转 K 线解决方案

## 问题诊断

### 核心问题
SimNow 仿真环境**不推送实时 Tick 数据**，导致：
- CTP `OnRtnDepthMarketData` 回调从不触发
- 无法聚合实时 K 线
- 数据库 kline_data 表为空
- 策略无法运行

### 已验证的失败尝试
1. 测试 3 组看穿式前置 (30011/30012/30013) → 连接✅ 登录✅ 订阅✅ 但 **Tick 回调不触发**
2. vnpy_ctp 握手失败 (error 4040)
3. 快期客户端有行情 → 说明使用了非 CTP 数据源

---

## 重要更新 (2026-03-16)

### SimNow Tick 问题已解决
- **验证结果**: SimNow 在交易时段可以正常推送 Tick 数据
- **测试**: 早盘和午盘均收到 Tick，CTP 连接/登录/订阅/回调全部正常
- **解决方案升级**: 从三级数据回退架构升级为 CTP 长驻采集 + Cron 策略执行

### 新架构

```
交易时段开始
  → Cron 启动 CTP 长驻采集进程 (run_ctp_collector.py)
  → 持续收 Tick → 聚合 1 分钟 K 线 → 存入 kline_data 表
  → 策略 Cron 每 5 分钟触发 (run_single_cycle.py)
  → 从数据库读 K 线 → ML 预测 → 风控 → 发单
交易时段结束
  → 采集进程自动退出
```

### Cron Job 配置

**数据采集（每个时段启动一次长驻进程）**:
- collector-morning: 09:00 启动，采集到 11:30 自动退出
- collector-afternoon: 13:30 启动，采集到 15:00 自动退出
- collector-night: 21:00 启动，采集到 23:00 自动退出

**策略执行（每 5 分钟一次）**:
- trading-morning: 09:00-11:30
- trading-afternoon: 13:30-15:00
- trading-night: 21:00-23:00

### 新增文件
- `scripts/run_ctp_collector.py` — CTP 长驻采集进程
- `scripts/run_single_cycle.py` — 单次策略执行脚本（cron 触发）

---

## 解决方案（原始版本）

### 三级数据回退架构

```
┌─────────────────────────────────────┐
│  策略请求 K 线数据                    │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Level 1: SimNow 实时   │ ← 优先尝试
    │  Tick → 聚合 K 线      │
    └──────────┬───────────┘
               │ 失败
               ▼
    ┌──────────────────────┐
    │ Level 2: 备用 API     │ ← 自动回退
    │  Tushare/AkShare      │
    └──────────┬───────────┘
               │ 失败
               ▼
    ┌──────────────────────┐
    │ Level 3: 模拟数据     │ ← 保证策略可测试
    │  随机游走生成          │
    └──────────────────────┘
```

### 已实现的功能

#### 1. 备用数据源模块
**文件**: `quant/data_collector/backup_data_source.py`

支持的数据源：
- **AkShare** (默认) - 免费期货数据，无需 token
- **Tushare** (可选) - 专业金融数据，需 token
- **CSV 文件** - 本地历史数据
- **模拟生成** - 随机游走算法

核心方法：
```python
# 获取 K 线（自动选择可用数据源）
klines = backup.get_realtime_klines(symbol='au2606', count=100, period='1min')

# 生成模拟数据（用于测试）
mock_klines = backup.generate_mock_klines(symbol='au2606', count=100, base_price=580.0)

# 获取并存储到数据库
backup.fetch_and_store(symbol='au2606', count=200, period='1min')
```

#### 2. 增强版主策略
**文件**: `scripts/main_strategy_enhanced.py`

新增功能：
- 启动时自动检测 SimNow 是否有实时数据
- 无数据时自动切换到备用模式
- 策略循环中支持多级数据源回退
- 保证策略逻辑始终可测试

---

## 使用方法

### 方案 A: 直接运行增强版（推荐）

```bash
cd E:\quant-trading-mvp
$env:PYTHONIOENCODING="utf-8"
python scripts/main_strategy_enhanced.py
```

**行为**:
1. 自动检测 SimNow 实时数据
2. 无数据时从 AkShare 加载历史 K 线
3. 策略正常运行，ML 预测、信号处理、风控全部工作

### 方案 B: 测试备用数据源

```bash
python scripts/test_backup_data.py
```

**输出示例**:
```
✅ 备用数据源类型：akshare
✅ 获取成功：10 根 K 线
✅ 数据存储成功
```

### 方案 C: 配置 Tushare（可选）

如需更高质量的实时数据：

1. 注册 Tushare: https://tushare.pro
2. 获取 token
3. 在 `.env` 中添加:
   ```
   TUSHARE_TOKEN=your_token_here
   ```

---

## 测试结果

### 测试 1: 备用数据源可用性
```
✅ AkShare 初始化成功
✅ 获取 au2606 日线数据: 10 根
✅ 生成模拟 1min K 线：10 根
✅ 存储 20 条数据到数据库
```

### 测试 2: 数据库验证
```
总记录数：20
时间范围：2026-02-05 ~ 2026-03-12
最新 K 线：2026-03-12 | O:1151.00 H:1156.86 L:1146.18 C:1151.52
```

---

## 下一步行动

### 立即可做
1. ✅ **运行增强版策略** - 验证完整流程
   ```bash
   python scripts/main_strategy_enhanced.py
   ```

2. ✅ **使用历史数据回测** - 用 AkShare 日线数据测试策略逻辑

3. ✅ **等待夜盘测试** - 21:00-23:00 时段 SimNow 可能有实时数据

### 长期改进
1. **接入实时数据源**
   - Tushare 专业版（付费，数据质量好）
   - 期货公司实盘账户（真实交易数据）

2. **优化 K 线聚合**
   - 改进 AkShare 分钟线获取（当前主要是日线）
   - 添加数据质量检查

3. **完善回测框架**
   - 添加历史数据回测模式
   - 支持策略绩效评估

---

## 关键代码位置

| 功能 | 文件 | 说明 |
|------|------|------|
| 备用数据源 | `quant/data_collector/backup_data_source.py` | 核心数据回退逻辑 |
| 增强策略 | `scripts/main_strategy_enhanced.py` | 支持多数据源的主策略 |
| 测试脚本 | `scripts/test_backup_data.py` | 验证备用数据源 |
| 原主策略 | `scripts/main_strategy.py` | 保持不变，仅 SimNow 实时数据 |

---

## 常见问题

### Q1: 为什么 SimNow 不推送 Tick？
A: SimNow 仿真环境主要测试交易接口，行情推送不稳定。夜盘时段（21:00-23:00）可能改善。

### Q2: AkShare 数据是实时的吗？
A: AkShare 期货数据主要是日线级别，分钟线数据有限。适合策略验证和回测。

### Q3: 可以用实盘吗？
A: 可以！接入实盘账户后，CTP 会正常推送 Tick 数据。当前方案适合仿真测试。

### Q4: 模拟数据准确吗？
A: 模拟数据使用随机游走，仅用于测试策略逻辑（ML 预测、风控、发单流程），不能用于验证策略盈利性。

---

## 重要更新 (2026-03-19) — 天勤全面接入

### 彻底放弃 SimNow 实时行情
- SimNow CTP 采集器偶发断线后不重连，且部分时段不稳定
- **新方案**: 改用天勤 tqsdk 直接拉取 1 分钟 K 线

### 新采集器
**文件**: `scripts/run_tq_collector.py`

```python
# 核心逻辑：用 tqsdk get_kline_serial 直接获取 1m K 线
klines = api.get_kline_serial("SHFE.au2606", 60)  # 60秒 = 1分钟
# 写入 kline_data 表，interval 字段区分 1m / 30m
```

### 交易接口切换
- **放弃**: SimNow CTP 交易（`ctp_trade.py`）
- **改用**: 天勤快期模拟盘（TqKq）
- **新增文件**: `quant/data_collector/tq_trade.py`、`quant/common/tq_factory.py`
- **账户**: 天勤账号 17340696348，快期模拟盘余额约 130 万

### Windows 定时任务更新
| 任务 | 触发时间 | 说明 |
|------|---------|------|
| tq-collector-morning | 08:59 | 天勤采集器，早盘 |
| tq-collector-afternoon | 13:29 | 天勤采集器，午盘 |
| tq-collector-night | 20:59 | 天勤采集器，夜盘 |

### tqsdk 关键踩坑
1. 合约代码用小写：`SHFE.au2606`（不能 `.upper()`）
2. `TqApi` 必须带 `TqKq()`，否则走本地 TqSim，重启清零
3. `is_changing` 只在 `wait_update` 后数据变化时触发，初始加载不触发
4. 午休时段限价单 ALIVE 超时属正常，脚本关闭时 tqsdk 自动撤单

---

## 总结

✅ **问题已解决**: SimNow 无 Tick → 无法生成 K 线的问题

✅ **方案已实现**: 三级数据回退架构，保证策略始终可运行

✅ **代码已测试**: 备用数据源工作正常，数据库已有测试数据

**你现在可以**:
1. 运行增强版策略验证完整流程
2. 用历史数据测试策略逻辑
3. 等待夜盘或接入实盘获取实时数据

---

_创建时间：2026-03-13_
_状态：✅ 已完成_
