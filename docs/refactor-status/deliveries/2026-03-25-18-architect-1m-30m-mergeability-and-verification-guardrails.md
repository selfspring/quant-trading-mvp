# Design Note - 1m -> 30m 可合并策略与 verification 防退化规则（最小方案）

**日期**: 2026-03-25  
**角色**: architect  
**范围**: 规则/方案设计，不含代码实现、不含数据回补执行  
**目标**: 在已确认 `au9999` 存在 `30m` 缺失、且关键窗口 `1m` 也不完整的前提下，定义一套最小可落地策略：

1. **先把能合并的合并**
2. **不能合并的标注出来**
3. **在 verification 层加入防退化规则，避免“无真实基础价格还硬验证”**

---

## 0. 战前回忆 / 本设计严格遵守的既有约束

已回看并遵守：
- `quant/common/README.md`
- `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`
- `docs/refactor-status/llm-news-pipeline-status.md`
- `docs/refactor-status/llm-news-pipeline-constraints.md`
- `docs/refactor-status/deliveries/2026-03-25-17-runtime-note-kline-index-coverage-check.md`
- `docs/refactor-status/deliveries/2026-03-25-18-runtime-note-au9999-1m-coverage-audit.md`

本设计显式遵守以下坑位：
- **不把不完整 1m 静默伪装成原生 30m**
- **不把“数据补齐规则”和“verification 判定规则”混成一层**
- **不在没有有效 base price 的情况下硬生成 verification 结论**
- **不扩大到直接实现、补数据、建索引或改 schema 细节落地**

---

## 1. 现场结论归纳（作为本设计输入前提）

基于当前 runtime note，可先冻结以下前提：

1. `au9999` 在 `2013-01-02` 邻近窗口，`30m` 数据缺失不是纯索引问题，**主因偏数据缺口**。
2. 同窗口 `1m` 也并不完整，存在约 **90 小时**的大缺口。
3. 因此，**不能采用“只要 30m 缺了，就无条件拿 1m 聚成 30m”** 的策略。
4. 但 `1m` 在很多其他窗口可能是连续且可用的，因此也**不应该因为某些脏窗口存在，就彻底放弃 1m -> 30m 的可合并能力**。

因此，本轮最小策略的核心不是“全量回补”，而是：

> **把 1m -> 30m 看成一种“有条件派生”能力，而不是默认等价替代。**

---

# A. 1m -> 30m 可合并规则

## A.1 设计目标

本层只回答一个问题：

> 当原生 `30m` 缺失时，当前这个 `30m` 时间桶是否允许由 `1m` 数据派生出来？

注意：
- 这是**数据补齐/派生规则**；
- 不是 verification 结论规则；
- 不是交易决策规则。

---

## A.2 基本原则

### A.2.1 原生优先
若目标 `30m` 桶已有原生 `30m` 数据，则：
- **直接使用原生 30m**
- 不再尝试用 `1m` 覆盖或替换

原因：
- 原生粒度优先级最高
- 避免派生结果覆盖真实数据
- 避免后续审计无法区分数据来源

### A.2.2 只允许“同桶聚合”，不允许“跨桶拼凑”
若要由 `1m` 聚成 `30m`，只能使用：
- **同一个目标 30m 时间桶内部** 的 `1m` 记录
- 不允许从前后相邻 30m 桶借分钟数据拼凑
- 不允许拿“最近前值 + 最近后值”去插值或模拟 OHLC

原因：
- 一旦跨桶拼凑，派生的时间语义就不再是该 30m 桶本身
- 会把“可合并”和“估算/插值”混在一起

### A.2.3 只允许在合法交易时段内聚合
建议以该 symbol 对应市场的**合法交易分钟集合**作为可合并前提：
- 只有落在合法交易时段内的分钟，才计入“理论应有分钟数”
- 非交易时段不计缺失
- 若该 30m 桶本身跨越非交易时段边界，则该桶默认视为**不可由最小规则自动合并**，除非后续专门补充交易日历规则

这是最小方案里非常关键的一刀：
- **先只处理“完整落在一个合法连续交易段内”的 30m 桶**
- 暂不在第一轮处理中自动支持复杂的跨午休 / 跨夜盘 / 跨节假日边界桶

原因：
- 否则会立刻把方案拖入复杂交易日历与交易所微结构问题
- 当前用户要的是“先能合并的合并”，不是一次性吃掉所有历史日历复杂性

---

## A.3 可合并判定条件（最小建议）

