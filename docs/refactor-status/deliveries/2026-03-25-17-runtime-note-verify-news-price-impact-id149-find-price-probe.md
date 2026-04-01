# Runtime Note - verify_news_price_impact id=149 find_price path fine-grained probe

## 摘要
本轮仅针对 `news_analysis.id=149`（`analysis_id=149`）执行 `find_price()` 路径细粒度探针，目标是定位第 2 条记录进入 `find_price` 链路后的**首个真实慢查询 / 超时点**。

结论先行：
- **本轮未复现硬超时。** 所有数据库子查询均在 5 秒 `statement_timeout` 边界内返回。
- **已定位首个显著慢点**：`find_price_base()` 内的第一个分钟线子查询链路。
- 更细粒度地说，**首个显著变慢的单个数据库子查询**是：
  - `find_price_base_30m_before_query`
  - SQL 目标：`kline_data`，`symbol='au9999'`，`interval='30m'`，条件 `time <= anchor_time`，排序 `ORDER BY time DESC LIMIT 1`
  - 耗时：**594ms**
  - 结果：未命中（`row=None`）
- 若按“首个显著慢步骤（函数级）”定义，则是：
  - `find_price_base`
  - 总耗时：**3328ms**
  - 由连续多次 fallback 查询叠加导致：`30m before` → `30m after` → `1m before` → `1m after`
- 本轮证据显示，`id=149` 的首个明显退化点不是 `find_best_symbol()`，而是**进入 `find_price()` 后，对 `kline_data` 的多轮 before/after 最近价查询**。

## 战前回忆 / 已遵守踩坑记录
已先回看并遵守：
- `quant/common/README.md`
  - 本轮不改正式业务逻辑，仅新增独立 probe 脚本
- `docs/CODING_STANDARDS.md`
  - 保持最小侵入；日志落盘；不做大范围改造
- 既有 runtime notes（尤其 first-record probe）
  - 已知第 1 条记录 `id=148` 非慢点
  - 已知第 2 条记录 `id=149` / `symbol=au9999` 是应继续收缩的目标
- 额外遵守：
  - **未回退到 legacy `time`**
  - **未跑整批**
  - **每个 DB 子查询均设置 5 秒 statement timeout**
  - **每个子步骤都记录耗时 / 命中 / timeout 情况**

## Probe 日志文件路径
- `E:\quant-trading-mvp\logs\verify_news_price_impact_id149_find_price_probe_20260325-171907.log`

## id=149 关键记录信息
- `id=149`
- `analysis_id=149`
- `news_id=159706`
- `anchor_time=2013-01-02 18:33:56+08:00`
- `published_time=None`
- `analyzed_at=None`
- `effective_time=None`
- `news_time=2013-01-02 18:33:56+08:00`
- `direction=bearish`
- `importance=medium`
- `confidence=0.72`
- `title='Mining and banking shares lead the way as FTSE receives fiscal cliff boost'`
- 已确认 `find_best_symbol()` 选中：`symbol=au9999`

## 细粒度探针点到达情况
### 1. 记录装载 / 关键字段确认
- **已到达**
- `record_load`: 172ms
- 成功确认 `id=149` 关键字段与 anchor time

### 2. `find_best_symbol`
- **已到达**
- `find_best_symbol_30m_window`
  - 目标表：`kline_data`
  - 条件：`interval='30m'`，窗口 `[anchor-1d, anchor+2d]`
  - 耗时：62ms
  - 结果：`[]`
- `find_best_symbol_all_interval_window`
  - 目标表：`kline_data`
  - 条件：不限制 interval，同窗口
  - 耗时：47ms
  - 结果：`[['au9999', 243]]`
- `find_best_symbol_select`
  - 耗时：46ms
  - 结果：`symbol=au9999`
- 结论：**`find_best_symbol` 不是首个慢点**

### 3. `find_price_base` 前后
- **已到达**
- 这是本轮首个明显慢步骤，函数总耗时 **3328ms**

子查询明细：
1. `find_price_base_30m_before_query`
   - SQL 目标：`kline_data` / `interval='30m'`
   - 条件：`symbol='au9999' AND time <= anchor_time`
   - 排序：`ORDER BY time DESC LIMIT 1`
   - 耗时：**594ms**
   - 结果：未命中
   - 判定：**首个显著慢子查询**
2. `find_price_base_30m_after_query`
   - 条件：`symbol='au9999' AND time >= anchor_time AND interval='30m'`
   - 排序：`ORDER BY time ASC LIMIT 1`
   - 耗时：**1265ms**
   - 结果：未命中
3. `find_price_base_1m_before_query`
   - 条件：`symbol='au9999' AND time <= anchor_time AND interval='1m'`
   - 排序：`ORDER BY time DESC LIMIT 1`
   - 耗时：391ms
   - 结果：命中 `340.2900 @ 2012-12-31 15:00:00+08:00`
4. `find_price_base_1m_after_query`
   - 条件：`symbol='au9999' AND time >= anchor_time AND interval='1m'`
   - 排序：`ORDER BY time ASC LIMIT 1`
   - 耗时：**750ms**
   - 结果：命中 `336.9000 @ 2013-01-04 09:01:00+08:00`

