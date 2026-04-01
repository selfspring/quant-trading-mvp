# 任务卡

## 1. 任务名称
- 设计 `news_verification` 最小分层方案，并输出 analysis / verification 边界切分与最小改造顺序

---

## 2. 任务类型
- 审计 / 设计

---

## 3. 指派对象
- agent：
  - architect

- 为什么由这个 agent 负责：
  - 当前已完成时间语义落地，下一大项是将 verification 从 analysis 中解耦，需先做边界设计与最小迁移顺序定义

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
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-20-llm-news-refactor-time-semantics-closure.md`

- 重点代码：
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - `E:\quant-trading-mvp\quant\signal_generator\news_vector_store.py`
  - 如有必要，可检查回测和下游读取 verification 字段的脚本

本任务属于以下阶段：
- P1 准备 / analysis-verification 分层设计

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - `news_analysis` 只表达分析结果
  - `news_verification` 只表达价格验证结果
  - verification 默认锚点仍应基于 `effective_time`
  - 不允许把验证标签继续当成 analysis 主语义字段

- 一票否决风险：
  - 只是把旧验证字段换个地方写，但 analysis 主表仍继续承担验证语义
  - 未定义过渡期兼容策略，导致下游脚本大面积断裂
  - 没区分默认 verification 口径与研究对照口径

- 本轮明确不做：
  - 不直接改代码
  - 不直接建最终完整 schema migration
  - 不直接清理所有下游消费方
  - 不做 RAG / backtest 治理

---

## 6. 任务目标
完成后，以下事实必须成立：

1. `news_verification` 的最小职责边界被明确定义
2. `news_analysis` 与 `news_verification` 的字段边界被明确定义
3. 当前哪些验证字段应迁出 `news_analysis` 被明确列出
4. 过渡期兼容策略被说明清楚
5. backend 最小改造顺序被给出
6. 下游高风险消费点被指出

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 梳理当前 verification 字段与写回路径
- 设计 `news_verification` 的最小表职责
- 列出 analysis / verification 的字段边界
- 设计过渡期兼容策略
- 给出 backend 最小实施顺序建议

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不直接写 migration SQL
- 不直接修改所有消费方
- 不做回测口径大改
- 不做向量库全量治理
- 不做候选层重构

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
  - 职责边界设计
  - 字段迁移清单
  - 兼容策略
  - backend 最小改造顺序

---

## 10. 预期交付物
必须交付：

1. 当前 verification 字段与写回路径盘点
2. `news_verification` 最小职责定义
3. analysis / verification 字段边界清单
4. 过渡期兼容策略
5. backend 最小改造顺序建议
6. 高风险下游消费点清单
7. 风险与遗留问题
8. 下一步建议

最好单独产出一个可引用文档，便于 backend 下一轮直接使用。

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有关键文件
- [ ] 区分“当前现实”和“目标分层设计”
- [ ] 列出应迁出 `news_analysis` 的验证字段
- [ ] 明确默认 verification 锚点
- [ ] 明确过渡期兼容策略
- [ ] 给出 backend 最小任务顺序

禁止：
- 只写抽象原则，不列字段
- 跳过兼容策略直接给理想化终局方案
- 直接展开到回测/RAG 大设计

---

## 12. 输出格式要求
请按以下结构输出：

### A. 结果摘要
- 

### B. 当前 verification 字段与写回路径盘点
- 

### C. `news_verification` 最小职责定义
- 

### D. analysis / verification 字段边界清单
- 

### E. 过渡期兼容策略
- 

### F. backend 最小改造顺序建议
- 

### G. 高风险下游消费点
- 

### H. 风险与遗留
- 

### I. 下一步建议
- 