建议对每个目标 `30m` 桶计算一个 `mergeability_status`，并按以下顺序判定。

### A.3.1 条件 1：目标桶必须是合法 30m 桶
要求：
- 桶边界遵循统一的 30 分钟切分规则
- 时间戳必须可稳定映射到唯一 30m bucket

建议：
- 使用 **bucket_start** 作为桶标识
- 例如：`09:00`, `09:30`, `10:00`, ...
- 对应派生 K 线的主时间戳建议也使用 `bucket_start`

不建议：
- 一会儿用开盘时间，一会儿用收盘时间
- 一会儿存 `09:00`，一会儿存 `09:29` 或 `09:30`

### A.3.2 条件 2：目标桶完整落在同一合法连续交易段内
要求：
- 该 `30m` 桶的全部理论分钟都属于同一连续合法交易段
- 不跨午休、收盘、夜盘切换、节假日断点

最小判定建议：
- backend 先维护一个“该 symbol 的合法交易分钟判定函数/服务”
- 若某桶无法明确判定是否为同一连续交易段，则先保守判定为 `UNKNOWN_SESSION` / 不自动合并

### A.3.3 条件 3：桶内 1m 覆盖率达到阈值
建议同时检查两个指标：

1. **分钟覆盖率**
   - `observed_minutes / expected_minutes`
2. **首尾完整性**
   - 桶首分钟、桶末分钟是否存在（或至少首尾边界不缺失）

### A.3.4 阈值建议：采用“双阈值”，但最小实施先只开放严格档

建议定义两档：

#### 严格可合并（recommended for phase 1）
- `coverage_ratio = 100%`
- 且桶内不存在分钟断点
- 且首尾分钟齐全

处理：
- **允许派生 30m**
- 标记为 `AGGREGATED_FROM_1M_STRICT`

#### 宽松可合并（先定义，首轮默认不启用）
- `coverage_ratio >= 95%`
- 且缺失分钟数 `<= 1~2`（具体由 backend 在实现阶段按市场分钟结构校准）
- 且缺失不发生在首尾边界
- 且缺失分钟连续跨度不超过 `2m`

处理：
- 第一轮**先不自动启用**
- 仅保留为后续扩展选项

### A.3.5 最小落地建议：第一轮只接受 100% 完整桶

在当前现场下，第一轮最好用最保守规则：

> **只有当某个目标 30m 桶在合法连续交易段内、且理论应有 1m 全部齐全时，才允许由 1m 聚合生成 30m。**

原因：
- 这是最容易解释、最不容易误用的规则
- 可以立刻把“能补的补掉”与“不能补的标出来”分开
- 避免一开始就陷入“95% 到底够不够”的争议

---

## A.4 30m 派生值生成规则

当一个桶被判定为可合并时，建议按标准 OHLCV 聚合：

- `open` = 桶内最早一分钟的 open
- `high` = 桶内所有 1m 的 high 最大值
- `low` = 桶内所有 1m 的 low 最小值
- `close` = 桶内最后一分钟的 close
- `volume` / `amount` / `open_interest` 等：
  - 若源字段存在且语义明确，则按既有 K 线聚合语义处理
  - 若历史字段语义不稳或不同 symbol 不一致，则第一轮只保证价格字段可用，并把其他字段列入“后续细化项”

### A.4.1 时间戳规则建议
建议统一：
- 派生 `30m` 的时间戳 = `bucket_start`
- 同时保留可追踪元信息：
  - `source_interval = '1m'`
  - `derived_bucket_minutes = 30`
  - `coverage_ratio`
  - `expected_minutes`
  - `observed_minutes`

原因：
- 与“用开始时间标识 K 线桶”的语义最稳定
- 可避免 “09:30 这一根到底表示 09:00-09:30 还是 09:30-10:00” 的歧义

### A.4.2 不允许的派生方式
明确禁止：
- 用前后最近价插值生成 OHLC
- 用单个 1m close 复制成伪 30m OHLC
- 桶内只拿部分分钟就静默生成且不标注
- 聚合成功后写回时不保留来源标识

---

## A.5 可合并状态枚举建议

建议最小定义以下状态：

- `NATIVE_30M`
  - 原生 30m 存在，直接使用
- `MERGEABLE_FROM_1M`
  - 原生 30m 缺失，但 1m 满足严格聚合条件，可派生
- `NOT_MERGEABLE_1M_GAP`
  - 原生 30m 缺失，且桶内 1m 不完整/覆盖不足
