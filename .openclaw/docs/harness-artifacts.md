# Harness Artifacts v1

> 定义 harness 中关键结构化工件，用于计划、交接、审查、验收与恢复现场。

## 1. Artifact 设计原则

所有 artifact 应满足：
- 可读
- 可版本化
- 可交接
- 可在新 session 中直接使用
- 不依赖聊天上下文才能理解

---

## 2. 核心 Artifact 类型

## 2.1 Plan
作用：
- 将高层目标拆成可执行步骤
- 定义阶段、依赖、范围

建议字段：
- title
- goal
- scope
- milestones
- sprint list
- risks
- acceptance criteria

---

## 2.2 Sprint Contract
作用：
- 在某轮工作开始前，对齐“本轮做什么、怎么验收、什么算 done”

建议字段：
- sprint id
- scope in
- scope out
- deliverables
- validation method
- pass criteria
- open questions

---

## 2.3 Handoff Summary
作用：
- 让下一轮 agent / session 能 clean-slate 接续工作

建议字段：
- current goal
- completed
- remaining
- known issues
- decisions made
- next recommended step
- relevant paths
- verification status

---

## 2.4 Review Report
作用：
- 记录 evaluator / QA 对本轮结果的审查结论

建议字段：
- target artifact / target commit / target sprint
- checks performed
- findings
- severity
- pass/fail
- required fixes
- notes

---

## 2.5 Work Log
作用：
- 记录一轮工作做了什么、发现了什么、还剩什么
- 用于现场恢复与连续推进

建议字段：
- timestamp
- task summary
- actions taken
- issues found
- outputs
- pending items
- next step

---

## 2.6 Acceptance Result
作用：
- 记录最终是否达到本轮/整体验收标准

建议字段：
- target
- acceptance criteria checked
- result
- evidence
- blocker if failed
- decision

---

## 3. 文件组织建议

可按以下结构组织：

- `plans/`
- `artifacts/contracts/`
- `artifacts/handoffs/`
- `reviews/`
- `work-log/`
- `acceptance/`

---

## 4. 使用原则

### 4.1 不把 artifact 写成长聊天记录
artifact 应该是结构化的恢复材料，而不是聊天 dump。

### 4.2 handoff 要站在“下一个 agent 不知道上下文”的角度写
不要默认后续执行者看过全部历史。

### 4.3 review report 必须能直接驱动下一轮修复
不要只说“有问题”，要明确问题位置、严重程度和修复要求。

### 4.4 work log 要持续写，不等任务彻底结束
长任务中，工作日志本身就是上下文的一部分。

---

## 5. v0.1 最小必需工件

如果只做最小闭环，至少要有：
- Plan
- Sprint Contract
- Handoff Summary
- Review Report
- Work Log

这是最小可续跑、可验收、可恢复的 artifact 组合。
