# Loop Runner Procedure

This is the orchestration logic for the main agent running the Ralph Loop.

## Pre-Flight

1. Confirm `RALPH_PLAN.md` exists in the project directory
2. Parse config section: `max_iterations`, `backpressure`, `retry_limit`
3. Count total tasks and completed tasks
4. If all done already, report and stop

## Loop Execution

```
iteration = 0
consecutive_failures = {}  # task_id -> fail_count

while iteration < max_iterations:
    iteration += 1

    # Count remaining tasks
    remaining = count unchecked tasks in RALPH_PLAN.md
    if remaining == 0:
        report "All tasks complete after {iteration} iterations"
        break

    # Skip stuck tasks
    if all remaining tasks are marked [!] STUCK:
        report "All remaining tasks are stuck. Human intervention needed."
        break

    # Build the iteration prompt
    # See iteration-prompt.md for template

    # Spawn agent
    result = sessions_spawn(
        agentId: pick appropriate agent (backend/frontend/etc),
        mode: "run",
        runtime: "subagent",
        task: built_prompt,
        timeoutSeconds: 600
    )

    # Wait for completion (push-based, don't poll)
    # sessions_yield to receive result

    # Parse result
    if agent output contains "RALPH_COMPLETE":
        # All tasks done — still need QA
        qa_passed = run_qa_verification(task_id, agent_output)
        if qa_passed:
            report success
            write_work_log()
            break
        else:
            # QA failed, don't mark complete
            log "RALPH_COMPLETE claimed but QA failed, retrying"
            consecutive_failures[task_id] += 1

    elif agent output contains "TASK_DONE: {task_id}":
        # Dev agent says done — run QA verification
        qa_result = sessions_spawn(
            agentId: "qa",
            mode: "run",
            runtime: "subagent",
            task: build_qa_prompt(task_id, task_description, agent_output),
            runTimeoutSeconds: 900
        )
        # sessions_yield to receive QA result

        if qa_result contains "PASS":
            consecutive_failures[task_id] = 0
            log "Iteration {iteration}: task {task_id} completed + QA passed"
        else:
            # QA failed — 提取失败原因，写入 RALPH_PLAN.md 的任务备注
            qa_failure_reason = extract_failure_reason(qa_result)  # 解析 QA_FAIL 后面的问题列表
            unmark task_id in RALPH_PLAN.md  # 回滚 [x] → [ ]
            append_qa_feedback_to_plan(task_id, qa_failure_reason)  # 在任务下方追加 > QA反馈: ...
            consecutive_failures[task_id] += 1
            log "Iteration {iteration}: task {task_id} QA FAILED: {qa_failure_reason}"
            if consecutive_failures[task_id] >= retry_limit:
                mark task as [!] STUCK in RALPH_PLAN.md
                log "Task {task_id} marked STUCK after {retry_limit} QA failures"

    elif agent output contains "TASK_FAILED: {task_id}":
        consecutive_failures[task_id] += 1
        if consecutive_failures[task_id] >= retry_limit:
            mark task as [!] STUCK in RALPH_PLAN.md
            log "Task {task_id} marked STUCK after {retry_limit} failures"
        else:
            log "Task {task_id} failed (attempt {n}/{retry_limit}), will retry"

    # Brief status update to user every 5 iterations
    if iteration % 5 == 0:
        report progress: "{completed}/{total} tasks, iteration {iteration}/{max}"
```

### QA Feedback Format in RALPH_PLAN.md

当 QA FAIL 时，在 RALPH_PLAN.md 对应任务行下方追加反馈，格式如下：

```markdown
- [ ] 任务描述
  > QA反馈[1]: 问题1描述；问题2描述；问题3描述
  > QA反馈[2]: 第二次失败的新问题（如果有）
```

开发 agent 看到 `> QA反馈` 标记时，必须逐条解决后才能标记 `[x]`。

### QA Prompt Builder

```python
def build_qa_prompt(task_id, task_description, dev_agent_output):
    return f"""
你是 QA agent，负责独立验证开发 agent 的交付物。

## 验证目标
任务 #{task_id}: {task_description}

## 开发 agent 自述的完成情况
{dev_agent_output}

## 验收规则（强制）
1. 不信任开发 agent 的自述，必须自己运行命令验证
2. 读取修改过的文件，确认内容与预期一致
3. 运行相关测试，贴出实际输出
4. 每条验收标准必须有实际命令输出作为证据
5. 发现问题必须明确描述：哪里不对、期望什么、实际什么

## 输出（必须以下面之一结尾）
- QA_PASS: {task_id}（所有标准通过）
- QA_FAIL: {task_id} — [问题列表]
"""
```

## Post-Loop

1. Read final `RALPH_PLAN.md`
2. Count completed / stuck / remaining
3. **写工作日志**（强制，不可跳过）：
   - 路径：`{project_dir}/docs/work-log/YYYY-MM-DD-HH-ralph-loop-任务名.md`
   - 内容：已完成任务列表、失败任务及原因、遗留事项、下一步建议
   - 目的：上下文清除后可快速恢复现场
4. Report summary to user:
   - Completed tasks
   - Stuck tasks (with failure reasons if available)
   - Remaining tasks
   - Total iterations used
   - QA pass/fail statistics
5. If stuck tasks exist, suggest splitting them into smaller tasks
6. 将本次循环经验存入 Dual-Track Memory（scope: ralph-loop/日期）

## Agent Selection Heuristic

Pick agent based on task content keywords:
- Database/API/Python → `backend`
- UI/React/CSS → `frontend`
- Tests/QA → `qa`
- Deploy/CI/Docker → `devops`
- Architecture/design → `architect`
- Default → `backend`

If no specialized agents are configured, use default agent.
fault → `backend`

If no specialized agents are configured, use default agent.
