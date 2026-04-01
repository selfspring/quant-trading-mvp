# Loop Runner Procedure

## Pre-Flight

1. 确认 `ISSUE_LIST.md` 存在（不存在则创建空文件，review agent 会填充）
2. 读取 config：`max_rounds`, `target_files`, `review_focus`
3. 统计当前 open issues 数量

## Loop Execution

```
round = 1

while round <= max_rounds:

    # Step 1: Review
    spawn review agent with review-prompt.md
    wait for completion
    new_issues = count newly added [ ] issues in ISSUE_LIST.md

    if new_issues == 0:
        log "Round {round}: No new issues found. Loop complete."
        break

    # Step 2: Fix
    spawn fix agent with fix-prompt.md
    wait for completion

    # Step 3: QA Verify
    spawn QA agent with qa-prompt.md
    wait for completion

    reopened = count [X] issues
    verified = count [V] issues
    log "Round {round}: fixed={verified}, reopened={reopened}"

    round += 1

# Post-Loop
write final report (see below)
```

## Post-Loop Report

统计 ISSUE_LIST.md 中各状态数量，输出：

```
=== Iterative Review Complete ===
Rounds completed: N
Total issues found: X
  Verified fixed: V
  Still open: O
  Skipped (manual): S

Open issues requiring attention:
  ISSUE-XXX: 描述
  ...
```

## Update Config in ISSUE_LIST.md

每轮开始前更新 `current_round` 字段。

## Agent Selection

| Agent | 职责 |
|-------|------|
| code-artisan | review agent（发现问题，擅长代码审查，落盘稳定）|
| backend | fix agent（修复代码）|
| qa | QA agent（验证修复）|

> ⚠️ 不使用 architect 作为 review agent：architect 分析能力强但工具落盘不稳定。

## Spawn Timeout

| 阶段 | runTimeoutSeconds |
|------|-------------------|
| review | 1200 |
| fix | 1800 |
| QA | 900 |