- `NOT_MERGEABLE_CROSS_SESSION`
  - 目标桶跨越交易段边界，不在最小自动合并范围内
- `NOT_MERGEABLE_NO_1M`
  - 原生 30m 缺失，且桶内没有足够 1m 记录可用
- `UNKNOWN_CALENDAR`
  - 无法可靠判断该 symbol 在该时刻的合法交易段

其中第一轮 backend 实现最少只要能稳定区分：
- `NATIVE_30M`
- `MERGEABLE_FROM_1M`
- `NOT_MERGEABLE_1M_GAP`
- `NOT_MERGEABLE_NO_1M`

就已经足够支撑当前需求。

---

# B. 不可合并标注规则

## B.1 设计目标

本层只回答：

> 某个目标 30m 桶为什么不能由 1m 补齐？这个事实应该记录到哪里，供后续 verification 与审计使用？

这里的关键是：
- **不可合并不是异常日志，而是业务状态**
- 需要能被 downstream 稳定消费

---

## B.2 最小标注内容

对每个目标 30m 桶，建议至少记录：

- `symbol`
- `bucket_start`
- `target_interval = '30m'`
- `availability_status`
- `price_source_type`
- `coverage_ratio`
- `expected_minutes`
- `observed_minutes`
- `missing_reason_code`
- `session_validity`
- `evaluated_at`
- `rule_version`

其中语义建议如下：

### B.2.1 `availability_status`
表示这个 30m 桶最终是否可用：
- `AVAILABLE_NATIVE`
- `AVAILABLE_AGGREGATED`
- `UNAVAILABLE_NOT_MERGEABLE`
- `UNAVAILABLE_UNKNOWN`

### B.2.2 `price_source_type`
表示可用价格来源：
- `NATIVE_30M`
- `AGGREGATED_FROM_1M`
- `NONE`

### B.2.3 `missing_reason_code`
建议最小枚举：
- `NO_NATIVE_30M`
- `NO_1M_DATA`
- `PARTIAL_1M_COVERAGE`
- `CROSS_SESSION_BUCKET`
- `UNKNOWN_TRADING_CALENDAR`

注意：
- `NO_NATIVE_30M` 本身不是最终不可用理由，而是背景事实
- 最终不可合并通常还需要叠加 `NO_1M_DATA` 或 `PARTIAL_1M_COVERAGE` 等原因

---

## B.3 标注写在哪里的建议

### B.3.1 不建议直接污染原始 `kline_data`
不建议第一轮把这类“可用性/派生性”状态直接混写进原始 K 线主表字段，原因：
- `kline_data` 当前语义更偏事实行情表
- 把“是否可合并 / 为什么不可合并”写进主行情表，容易把事实层与治理层混在一起
- 后续若规则版本变化，会导致原始事实表被治理逻辑反复重写

### B.3.2 最小建议：单独建一张“30m 可用性/派生审计表”
建议一个中间层或派生层表，名字可由 backend 定，但语义建议类似：

- `kline_30m_availability`
- 或 `kline_derived_coverage_status`
- 或 `kline_bucket_lineage`

这张表不一定现在立刻做成复杂 schema，但应承担：
- 记录某个 `symbol + bucket_start + target_interval` 的可用性判定
- 记录来源是原生还是 1m 聚合
- 记录不可合并的原因
- 给 verification 提供稳定输入

### B.3.3 为什么不是只靠运行时临时判断
因为用户要的不是一次性 debug，而是工程规则：
- 若每次 verification 都现场重新扫描判断，会重复计算，且审计困难
- 单独的 availability / lineage 层可以把“数据是否可信可用”从 verification 里拆出来

---

## B.4 如何区分三类状态

这是本轮设计必须冻结的核心语义。

### B.4.1 原生 30m
定义：
- 目标桶存在原始 `30m` K 线记录

标记建议：
- `availability_status = AVAILABLE_NATIVE`
- `price_source_type = NATIVE_30M`
- `missing_reason_code = NULL`

### B.4.2 1m 聚合 30m
定义：
- 原生 `30m` 缺失
- 但同桶内 `1m` 满足严格合并条件
- 由 `1m` 标准聚合派生出 30m

标记建议：
- `availability_status = AVAILABLE_AGGREGATED`
- `price_source_type = AGGREGATED_FROM_1M`
- `missing_reason_code = NO_NATIVE_30M`
- 另附：`coverage_ratio = 1.0`

注意：
- `NO_NATIVE_30M` 在这里是背景事实，不代表不可用
- 真正是否可用由 `availability_status` 决定

