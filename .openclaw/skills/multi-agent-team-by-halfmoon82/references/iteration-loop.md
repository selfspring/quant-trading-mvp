# 迭代反馈循环 (Iteration Loop) 编排逻辑

> 基于 Anthropic Harness Design 中 GAN 灵感的 Generator-Evaluator 模式。
> Coordinator 在检测到 step 配置了 `evaluator` + `iterateUntil` 时自动进入此循环。

---

## 核心概念

- **Generator**: 产出工作成果的角色（如 backend, frontend）
- **Evaluator**: 评估成果质量的角色（如 qa, code-artisan）
- **分离原则**: Generator 和 Evaluator 必须是不同的 agent session，确保评估独立性
- **Context Reset**: 每轮迭代都是全新 session，通过 handoff 文件传递状态

## Step 配置格式

```json
{
  "step": 3,
  "roles": ["frontend", "backend"],
  "action": "并行开发",
  "parallel": true,
  "output": "代码实现",
  "evaluator": "qa",
  "iterateUntil": {
    "minScore": 7,
    "maxIterations": 5
  },
  "contextReset": true,
  "handoffOutput": "handoff-{step}-{role}.md"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `evaluator` | string | 评估角色 ID（必须是 roleTemplates 中的有效角色） |
| `iterateUntil.minScore` | number (1-10) | 所有评估维度都必须 >= 此分数才通过 |
| `iterateUntil.maxIterations` | number | 最大迭代轮数，防止无限循环 |

---

## 迭代循环编排逻辑

当一个 workflow step 配置了 `evaluator` 和 `iterateUntil` 时，Coordinator 执行以下循环：

### 1. 初始化 (Initialize)

读取 step 配置，获取：
- Generator role(s)
- Evaluator role
- `minScore` 和 `maxIterations`
- 创建迭代状态跟踪文件 `iteration-state-{step}.json`

### 2. Generator Phase

- Spawn generator agent（**全新 session**）
- 如果是第一轮：给它原始任务描述 + 架构文档等上下文
- 如果是后续轮：注入上一轮的 feedback 文件内容
- Generator 完成后写入：
  - 工作成果（代码、文档等）
  - Handoff 文件: `teamtask/tasks/{task-id}/handoff-{step}-{role}.md`

### 3. Evaluator Phase

- Spawn evaluator agent（**全新 session**）
- 给它：
  - 评估标准（evaluation criteria）
  - Generator 的产出路径
  - Generator 的 handoff 文件
  - 原始任务需求（作为对照基准）
- Evaluator 按维度打分 (1-10) + 写具体批评到:
  - `teamtask/tasks/{task-id}/feedback-{step}-iteration-{N}.md`
- 判定：如果**所有维度** >= `minScore` → **PASS**，跳出循环

### 4. Feedback Injection

- 如果未通过且未达到 `maxIterations`：
  - 读取 feedback 文件
  - 构造增强版 task prompt（原始任务 + feedback + 上一轮 handoff）
  - Context Reset: 下一轮 generator 是**全新 session**，不继承任何上下文
  - 回到步骤 2

### 5. 循环终止

| 终止条件 | 标记 | 后续行动 |
|---------|------|---------|
| 所有维度达标 | ✅ PASS | 进入下一个 workflow step |
| 达到 maxIterations 但仍未达标 | ⚠️ PARTIAL | 生成报告，让人类介入决策 |

---

## Coordinator 视角伪代码

```pseudocode
function executeIterativeStep(step, taskId, taskContext):
    generator = step.roles  // 可以是单个或多个角色
    evaluator = step.evaluator
    minScore = step.iterateUntil.minScore
    maxIter = step.iterateUntil.maxIterations
    
    iteration = 0
    passed = false
    lastFeedback = null
    
    while iteration < maxIter AND NOT passed:
        iteration += 1
        
        // ===== Generator Phase =====
        generatorPrompt = buildGeneratorPrompt(
            taskContext,
            iteration,
            lastFeedback  // null on first iteration
        )
        
        for each role in generator:
            // 全新 session，无历史上下文
            spawnAgent(role, generatorPrompt)
            waitForCompletion(role)
            // agent 会自动写 handoff 文件（因为 contextReset: true）
        
        // ===== Evaluator Phase =====
        evaluatorPrompt = buildEvaluatorPrompt(
            taskContext,
            step,
            iteration,
            getHandoffPaths(generator, step, taskId),
            getOutputPaths(generator, step, taskId)
        )
        
        spawnAgent(evaluator, evaluatorPrompt)
        waitForCompletion(evaluator)
        
        // 读取评估结果
        feedback = readFeedback(taskId, step, iteration)
        scores = feedback.scores  // { dimension: score }
        
        if ALL scores >= minScore:
            passed = true
            markStepResult(taskId, step, "PASS", iteration)
        else:
            lastFeedback = feedback
            logIteration(taskId, step, iteration, scores)
    
    if NOT passed:
        markStepResult(taskId, step, "PARTIAL", iteration)
        generateHumanInterventionReport(taskId, step, feedback)
        notifyHuman("Step {step} 未能在 {maxIter} 轮内达标，需要人工介入")
    
    return { passed, iteration, scores }
```

---

## Agent Prompt 注入模板

### Generator Prompt — 首轮

```markdown
# 任务: {task-title}

## 任务描述
{original-task-description}

## 你的角色
你是 {role-name}，负责 {action-description}。

