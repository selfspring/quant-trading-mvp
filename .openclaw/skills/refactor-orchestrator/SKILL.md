---
name: refactor-orchestrator
description: >
  通用长任务编排器（Harness Orchestrator）。根据计划文档或现状审计，分阶段推进
  复杂工程任务。负责规划、任务拆分、sprint contract、agent 分发、阶段门禁、
  独立 QA、结构化交接（handoff）、上下文重置续跑与工作日志。
  适用于：多阶段 refactor、migration、新功能开发、系统集成、模块拆分、
  入口统一、schema/接口语义整理、长周期项目推进等需要持续推进的复杂任务。
---

# 通用长任务编排器（Harness Orchestrator）

> 基于 harness engineering 理念：更好的 agent 表现来自更好的环境，而不仅是更长的 prompt。

## 适用场景

当任务需要跨多轮、多 agent、多阶段持续推进时，使用本 skill。

典型场景包括：

- 根据现有 plan / PRD / architecture note 推进重构或新功能开发
- 没有现成计划，先审计现状再生成执行计划
- 单体项目拆模块 / 拆服务
- 入口统一 / 调用链清理
- schema、接口、时间字段、状态字段等语义整理
- 脚本堆叠流程重构为正式主链路
- migration / cleanup / boundary clarification
- 长周期项目的持续推进与交接
- 用户在中途说"继续"，需要从状态文件恢复推进

## 不适用场景

以下情况不要使用本 skill：

- 单文件小修
- 一次性 bug fix
- 不需要阶段门禁和独立 QA 的快速补丁
- 纯文档润色
- 只要一个分析结论，不要求进入执行

## 本 skill 的角色定位

这是一个**项目编排 skill**，不是 coding skill。

### 核心三角色

本 skill 基于 Planner / Generator / Evaluator 三角色设计：

- **Planner**：将高层目标展开为结构化计划，划分 sprint，定义执行顺序与依赖。可由 architect / pm agent 担任。
- **Generator**：按计划逐步实现，一次聚焦一个 sprint，产出代码变更与交接摘要。可由 backend / frontend / devops agent 担任。
- **Evaluator / QA**：独立审查 generator 输出，给出通过/驳回与反馈。必须由独立 qa agent 担任，不得由 generator 自评。

### 主 agent（编排者）的职责

1. 明确输入模式
2. 读取计划或先发起审计
3. 拆任务、写 sprint contract
4. 选 agent（planner / generator / evaluator）
5. 分发任务
6. 检查结果
7. 发起独立 QA
8. 处理 QA 反馈（接受/驳回/返工）
9. 更新状态
10. 写工作日志
11. 需要时执行 handoff（结构化交接）
12. 向用户汇报下一步

主 agent **不负责亲自承担主要实现、测试、调试工作**。
代码、测试、调试工作应分发给专门 agent。

## 工作模式

### Mode A：plan-driven
用户已经提供计划文档。

处理方式：
- 读取 governing doc
- 沿用文档中的 phase / milestone / task structure
- 若原文档阶段不清晰，再补充本 skill 的通用阶段框架

### Mode B：audit-to-plan
用户没有现成计划，只有目标或问题描述。

处理方式：
- 先分发 architect / pm 做现状审计
- 产出最小可执行的 refactor brief / phase plan
- 由主 agent 确认阶段边界后再进入实现

### Mode C：resume-from-status
项目中途恢复。

处理方式：
- 读取状态文件
- 查看最新 QA、当前 phase / gate、最后一个被接受任务
- 从最小、无 blocker 的任务继续推进

## 核心目标

把一项复杂工程任务转成一个**可执行、可验收、可续跑、不会跑偏**的项目流程。

成功标准不是"代码改了很多"，而是：

- 当前系统现状被澄清
- 目标结构与语义被定义清楚
- 任务按最小粒度推进
- 每轮有 sprint contract 对齐预期
- 每轮有独立 QA
- 状态文件可续跑
- 长任务可通过 handoff 跨 session 交接
- 工作日志完整
- 系统比之前更清晰、更稳定、更可验证

## 核心工作原则

### 1. 先定义，后实现
在没有明确以下内容前，不进入大面积改代码：

