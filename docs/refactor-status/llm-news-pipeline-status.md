# LLM 新闻链路重构状态

## 1. Governing Doc
- 主计划文档：
  - `docs/LLM_NEWS_PIPELINE_REFACTOR_PLAN.md`

- 相关补充文档：
  - `docs/refactor-status/llm-news-pipeline-constraints.md`

---

## 2. 工作模式
- plan-driven

---

## 3. 当前阶段
- 当前阶段：
  - P0

- 当前 Gate 状态：
  - 进行中

- 当前阶段目标：
  - 统一主入口
  - 去除时间语义混乱
  - 重写 candidate screening
  - 移除硬编码 secrets/passwords

- 当前阶段明确不做：
  - RAG
  - signal fusion
  - strategy backtest
  - 向量库增强实验

---

## 4. 项目约束
- 关键语义约束：
  - 时间字段必须去歧义
  - analysis 与 verification 必须分层
  - candidates 只表达候选筛选，不表达最终真值

- 一票否决风险：
  - future labels 或验证结果回灌 prompt
  - `time` 字段继续承担多重语义
  - analysis / verification 混层

- 验证口径：
  - 先做 P0 定义清理与主入口统一，不用收益结果替代结构验证

- 兼容性 / 迁移要求：
  - 在明确替代路径前，不静默破坏现有主链路

---

## 5. 已完成任务
- [x] 初始化 constraints 文件
- [x] 初始化状态文件
- [x] 完成 architect 第一轮现状审计
- [x] 完成 backend P0 补丁轮（secrets + 旁路风险收紧）
- [x] 补归档 backend delivery 文件（两轮）
- [x] 完成 architect 时间字段语义治理定义
- [x] 完成 backend 最小时间语义落地实现
- [x] 完成 architect verification 分层设计

---

## 6. 已通过 QA 的任务
- [x] backend 第一轮：主入口收敛（有条件通过）
- [x] backend P0 补丁轮：secrets + legacy guard（通过）
- [x] backend 最小时间语义落地（通过，已补 runtime note）

---

## 7. 被驳回 / 返工任务
- [ ]

---

## 8. 当前正在进行的任务
- 任务名称：最小 verification 分层实施（新表落地 + 默认写新表 + 短期双写兼容）
- 负责人 agent：backend
- 任务目标：建立 `news_verification` 最小表，改造 `verify_news_price_impact.py` 默认写新表，并在过渡期短期双写 legacy verification 字段，避免下游立即断裂
- 对应计划条目：P1 / verification 分层 / 默认锚点维持 `effective_time`
- 当前状态：待分发
- 预计下一动作：向 backend 分发 verification 分层最小实施任务

---

## 9. 最新 QA 结论
- QA 时间：2026-03-24 19:49 GMT+8
- QA agent：qa
- 验收范围：backend P0 补丁轮（secrets + legacy guard）及其 Case 7 补判收口
- 结论：
  - 通过

---

## 10. 当前 blockers
- [ ] verification 结果仍默认回写 `news_analysis`
- [ ] `news_verification` 新真源尚未落地
- [ ] 下游消费方仍直接依赖 `news_analysis` 上的 verification 字段

---

## 11. 关键决策记录
- 日期：2026-03-24
  - 决策：先按通用 refactor-orchestrator skill 启动，不直接让 backend 改代码
  - 原因：当前问题首先是定义不统一，需先审计再实施
  - 影响：第一轮任务固定为 architect 审计

- 日期：2026-03-24
  - 决策：backend 第一轮先做主入口收敛，不先碰 verification / RAG / backtest
  - 原因：当前最小、最关键、最可验收的问题是双入口并存与 baseline 主链路不清
  - 影响：下一轮只做主入口统一与旧入口主链路地位收敛

- 日期：2026-03-24
  - 决策：QA 对主入口收敛任务给出“有条件通过”，下一轮先补 secrets 与旁路风险
  - 原因：入口收敛目标已达成，但 baseline 主入口仍含硬编码 secrets，且旧一体化方法仍有旁路风险
  - 影响：在进入时间语义治理前，先做一轮 P0 补丁清理

- 日期：2026-03-24
  - 决策：backend 每轮结果需补归档为 delivery 文件，再进入 QA
  - 原因：防止 QA 后续拿不到 backend 汇报材料，无法执行“汇报 vs 实际”对照
  - 影响：后续将把 delivery 文件作为 QA 强制输入工件

- 日期：2026-03-24
  - 决策：P0 补丁轮收口后，下一大项切到时间字段语义治理，先定义后实现
  - 原因：当前最核心剩余问题已从入口/安全补丁转为时间语义混义，需先冻结定义再做 backend 改造
  - 影响：下一轮先由 architect 输出时间字段语义与迁移约束

---

## 12. 下一步推荐任务
- 推荐任务：向 backend 分发“最小 verification 分层实施（新表落地 + 默认写新表 + 短期双写兼容）”
- 推荐分发给：
  - backend

- 为什么是下一步：
  - architect 已完成 verification 分层设计，当前应先把新表与默认写入路径落地，建立 verification 新真源

- 进入此任务前需要确认：
  - 本轮不扩展到大规模下游消费方迁移
  - 短期兼容策略采用双写，避免旧脚本立即断裂

---

## 13. 恢复执行提示
当用户说“继续”时，优先按以下顺序恢复：

1. 读取本状态文件
2. 查看当前阶段与 Gate 状态
3. 查看“当前正在进行的任务”
4. 查看“最新 QA 结论”
5. 查看“下一步推荐任务”
6. 如状态与代码现实不一致，先发起审计任务

---

## 14. 最后更新时间
- 更新时间：2026-03-24 21:01 GMT+8
- 更新人：main
- 备注：verification 分层设计完成，进入 backend 最小实施阶段
