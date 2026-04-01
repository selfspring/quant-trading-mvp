# 任务卡

## 1. 任务名称
- 时间语义 schema 对齐与 verification 运行验证解阻

---

## 2. 任务类型
- 实现 / 环境对齐

---

## 3. 指派对象
- agent：
  - backend

- 为什么由这个 agent 负责：
  - 当前 verification 分层最小实现已完成，但运行级验证被目标数据库 schema 未同步前序时间语义改造所阻塞；需要 backend 先完成 schema 对齐并复验运行路径

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

- 前序 backend delivery：
  - `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-24-20-backend-time-semantics-minimal-implementation.md`
  - `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-24-20-runtime-note-verify-news-price-impact-dry-run.md`
  - `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-24-21-backend-verification-layering-minimal-implementation.md`

- 已知 blocker：
  - 目标数据库缺少前一轮时间语义列，导致 verification 新逻辑在运行级验证时被 schema 不一致卡住
  - 已知至少缺失：`news_analysis.effective_time`
  - 需同时确认 `published_time`、`analyzed_at` 是否也已在目标 DB 就绪

- 重点代码：
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\init_db.py`
  - 如有必要，可检查现有 schema 初始化/迁移脚本

本任务属于以下阶段：
- P1 运行验证解阻

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - `published_time` = 新闻发布时间
  - `analyzed_at` = LLM 分析结果完成/写入时间
  - `effective_time` = 当前默认等于 `analyzed_at` 的生效时间
  - verification 默认锚点继续维持 `effective_time`
  - `news_analysis.time` = legacy ambiguous field，禁止新逻辑继续依赖

- 一票否决风险：
  - 为了让 dry-run 通过，回退到继续依赖含混 `time` 字段
  - 只补单个缺失列，但不核对前序时间语义改造的整体一致性
  - 在未说明迁移路径前，直接破坏旧环境或旧脚本

- 本轮明确不做：
  - 不新增新的 verification 业务语义
  - 不扩展到大规模下游消费方迁移
  - 不做 RAG / vector store / backtest 全量治理
  - 不顺手扩大成完整历史数据迁移

---

## 6. 任务目标
完成后，以下事实必须成立：

1. 目标数据库已确认并补齐前序时间语义所需的关键列
2. 至少明确 `published_time / analyzed_at / effective_time` 在目标 DB 的实际状态
3. `verify_news_price_impact.py --dry-run --anchor-time effective_time` 的阻塞原因被消除或被精确定界到新的非 schema 问题
4. 若需要最小 schema 补丁，已明确其落地方式与影响范围
5. 本轮结果被写成可引用的 delivery 文件，供后续 QA 使用

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 审计目标数据库 `news_analysis` 当前实际列结构
- 对齐前序时间语义改造要求与当前 DB 差异
- 以最小方式补齐缺失列/约束（如确有必要）
- 重新执行 verification dry-run，验证 blocker 是否解除
- 记录运行结果、剩余风险与下一步建议
- 生成 delivery 文件

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不做 `news_verification` 下游消费方迁移
- 不做全库历史数据修复/回填
- 不做回测口径全面重构
- 不做 candidate screening 或 prompt 治理扩展
- 不把本轮扩大成完整数据库迁移专项

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中时间语义治理、verification 默认锚点、P0/P1 最小实施依赖
- 要点：
  - `published_time / analyzed_at / effective_time` 必须去歧义
  - verification 默认锚点应为 `effective_time`
  - verification 分层实施依赖前序时间语义 schema 已在目标环境可用
- 本轮只落实其中哪些内容：
  - 目标数据库 schema 对齐
  - verification dry-run 解阻
  - 为 verification 分层 QA 恢复前置条件

---

## 10. 预期交付物
必须交付：

1. 目标数据库 `news_analysis` 当前关键列现状
2. 缺失/不一致项清单
3. 如做了 schema 补丁：补丁内容与落地位置
4. 重新运行 verification dry-run 的命令、结果、报错/输出摘要
5. 当前 blocker 是否已解除
6. 风险与遗留问题
7. 下一步建议
8. delivery 文件

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回涉及的关键 schema / 脚本文件
- [ ] 明确列出目标 DB 中 `published_time / analyzed_at / effective_time` 的实际状态
- [ ] 若补 schema，明确说明补丁通过什么路径落地
- [ ] 重新运行 `verify_news_price_impact.py --dry-run --anchor-time effective_time`
- [ ] 明确说明 blocker 是否解除；若未解除，指出新的精确卡点
- [ ] 生成 delivery 文件
- [ ] 汇报实际结果，不得只说“应该可以”

禁止：
- 为了通过验证而回退到 legacy `time`
- 不查 DB 现状就假定 schema 已一致
- 一边补 schema 一边顺手做大规模业务改造

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 目标数据库关键列现状
- 

### C. 缺失 / 不一致项
- 

### D. schema 对齐处理
- 做了什么：
- 通过什么路径落地：
- 影响范围：

### E. 运行验证过程
- 执行了哪些命令：
- 结果：
- blocker 是否解除：

### F. 风险与遗留
- 
- 

### G. 下一步建议
- 