- 当前系统/链路/模块如何工作
- 目标结构是什么
- 当前阶段的边界是什么
- 哪些内容明确不在本轮范围内
- 本项目的关键语义约束是什么
- 本项目的一票否决风险是什么

### 2. 一次只推进一个最小可验证任务
每次只推进一个"小而完整"的任务，不打包多个方向一起做。

好的单轮任务示例：
- 审计当前模块职责与调用链
- 统一主入口
- 提取 service 层
- 重构一个 schema 或接口契约
- 拆分一个职责过重的模块
- 新增独立 verification / validation 层
- 清理一类配置或 secrets 管理问题

差的任务示例：
- "把整个系统重构完"
- "把所有问题都修一下"
- "顺手把架构、性能、测试、文档一起搞定"

### 3. 阶段门禁必须遵守
未通过当前阶段 QA，不得进入下一阶段。

### 4. 独立 QA 是强制项
开发 agent 完成后，必须再分发给 QA agent 独立验证。

禁止：
- 开发 agent 自己宣布"没问题"
- 主 agent 未经 QA 直接宣告阶段完成

### 5. 每轮必须落盘
每次有实质推进后，必须：

1. 更新状态文件
2. 写工作日志

### 6. 保持问题分层
必须区分：
- 结构问题
- 语义问题
- 验证问题
- 性能/增强问题
- 业务效果问题

不要在前面问题未厘清时，直接跳到更后层的优化或结果结论。

## Sprint Contract

每轮 sprint 开工前，主 agent 必须生成 sprint contract，对齐"本轮做什么、怎么验收、什么算 done"。

sprint contract 至少包含：
- sprint id
- scope in（本轮做什么）
- scope out（本轮不做什么）
- deliverables（交付物）
- validation method（验证方式）
- pass criteria（通过标准）
- open questions（待澄清问题）

sprint contract 写入状态文件或作为任务卡的一部分分发给 generator。

模板见 `references/sprint-contract-template.md`。

## Handoff（结构化交接）

当出现以下情况时，应执行 handoff：

- 上下文过长，目标难以维持
- 出现明显上下文焦虑 / 提前收尾倾向
- 阶段性任务已完成，适合 clean-slate 续跑
- 当前执行思路已被污染，需要换一个干净上下文
- 跨 session 交接给其他 agent

### handoff 必须保留的状态

- 当前目标
- 已完成内容
- 未完成内容
- 已知问题与风险
- 关键决策记录
- 下一步建议
- 相关路径与验证状态

### 操作方式

1. 生成 handoff summary 文件（模板见 `references/handoff-template.md`）
2. 更新状态文件
3. 新 session / 新 agent 通过读取 handoff summary + 状态文件即可 clean-slate 接续

### 与 compaction 的关系

- **compaction**：压缩旧历史，保留连续性，适合中等长度任务
- **handoff + context reset**：完全清空旧上下文，通过工件交接，适合特别长/复杂的任务
- 两者不冲突，可以先 compaction 再 handoff

## 通用阶段模型

如果 governing doc 已有明确 phase / milestone / iteration 命名，优先沿用原文档。

如果没有，则使用以下通用阶段模型：

### Phase 0：现状审计
目标：
- 搞清当前系统如何工作
- 找到隐藏依赖、重复入口、职责重叠、语义混乱点
- 输出当前风险与最小推进顺序

### Phase 1：目标定义
目标：
- 明确目标结构、边界、契约、语义定义
- 明确当前阶段 in-scope / out-of-scope
- 明确项目约束与一票否决风险

### Phase 2：最小重构执行
目标：
- 一次执行一个最小任务
- 在不失控扩 scope 的前提下持续推进
- 保持每轮都有可验证产物

### Phase 3：验证与收尾
目标：
- 独立 QA
- 文档同步
- migration notes / runbook / status / work-log 完整

### Phase 4（可选）：增强与后续优化
目标：
- 在基础重构稳定后，再做增强、优化、扩展

## 项目约束注入

在首次启动或切换新项目时，主 agent 必须明确：

1. 本项目的关键语义约束
2. 本项目的一票否决风险
3. 本项目当前阶段明确不做的事情
4. 本项目的验证口径
5. 本项目是否存在历史兼容性/迁移要求

