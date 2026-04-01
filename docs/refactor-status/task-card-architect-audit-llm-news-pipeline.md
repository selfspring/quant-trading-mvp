# 任务卡

## 1. 任务名称
- 审计当前 LLM 新闻链路，并输出 P0 最小拆分建议

---

## 2. 任务类型
- 审计

---

## 3. 指派对象
- agent：
  - architect

- 为什么由这个 agent 负责：
  - 本轮任务核心是梳理现状链路、职责边界、语义冲突和最小重构顺序，属于架构审计而非实现

---

## 4. 背景
请先阅读并理解以下背景：

- governing doc / brief：
  - `E:\quant-trading-mvp\docs\LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- 项目约束：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-constraints.md`

- 相关代码 / 文档：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\run_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\filter_news.py`
  - `E:\quant-trading-mvp\scripts\verify_news_price_impact.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - `E:\quant-trading-mvp\quant\signal_generator\news_vector_store.py`

本任务属于以下阶段：
- P0

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - 时间字段必须去歧义
  - analysis 与 verification 必须分层
  - candidates 只表达候选筛选，不表达最终真值

- 一票否决风险：
  - future labels 回灌 prompt
  - 时间字段混义
  - analysis / verification 混层

- 本轮明确不做：
  - 不改代码
  - 不做 RAG
  - 不做 backtest
  - 不做 signal fusion
  - 不实现 verification 新表

如发现计划与代码现实冲突，先报告，不要私自改口径。

---

## 6. 任务目标
完成后，以下事实必须成立：

1. 当前主链路实际如何流转已被说明清楚
2. 关键脚本/模块当前职责与重叠关系已被说明清楚
3. 时间字段当前实际语义、混用位置、与 plan 的冲突点已被说明清楚
4. P0 阶段最小推进顺序已被明确给出

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 审计当前新闻链路脚本与模块
- 梳理调用链、职责边界、数据流和时间语义
- 对照 plan 指出主要冲突点
- 输出 P0 最小任务顺序建议

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不直接修改实现代码
- 不设计 P1/P2 的详细执行方案
- 不做收益/回测讨论
- 不做 RAG 设计
- 不做 verification 表落地

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中“当前核心结论”“重构目标”“推荐的新链路”“最小可信实验路径”“P0”
- 要点：
  - 先统一定义，再进入实现
  - 先明确主入口、时间语义、candidate screening，再讨论增强
- 本轮只落实其中哪些内容：
  - 审计当前实现与目标定义的差距
  - 给出 P0 的最小推进顺序

---

## 10. 预期交付物
必须交付：

1. 当前主链路说明
2. 关键脚本/模块职责映射
3. 时间字段语义映射
4. 与 plan 的主要冲突点列表
5. P0 最小任务顺序建议
6. 风险与遗留问题
7. 下一步建议（backend 最小任务建议）

如果发现计划文档不足以解释当前现实，也要明确指出。

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有关键文件
- [ ] 对照任务目标逐条检查
- [ ] 区分“已确认事实”和“合理推测”
- [ ] 汇报实际结果，不得只说“应该可以”
- [ ] 标出风险、假设、遗留问题
- [ ] 给出建议下一步

禁止：
- 不读回文件就宣告完成
- 凭印象总结代码现实
- 擅自进入实现方案细化并跳过现状审计

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 当前主链路
- 

### C. 关键脚本/模块职责映射
- 

### D. 时间字段语义映射
- 

### E. 与 plan 的主要冲突点
- 

### F. P0 最小推进顺序建议
- 

### G. 风险与遗留
- 

### H. backend 下一步最小任务建议
- 
