# 编码规范

> 所有 agent 写代码前必读。本文件是约束，不是建议。
> 最后更新：2026-03-18

## 核心原则

**用已有的，不要重新造。**

涉及 CTP 连接、数据库、配置、常量时，先查 `quant/common/README.md`，里面有现成模块。

---

## 强制规则

### 1. CTP 连接

✅ 唯一正确方式：
```python
from quant.common.ctp_factory import ctp_trade_session

with ctp_trade_session(config) as trade_api:
    ...
```

❌ 禁止：
```python
trade_api = CTPTradeApi(broker_id=..., password="硬编码")
trade_api.connect()
# 忘记 disconnect → 连接泄漏
```

### 2. 数据库连接

✅ pandas 场景用 `db_engine`：
```python
from quant.common.db import db_engine

with db_engine(config) as engine:
    df = pd.read_sql(sql, engine)
```

✅ 非 pandas 场景用 `db_connection`：
```python
from quant.common.db import db_connection

with db_connection(config) as conn:
    cur = conn.cursor()
```

❌ 禁止：
```python
import psycopg2
conn = psycopg2.connect(host="localhost", password="@Cmx...")
```

### 3. 配置与常量

✅ 从 config 读：
```python
from quant.common.config import config

tick_size = config.strategy.tick_size
slippage = config.strategy.slippage_ticks
```

❌ 禁止硬编码魔法数字：
```python
TICK_SIZE = 0.02   # ❌ 不要在业务代码里定义
limit_price = price + 0.02 * 5  # ❌
```

### 4. 密码与敏感信息

- 所有密码字段用 `SecretStr`，读取时调用 `.get_secret_value()`
- 拼接 URL 时含特殊字符的密码必须 `urllib.parse.quote_plus(password)`
- 禁止在日志里打印密码

### 5. 状态文件写入

✅ 原子写入：
```python
import os, json
tmp = state_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(state, f)
os.replace(tmp, state_path)
```

❌ 禁止直接覆盖（崩溃会损坏文件）：
```python
with open(state_path, 'w') as f:
    json.dump(state, f)
```

### 6. 订单结果处理

- `wait_for_order()` 返回 `None` 时，不得更新持仓 state
- timeout / cancelled / rejected 均视为失败，让下一轮从 CTP 同步持仓确认
- 禁止在超时时乐观地认为订单成功

### 7. 日志

- 使用标准 `logging`，不用 `print`
- `logging.basicConfig()` 必须加 `force=True`，防止被上游模块抢占
- 禁止在生产代码中保留 structlog/MessageTracer（CTP 回调线程敏感）

---

## 新增公共模块流程

如果发现 3 处以上重复代码，应抽到 `quant/common/`：

1. 在 `quant/common/` 新建模块
2. 更新 `quant/common/README.md`
3. 更新本文件（CODING_STANDARDS.md）
4. 更新 `docs/SCAFFOLDING.md` 对应检查项标记为 ✅
5. 更新 `docs/INDEX.md` 的日期

---

## 检查清单（提交前）

- [ ] 没有 `CTPTradeApi(...)` 直接实例化
- [ ] 没有 `psycopg2.connect(...)` 直接调用
- [ ] 没有硬编码密码或 TICK_SIZE
- [ ] 状态文件用原子写入
- [ ] `wait_for_order` 的 None/timeout 有处理
- [ ] 日志用 logging，不用 print

---

**维护**: 每次发现新的反模式，加到本文件。
