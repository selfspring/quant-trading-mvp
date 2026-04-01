# quant/common — 公共工具库

> **Agent 必读**：写任何涉及 CTP、数据库、配置、常量的代码前，先看这个文件。
> 禁止绕过这里的工具直接使用底层 API。
> 最后更新：2026-03-18

---

## 模块清单

### `ctp_factory.py` — CTP 连接工厂

```python
from quant.common.ctp_factory import ctp_trade_session

# 唯一正确的 CTP 连接方式
with ctp_trade_session(config) as trade_api:
    trade_api.do_something()
# 自动 disconnect，无需 try/finally
```

**禁止**：
```python
# ❌ 不要直接创建 CTPTradeApi
trade_api = CTPTradeApi(broker_id=..., password=...)
trade_api.connect()
```

---

### `db.py` — 数据库连接工厂（首选）

```python
from quant.common.db import db_engine, db_connection

# pandas / SQLAlchemy 场景（首选）
with db_engine(config) as engine:
    df = pd.read_sql(sql, engine)

# 原生 psycopg2 场景（非 pandas）
with db_connection(config) as conn:
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
```

**禁止**：
```python
# ❌ 不要硬编码密码
conn = psycopg2.connect("host=localhost password=xxx")
# ❌ 密码含 @ 等特殊字符必须 URL 编码（db.py 内部已处理，勿自行拼接）
```

---

### `db_pool.py` — 连接池（高频场景）

适用于需要持续、频繁查询的长驻进程（如 K 线采集器）。**单次脚本用 `db_engine` 即可，不需要连接池。**

```python
from quant.common.db_pool import get_db_connection

# 高频查询场景（长驻进程）
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM klines WHERE ...", params)
        rows = cur.fetchall()
```

**选择原则**：
- 单次脚本（cron 触发）→ `db_engine` / `db_connection`
- 长驻进程（采集器）→ `db_pool.get_db_connection()`

---

### `ctp_constants.py` — 常量定义

```python
from quant.common.ctp_constants import TICK_SIZE, SLIPPAGE_TICKS, MAX_POSITION

# 不要在业务代码里写魔法数字
limit_price = price + TICK_SIZE * SLIPPAGE_TICKS
```

**禁止**：
```python
# ❌ 魔法数字
limit_price = price + 0.02 * 5
```

---

### `kline_availability.py` — 30m availability / lineage 最小规则

```python
from quant.common.kline_availability import evaluate_bucket, floor_to_30m_bucket

bucket_start = floor_to_30m_bucket(anchor_time)
evaluation = evaluate_bucket(
    symbol='au9999',
    bucket_start=bucket_start,
    native_30m_exists=False,
    minute_timestamps=minute_rows,
)
```

用途：
- 冻结 `NATIVE_30M / MERGEABLE_FROM_1M / NOT_MERGEABLE_* / UNKNOWN_CALENDAR` 最小状态枚举
- 提供严格 1m→30m 可合并判定（仅 100% 完整桶）
- 提供独立 `kline_30m_availability` 表的最小 schema SQL

**禁止**：
```python
# ❌ 不要把不完整 1m 静默当成 30m 可用
# ❌ 不要把 availability / lineage 直接混写进 kline_data 事实语义
```

---

### `config.py` — 全局配置

```python
from quant.common.config import config

# 所有运行参数从 config 读取
tick_size = config.strategy.tick_size
max_pos = config.risk.max_position
```

---

### `tracer.py` — 消息追踪（可选，有限制）

`MessageTracer` 用于调试和链路追踪，依赖 `structlog` + `redis`。

⚠️ **重要限制**：
- **禁止在任何 CTP 相关模块中 import tracer**（structlog/redis 会干扰 CTP 回调线程，导致 Tick 不触发）
- 只允许在独立的监控/调试脚本中使用
- 生产交易路径（ctp_market.py、ctp_trade.py、run_single_cycle.py）中禁止使用

```python
# ✅ 只在独立调试脚本中使用
from quant.common.tracer import MessageTracer

# ❌ 禁止在 CTP 模块中 import
# ctp_market.py 中不得出现 from quant.common.tracer import ...
```

---

## 新增公共工具的规则

如果你发现某段代码在 2 处以上重复出现，应该抽到这里：

1. 在 `quant/common/` 新建文件
2. 更新本 README（加到模块清单）
3. 更新 `docs/CODING_STANDARDS.md`（加入对应规范）
4. 更新 `docs/SCAFFOLDING.md`（标记对应检查项为已实现）
5. 替换所有旧的调用点

---

## 检查清单（agent 自检）

写代码前确认：
- [ ] CTP 连接用 `ctp_trade_session()`
- [ ] 数据库连接用 `db_engine()` / `db_connection()` / `get_db_connection()`（按场景选）
- [ ] 常量从 `ctp_constants.py` 或 `config.strategy` 读取
- [ ] 没有硬编码密码、IP、账号
- [ ] 没有裸露的 `psycopg2.connect()` 或 `CTPTradeApi()` 直接调用
- [ ] CTP 相关模块没有 import tracer/structlog/redis

**如果某项未通过**：停下来，先把对应公共模块的用法看清楚再写，或者告知主 agent 需要新建公共模块。
