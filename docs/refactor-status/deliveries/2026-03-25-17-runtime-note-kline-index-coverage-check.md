# Runtime Note - kline_data 索引 / 执行计划 / 数据覆盖检查（id=149）

## 摘要
本轮仅做只读取证，目标是判断 `news_analysis.id=149` 的 `find_price` 慢路径，主要由 **索引问题**、**数据缺口**，还是**两者叠加**导致。

结论先行：
- **判断：两者叠加，但主因更偏向数据缺口。**
- 证据链如下：
  1. `au9999` 在 `anchor_time=2013-01-02 18:33:56+08` 附近，**30m 数据完全缺失**；查询前后都找不到任何 30m 记录。
  2. 同一时间窗内，`1m` 也存在**跨交易日的大空档**：最近前值在 `2012-12-31 15:00:00+08`，最近后值在 `2013-01-04 09:01:00+08`，中间跨越约 **90.0 小时**。
  3. `kline_data` 当前**没有 `(symbol, interval, time)` 这一类能直接支撑查询模式的复合索引**；现有索引主要是 `(symbol, time)`、`time DESC`、以及主键 `(time, symbol, interval)`。
  4. `EXPLAIN ANALYZE` 显示 30m 查询在找不到数据时，需要扫描大量 chunk / page，尤其 `30m after` 明显更重；这说明**索引不匹配放大了“无数据/有缺口”场景的代价**。

因此：
- **不是纯索引问题**：因为即使索引更好，`30m` 这里仍然是“查不到”。
- **也不是纯数据问题**：因为当前索引形态不适合 `symbol + interval + time +/- ORDER BY time LIMIT 1`，导致无命中时扫描放大。
- **综合判断：两者叠加，主因更偏数据缺口，索引问题负责把慢路径放大。**

---

## 战前回忆 / 已遵守踩坑记录
已先回看并遵守：
- `quant/common/README.md`
- `docs/CODING_STANDARDS.md`
- `docs/refactor-status/deliveries/2026-03-25-17-runtime-note-verify-news-price-impact-id149-find-price-probe.md`
- `scripts/verify_news_price_impact_id149_find_price_probe.py`

本轮额外遵守：
- **不改业务逻辑**
- **不创建索引**
- **不修改数据**
- 对分析型 SQL 设置 `statement_timeout='5s'`
- 只围绕 `id=149 / au9999 / 2013-01-02` 做边界内取证

---

## 关键上下文
- `analysis_id / id`: `149`
- `anchor_time`: `2013-01-02 18:33:56+08:00`
- `symbol`: `au9999`
- 已知慢查询模式：
  - `symbol='au9999' AND interval='30m' AND time <= anchor_time ORDER BY time DESC LIMIT 1`
  - `symbol='au9999' AND interval='30m' AND time >= anchor_time ORDER BY time ASC LIMIT 1`

---

## 实际执行的 SQL / 命令摘要
由于本机 `psql` 不在 PATH，本轮改用 `python + psycopg2` 执行只读 SQL。

核心检查包括：
1. 读取 `pg_indexes` 查看 `kline_data` 索引
2. 读取 `id=149` 的 `anchor_time`
3. 对以下 SQL 做 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)`：
   - `30m before`
   - `30m after`
   - `1m before`
   - `1m after`
4. 检查 `au9999` 在 `2012-12-30 ~ 2013-01-06` 窗口内的 `30m / 1m` 覆盖
5. 计算 anchor 与最近前/后可用记录的距离

本轮中间产物：
- `E:\quant-trading-mvp\tmp_kline_index_coverage_summary.json`

---

## kline_data 关键索引现状摘要
从 `pg_indexes` 读到的 public 层索引如下：

1. `idx_kline_data_symbol_time`
   - `CREATE INDEX idx_kline_data_symbol_time ON public.kline_data USING btree (symbol, "time")`
2. `idx_kline_symbol_time`
   - `CREATE INDEX idx_kline_symbol_time ON public.kline_data USING btree (symbol, "time" DESC)`
3. `kline_data_pkey`
   - `CREATE UNIQUE INDEX kline_data_pkey ON public.kline_data USING btree ("time", symbol, "interval")`
4. `kline_data_time_idx`
   - `CREATE INDEX kline_data_time_idx ON public.kline_data USING btree ("time" DESC)`

### 索引判断
**不存在**以下更贴近慢查询模式的索引：
- `(symbol, interval, time)`
- `(symbol, interval, time DESC)`
- 其他等价覆盖 `symbol + interval + time` 最近价查询的复合索引

### 影响解释
当前最近价查询既过滤 `symbol`，又过滤 `interval`，还要求按 `time` 正/倒序找最近一条：
- 现有 `(symbol, time)` 索引只能先按 symbol/time 缩小，但 **interval 仍需过滤**。
- 主键 `(time, symbol, interval)` 以 `time` 为前导列，不适合本次按 `symbol + interval` 精确过滤后再最近价检索的模式。
- 所以从索引适配性看，**当前索引不是理想形态**。

---

## 关键慢查询执行计划摘要

> 注：下述均为 `statement_timeout='5s'` 内的 `EXPLAIN ANALYZE` 摘要。

### 1) 30m before
SQL：
```sql
SELECT close, time
FROM kline_data
WHERE symbol = 'au9999'
  AND interval = '30m'
  AND time <= TIMESTAMPTZ '2013-01-02 18:33:56+08'