## 上下文文件
以下文件包含前序步骤的产出，请仔细阅读：
{list-of-context-files}

## 产出要求
1. 完成 {action-description}
2. 将成果写入 `teamtask/tasks/{task-id}/` 目录
3. 写入 handoff 文件: `teamtask/tasks/{task-id}/handoff-{step}-{role}.md`
4. handoff 格式参考团队标准（参见 references/handoff-format.md）

## 重要
- 写完 handoff 后你的任务就结束了
- 不要试图做下一步的工作
- 专注于高质量地完成你的部分
```

### Generator Prompt — 后续轮（带 Feedback Injection）

```markdown
# 任务: {task-title} — 迭代第 {N} 轮

## 任务描述
{original-task-description}

## 你的角色
你是 {role-name}，负责 {action-description}。

## ⚠️ 迭代背景
这是第 {N} 轮迭代。上一轮的工作已经被评估，以下是评估反馈：

### 上一轮评估分数
{scores-table}

### 必须修复的问题
{must-fix-items}

### 建议改进
{should-fix-items}

## 上一轮 Handoff（参考）
{previous-handoff-content}

## 你需要做的
1. **仔细阅读上面的反馈**
2. 针对"必须修复"的每一条进行修复
3. 尽可能处理"建议改进"的内容
4. 将改进后的成果写入 `teamtask/tasks/{task-id}/`
5. 写入新的 handoff: `teamtask/tasks/{task-id}/handoff-{step}-{role}.md`
6. 在 handoff 中明确说明针对每条 feedback 做了什么改动

## 重要
- 不要忽略任何"必须修复"的反馈
- 如果某条反馈你认为不合理，在 handoff 中解释原因
- 写完 handoff 后你的任务就结束了
```

### Evaluator Prompt

```markdown
# 评估任务: Step {step} — {action}

## 你的角色
你是 {evaluator-role-name}，负责评估 {generator-role} 的工作成果。

## 评估标准
从 `config/evaluation-criteria.json` 加载适用的评估预设（fullstack / backend-api / data-pipeline / custom）。
按预设中定义的**每个维度**打分（1-10），**所有维度 >= {minScore} 才算通过**。

评估预设由 Coordinator 根据任务类型选择并注入到你的 prompt 中。
详细的打分规则和反偏倚要求参见 `references/evaluator-prompt.md`。

## 原始需求（对照基准）
{original-task-description}

## Generator 产出
请审查以下文件：
{list-of-output-files}

## Generator Handoff
请阅读 Generator 的 handoff 了解他的工作思路：
{handoff-file-path}

## 迭代信息
- 当前是第 {iteration} 轮评估
- 最大迭代次数: {maxIterations}
{if iteration > 1: - 上一轮你的反馈: {previous-feedback-path}}

## 产出要求
写入评估报告到: `teamtask/tasks/{task-id}/feedback-{step}-iteration-{iteration}.md`

报告格式：
```
## 评估结果

| 维度 | 分数 (1-10) | 说明 |
|------|------------|------|
| {dimension_1} | X | ... |
| {dimension_2} | X | ... |
| ... | ... | ... |
（维度列表从 evaluation-criteria.json 对应 preset 的 dimensions 获取）

## 结论
- **通过/未通过** (所有维度 >= {minScore})

## 必须修复
1. ...

## 建议改进
1. ...

## 锦上添花
1. ...
```

## 重要
- 严格按维度打分，不要心软
- 批评要具体：指出文件名、行号、具体问题
- "必须修复"只放真正的 blocker
- 你是独立评估者，不要替 generator 找借口
```

---

## 迭代状态跟踪文件

Coordinator 维护 `teamtask/tasks/{task-id}/iteration-state-{step}.json`：

> 注意：下面示例中的维度名（功能完整性、代码质量等）仅为示意。实际维度从 `evaluation-criteria.json` 对应 preset 动态加载。

```json
{
  "taskId": "task-001",
  "step": 3,
  "generator": ["frontend", "backend"],
  "evaluator": "qa",
  "minScore": 7,
  "maxIterations": 5,
  "currentIteration": 2,
  "status": "in-progress",
  "history": [
    {
      "iteration": 1,
      "scores": {
        "功能完整性": 6,
        "代码质量": 7,
        "测试覆盖": 4,
        "安全性": 7,
        "可维护性": 6
      },
      "passed": false,
      "feedbackFile": "feedback-3-iteration-1.md",
      "handoffFiles": ["handoff-3-frontend.md", "handoff-3-backend.md"],
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "iteration": 2,
      "scores": {
        "功能完整性": 8,
        "代码质量": 8,
        "测试覆盖": 7,
        "安全性": 7,
        "可维护性": 7
      },
      "passed": true,
      "feedbackFile": "feedback-3-iteration-2.md",
      "handoffFiles": ["handoff-3-frontend.md", "handoff-3-backend.md"],
      "timestamp": "2025-01-15T11:45:00Z"
    }
  ]
}
```

---

## 与 Context Reset 的关系

迭代循环**天然依赖** Context Reset 机制：

1. 每轮 Generator 都是全新 session → 避免 context anxiety
2. 通过 handoff 传递状态 → 信息不丢失
3. Evaluator 独立 session → 评估不受 generator 的 prompt 影响
4. Feedback 通过文件注入 → 结构化、可追溯

这与 Anthropic 文章中的核心洞察一致：**长任务拆成短 session + 结构化传递 > 一个超长 session 硬扛到底**。