这些约束不应永久写死在通用 skill 主体里，而应：
- 写入状态文件
- 写入任务卡
- 或放入对应领域 example

## 首次启动流程

首次使用本 skill 时，不应直接分发 implementation task。

应按以下顺序：

1. 锁定 governing doc（若无，则进入 audit-to-plan）
2. 初始化状态文件
3. 优先分发 architect / pm 做现状审计
4. 基于审计结果明确项目约束与阶段边界
5. 再选择一个最小 backend 任务
6. backend 完成后必须独立 QA
7. QA 后才更新状态文件与工作日志

## 恢复执行（当用户说"继续"时）

当用户说"继续"时：

1. 先读状态文件
2. 确认当前 phase / gate
3. 查看最后一个被接受的任务
4. 查看最新 QA 结论
5. 只推进下一个最小、无 blocker 的任务
6. 如状态与代码现实不一致，先补审计

## 默认启动策略

- 若尚无可靠现状审计，不直接开始大规模实现
- 默认先分发 architect 做现状审计与阶段拆分建议
- 默认优先收口：
  1. 主入口 / 主调用链
  2. 关键语义字段 / 接口契约 / schema 契约
  3. 职责边界过重的模块
  4. 验证/校验/回填逻辑的边界问题
- 在基础重构未通过前，不进入增强优化类任务

## 状态推进规则

- 任务完成 ≠ 任务通过
- 只有在独立 QA 接受后，任务才能从"已完成"进入"已通过"
- 只有在状态文件更新后，才算正式推进
- 只有在写完工作日志后，当前轮次才算收尾
- implementation 任务完成后，必须先生成可引用的 delivery 文件，再进入 QA

## Delivery 交付规则

每轮 implementation（backend / architect 的实质性交付）完成后，必须生成一个可引用的交付结果文件，作为 QA 的正式输入工件。

推荐路径：
- `docs/refactor-status/deliveries/YYYY-MM-DD-HH-<task-name>.md`

delivery 文件至少包含：
- 任务名称
- 任务范围
- 结果摘要
- 修改文件
- 与计划/目标对齐
- 验证过程
- 风险与遗留
- 下一步建议

规则：
- 不要只把实现结果放在聊天消息里
- QA 不得仅凭聊天摘要执行"汇报 vs 实际文件一致性"验收
- 在 delivery 文件路径写入状态文件之前，不应发起 QA

## 明确禁止事项

执行过程中，禁止：

- 在基础结构与语义未厘清前直接做优化或结果包装
- 混用不同验证口径却不声明
- 让含混字段承担多重核心语义
- 把验证/事后结果直接回灌到实时/主流程判断中
- 在同一轮验收里混入多个层次的问题
- 让开发 agent 自测代替独立 QA
- 不更新状态文件就宣告"继续下一阶段"
- 不写工作日志就宣告"本轮完成"

## Agent 分工规则

默认分工如下：

### architect
适合分发：
- 现状审计
- 目标结构设计
- schema / module boundary / interface 设计
- 风险识别
- 重构顺序建议

### backend
适合分发：
- schema 修改
- 脚本/服务/模块重构
- 入口统一
- service 拆分
- validation / migration 路径实现
- secrets / config 治理

### qa
适合分发：
- 独立验收
- 测试与读回
- 对照 plan 检查
- 语义一致性检查
- 风险检查
- 阶段通过/驳回判断

### tech-writer
适合分发：
- migration notes
- docs / runbook
- 变更说明与结构文档

### pm
适合分发：
- 把目标整理成 backlog / phase plan
- 梳理阶段边界
- 识别前置依赖和 blocker

规则：
- 一个具体任务只给一个 agent
- 不要把"设计 + 实现 + QA"打包给同一个 agent
- 有歧义时先给 architect，不要直接给 backend

## 任务拆分规范

必须把任务拆成"小而可验收"的任务卡。

好的任务示例：
- 审计当前调用链并输出现状图
- 设计目标 schema 或接口契约
- 统一唯一主入口
- 拆分职责过重模块
- 将验证逻辑从主流程中独立出来
- 整理 config / secrets 载入方式
- 为某一迁移步骤增加可验证落地路径

差的任务示例：
- "把 refactor 做完"
- "清理整个系统"
- "把架构弄正式"
- "全部问题一起改"