### B.4.3 数据缺口不可合并
定义：
- 原生 `30m` 缺失
- `1m` 也不满足严格合并条件
- 因此该 30m 桶不可派生

标记建议：
- `availability_status = UNAVAILABLE_NOT_MERGEABLE`
- `price_source_type = NONE`
- `missing_reason_code` 取以下其一：
  - `NO_1M_DATA`
  - `PARTIAL_1M_COVERAGE`
  - `CROSS_SESSION_BUCKET`
  - `UNKNOWN_TRADING_CALENDAR`

这三类必须在 downstream 被明确区分，**绝不能把 `AVAILABLE_AGGREGATED` 和 `AVAILABLE_NATIVE` 视作完全等价，也不能把 `UNAVAILABLE_NOT_MERGEABLE` 静默当成“稍后 fallback 一下就行”。**

---

# C. verification 防退化规则草案

## C.1 设计目标

本层回答的是另一个问题：

> 当 verification 需要 anchor price / future price 时，在数据存在缺口的情况下，系统是否还能给出“可信的验证结论”？

这与 A/B 两节不同：
- A/B 关心的是 **30m 桶能否补齐/如何标注**
- C 关心的是 **verification 能否成立，何时必须拒绝输出结论**

这两层必须分开。

---

## C.2 总原则：verification 的目标是“避免伪确定性”

当前已知风险不是“查不到价格”，而是：
- 查到了一个离 anchor 很远的价格
- 然后系统把它当成 anchor/base price 继续算涨跌
- 最终生成了看似完整、其实不可信的 verification 结果

因此 verification 层必须遵循：

> **宁可输出“不可验证 / 延后验证”，也不要用过远的替代价格硬凑一个结论。**

---

## C.3 是否允许 30m 缺失时 fallback 到 1m

### 结论：允许，但必须是“受约束 fallback”，不能是无条件 fallback

建议顺序如下：

1. **优先使用原生 30m**
2. 若原生 30m 缺失，则查询 availability/lineage：
   - 若该桶为 `AVAILABLE_AGGREGATED`，可使用该聚合 30m
3. 若该桶为 `UNAVAILABLE_NOT_MERGEABLE`，则：
   - **不允许再把“最近前/后 1m”直接当作伪 30m base price**
   - 只能进入“受约束 1m fallback 验证模式”

### 受约束 1m fallback 验证模式
仅建议在以下场景允许：
- verification 不是要求“该 30m 桶收盘价”，而是只要求“anchor 附近一个可接受的真实市场价”
- 且最近 1m 价格距离 anchor 的时间偏差在阈值内
- 且该价格落在同一合法交易段或定义允许的最近可交易窗口内

否则应直接判为：
- `NO_VALID_BASE_PRICE`
- 或 `DEFERRED_VERIFICATION`

---

## C.4 base price 选择规则建议

建议把 verification 的 base price 选择拆成明确优先级：

### C.4.1 Level 1：原生或严格派生的 30m 桶价格
按优先级：
1. `NATIVE_30M`
2. `AGGREGATED_FROM_1M`（仅严格完整桶）

这是首选，因为其与现有 verification 的 30m 语义最接近。

### C.4.2 Level 2：近邻 1m 真值价格（仅作为受约束 fallback）
若 Level 1 不可用，可允许寻找 anchor 附近最近 1m 真值价格，但必须加限制。

建议至少定义两个阈值：

#### 软阈值：`base_price_max_gap_soft`
建议：**<= 30 分钟**

语义：
- 若最近可用 1m 距 anchor 在 30 分钟内，可认为仍具备“近邻 anchor price”语义
- 允许进入 verification，但必须记录 `base_price_source = FALLBACK_1M_NEARBY`

#### 硬阈值：`base_price_max_gap_hard`
建议：**<= 2 小时**

语义：
- 超过软阈值但未超过硬阈值：
  - 仅允许标记为 `LOW_QUALITY_VERIFICATION_CANDIDATE`
  - 第一轮默认**不自动出最终 correct/incorrect 结论**
  - 更适合标记为 `DEFERRED_VERIFICATION`
- 超过硬阈值：
  - **直接视为无有效 base price**
  - 不得继续 verification

### C.4.3 为什么硬阈值不能太大
以当前 `au9999` 案例为例：
- anchor 前最近 1m 距离约 `51.6h`
- anchor 后最近 1m 距离约 `38.5h`

