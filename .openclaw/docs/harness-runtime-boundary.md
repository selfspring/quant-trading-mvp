# Harness / Runtime / Workflow / Workspace / ACP 边界说明

> 用于在设计中区分几个最容易混淆的概念。

## 1. Model API
定义：
- 提供智能生成与推理能力的底层模型接口

职责：
- 输入 prompt / messages
- 输出 completion / message / tool intent

不是：
- 完整运行系统
- 任务管理系统

---

## 2. Agent
定义：
- 具有某种角色、策略和行为约束的智能体

职责：
- 理解目标
- 决策下一步动作
- 调用工具或产出内容

不是：
- 宿主环境本身

---

## 3. Runtime
定义：
- 承载 agent 运行的机制与执行层

职责：
- 调模型 API
- 管理 session/run
- 暴露工具
- 维持状态
- 支持长任务执行

注意：
- runtime 承载 agent
- runtime 使用 workspace
- runtime 不等于 workspace

---

## 4. Workspace
定义：
- agent/runtme 工作时接触的项目现场与文件系统上下文

职责：
- 提供代码、文档、脚本、日志、配置等真实材料
- 作为执行与验证发生的现场

注意：
- workspace 是工作环境
- 不是 agent 本身
- 不是 runtime 本身

---

## 5. Workflow
定义：
- 描述任务如何被拆分、流转、验收和重试的流程结构

职责：
- 规定先做什么、后做什么
- 定义失败回路和验收回路
- 组织多 agent 协作

例子：
- planner → generator → evaluator
- architect → backend → qa
- iterative review loop

---

## 6. Harness
定义：
- 让 agent 在真实工程环境中长期、稳定、可验证地完成复杂任务的运行与控制系统

它通常包含：
- runtime
- workspace/environment
- workflow
- artifact handoff
- evaluation loop
- constraint system
- observability / verification access

注意：
- harness 比 runtime 更宽
- harness 不只是 adapter

---

## 7. ACP
定义：
- 对外标准化调用 runtime / harness 的协议或接入机制

职责：
- 统一 session / run / event 等交互方式
- 让上层编排系统可以用标准方式驱动下层执行系统

注意：
- ACP 不是 harness 全部
- ACP 更像 harness 的接口层/接入面

---

## 8. 关系总结

可以用下面这张图理解：

```text
Model API
  └─ 提供智能能力

Agent
  └─ 决定行为与任务推进方式

Runtime
  └─ 承载 agent，调模型，接工具，管 session/run

Workspace
  └─ 提供项目现场与文件上下文

Workflow
  └─ 规定任务如何拆解、执行、评估、回路

Harness
  └─ 将 runtime + workspace + workflow + artifacts + evaluation + constraints 组织成完整系统

ACP
  └─ 让外部系统以标准方式调用 harness/runtime
```

---

## 9. 最短记忆版

- Model API：提供智能
- Agent：决定怎么干
- Runtime：让 agent 跑起来
- Workspace：agent 干活的现场
- Workflow：规定事情怎么推进
- Harness：把以上这些组织成可持续工作的系统
- ACP：把这个系统标准化暴露给外部调用
