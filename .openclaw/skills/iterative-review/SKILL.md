---
name: iterative-review
description: >
  Autonomous iterative code review and fix loop. Spawns review agent to find problems,
  fix agent to resolve them, QA agent to verify, then repeats with fresh context until
  no new issues are found or max rounds reached. Use when: user says "find and fix problems",
  "iterative review", "audit and fix", "clean up the code", "循环审查", "找问题并修复".
  NOT for: single one-shot fixes, quick patches, or tasks needing human decisions at each step.
---

# Iterative Review

Autonomous multi-round code review + fix loop with fresh context each round to avoid path dependency.

## Core Concept

```
while open_issues > 0 and round < max_rounds:
    spawn review agent → scan target files → append new issues to ISSUE_LIST.md
    if no new open issues: break
    spawn fix agent → fix all open issues → mark as fixed
    spawn QA agent → verify fixes → mark as verified or reopen
    round += 1
write final report
```

Each agent gets **fresh context**. State persists in `ISSUE_LIST.md` on disk.

## Workflow

### 1. Prepare

Create `ISSUE_LIST.md` in the project directory (or let the first review agent create it).

See `references/issue-list-format.md` for the file format.

### 2. Configure

Set in your task prompt:
- `target_files`: which files/directories to review
- `review_focus`: what to look for (logic bugs, data integrity, API usage, performance, etc.)
- `max_rounds`: default 3
- `project_dir`: absolute path to project

### 3. Run the Loop

Follow `references/loop-runner.md` for orchestration logic.

See `references/review-prompt.md` for the review agent prompt template.
See `references/fix-prompt.md` for the fix agent prompt template.
See `references/qa-prompt.md` for the QA agent prompt template.

### 4. Completion

Loop ends when:
- All issues are `verified` → report success
- Max rounds reached → report remaining open issues
- Review agent finds 0 new issues → report clean

## Output

Final `ISSUE_LIST.md` with all issues and their status, plus a summary report.