这种距离下，即使找到了真实价格，也已经失去“新闻 anchor 附近市场反应起点”的意义。

所以像当前案例，应直接判：
- `NO_VALID_BASE_PRICE`
- 或 `DEFERRED_UNTIL_DATA_BACKFILL`

而不是继续生成涨跌验证。

---

## C.5 future horizon price 的防退化规则

不仅 base price 要受控，`30m / 4h / 1d` 等 horizon price 也应受控。

建议：
- 每个目标 horizon 都单独检查对应 price 是否可用
- 若 `base_price` 有效，但某个 horizon 对应价格无有效来源，则：
  - 该 horizon 标记为 `HORIZON_PRICE_UNAVAILABLE`
  - 不输出该 horizon 的 `correct_xx`
- 不允许因为某个 horizon 缺失，就拿极远的最近价替代后继续算正确率

这意味着 verification 结果应允许出现：
- `30m` 不可验证
- 但 `4h` / `1d` 仍可验证

反之亦然。

---

## C.6 verification 状态枚举建议

建议在 `news_verification` 或其派生状态字段中引入最小状态：

### C.6.1 整体验证状态
- `VERIFIED`
- `PARTIALLY_VERIFIED`
- `NOT_VERIFIABLE`
- `DEFERRED`

### C.6.2 base price 状态
- `BASE_PRICE_NATIVE_30M`
- `BASE_PRICE_AGGREGATED_30M`
- `BASE_PRICE_FALLBACK_1M_NEARBY`
- `NO_VALID_BASE_PRICE`

### C.6.3 不可验证原因
- `BASE_PRICE_TOO_FAR_FROM_ANCHOR`
- `TARGET_BUCKET_NOT_MERGEABLE`
- `HORIZON_PRICE_UNAVAILABLE`
- `DATA_GAP_AROUND_ANCHOR`
- `UNKNOWN_TRADING_SESSION`

---

## C.7 何时应判定“不可验证 / 无有效 base price / 延后验证”

建议最小规则如下。

### C.7.1 判定 `NO_VALID_BASE_PRICE`
满足任一条件即可：
- 原生 `30m` 不存在
- 严格派生 `30m` 不可用
- 且最近可用 `1m` 距 anchor 超过硬阈值

或：
- 能找到 `1m`，但不在合法交易段语义内

结果：
- 不计算 price change
- 不输出 `correct_xx`
- verification 记录保留原因码

### C.7.2 判定 `DEFERRED`
建议在以下情况使用：
- 当前没有有效 base price，但可合理期待后续数据回补
- 或未来 horizon 尚未到达完整验证窗口
- 或最近 1m 距 anchor 处于软/硬阈值之间，需要人工或后续回补策略判定

结果：
- 记录为延后验证
- 不立即输出方向正确/错误结论

### C.7.3 判定 `NOT_VERIFIABLE`
建议在以下情况使用：
- 数据缺口已被确认，不属于短期待回补状态
- base price 与 horizon price 都无法形成可信验证链
- 当前窗口对应数据源长期不可用

结果：
- 明确告诉 downstream：这条样本在当前数据条件下不可用于 accuracy 统计

---

## C.8 最小规则的一句话版本

> **verification 允许从原生 30m fallback 到“严格聚合 30m”，再在受约束条件下 fallback 到近邻 1m；但一旦最近真实价格离 anchor 过远，就必须停止并标记为不可验证或延后验证，而不是继续硬算。**

---

# D. 最小实施顺序建议

这里给的是下一轮 backend 可执行的最小顺序，不是大而全路线图。

## D.1 第一步：先冻结状态语义与规则枚举

先由 architect/backend 一起冻结最小枚举，不先写复杂实现。

至少先冻结：

### 数据可用性层
- `NATIVE_30M`
- `MERGEABLE_FROM_1M`
- `NOT_MERGEABLE_1M_GAP`
- `NOT_MERGEABLE_NO_1M`

### verification 层
- `VERIFIED`
- `DEFERRED`
- `NOT_VERIFIABLE`
- `NO_VALID_BASE_PRICE`

### price source 层
- `NATIVE_30M`
- `AGGREGATED_FROM_1M`
- `FALLBACK_1M_NEARBY`
- `NONE`

为什么先做这个：
- 不先冻结枚举，backend 很容易把“不可合并”和“不可验证”又混写成新的模糊状态

---

## D.2 第二步：落一个最小 availability / lineage 承载层

