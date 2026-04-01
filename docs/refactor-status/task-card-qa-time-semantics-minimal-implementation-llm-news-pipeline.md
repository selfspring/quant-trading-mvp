# QA 任务卡

## 1. 任务名称
- 验收“最小时间语义落地（analysis 写入三字段 + verification 默认锚点切换）”

---

## 2. 任务类型
- QA

---

## 3. 指派对象
- agent：
  - qa

- 为什么由这个 agent 负责：
  - 本轮需要基于已定义测试用例，独立验收时间语义落地，而不是复述 backend 结果

---

## 4. 背景
请先阅读并理解以下背景：

- governing doc：
  - `E:\quant-trading-mvp\docs\LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- 项目约束：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-constraints.md`

- backend 任务卡：
  - `E:\quant-trading-mvp\docs\refactor-status\task-card-backend-time-semantics-minimal-implementation-llm-news-pipeline.md`

- QA 测试用例：
  - `E:\quant-trading-mvp\docs\refactor-status\qa-cases-backend-time-semantics-minimal-implementation-llm-news-pipeline.md`

- backend delivery 文件：
  - `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-24-20-backend-time-semantics-minimal-implementation.md`

- 重点文件：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`

本次验收所属阶段：
- P0

---

## 5. 项目约束
验收时必须重点检查：

- 关键语义约束：
  - `published_time`、`analyzed_at`、`effective_time` 必须各自有明确来源与唯一语义
  - 当前默认：`effective_time = analyzed_at`
  - `news_analysis.time` 只能作为 legacy ambiguous field，不得继续扩成新主语义

- 一票否决风险：
  - 只是加了字段名，实际默认口径没变
  - verification 默认仍走旧发布时间逻辑却不显式标注
  - 继续把 `news_analysis.time` 作为新默认主时间

- 本轮明确不做：
  - 不要求本轮完成 verification 分层
  - 不要求本轮完成历史全量回填
  - 不要求本轮完成所有下游消费方迁移
  - 不要求本轮完成 RAG / backtest 治理

---

## 6. 验收目标
你需要严格按照 QA 测试用例文档执行验收，而不是自由发挥。

本轮你要独立判断：

1. 三正式时间字段是否已在 baseline 写入链路真实落地
2. 默认 `effective_time = analyzed_at` 是否在实现中成立
3. verification 默认锚点是否已切到 `effective_time`
4. 是否仍保留显式 `published_time` 研究口径
5. `news_analysis.time` 是否已冻结为 legacy 字段
6. backend 是否越界改动到不属于本轮范围的层面
7. backend delivery 文件是否与实际代码一致

---

## 7. 强制要求
- 必须按 QA 用例逐条执行
- 必须读取 delivery 文件
- 必须读回关键文件
- 必须在需要的 case 中实际运行或复核相应验证命令
- 必须给出每个 case 的 pass/fail
- 必须给出证据
- 必须输出：通过 / 有条件通过 / 驳回
- 若驳回，必须给出明确返工项

禁止：
- 只复述 backend 结果
- 不按测试用例逐条验
- 因为 verification 分层/历史回填等后续问题未完成就直接驳回本轮

---

## 8. 输出格式要求
请按以下结构输出：

### A. 总结结论
- 通过 / 有条件通过 / 驳回

### B. Case-by-case 结果
- Case 1：Pass / Fail
  - 证据：
- Case 2：Pass / Fail
  - 证据：
- Case 3：Pass / Fail
  - 证据：
- Case 4：Pass / Fail
  - 证据：
- Case 5：Pass / Fail
  - 证据：
- Case 6：Pass / Fail
  - 证据：
- Case 7：Pass / Fail
  - 证据：

### C. 问题项
- 
- 

### D. 遗留风险
- 
- 

### E. 最终建议
- 是否允许接受：是 / 否
- 是否允许进入下一任务：是 / 否
- 若否，返工要求：
