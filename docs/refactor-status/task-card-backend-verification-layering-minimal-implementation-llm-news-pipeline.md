# 任务卡

## 1. 任务名称
- 最小 verification 分层实施（新表落地 + 默认写新表 + 短期双写兼容）

---

## 2. 任务类型
- 实现

---

## 3. 指派对象
- agent：
  - backend

- 为什么由这个 agent 负责：
  - verification 分层设计已完成，下一步需要最小实现把新表和默认写入路径落地，同时不打断现有下游

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
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-20-llm-news-refactor-time-semantics-closure.md`
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-21-llm-news-refactor-verification-layering-definition.md`

- architect 设计结论已体现在状态与工作日志中，请按其定义执行

- 重点代码：
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - `E:\quant-trading-mvp\quant\signal_generator\news_vector_store.py`
  - 如有必要，可查看现有 schema 初始化/迁移脚本

本任务属于以下阶段：
- P1 最小实施

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - `news_analysis` 只表达分析结果主语义
  - `news_verification` 只表达价格验证结果
  - 关联对象必须是 `analysis_id`
  - 默认 verification 口径继续维持 `effective_time`

- 一票否决风险：
  - 只是新增新表，但默认写入仍留在 `news_analysis`
  - 未定义 `verification_scope` / `verification_anchor_time`
  - 一步切断 legacy 字段，导致现有下游脚本立即断裂

- 本轮明确不做：
  - 不做大规模下游消费方迁移
  - 不做 RAG / vector store 全量治理
  - 不做 backtest 全量口径改造
  - 不做候选层重构
  - 不做历史全量回填

---

## 6. 任务目标
完成后，以下事实必须成立：

1. `news_verification` 最小表已落地
2. `verify_news_price_impact.py` 默认写入 `news_verification`
3. 默认 verification 口径继续是 `effective_time`
4. 研究对照口径仍支持 `published_time`
5. 短期兼容策略生效：可继续双写 legacy verification 字段，避免旧下游立即断裂
6. 本轮未扩展到大规模消费方迁移或 RAG/backtest 治理

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 为 `news_verification` 新表做最小 schema 落地
- 让 verification 脚本默认写新表
- 明确写入：
  - `analysis_id`
  - `verification_scope`
  - `verification_anchor_time`
  - 价格快照/变化结果
  - 正确性结果
  - `verification_version`
  - `verified_at`
- 在过渡期保留短期双写 legacy 字段
- 生成 delivery 文件

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不迁移 `news_vector_store.py`
- 不迁移 `backtest_signal_fusion.py`
- 不清理所有检查脚本
- 不做 `direction_correct` 终局语义清洗
- 不做历史 verification 全量回填
- 不做 prompt 泄漏全量治理

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中 `news_verification` 设计、关键规则、P1 任务
- 要点：
  - verification 应独立成层
  - 默认锚点为 `effective_time`
  - 不再把验证标签混回 analysis 主语义
- 本轮只落实其中哪些内容：
  - 新表最小落地
  - 默认写新表
  - 短期双写兼容

---

## 10. 预期交付物
必须交付：

1. 修改文件清单
2. 每个文件改动目的
3. `news_verification` 最小表结构说明
4. 默认 verification 写入路径说明
5. 双写兼容策略说明
6. 验证过程与结果
7. 风险与遗留问题
8. 下一步建议
9. delivery 文件

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有修改过的关键文件
- [ ] 明确说明 `news_verification` 的关键字段与唯一键/约束
- [ ] 明确说明默认写入路径已经切到新表
- [ ] 明确说明双写兼容策略怎么实现
- [ ] 明确说明默认 verification 口径仍是 `effective_time`
- [ ] 运行相关检查 / dry-run（如适用）
- [ ] 生成 delivery 文件
- [ ] 汇报实际结果，不得只说“应该可以”

禁止：
- 只建表不改默认写入路径
- 只改脚本不落新表
- 直接切断 legacy 字段导致现有脚本马上断裂
- 把本轮扩大成大规模消费方迁移

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 修改文件
- `path/to/file`
  - 修改内容：
  - 修改目的：

### C. `news_verification` 最小表说明
- 

### D. 默认 verification 写入路径说明
- 

### E. 双写兼容策略说明
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
