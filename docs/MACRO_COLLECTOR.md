# 宏观数据定时采集说明

## 功能

自动采集以下宏观经济数据并存入数据库：

1. **美元指数** (Dollar Index) - 日度
2. **10年期美债收益率** - 日度
3. **美联储基准利率** - 月度
4. **非农就业数据** - 月度
5. **CPI通胀数据** - 月度

## 使用方法

### 方式1: 直接运行（推荐用于测试）

```bash
# Windows
start_macro_collector.bat

# 或直接用 Python
python scripts/scheduled_macro_collector.py
```

### 方式2: Windows 任务计划程序（推荐用于生产）

1. 打开"任务计划程序"（Task Scheduler）
2. 创建基本任务
3. 触发器：每天 09:00
4. 操作：启动程序
   - 程序：`python.exe` 的完整路径
   - 参数：`scripts\scheduled_macro_collector.py`
   - 起始于：`E:\quant-trading-mvp`

### 方式3: 后台服务（可选）

使用 NSSM 将脚本注册为 Windows 服务：

```bash
# 下载 NSSM: https://nssm.cc/download
nssm install MacroCollector "C:\...\python.exe" "E:\quant-trading-mvp\scripts\scheduled_macro_collector.py"
nssm start MacroCollector
```

## 采集频率

- **默认**: 每天 09:00 执行一次
- **原因**: 宏观数据通常是日度/月度更新，无需高频采集
- **修改**: 编辑 `scripts/scheduled_macro_collector.py` 中的 `scheduler.add_job()` 参数

## 数据存储

- **表名**: `macro_data`
- **字段**:
  - `time`: 日期
  - `indicator`: 指标名称（DOLLAR_INDEX, US10Y_YIELD, FED_FUNDS_RATE, NON_FARM_PAYROLL, CPI_USA）
  - `value`: 数值
  - `unit`: 单位
  - `source`: 数据源

## 日志

- **位置**: `logs/macro_collector.log`
- **级别**: INFO
- **内容**: 采集状态、数据量、错误信息

## 注意事项

1. **网络依赖**: 需要访问 yfinance、AKShare、FRED 等数据源
2. **限流风险**: yfinance 有请求频率限制，如遇限流会自动切换到备用数据源
3. **数据延迟**: 宏观数据通常有1-2天的发布延迟
4. **首次运行**: 会采集最近30天的数据，后续只更新增量

## 故障排查

### 问题1: yfinance 限流

```
YFRateLimitError: Too Many Requests
```

**解决**: 等待一段时间后重试，或使用代理

### 问题2: AKShare 接口变更

```
KeyError: '美元指数'
```

**解决**: 更新 akshare 版本 `pip install -U akshare`

### 问题3: 数据库连接失败

```
psycopg2.OperationalError: could not connect
```

**解决**: 检查 PostgreSQL 是否运行，检查 `.env` 配置

## 手动测试

```bash
# 测试单个数据源
python scripts/test_fundamental_collector.py

# 查看数据库内容
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', database='quant_trading', user='postgres', password='@Cmx1454697261')
cur = conn.cursor()
cur.execute('SELECT time, indicator, value FROM macro_data ORDER BY time DESC LIMIT 10')
for row in cur.fetchall():
    print(row)
"
```

## 停止采集器

- 前台运行: 按 `Ctrl+C`
- 任务计划程序: 禁用任务
- Windows 服务: `nssm stop MacroCollector`
