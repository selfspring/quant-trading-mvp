# 通用长任务编排 skill：首次启动与续跑操作手册

> 本文件用于指导主控 agent 如何首次启动本 skill，以及在用户说"继续"时如何恢复推进。

## 一、首次启动的核心顺序

首次启动时，不要直接进入大规模 implementation。

正确顺序是：

1. 锁定 governing doc；若无，则进入 audit-to-plan
2. 初始化状态文件
3. 先做现状审计
4. 明确项目约束与一票否决风险
5. 再选一个最小 backend 任务
6. backend 完成后独立 QA
7. QA 后再更新状态与工作日志
8. 然后才进入下一轮

原则上：

- **先 architect，后 backend**
- **先 QA，再算通过**
- **先状态更新，再算推进**
- **先基础结构，后增强优化**

## 二、首次启动标准流程

### Step 0：锁定 governing doc 或进入 audit-to-plan
- 如果用户已提供计划文档，以该文档为 governing doc
- 如果用户没有计划文档，先分发 architect / pm 生成最小 refactor brief

### Step 1：初始化状态文件
推荐路径：
- `docs/refactor-status/<project>-status.md`

至少写入：
- 工作模式
- 当前阶段
- 当前阶段目标
- 当前阶段明确不做的内容
- 项目约束
- 当前正在进行的任务
- 下一步推荐任务
- 最新 QA 状态
- blocker

### Step 2：先分发 architect 做现状审计
首次启动时，默认不要直接分发 backend 改代码。

应优先让 architect 回答：
1. 当前系统/链路/模块如何工作
2. 哪些入口、职责、契约、字段存在冲突或重叠
3. 当前实现与目标要求的主要冲突点
4. 当前一票否决风险在哪里
5. 最适合按什么最小顺序推进

### Step 3：基于审计结果，选择一个最小 backend 任务
优先原则：
1. 先收口主入口 / 主调用链
2. 再收口关键语义字段 / schema / 接口契约
3. 再收口职责边界过重模块
4. 最后再进入增强、优化、扩展

一次只做一个最小、可验收任务。

### Step 4：backend 完成后，必须分发独立 QA
QA 必须独立判断：
- 是否真的完成目标
- 是否符合 governing doc 或目标要求
- 是否引入新的语义混乱或结构倒退
- 是否触发一票否决风险
- 是否允许进入下一步

### Step 5：更新状态文件 + 写工作日志
只有在 backend 完成且 QA 给出结论后，才能：
1. 更新状态文件
2. 写工作日志
3. 对用户汇报下一步

## 三、推荐轮次模板

### Round 1：planner（architect / pm）审计与规划
目标：
- 现状审计
- 识别职责冲突 / 重复入口 / 隐藏依赖 / 语义混乱
- 给出结构化计划与最小推进顺序

### Round 2：sprint contract 对齐
目标：
- 写 sprint contract
- 明确本轮 scope in / out、deliverables、pass criteria

### Round 3：generator（backend / frontend）执行最小任务
目标：
- 只完成一个最小、最关键、最可验收的任务
- 生成 delivery 文件

### Round 4：evaluator（qa）独立验收
目标：
- 独立验收 generator 本轮任务
- 判断是否允许进入下一步

### Round 5：handoff 判断
目标：
- 判断上下文是否需要 reset
- 如需要，生成 handoff summary

后续继续按"sprint contract + generator + evaluator"循环推进。

## 四、恢复推进（用户说"继续"时）

恢复顺序：
1. 读取状态文件
2. 查看当前阶段与 Gate 状态
3. 查看"当前正在进行的任务"
4. 查看"最新 QA 结论"
5. 查看"下一步推荐任务"
6. 如状态与代码现实不一致，先发起审计任务

恢复时，优先判断：
- 最后一个**被接受**的任务是什么
- 当前 gate 是否通过
- 当前是否卡在 architect / backend / QA 某一环
- 下一个最小、无 blocker 的任务是什么

## 五、成功标志

首次启动是成功的，不是因为"已经开始改代码"，而是因为：
- governing doc 或 refactor brief 已明确
- 状态文件已初始化
- architect 审计已启动或完成
- 当前阶段与下一步明确
- 没有一开始就失控扩 scope
