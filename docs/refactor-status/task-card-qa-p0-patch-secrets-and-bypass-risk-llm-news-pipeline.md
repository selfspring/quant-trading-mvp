# QA 任务卡

## 1. 任务名称
- 验收“清理 baseline 入口硬编码 secrets，并收紧旧一体化旁路风险”

---

## 2. 任务类型
- QA

---

## 3. 指派对象
- agent：
  - qa

- 为什么由这个 agent 负责：
  - 本轮需要基于已定义测试用例，独立验收 backend 补丁，而不是复述 backend 结果

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
  - `E:\quant-trading-mvp\docs\refactor-status\task-card-backend-p0-patch-secrets-and-bypass-risk-llm-news-pipeline.md`

- QA 测试用例：
  - `E:\quant-trading-mvp\docs\refactor-status\qa-cases-backend-p0-patch-secrets-and-bypass-risk-llm-news-pipeline.md`

- 重点文件：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - 如有必要，可检查 `E:\quant-trading-mvp\scripts\run_llm_analysis.py`

本次验收所属阶段：
- P0

---

## 5. 项目约束
验收时必须重点检查：

- 关键语义约束：
  - baseline 唯一主入口仍必须是 `batch_llm_analysis.py`
  - 本轮只处理 baseline secrets 与 legacy guard
  - 旧一体化方法不应再默认可执行

- 一票否决风险：
  - secrets 只是换地方硬编码
  - legacy guard 只写说明，没有真实生效
  - 本轮补丁意外动摇 baseline 唯一入口结论

- 本轮明确不做：
  - 不要求本轮完成时间字段治理
  - 不要求本轮完成 verification 分层
  - 不要求本轮完成 RAG/future-label leakage 全量治理
  - 不要求本轮解决所有 pre-commit 问题

---

## 6. 验收目标
你需要严格按照 QA 测试用例文档执行验收，而不是自由发挥。

本轮你要独立判断：

1. secrets 是否真的从 baseline 主入口中移除
2. secrets 是否改为走现有配置体系读取
3. `fetch_and_analyze_latest()` 是否默认被 guard 阻断
4. 只有显式环境变量时才允许旧兼容路径放行
5. baseline 唯一主入口结论是否保持不变
6. backend 是否越界改动到不属于本轮范围的层面
7. backend 汇报是否与实际文件一致

---

## 7. 强制要求
- 必须按 QA 用例逐条执行
- 必须读回关键文件
- 必须在需要的 case 中实际运行或复核相应验证命令
- 必须给出每个 case 的 pass/fail
- 必须给出证据
- 必须输出：通过 / 有条件通过 / 驳回
- 若驳回，必须给出明确返工项

禁止：
- 只复述 backend 结果
- 不按测试用例逐条验
- 因为时间字段/verification 等后续问题尚未解决而直接驳回本轮

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
