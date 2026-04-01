# Iteration Prompt Template

Build this prompt for each spawned agent. Replace `{variables}` with actual values.

---

## Prompt

```
你在项目 {project_dir} 中执行 Ralph Loop 的第 {iteration}/{max_iterations} 轮迭代。

## 你的任务

1. **查阅历史坑（必须）**：先调用 `python C:\Users\chen\.openclaw\workspace\skills\dual-track-memory\scripts\memory_tool.py recall --query "当前项目的已知坑和报错解决经验"` 了解项目中的雷区（如代理、编码等问题）。
2. 读取 {project_dir}/RALPH_PLAN.md
3. 找到第一个未完成的 `- [ ]` 任务（跳过 `[x]` 和 `[!]`）
4. **检查该任务下是否有 QA 反馈**（格式为 `> QA反馈[N]: ...`）：
   - 如果有，说明上一轮被 QA 打回了，必须先仔细阅读反馈，针对性修复，不要重复同样的错误
   - 如果没有，正常实现
5. 完整实现这个任务
6. 运行验证：{backpressure_checks}
5. 如果验证通过：
   a. 提交代码（commit message 包含任务描述）
   b. 在 RALPH_PLAN.md 中将该任务标记为 `- [x]`
   c. 如果所有任务都完成了，输出 RALPH_COMPLETE
   d. 否则输出 TASK_DONE: {task_number}
6. 如果验证失败：
   a. 输出 TASK_FAILED: {task_number}
   b. 附上失败原因

## 规则

- 只做一个任务，不要多做
- 不要修改其他任务的代码
- 不要跳过验证步骤
- commit message 格式：[Ralph #{iteration}] {task_description}
- 如果任务不清楚，选择最保守的实现方式

## ⚠️ 强制落盘规则（最高优先级）

1. 每次修改文件后，立即调用 read 工具回读关键片段，确认内容真实落盘
2. 在 RALPH_PLAN.md 标记 [x] 之前，必须先完成回读验证
3. 如果任务需要产出新文件（如设计文档、迁移脚本），必须先用 write 工具创建占位文件，再填入内容
4. 禁止只在对话里描述改动而不调用工具
5. 最终回复必须包含：你实际调用了哪些工具、修改了哪些文件、回读结果是什么

## 验证清单（必须逐条执行）

1. 读回你修改过的文件关键片段，确认改动真实落盘
2. 运行 backpressure 检查：{backpressure_checks}
3. 确认 RALPH_PLAN.md 中该任务已标记 [x]
4. 明确写出"未验证项"与原因

## 当前进度

已完成: {completed_count}/{total_count}
本轮目标: 任务 #{next_task_number} - {next_task_description}
```

---

## Backpressure Check Commands

Based on the `backpressure` config, include these in the prompt:

| Check | Command |
|-------|---------|
| tests | `python -m pytest tests/ -x -q` |
| lint | `python -m ruff check {project_dir}` |
| typecheck | `python -m mypy {project_dir}/quant --ignore-missing-imports` |
| build | project-specific build command |

If no backpressure is configured, agent should still verify the change doesn't break imports:
```
python -c "import {main_package}"
```

## Output Protocol

Agent MUST end its output with exactly one of:
- `RALPH_COMPLETE` — all tasks in plan are [x]
- `TASK_DONE: N` — task N completed and verified
- `TASK_FAILED: N` — task N failed verification
- `TASK_STUCK: N` — task N is blocked by external dependency

The loop runner parses these tokens to decide next action.
