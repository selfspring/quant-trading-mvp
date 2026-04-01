# 任务卡

## 1. 任务名称
- 清理 baseline 入口硬编码 secrets，并收紧旧一体化旁路风险

---

## 2. 任务类型
- 实现

---

## 3. 指派对象
- agent：
  - backend

- 为什么由这个 agent 负责：
  - 本轮仍属于最小实现类补丁任务，需要在不扩大范围的前提下，消除 QA 标出的条件通过风险

---

## 4. 背景
请先阅读并理解以下背景：

- governing doc / brief：
  - `E:\quant-trading-mvp\docs\LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- 项目约束：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-constraints.md`

- 本轮前置结果：
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-16-llm-news-refactor-entrypoint-round.md`

- 相关代码 / 文档：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`

本任务属于以下阶段：
- P0

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - 不改变 baseline 唯一主入口结论
  - 本轮只处理 secrets 与旁路风险，不扩展到时间字段治理
  - 不进入 verification 设计与 RAG 设计

- 一票否决风险：
  - 为了清理 secrets 而顺手引入更大范围重构
  - 让 `LLMNewsAnalyzer` 再次具备事实主链路地位
  - 引入新的配置读取不稳定性，导致 baseline 主入口不可运行

- 本轮明确不做：
  - 不做时间字段去歧义
  - 不做 verification 分层
  - 不做 candidate screening 重构
  - 不做 backtest / signal fusion / RAG 改造
  - 不做全仓库 secrets 大扫除，只处理与本轮目标直接相关部分

---

## 6. 任务目标
完成后，以下事实必须成立：

1. `batch_llm_analysis.py` 中不再保留硬编码 API key / DB password，应改为从配置、环境变量或项目已有安全载入方式读取
2. `LLMNewsAnalyzer.fetch_and_analyze_latest()` 被进一步收紧，降低被新代码或维护者继续旁路调用成“事实主链路”的风险
3. baseline 唯一主入口仍保持为 `batch_llm_analysis.py`
4. 本轮未扩展到时间字段、verification、RAG 等其他层面

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 清理 `batch_llm_analysis.py` 中与本轮直接相关的硬编码 secrets/passwords
- 为 `LLMNewsAnalyzer.fetch_and_analyze_latest()` 增加更强的停用/保护/迁移提示或防护逻辑
- 补充最小必要说明，防止旁路继续被当作主链路
- 做到本轮可验证、可说明、可验收

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不做 `news_verification` 表设计
- 不做时间字段正式迁移
- 不做向量库 schema 重构
- 不做 future-label leakage 的全量治理
- 不顺手清理整个仓库所有 hardcoded secrets
- 不重构整个 `LLMNewsAnalyzer` 架构

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中 P0 的“移除硬编码密钥/密码”
  - architect / QA 已指出的“旧一体化方法旁路风险”
- 要点：
  - 基线主链路必须清晰且更安全
  - 旧路径不应继续维持事实主流程地位
- 本轮只落实其中哪些内容：
  - baseline 入口 secrets 清理
  - 旧方法旁路风险收紧

---

## 10. 预期交付物
必须交付：

1. 修改文件清单
2. 每个文件改动目的
3. secrets 现在从哪里读取
4. `fetch_and_analyze_latest()` 现在如何被限制/保护
5. 验证过程与结果
6. 风险与遗留问题
7. 下一步建议

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有修改过的关键文件
- [ ] 明确说明 secrets 的新读取方式
- [ ] 明确说明旧方法现在如何被限制
- [ ] 对照任务目标逐条检查
- [ ] 运行相关检查 / dry-run（如适用）
- [ ] 汇报实际结果，不得只说“应该可以”
- [ ] 标出风险、假设、遗留问题
- [ ] 给出建议下一步

禁止：
- 只把 secrets 挪到另一个硬编码位置
- 只写注释不做实际限制
- 把任务扩大成全链路重构

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 修改文件
- `path/to/file`
  - 修改内容：
  - 修改目的：

### C. secrets 新读取方式说明
- 

### D. 旧方法旁路风险收紧说明
- 

### E. 验证过程
- 做了哪些验证：
- 验证结果：
- 是否通过：

### F. 风险与遗留
- 
- 

### G. 下一步建议
- 
