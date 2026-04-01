# Harness Design v1

> 第一版设计草案，基于 OpenAI《Harness engineering》与 Anthropic《Harness design for long-running application development》的共同经验整理。

## 1. 定义

本文中的 harness 指：

> 一套为了让 agent 在真实工程环境中长期、稳定、可验证地完成复杂任务，而建立的运行机制、环境结构、反馈回路、交接工件与约束系统的总和。

它不是单个 adapter，不只是 prompt，也不只是 ACP 接口。

---

## 2. 设计目标

本 harness 的目标是支撑以下能力：

- 长时间运行任务
- 多 agent 分工协作
- 结构化上下文交接
- 工程环境对 agent 友好
- 独立评估与 QA
- 可验证交付
- 任务可续跑、可恢复、可审计

---

## 3. 问题背景

裸模型调用或单 agent 单轮执行，在复杂软件工程任务中会遇到：

1. **长任务失控**
   - 上下文过长
   - 忘记目标
   - 提前草率收尾
   - 跑偏

2. **自评不可靠**
   - 自己做自己评时偏乐观
   - 主观质量判断失真

3. **环境对 agent 不友好**
   - 关键知识散落在聊天、脑内、外部文档里
   - repo 之外的信息对 agent 不可见

4. **缺少结构化交接**
   - 跨 session / 跨 agent 接力不稳
   - 无法 clean-slate 续跑

5. **缺少硬反馈回路**
   - 没有 QA、lint、测试、阈值和结构约束
   - drift 会不断累积

---

## 4. 设计原则

### 4.1 环境优先，不是提示词优先
更好的 agent 表现来自更好的环境，而不仅是更长的 prompt。

### 4.2 文档是地图，不是百科全书
顶层文档保持短小、稳定、可导航；深知识放入结构化 docs。

### 4.3 生成与评估分离
实现和验收不要由同一个 agent 承担。

### 4.4 长任务必须支持结构化交接
复杂任务不能默认单次上下文跑到底，必须有 artifact/handoff。

### 4.5 约束优先于微观指挥
不要在 prompt 里写满实现细节；应通过边界、不变量和验证系统来控制质量。

### 4.6 可验证性优先于“看起来完成了”
所有关键阶段尽量绑定测试、检查、评估阈值。

### 4.7 计划是一等工件
计划必须结构化、可追踪、可交接，而不是口头共识。

---

## 5. 核心组件

### 5.1 Planner
职责：
- 将高层目标展开为结构化计划
- 划分 sprint / feature
- 定义执行顺序与依赖

输出：
- spec
- exec plan
- sprint list
- acceptance points

### 5.2 Generator
职责：
- 按计划逐步实现
- 一次聚焦一个 sprint 或 feature
- 产出实现结果与交接摘要

输出：
- 代码变更
- 实现说明
- 自检结果
- handoff artifact

### 5.3 Evaluator / QA
职责：
- 独立审查 generator 输出
- 发现 bug、质量问题、偏离需求的问题
- 给出通过/驳回与反馈

### 5.4 Artifact Layer
职责：
- 保存计划、交接、审查、工作日志等结构化工件
- 为跨 session / 跨 agent 接力提供稳定接口

### 5.5 Context Manager
职责：
- 管理上下文增长
- 决定何时 compaction
- 决定何时 reset
- 支持 clean-slate continuation

### 5.6 Workspace / Environment Layer
职责：
- 提供 agent 可工作的真实项目现场
- 让 repo 成为 agent 可见知识世界
- 让 docs、scripts、logs、UI、metrics 对 agent 可达

### 5.7 Constraint & Verification Layer
职责：
- 机械执行质量边界与不变量
- 防止长期 drift

可包含：
- lint
- tests
- build checks
- architecture boundaries
- evaluator thresholds

---

## 6. 运行流程

### 6.1 高层流程
1. 接收高层目标
2. planner 生成计划
3. 定义 sprint 列表
4. generator 选择一个 sprint 开工
5. evaluator 与 generator 对齐 sprint contract
6. generator 实现
7. evaluator 验收
8. 失败则返回反馈并重做
9. 通过则写 work log / handoff，进入下一 sprint
10. 必要时 compaction 或 reset
11. 全部完成后输出最终交付摘要

### 6.2 Sprint 流程
每轮 sprint 至少包含：
- contract 对齐
- 实现
- 自检
- 独立评估
- 通过/驳回
- 写交接工件

---

## 7. 知识与文档结构

参考 OpenAI 的经验，知识应采用“地图 + 深文档”结构。

建议目录：

- `AGENTS.md`：总导航
- `docs/`：深层文档
- `plans/`：计划
- `reviews/`：审查与 QA 结果
- `artifacts/`：交接工件
- `work-log/`：工作日志

原则：
- 顶层入口短小
- 深文档结构化
- 计划/日志版本化
- 尽量让关键知识进入 repo

---

## 8. 上下文管理策略

### 8.1 策略层次
- 短任务：直接连续执行
- 中任务：优先 compaction
- 长任务：artifact handoff + context reset

### 8.2 何时 reset
当出现以下情况时考虑 reset：
- 历史过长，目标难以维持
- 出现明显上下文焦虑/提前收尾倾向
- 阶段性任务已完成，适合 clean-slate 续跑
- 当前执行思路已被污染，需要换一个干净上下文

### 8.3 reset 后必须保留的状态
- 当前目标
- 已完成内容
- 未完成内容
- 已知问题与风险
- 下一步建议
- 相关路径与验证状态

---

## 9. 评估机制

### 9.1 客观任务
优先使用：
- tests
- lint
- build
- logs
- metrics
- DB/API checks

### 9.2 主观任务
使用：
- criteria-based evaluator
- score + critique
- threshold-based pass/fail

### 9.3 原则
- generator 不做最终裁决
- evaluator 要相对 skeptical
- 必须有 fail path

---

## 10. v0.1 范围

### 必做
- planner / generator / evaluator 三角色
- sprint-based execution
- artifact handoff
- work log
- 基本 context management
- 独立 QA 验收
- 文档地图化组织

### 可选
- 浏览器驱动 UI 验证
- metrics / logs 自动检查
- doc-gardening agent
- 自动后台 cleanup loop

### 不做
- 全量多 runtime 支持
- 重型分布式系统
- 过早抽象成超通用平台
- 完全无人监督的最终上线

---

## 11. ACP 的位置

ACP 不作为 harness 的定义核心，而作为 **对外接入层** 存在。

也就是说：
- harness 本体 = 长任务执行与控制系统
- ACP = harness 暴露给外部编排系统的标准接口

---

## 12. 第一版成功标准

如果 v0.1 成功，应该能够做到：

1. 用户给出高层目标
2. planner 自动生成结构化计划
3. generator 按 sprint 实现
4. evaluator 独立验收
5. 任务可跨长时间持续推进
6. 中途可 reset 后继续
7. 文档、计划、日志、工件都被留下
8. 最终输出是可恢复、可验证、可延续的工程状态