backend 最小实现建议：
- 新建一张轻量级表或派生表，记录 `symbol + bucket_start + 30m` 的可用性与来源
- 第一轮只支持：
  - 原生存在
  - 严格可由 1m 聚合
  - 不可聚合（无 1m / 1m 不完整）

第一轮**不要做**：
- 宽松阈值聚合
- 全量历史一次性回填
- 跨 session 复杂桶处理
- 所有指标字段完整聚合

目标：
- 先把“可用 / 不可用 / 来源是什么”稳定落地

---

## D.3 第三步：verification 读取 availability 结果，而不是自行硬猜

backend 改造 verification 时，最小原则：
- 先查 30m availability / lineage
- 若 `AVAILABLE_NATIVE`：直接用
- 若 `AVAILABLE_AGGREGATED`：用严格聚合 30m
- 若 `UNAVAILABLE_NOT_MERGEABLE`：进入受约束 1m fallback 判定
- 若 fallback 也不满足阈值：输出 `DEFERRED` 或 `NOT_VERIFIABLE`

这一层是本轮最关键的防退化点。

---

## D.4 第四步：只在 verification 结果层输出“不可验证/延后验证”，不要偷偷算 correct

最小要求：
- 当 `NO_VALID_BASE_PRICE` 时，相关 `correct_30m / correct_4h / correct_1d` 字段不应伪造布尔值
- 应允许为 `NULL`，同时配套状态字段说明原因

这样下游统计时：
- 可以把“不可验证样本”单独计数
- 不会误进 accuracy denominator

---

## D.5 本轮明确暂不做

为防扩 scope，以下内容建议本轮不做：

1. **不做大规模历史回补**
2. **不做宽松阈值（95%）自动启用**
3. **不做复杂交易日历全覆盖建模**
4. **不做索引优化与性能重构**（虽然后续值得做，但不属于本设计主任务）
5. **不做所有下游消费方改造完毕**
6. **不做 verification 统计口径大改**

本轮只求：
- 把“能补的补出来”
- 把“不能补的写清楚”
- 把“不能可信验证的样本挡住”

---

# E. 给 backend 的最小实施口令版摘要

如果要把本设计压缩成可执行指令，建议是：

1. **先定义 30m 桶可用性状态，不要直接补数据**
2. **原生 30m 永远优先**
3. **只有同一合法连续交易段内、且 1m 100% 齐全的桶，才允许严格聚合成 30m**
4. **不能严格聚合的桶，必须记录不可合并原因**
5. **verification 先读可用性状态，再决定用 native / aggregated / fallback 1m / reject**
6. **若最近真实价格离 anchor 太远，则直接 `NO_VALID_BASE_PRICE`，不要硬算 correct**

---

# F. 对照任务要求检查

## F.1 A. 1m->30m 可合并规则
- 什么时候允许合并：**已定义**
- 覆盖率/完整率阈值建议：**已定义，首轮建议 100% 严格档**
- 是否要求同一合法交易时段内聚合：**已明确要求**
- 时间桶与时间戳规则建议：**已定义 bucket_start 规则**

## F.2 B. 不可合并标注规则
- 标注哪些状态：**已定义 availability/source/reason**
- 标注写在哪里：**已建议单独 availability/lineage 表**
- 如何区分三类状态：**已明确区分 native / aggregated / not mergeable**

## F.3 C. verification 防退化规则草案
- 30m 缺失时是否允许 fallback 到 1m：**已定义为受约束允许，不是无条件允许**
- 最近可用价格离 anchor 太远时如何处理：**已定义 soft/hard gap 和 reject/defer 逻辑**
- 什么情况下判定不可验证 / 无有效 base price / 延后验证：**已明确**

## F.4 D. 最小实施顺序建议
- 先定义什么：**已给出状态枚举冻结顺序**
- 再由 backend 做什么最小实现：**已给出 availability 层 + verification 接入顺序**
- 哪些内容暂不做：**已列出**

---

# G. 最终结论

本轮最小工程策略建议冻结为：

> **把 `1m -> 30m` 定义成“严格条件下可派生”的补齐能力，而不是默认替代能力；把无法派生的桶显式标注；verification 只在存在可信 base price 时才给结论，否则输出 `DEFERRED / NOT_VERIFIABLE / NO_VALID_BASE_PRICE`。**

这套策略的价值在于：
- 它允许系统先恢复一部分本来可由 1m 严格补齐的 30m 能力；
- 同时不会把有明显缺口的数据窗口伪装成可验证样本；
- 并且能为 backend 下一轮提供明确、最小、可实施的落地顺序。