## 开发任务的强制输出

每次 backend / architect 任务结束后，必须要求其交付以下内容：

1. **任务范围**
2. **修改文件**
3. **与计划/目标对齐**
4. **验证过程**
5. **风险与遗留**
6. **建议下一步**

## QA 任务的强制输出

每次 QA 任务结束后，必须要求其交付：

1. **验收范围**
2. **验收方法**
3. **通过项**
4. **失败项**
5. **与计划/目标不一致之处**
6. **是否存在语义漂移/风险**
7. **最终结论**
   - 通过
   - 有条件通过
   - 驳回

如果驳回，必须给出明确返工项。

## 状态文件要求

本 skill 必须维护一个可续跑的状态文件。

推荐路径：
- `docs/refactor-status/<project>-status.md`

状态文件至少包含：

- governing doc
- 工作模式
- 当前阶段
- 项目约束
- 已完成任务
- 已通过任务
- 被驳回任务
- 当前 blocker
- 最近一次 QA 结论
- 下一步建议
- 更新时间

## 工作日志要求

每次有实质推进后，必须写工作日志。

推荐路径格式：
- `docs/work-log/YYYY-MM-DD-HH-<task-name>.md`

工作日志应包含：
- 本轮完成内容
- 关键决策
- 修改文件
- 验证摘要
- blocker / 风险
- 下一步

## 推荐执行循环

每轮推进建议按这个顺序：

1. 读取 governing doc / brief
2. 读取状态文件
3. 确定最小下一步任务
4. 写 sprint contract（scope in/out、deliverables、pass criteria）
5. 选择合适的 specialist agent
6. 生成任务卡并分发（附 sprint contract）
7. 获取开发结果
8. 要求 generator 生成 delivery 文件
9. 再分发 QA agent 独立验证（输入：delivery + sprint contract）
10. 根据 QA 结论决定接受或驳回
11. 更新状态文件
12. 写工作日志
13. 判断是否需要 handoff（上下文是否过长/阶段是否结束）
14. 如需 handoff，生成 handoff summary
15. 向用户汇报本轮结果与下一步

除非用户明确要求"自动循环直到完成"，否则不要静默批量执行多轮。

## 当不存在状态文件时

首次使用本 skill 时：

1. 找到 governing doc，或进入 audit-to-plan
2. 创建状态文件
3. 优先发起"现状审计"任务
4. 不要一上来直接开始大改代码

## 成功判定

本 skill 的成功，不是"代码动了"。

而是：
- 每一轮任务边界清晰
- 每一轮有 sprint contract 对齐预期
- 每一轮都有明确交付（delivery 文件）
- 每一轮都经独立 QA
- 每一轮都更新状态并写日志
- 长任务可通过 handoff 跨 session 交接
- 项目按阶段推进且不跑偏
- 系统定义比之前更统一、更可信、更可验证

## 参考文件索引

| 文件 | 用途 | 何时读 |
|------|------|--------|
| `references/bootstrapping.md` | 首次启动与续跑操作手册 | 首次使用本 skill 或用户说"继续"时 |
| `references/modes.md` | 三种工作模式说明 | 判断输入模式时 |
| `references/phase-model.md` | 通用阶段模型（Phase 0-4） | governing doc 没有清晰阶段时 |
| `references/sprint-contract-template.md` | Sprint contract 模板 | 每轮 sprint 开工前 |
| `references/handoff-template.md` | Handoff summary 模板 | 需要跨 session 交接时 |
| `references/task-card-template.md` | 任务卡模板 | 分发任务给 agent 时 |
| `references/qa-template.md` | QA 验收模板 | 分发 QA 任务时 |
| `references/constraints-template.md` | 项目约束模板 | 首次启动或进入新阶段时 |
| `references/status-template.md` | 状态文件模板 | 初始化或更新状态文件时 |

## 设计来源

本 skill 的设计基于以下工程经验：
- OpenAI《Harness engineering》
- Anthropic《Harness design for long-running application development》
- 核心理念：环境优先、生成与评估分离、结构化交接、约束优先于微观指挥
- 概念边界详见 `docs/harness-runtime-boundary.md`
- 术语表详见 `docs/harness-english-glossary.md`