选择逻辑：
- `nearest` 比较 before/after 时间差后，选择了 `after`
- 最终：`base_price=336.9`
- `base_time=2013-01-04 09:01:00+08:00`
- `base_interval=1m`
- gap：138424 秒（约 38.45 小时），仍在脚本允许的 5 天边界内

### 4. `find_price_30m` 前后
- **已到达**
- 函数总耗时：1719ms

子查询明细：
1. `find_price_30m_30m_after_query`
   - `kline_data`, `interval='30m'`
   - 耗时：844ms
   - 未命中
2. `find_price_30m_1m_after_query`
   - `kline_data`, `interval='1m'`
   - 耗时：766ms
   - 命中 `336.9000 @ 2013-01-04 09:01:00+08:00`

结论：此步骤也偏慢，但它不是首个慢点；首个慢点已在 `find_price_base` 内出现。

### 5. `find_price_4h` 前后
- **已到达**
- 函数总耗时：1657ms

子查询明细：
1. `find_price_4h_30m_after_query`
   - 耗时：843ms
   - 未命中
2. `find_price_4h_1m_after_query`
   - 耗时：719ms
   - 命中 `336.9000 @ 2013-01-04 09:01:00+08:00`

### 6. `find_price_1d` 前后
- **已到达**
- 实际路径走的是 daily fallback 查询：
  - `find_price_1d_daily_query`
  - 目标表：`kline_daily`
  - 条件：`symbol='au_continuous' AND time > 2013-01-02`
  - 排序：`ORDER BY time ASC LIMIT 1`
  - 耗时：63ms
  - 命中：`336.84 @ 2013-01-04`
- 结论：`1d` 路径不慢

### 7. fallback / interval 切换点
- **已到达并明确记录**
- `find_best_symbol`：`30m` 窗口无命中，fallback 到 `ALL interval`
- `find_price_base`：`30m before` 未命中 → `30m after` 未命中 → fallback 到 `1m before` / `1m after`
- `find_price_30m`：`30m after` 未命中 → fallback 到 `1m after`
- `find_price_4h`：`30m after` 未命中 → fallback 到 `1m after`
- `find_price_1d`：直接走 `kline_daily`

## 首个真实慢查询 / 超时点
### 硬超时结论
- **未复现硬超时**
- 所有查询均在 5 秒 `statement_timeout` 内返回

### 首个真实显著慢点
分两层给出：

1. **首个显著慢子查询（SQL 级）**
   - `find_price_base_30m_before_query`
   - 耗时：**594ms**
   - 目标：`kline_data` / `symbol='au9999'` / `interval='30m'`
   - 条件：`time <= anchor_time`
   - 结果：未命中

2. **首个显著慢步骤（函数级）**
   - `find_price_base`
   - 耗时：**3328ms**
   - 原因：30m 未命中后继续做 30m/1m 多轮 before/after 查询，累计耗时明显放大

## 为什么可以判定这是首个慢点
- 在它之前：
  - `record_load=172ms`
  - `find_best_symbol_30m_window=62ms`
  - `find_best_symbol_all_interval_window=47ms`
  - `find_best_symbol_select=46ms`
- 到 `find_price_base_30m_before_query` 时首次跨过显著阈值（本轮以 500ms 记作显著慢）
- 且后续 `find_price_base` 累计到 3.3s，已经构成第 2 条记录链路中的首个明显退化区段

## 临时探针改动
### 修改文件清单
- `E:\quant-trading-mvp\scripts\verify_news_price_impact_id149_find_price_probe.py`

### 改动目的
- 独立复刻 `id=149` 的 `find_best_symbol` / `find_price` 细粒度链路
- 给每个 DB 子查询单独加 `statement_timeout=5000`
- 输出每一步：目标表/interval、耗时、是否命中、是否 timeout
- 不改正式业务脚本

## 关键读回确认
已读回：
- `E:\quant-trading-mvp\logs\verify_news_price_impact_id149_find_price_probe_20260325-171907.log`
- `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-25-17-runtime-note-verify-news-price-impact-id149-find-price-probe.md`
- `E:\quant-trading-mvp\scripts\verify_news_price_impact_id149_find_price_probe.py`

## 最小下一步修复建议
只给最小建议，不扩大到通用修复：
1. 优先检查 `kline_data` 上是否缺少能支撑以下模式的索引：
   - `(symbol, interval, time)`
   - 尤其是支持 `WHERE symbol=? AND interval=? AND time<=? ORDER BY time DESC LIMIT 1`
   - 以及 `WHERE symbol=? AND interval=? AND time>=? ORDER BY time ASC LIMIT 1`
2. 若索引已存在，再检查 `au9999` 在 2013-01-02 附近是否存在长时间缺口，导致查询需要扫描大量记录后才发现无 30m 命中。
3. 修复验证应继续只盯 `id=149`，不要回到整批 dry-run。

## 对照期望输出检查
- Probe 日志文件路径：**已提供**
- `id=149` 关键记录信息：**已提供**
- `find_price` 路径各子步骤结果摘要：**已提供**
- 首个真实慢查询 / 超时点：**已明确（无硬超时；首个显著慢点已给出）**
- 临时探针改动：**已列出文件与目的**
- 最小下一步修复建议：**已提供**
- delivery / runtime note 文件：**已生成**