ORDER BY time DESC
LIMIT 1;
```

结果摘要：
- 返回：`NULL`（无命中）
- 顶层：`Limit`
- 顶层实际耗时：`58.363 ms`
- `shared_hit_blocks=95`
- `shared_read_blocks=1719`
- 扫描节点数（展开后统计）：约 `260`
- 采样索引名里主要出现：`kline_data_pkey` 系列 chunk 索引

执行计划结论：
- 查询没有找到任何 `30m` 记录。
- 计划在多个 chunk 上展开，发生了明显 IO（`1719` read blocks）。
- 说明在“无命中”情况下，需要跨 chunk 做较多尝试；而且没有一个直接匹配 `symbol+interval+time` 的索引来快速证明“没有”。

### 2) 30m after
SQL：
```sql
SELECT close, time
FROM kline_data
WHERE symbol = 'au9999'
  AND interval = '30m'
  AND time >= TIMESTAMPTZ '2013-01-02 18:33:56+08'
ORDER BY time ASC
LIMIT 1;
```

结果摘要：
- 返回：`NULL`（无命中）
- 顶层：`Limit`
- 顶层实际耗时：`369.541 ms`
- `shared_hit_blocks=30613`
- `shared_read_blocks=10778`
- 扫描节点数（展开后统计）：约 `690`
- 采样索引名混合出现 `kline_data_time_idx` / `kline_data_pkey` / 各 chunk 索引

执行计划结论：
- 这是本轮计划中最重的 30m 查询。
- 由于 `after` 方向同样无数据，执行器跨更多 chunk 展开检索，buffer 消耗非常大。
- **这更像“数据不存在 + 索引不匹配导致代价放大”的组合症状**，而不是单纯某个索引完全失效。

### 3) 1m before（对照）
SQL：
```sql
SELECT close, time
FROM kline_data
WHERE symbol = 'au9999'
  AND interval = '1m'
  AND time <= TIMESTAMPTZ '2013-01-02 18:33:56+08'
ORDER BY time DESC
LIMIT 1;
```

结果摘要：
- 命中：`2012-12-31 15:00:00+08`, `close=340.2900`
- 顶层耗时：`0.026 ms`
- `shared_hit_blocks=3`, `shared_read_blocks=0`

执行计划结论：
- 尽管索引不完美，但在“很快能找到一条候选记录”的场景下，1m 查询非常快。
- 这说明慢路径并不是所有最近价查询都慢，而是**“没有 30m、且 1m 也跨较大空档”时才会退化**。

### 4) 1m after（对照）
SQL：
```sql
SELECT close, time
FROM kline_data
WHERE symbol = 'au9999'
  AND interval = '1m'
  AND time >= TIMESTAMPTZ '2013-01-02 18:33:56+08'
