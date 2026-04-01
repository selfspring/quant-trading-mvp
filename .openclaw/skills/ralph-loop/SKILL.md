---
name: ralph-loop
description: >
  Autonomous iterative task completion using the Ralph Wiggum technique.
  Spawns a sub-agent in a loop: each iteration picks ONE task from a spec/plan,
  implements it, verifies acceptance criteria, and commits. The loop continues
  until all tasks are done or max iterations are reached.
  Use when: user says "ralph loop", "autonomous loop", "run until done",
  "implement this PRD", "loop until complete", "自主循环", "跑到完成为止",
  or wants a multi-task spec implemented end-to-end without manual intervention.
  NOT for: single one-shot tasks, quick fixes, or tasks that need human decisions at each step.
---

# Ralph Loop

Autonomous iterative task completion. Based on [Geoffrey Huntley's Ralph Wiggum technique](https://ghuntley.com/ralph/).

## Core Concept

```
while tasks remain:
    spawn agent → read plan → pick ONE task → implement → QA verify → commit
    if QA FAIL: retry (up to retry_limit) → if still fail: mark STUCK
    if all done: write work-log → stop
    else: next iteration (fresh context)
```

Each iteration gets a **fresh context window**. State persists on disk via the plan file.

## Workflow

### 1. Prepare the Plan

Before starting the loop, ensure a plan file exists. Two options:

**Option A: User provides a spec/PRD**
- Accept markdown file with `- [ ] task` checklist items
- Store at `{project}/RALPH_PLAN.md`

**Option B: Generate from user description**
- Ask the user what they want built
- Create `RALPH_PLAN.md` with numbered `- [ ] task` items and acceptance criteria
- Each task should be small enough to complete in one agent session

Plan format:

```markdown
# Implementation Plan

## Config
- project: E:\quant-trading-mvp
- max_iterations: 30
- backpressure: tests,lint

## Tasks
- [ ] 1. Create user authentication module
  - AC: login/logout endpoints exist, tests pass
- [ ] 2. Add JWT token validation
  - AC: middleware validates tokens, 401 on invalid
- [x] 3. Setup database schema (DONE)
```

### 1.5 Pre-Spawn Memory Dump (强制)

**在启动循环之前，主 Agent 必须先把子 Agent 需要的上下文存入双轨记忆系统。**

子 Agent 每次都是全新上下文（Fresh Context），它不知道主 Agent 踩过什么坑。
所以主 Agent 必须在 spawn 之前，调用 `store_memory` 把以下信息存入记忆库：

1. **项目已知坑**（代理配置、编码问题、API 限制等）
2. **当前任务的技术上下文**（相关文件路径、已有实现、接口约定）
3. **历史教训**（之前迭代中失败的原因和解决方案）

这样子 Agent 在 iteration-prompt 中被要求 `recall_memory` 时，才能真正查到有用的信息。

**没有记忆就没有传承。先存后发，不要跳过。**

### 2. Run the Loop

Read `references/loop-runner.md` for the orchestration procedure.

**Key parameters:**
- `max_iterations`: Safety limit (default 30)
- `backpressure`: Comma-separated checks that must pass (tests, lint, typecheck)
- `retry_limit`: Max retries per task before marking stuck (default 3)

### 3. Per-Iteration Agent Task

Each spawned agent receives a task prompt built from `references/iteration-prompt.md`.

The agent must:
1. Read `RALPH_PLAN.md`
2. Pick the **first unchecked** `- [ ]` task
3. Implement it completely
4. Run backpressure checks (tests/lint if configured)
5. If checks pass: commit changes, mark task `- [x]` in plan
6. If ALL tasks done: output `RALPH_COMPLETE`

### 4. Stuck Detection

If a task fails `retry_limit` consecutive times:
- Mark it `- [!] task (STUCK after N attempts)`
- Skip to next task
- Report stuck tasks to user at end

### 5. Completion

Loop ends when:
- All tasks are `[x]` → report success
- Max iterations reached → report progress + remaining
- All remaining tasks are stuck → report and ask user

## Important Rules

- **One task per iteration.** Never let agent do multiple tasks.
- **Fresh context each iteration.** Don't reuse agent sessions.
- **State on disk only.** Plan file is the single source of truth.
- **Backpressure gates.** Agent cannot mark done unless checks pass.
- **Trust but verify.** Agent decides what to implement; plan + checks keep it honest.

## 重构任务专用格式

当任务是架构重构（而非新功能开发）时，RALPH_PLAN.md 的每个任务需包含以下字段：

```markdown
- [ ] TASK-001 任务名称
  - 改前：当前状态描述
  - 改后：目标状态描述
  - 产物：需要产出的文件/SQL/脚本
  - 验证：如何用命令/grep/SQL 确认改动已生效
  - 回滚：如果失败如何撤销
  - agent: backend
  - timeout: 1800
```

重构任务的 config 建议：

```markdown
## Config
- project: E:\\quant-trading-mvp
- max_iterations: 20
- backpressure: read-verify    # 每步必须回读验证，不跑测试也要读文件确认
- retry_limit: 2
- default_timeout: 1800        # 重构任务给足时间
- agent: backend               # 重构任务默认用 backend，不用 architect
```

重构任务的验证标准（backpressure=read-verify 时）：
- agent 必须用 read/exec 工具回读改动，不能只说
