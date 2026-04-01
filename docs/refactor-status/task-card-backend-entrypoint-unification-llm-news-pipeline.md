# 任务卡

## 1. 任务名称
- 统一 LLM 新闻分析主入口，停用重复入口

---

## 2. 任务类型
- 实现

---

## 3. 指派对象
- agent：
  - backend

- 为什么由这个 agent 负责：
  - 本轮任务是最小实现类重构，需要在不扩 scope 的前提下收口 baseline 唯一分析入口

---

## 4. 背景
请先阅读并理解以下背景：

- governing doc / brief：
  - `E:\quant-trading-mvp\docs\LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- 项目约束：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-constraints.md`

- architect 审计结果（已落在状态文件与上轮结果中，请以状态文件为准）

- 相关代码 / 文档：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\scripts\run_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - 如有必要，可检查相关调用路径和注释文档

本任务属于以下阶段：
- P0

---

## 5. 项目约束
执行本任务时必须遵守：

- 关键语义约束：
  - baseline 主链路必须唯一
  - 本轮不解决 verification 设计，只处理主入口地位
  - 不得引入新的时间语义混乱

- 一票否决风险：
  - 保留“双入口都算主流程”的实际状态
  - 名义上弃用旧入口，实际上调用路径仍未隔离
  - 为了收口入口而顺手引入更大范围重构，导致 scope 失控

- 本轮明确不做：
  - 不改 verification 逻辑
  - 不做 RAG 改造
  - 不做 backtest / signal fusion
  - 不做 candidate schema 正式落地
  - 不做全量时间字段重构

如发现计划与代码现实冲突，先报告，不要私自改口径。

---

## 6. 任务目标
完成后，以下事实必须成立：

1. `batch_llm_analysis.py` 被明确为 baseline 唯一分析入口
2. `run_llm_analysis.py` 不再被视为主链路入口，应被停用、隔离或明确标记为非主链路/待废弃
3. 相关调用路径、说明或注释不再制造“双入口都可作为主流程”的歧义
4. 本轮未扩展到 verification / RAG / backtest 等其他层面

---

## 7. 任务范围（In Scope）
本轮允许做的内容：

- 明确 baseline 主入口
- 停用 / 隔离 / 标记废弃 `run_llm_analysis.py`
- 最小调整相关调用路径、文档说明、注释或保护逻辑
- 完成主入口收口所需的最小代码改动

---

## 8. 明确不做（Out of Scope）
本轮禁止顺手扩展到以下内容：

- 不拆 `LLMNewsAnalyzer` 职责
- 不实现 `news_verification`
- 不修改向量库 schema
- 不做 future-label leakage 的完整治理
- 不顺手处理所有 secrets
- 不顺手清理全部时间字段问题

---

## 9. 与计划/目标对齐
本任务对应的部分：

- 章节 / 条目：
  - `LLM_NEWS_PIPELINE_REFACTOR_PLAN.md` 中“单一入口”“P0（统一主入口，停用 run_llm_analysis.py）”
- 要点：
  - 同一类任务只保留一套主流程
  - 先统一定义，再做后续清理
- 本轮只落实其中哪些内容：
  - 主入口收口
  - 重复入口停用/隔离

---

## 10. 预期交付物
必须交付：

1. 修改文件清单
2. 每个文件改动目的
3. baseline 唯一入口的最终说明
4. `run_llm_analysis.py` 的处理方式说明
5. 验证过程与结果
6. 风险与遗留问题
7. 下一步建议

---

## 11. 强制验证清单
任务结束前必须逐条完成：

- [ ] 读回所有修改过的关键文件
- [ ] 明确说明 baseline 唯一入口是什么
- [ ] 明确说明旧入口当前处于什么状态
- [ ] 对照任务目标逐条检查
- [ ] 运行相关检查 / dry-run（如适用）
- [ ] 汇报实际结果，不得只说“应该可以”
- [ ] 标出风险、假设、遗留问题
- [ ] 给出建议下一步

禁止：
- 只加注释但不真正收口入口地位
- 把本轮实现扩大成全链路重构
- 不读回文件就宣告完成

---

## 12. 输出格式要求
请按以下结构输出结果：

### A. 结果摘要
- 

### B. 修改文件
- `path/to/file`
  - 修改内容：
  - 修改目的：

### C. baseline 主入口说明
- 

### D. 旧入口处理方式说明
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
