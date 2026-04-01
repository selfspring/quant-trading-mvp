# ISSUE_LIST.md Format

## Header

```markdown
# ISSUE_LIST.md

## Config
- project: <project_dir>
- target_files: <files/dirs under review>
- review_focus: <what to look for>
- max_rounds: 3
- current_round: 1
```

## Issue Entry Format

```markdown
- [ ] ISSUE-001 | round=1 | file=path/to/file.py:42 | severity=high
  **问题**: 描述具体问题是什么
  **影响**: 说明会导致什么后果
  **建议修复**: 具体修复方向

- [F] ISSUE-002 | round=1 | file=path/to/file.py:88 | severity=medium
  **问题**: ...
  **影响**: ...
  **建议修复**: ...
  **修复说明**: fix agent 的修复描述

- [V] ISSUE-003 | round=1 | file=path/to/file.py:12 | severity=low
  **问题**: ...
  **修复说明**: ...
  **QA验证**: QA agent 的验证结果
```

## Status Codes

| 标记 | 含义 | 谁来标 |
|------|------|--------|
| `[ ]` | open，待修复 | review agent |
| `[F]` | fixed，已修复待验证 | fix agent |
| `[V]` | verified，已验证通过 | QA agent |
| `[X]` | reopened，QA 验证失败重新打开 | QA agent |
| `[S]` | skipped，需人工决策，本轮跳过 | fix agent |

## Severity Levels

- `critical` — 数据错误/逻辑崩溃/安全漏洞
- `high` — 功能不正确/重要边界未处理
- `medium` — 代码质量/性能/可维护性
- `low` — 风格/注释/小优化

## Rules

- issue id 全局唯一，格式 ISSUE-NNN，不复用
- 每轮新发现的问题追加在文件末尾，不修改已有条目
- fix agent 只修改 `[ ]` → `[F]`，不修改其他状态
- QA agent 只修改 `[F]` → `[V]` 或 `[X]`
- review agent 不重复报告已有的 `[F]`/`[V]` 问题
