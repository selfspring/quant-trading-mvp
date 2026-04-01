# QA 测试用例：最小时间语义落地

## 1. 本轮测试范围
本轮只验证 backend 时间语义最小实现任务：

> 最小时间语义落地（analysis 写入三字段 + verification 默认锚点切换）

本轮测试目标来自以下输入：
- `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`
- `docs/refactor-status/llm-news-pipeline-constraints.md`
- `docs/refactor-status/task-card-backend-time-semantics-minimal-implementation-llm-news-pipeline.md`
- architect 时间语义定义结论
- backend delivery 文件

---

## 2. 本轮验收目标
本轮 QA 需要确认：

1. `batch_llm_analysis.py` 已在 baseline analysis 写入链路落地：
   - `published_time`
   - `analyzed_at`
   - `effective_time`
2. 当前默认规则已明确体现：
   - `effective_time = analyzed_at`
3. `verify_news_price_impact.py` 默认锚点已切到 `effective_time`
4. 仍支持显式研究对照口径：
   - `published_time`
5. `news_analysis.time` 已被明确冻结为 legacy ambiguous field，不再作为新语义主时间继续扩用
6. 本轮未越界扩展到 verification 分层 / RAG / backtest / schema 大改 / 全量历史回填
7. backend delivery 文件与实际代码状态一致

---

## 3. 本轮明确不测
本轮 **不** 验证以下内容：

- `news_verification` 表是否已建立
- analysis / verification 是否已完全分层
- 历史旧数据是否已全量回填三字段
- 所有下游消费方是否已全部切断 `news_analysis.time`
- RAG / future-label leakage 是否已治理
- backtest 是否已全面切到新口径
- pre-commit / ruff / mypy 是否全部通过

说明：
- 本轮只验证“最小时间语义落地”是否成立。
- 不能因为后续阶段问题尚未解决而直接驳回本轮。

---

## 4. 测试用例

### Case 1：analysis 写入链路已补齐三正式时间字段
**目标**：确认 baseline analysis 写入链路不再只有 legacy `time`，而是明确写入 `published_time / analyzed_at / effective_time`。  
**检查方法**：读回 `scripts/batch_llm_analysis.py`。  
**通过标准**：可在实际写入路径中看到三字段被写入。  
**失败条件**：仍只写 `time`，或三字段只停留在注释层面。

---

### Case 2：默认规则已体现为 `effective_time = analyzed_at`
**目标**：确认当前默认时间生效规则在代码中真实落地。  
**检查方法**：读回 `scripts/batch_llm_analysis.py` 写入逻辑。  
**通过标准**：代码中清楚体现 `effective_time` 来源于 `analyzed_at`。  
**失败条件**：`effective_time` 没写、写成别的含混来源、或未明确说明。

---

### Case 3：verification 默认锚点已切到 `effective_time`
**目标**：确认默认验证口径已从旧发布时间逻辑切到真实可用时间逻辑。  
**检查方法**：
1. 读回 `scripts/verify_news_price_impact.py`
2. 检查 CLI 默认参数与默认 SQL 锚点表达

**通过标准**：
- 默认 `--anchor-time` 为 `effective_time`
- 默认锚点 SQL 优先使用 `na.effective_time`
- 不再把 `news_analysis.time` 当默认新锚点

**失败条件**：
- 默认仍是 `published_time`
- 默认仍依赖 `news_analysis.time`

---

### Case 4：显式研究对照口径仍可使用 `published_time`
**目标**：确认系统没有丢掉事件发布时间研究口径，只是把它从默认口径降为显式对照。  
**检查方法**：读回 `scripts/verify_news_price_impact.py`。  
**通过标准**：
- 存在显式 `published_time` 选项
- 代码中能看到研究对照锚点路径

**失败条件**：
- 研究口径被删掉
- 或研究口径与默认口径无法区分

---

### Case 5：`news_analysis.time` 已冻结为 legacy 字段
**目标**：确认新实现没有继续把 `news_analysis.time` 包装成新的正式主时间。  
**检查方法**：读回：
- `scripts/batch_llm_analysis.py`
- `quant/signal_generator/llm_news_analyzer.py`
- 如有必要，读回 `scripts/verify_news_price_impact.py`

**通过标准**：
- 能看到明确的 legacy ambiguous field 说明或等价冻结表述
- 新逻辑的主语义依赖已转向正式三字段与默认锚点

**失败条件**：
- 仍把 `news_analysis.time` 当默认业务时间继续扩用

---

### Case 6：本轮未越界扩 scope
**目标**：确认 backend 没有把本轮任务扩展为其他层面的大改。  
**检查方法**：对照任务卡与实际改动文件/改动内容。  
**通过标准**：
- 重点仍聚焦时间语义落地与默认锚点切换
- 未展开 verification 分层 / RAG / backtest / 全量历史回填 / 大规模消费方迁移

**失败条件**：
- 本轮出现明显超边界重构

---

### Case 7：backend delivery 与实际代码一致
**目标**：确认本轮 backend 交付文件与当前代码现实一致。  
**检查方法**：读取 delivery 文件并逐条对照关键代码。  
**通过标准**：
- delivery 中关于三字段、默认锚点、legacy 冻结的关键声明均能在文件中找到证据

**失败条件**：
- delivery 声明与实际代码不符
- 关键实现无法在代码里找到

---

## 5. QA 输出要求
执行 QA 时，至少输出：

1. 每个 case 的 pass/fail
2. 证据来自哪些文件/命令
3. 最终结论：通过 / 有条件通过 / 驳回
4. 如果驳回，必须指出具体返工项
5. 如果通过，也要明确遗留风险

---

## 6. 备注
本测试用例文档的目标是：
- 让 QA 严格围绕“最小时间语义落地”本轮目标执行
- 避免把 verification 分层、历史回填、RAG 等后续任务混入本轮结论
- 让“时间定义真正落地”可以被逐项核验
