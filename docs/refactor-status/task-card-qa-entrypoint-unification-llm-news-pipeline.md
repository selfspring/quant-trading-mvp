# QA 任务卡

## 1. 任务名称
- 验收“统一 LLM 新闻分析主入口，停用重复入口”

---

## 2. 任务类型
- QA

---

## 3. 指派对象
- agent：
  - qa

- 为什么由这个 agent 负责：
  - 本轮需要基于已定义的测试用例执行独立验收，而不是复述 backend 结果

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
  - `E:\quant-trading-mvp\docs\refactor-status\task-card-backend-entrypoint-unification-llm-news-pipeline.md`

- QA 测试用例：
  - `E:\quant-trading-mvp\docs\refactor-status\qa-cases-backend-entrypoint-unification-llm-news-pipeline.md`

- 重点文件：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\run_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`

本次验收所属阶段：
- P0

---

## 5. 项目约束
验收时必须重点检查：

- 关键语义约束：
  - baseline 主链路必须唯一
  - 本轮只收口主入口，不扩展到 verification / RAG / backtest
  - 旧入口必须真实停用，而不是名义弃用

- 一票否决风险：
  - 双入口仍并列存在
  - 旧入口仍可执行旧主链路
  - 文件说明仍制造双入口歧义

- 本轮明确不做：
  - 不要求本轮完成 verification 分层
  - 不要求本轮完成时间字段治理
  - 不要求本轮完成 candidate screening 重构

---

## 6. 验收目标
你需要严格按照 QA 测试用例文档执行验收，而不是自由发挥。

本轮你要独立判断：

1. backend 是否真的完成了主入口收口目标
2. 旧入口是否真实停用
3. baseline 唯一入口是否在代码层面表达清楚
4. 本轮是否越界改动到不属于任务范围的层面
5. backend 汇报是否与实际文件一致

---

## 7. 强制要求
- 必须按 QA 用例逐条执行
- 必须读回关键文件
- 必须在需要的 case 中实际运行相应命令
- 必须给出每个 case 的 pass/fail
- 必须给出证据
- 必须输出：通过 / 有条件通过 / 驳回
- 若驳回，必须给出明确返工项

禁止：
- 只复述 backend 结果
- 不按测试用例逐条验
- 因为未来轮次的问题尚未解决而直接驳回本轮

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