ORDER BY time ASC
LIMIT 1;
```

结果摘要：
- 命中：`2013-01-04 09:01:00+08`, `close=336.9000`
- 顶层耗时：`0.078 ms`
- `shared_hit_blocks=6`, `shared_read_blocks=0`

执行计划结论：
- 1m after 虽然跨到了下一交易日，但在当前 warm/plan 条件下实际返回很快。
- 这也进一步说明：**真正异常的是 30m 完全缺失**；probe 中感知到的累计慢，主要来自 30m 两侧未命中后再 fallback，而不是 1m 单查本身必慢。

---

## au9999 在相关时间窗口的数据覆盖情况摘要
检查窗口：`2012-12-30 00:00:00+08 ~ 2013-01-06 00:00:00+08`

### 30m 覆盖
结果：
- `30m_window_count = 0`
- `30m_prev_next.prev_time = NULL`
- `30m_prev_next.next_time = NULL`

覆盖结论：
- `au9999` 在该窗口内 **完全没有 30m 数据**。
- 不只是 anchor 左右缺一边，而是前后都没有任何 30m 可供最近价查询使用。
- 这足以解释为什么 `30m before / 30m after` 都未命中，并触发 fallback。

### 1m 覆盖
结果：
- `1m_window_count = 450`
- 窗口首批数据从：`2012-12-31 09:01:00+08`
- 窗口末批数据到：`2013-01-04 15:00:00+08`
- anchor 前最近记录：`2012-12-31 15:00:00+08`
- anchor 后最近记录：`2013-01-04 09:01:00+08`

计算结果：
- anchor 距离最近前值：约 **51.566 小时**
- anchor 距离最近后值：约 **38.451 小时**
- 前后最近可用 1m 记录之间总间隔：约 **90.017 小时**

覆盖结论：
- `1m` 不是完全没有，但在 anchor 周围存在非常明显的**跨交易日大空档**。
- 这意味着 fallback 到 1m 后，虽然能找到价格，但这个价格离新闻 anchor 已经很远。

---

## 对“索引问题 vs 数据缺口”的判断结论
### 最终判断
**两者叠加，主因更偏数据缺口。**

### 为什么不是“主要是索引问题”
- `30m` 在目标窗口内是 **0 条**。
- 即使有理想索引，`30m before/after` 仍会返回空。
- 所以“查不到”本身首先是数据事实，而不是索引事实。

### 为什么不是“主要是纯数据缺口，与索引无关”
- 当前缺少 `(symbol, interval, time)` 这类直接匹配查询模式的索引。
- 执行计划中 `30m after` 为了证明“没有数据”，需要展开大量 chunk，读很多 block。
- 这表明索引不匹配**放大了无数据场景的开销**。

### 综合判断逻辑
- **数据缺口**决定了 30m 查询一定 miss，并触发 fallback；这是慢路径出现的根因。
- **索引不匹配**决定了 miss 过程不够高效；这是慢路径被放大的原因。

因此，用一句话概括：
> `id=149` 的 `find_price` 慢路径，根因是 `au9999` 在 anchor 附近缺少可用 30m 数据，且 1m 也有明显时间空档；同时 `kline_data` 缺少适配 `symbol+interval+time` 最近价检索的复合索引，使得“查不到”的成本被进一步放大。

---

## 与上一轮 probe 的对应关系
上一轮 probe 已显示：
- 首个显著慢子查询是 `find_price_base_30m_before_query`
- `30m before / after` 都未命中
- 随后 fallback 到 `1m before / after`

本轮补上的证据是：
- **为什么未命中**：因为 `30m` 在该窗口内确实为 0 条
- **为什么 miss 会变慢**：因为缺少更贴合访问模式的复合索引，计划需要跨大量 chunk 展开检索

两轮证据是互相闭环的。

---

## 最小下一步修复建议
> 本轮不修，只给最小建议。

1. **优先补充一个针对最近价查询模式的索引设计评估**
   - 重点验证 `(symbol, interval, time)` 或等价方案
   - 目标不是立即上线，而是先在测试环境验证该类 SQL 的 plan 变化

2. **并行评估 `au9999` 在历史窗口内的 30m 数据生成/补齐策略**
   - 因为本案里 30m 是完全缺失，单靠索引不能让查询命中

3. **业务侧可考虑对“目标 interval 完全无覆盖”的 symbol/time 组合做更早短路**
   - 但这是后续修复阶段的话题，本轮不展开

---

## 对照期望输出检查
- `kline_data` 关键索引现状摘要：**已提供**
- 关键慢查询的执行计划摘要：**已提供**
- `au9999` 在相关时间窗口的 30m / 1m 覆盖情况摘要：**已提供**
- 对“索引问题 vs 数据缺口”的判断结论：**已提供**
- 最小下一步修复建议：**已提供**
- delivery / runtime note 文件：**已生成**

---

## 关键读回确认
已读回：
- `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-25-17-runtime-note-kline-index-coverage-check.md`
- `E:\quant-trading-mvp\scripts\verify_news_price_impact_id149_find_price_probe.py`
- `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-25-17-runtime-note-verify-news-price-impact-id149-find-price-probe.md`
