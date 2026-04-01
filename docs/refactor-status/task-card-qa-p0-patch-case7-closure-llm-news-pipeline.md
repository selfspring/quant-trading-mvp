# QA 任务卡

## 1. 任务名称
- 补判 P0 补丁轮 QA Case 7：delivery 与实际文件一致性

---

## 2. 任务类型
- QA

---

## 3. 指派对象
- agent：
  - qa

- 为什么由这个 agent 负责：
  - 当前技术实现已完成且主要 case 已通过，本轮仅需补齐 delivery 文件与实际文件的一致性对照，完成 QA 收口

---

## 4. 背景
请先阅读并理解以下背景：

- 当前状态文件：
  - `E:\quant-trading-mvp\docs\refactor-status\llm-news-pipeline-status.md`

- backend delivery 文件：
  - `E:\quant-trading-mvp\docs\refactor-status\deliveries\2026-03-24-16-backend-p0-patch-secrets-guard.md`

- 上一轮 QA 用例：
  - `E:\quant-trading-mvp\docs\refactor-status\qa-cases-backend-p0-patch-secrets-and-bypass-risk-llm-news-pipeline.md`

- 重点文件：
  - `E:\quant-trading-mvp\scripts\batch_llm_analysis.py`
  - `E:\quant-trading-mvp\quant\signal_generator\llm_news_analyzer.py`
  - 如有必要，可检查 `E:\quant-trading-mvp\scripts\run_llm_analysis.py`

---

## 5. 验收目标
本轮只做一件事：

- 对上一轮 QA 中未闭环的 **Case 7** 进行补判：
  - backend delivery 文件中的关键汇报
  - 是否与当前实际文件状态一致

本轮不是重新跑整轮 QA，不要扩到其他 case。

---

## 6. 强制要求
- 必须读取 delivery 文件
- 必须读回关键代码文件
- 必须逐条对照 delivery 中的关键声明与实际文件状态
- 必须输出：
  - Case 7：Pass / Fail
  - 证据
  - 是否可将上一轮 QA 从“有条件通过”收口为“通过”

禁止：
- 重新发散到时间字段、verification、RAG 等后续问题
- 把本轮变成整轮 QA 重跑

---

## 7. 输出格式要求
请按以下结构输出：

### A. Case 7 结论
- Pass / Fail

### B. 对照结果
- delivery 声明 1：
  - 是否与实际一致：
  - 证据：
- delivery 声明 2：
  - 是否与实际一致：
  - 证据：
- delivery 声明 3：
  - 是否与实际一致：
  - 证据：

### C. 最终建议
- 是否可将上一轮 QA 收口为“通过”：是 / 否
- 若否，缺什么：
