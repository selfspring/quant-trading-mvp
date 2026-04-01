# 任务卡

## 1. 任务名称
- 最小时间语义落地（analysis 写入三字段 + verification 默认锚点切换）

---

## 2. 任务类型
- 实现

---

## 3. 指派对象
- agent：
  - backend

- 为什么由这个 agent 负责：
  - 当前已完成时间语义定义，下一步需要最小实现来把定义落到 analysis 写入与 verification 默认口径上

---

## 4. 背景
请先阅读并理解以下背景：

- governing doc / brief：
  - `E:\quant-trading-mvp\docs\LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- 项目约束：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-constraints.md`

- 前序工作日志：
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-19-llm-news-refactor-p0-patch-closure.md`
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-20-llm-news-refactor-time-semantics-definition.md`

- architect 结果已体现在状态与工作日志中，请按其定义执行

- 重点代码：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - 如有必要，可检查与 `news_analysis.time` 相关的消费方

本任务属于以下阶段：
- P0

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - `published_time` = 新闻发布时间
  - `analyzed_at` = LLM 结果完成/写入时间
  - `effective_time` = 当前默认等于 `analyzed_at` 的真实生效时间
  - `news_analysis.time` = legacy ambiguous field，禁止新逻辑继续依赖

- 一票否决风险：
  - 继续把新语义写进 `news_analysis.time`
  - verification 仍默认用 `published_time` 却不显式标注
  - 只改字段名，不改默认验证口径

- 本轮明确不做：
  - 不做 `news_verification` 表分层
  - 不做 candidate screening 重构
  - 不做 RAG / backtest / signal fusion
  - 不做大规模下游消费方清理
  - 不做全历史数据回填方案

---

## 6. 任务目标
完成后，以下事实必须成立：

1. baseline analysis 写入链路能明确写入 `published_time / analyzed_at / effective_time`
2. 当前默认规则明确体现：`effective_time = analyzed_at`
3. `verify_news_price_impact.py` 默认锚点切到 `effective_time`，并允许显式研究口径使用 `published_time`
4. 新实现不再把 `news_analysis.time` 当作正式主时间字段继续扩用
5. 本轮未扩展到 verification 分层或大规模 schema/回测改造

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 为 analysis 写入链路补齐时间字段
- 让 verification 默认锚点切到 `effective_time`
- 为研究对照保留 `published_time` 口径
- 对 `news_analysis.time` 增加 legacy 冻结性质说明/保护
- 做本轮必要的最小 schema/代码改动以支撑上述目标

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不正式拆 `news_verification` 表
- 不大规模改造向量库
- 不大规模清理回测脚本
- 不做所有下游脚本的全面迁移
- 不重构整个 `LLMNewsAnalyzer`

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中“时间语义不统一”“news_analysis 字段建议”“news_verification 锚点规则”“P0 时间字段重构”
- 要点：
  - `published_time / analyzed_at / effective_time` 三者分离
  - verification 默认锚点应为 `effective_time`
  - 不再混用 `time`
- 本轮只落实其中哪些内容：
  - analysis 写入链路时间字段落地
  - verification 默认锚点切换
  - 冻结 `news_analysis.time`

---

## 10. 预期交付物
必须交付：

1. 修改文件清单
2. 每个文件改动目的
3. 三个正式时间字段的实际写入/使用方式说明
4. verification 默认锚点与研究对照锚点说明
5. `news_analysis.time` 现在如何被冻结/限制
6. 验证过程与结果
7. 风险与遗留问题
8. 下一步建议
9. delivery 文件

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有修改过的关键文件
- [ ] 明确说明 `published_time / analyzed_at / effective_time` 分别从哪里来
- [ ] 明确说明为什么当前默认 `effective_time = analyzed_at`
- [ ] 明确说明 verification 默认锚点和研究对照锚点
- [ ] 明确说明 `news_analysis.time` 现在处于什么状态
- [ ] 运行相关检查 / dry-run（如适用）
- [ ] 生成 delivery 文件
- [ ] 汇报实际结果，不得只说“应该可以”

禁止：
- 继续把新逻辑写到 `news_analysis.time`
- 只加字段名不调整验证默认口径
- 把本轮任务扩大成 verification 分层大改

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 修改文件
- `path/to/file`
  - 修改内容：
  - 修改目的：

### C. 三个正式时间字段说明
- 

### D. verification 锚点说明
- 

### E. `news_analysis.time` 冻结说明
- 

### F. 验证过程
- 做了哪些验证：
- 验证结果：
- 是否通过：

### G. 风险与遗留
- 
- 

### H. 下一步建议
- 
