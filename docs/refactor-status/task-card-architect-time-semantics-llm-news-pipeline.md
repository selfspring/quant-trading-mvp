# 任务卡

## 1. 任务名称
- 冻结时间字段语义，并输出旧字段到新语义的迁移约束

---

## 2. 任务类型
- 审计 / 设计

---

## 3. 指派对象
- agent：
  - architect

- 为什么由这个 agent 负责：
  - 当前问题核心是时间语义定义与迁移边界，先做设计/约束输出比直接改代码更稳

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
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-16-llm-news-refactor-entrypoint-round.md`
  - `E:\quant-trading-mvp\docs\work-log\2026-03-24-19-llm-news-refactor-p0-patch-closure.md`

- 重点代码：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - 如有必要，可检查与 `news_analysis.time`、`news_raw.time`、`news_filtered.time` 相关的其他代码路径

本任务属于以下阶段：
- P0

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - `published_time`、`analyzed_at`、`effective_time` 必须各自只有一个明确含义
  - 不允许继续让 `news_analysis.time` 承担多重核心语义
  - 时间字段定义必须服务于后续 verification / backtest 口径稳定

- 一票否决风险：
  - 把旧混义字段包装一下继续沿用
  - 只改命名，不澄清验证锚点
  - 未区分“新闻发布时间”“分析完成时间”“真实可交易起点”

- 本轮明确不做：
  - 不直接修改数据库 schema
  - 不直接实现 verification 分层
  - 不直接改 backtest
  - 不做 candidate screening 重构

如发现计划与代码现实冲突，先报告，不要私自改口径。

---

## 6. 任务目标
完成后，以下事实必须成立：

1. 当前所有关键时间字段及其实际语义被说明清楚
2. `published_time / analyzed_at / effective_time` 的目标定义被明确给出
3. `news_analysis.time` 的历史混义问题被明确冻结，说明后续应如何处理
4. 后续 backend 的最小改造顺序被给出
5. verification 的默认时间锚点建议被明确说明

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 梳理当前代码中的时间字段与变量来源
- 映射当前实际语义与目标语义
- 定义后续字段命名与迁移约束
- 明确 verification 默认应以哪个时间为锚点
- 给出 backend 最小实施顺序建议

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不直接写数据库迁移代码
- 不直接改 `news_verification` 表
- 不直接实现 schema 重构
- 不直接修正所有调用方
- 不讨论 RAG / backtest / signal fusion

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中“时间语义不统一”“news_analysis 字段建议”“news_verification 锚点规则”“P0 时间字段重构”
- 要点：
  - `published_time` = 新闻发布时间
  - `analyzed_at` = LLM 完成时间
  - `effective_time` = 允许进入策略/验证的真实起点时间
  - 禁止继续混用 `time`
- 本轮只落实其中哪些内容：
  - 语义定义
  - 映射关系
  - 迁移约束
  - 最小改造顺序

---

## 10. 预期交付物
必须交付：

1. 当前时间字段语义映射
2. 目标时间字段定义
3. `news_analysis.time` 的冻结/迁移建议
4. verification 默认时间锚点建议
5. backend 最小改造顺序建议
6. 风险与遗留问题
7. 下一步建议

最好单独产出一个可引用文档，便于 backend 下一轮直接使用。

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有关键文件
- [ ] 区分“当前现实”和“目标定义”
- [ ] 区分“已确认事实”和“设计建议”
- [ ] 不得只给抽象原则，必须给字段级别映射
- [ ] 给出 verification 默认锚点建议
- [ ] 给出 backend 最小任务顺序

禁止：
- 只写概念，不落到字段和脚本
- 直接跳过定义阶段进入实现建议
- 混入 verification / backtest 大设计

---

## 12. 输出格式要求
请按以下结构输出：

### A. 结果摘要
- 

### B. 当前时间字段语义映射
- 

### C. 目标时间字段定义
- 

### D. `news_analysis.time` 冻结/迁移建议
- 

### E. verification 默认锚点建议
- 

### F. backend 最小改造顺序建议
- 

### G. 风险与遗留
- 

### H. 下一步建议
- 
