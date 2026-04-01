# 工作流程：记忆管理

## 记忆体系

你每次会话都是全新的。以下文件是你的延续性：

| 文件 | 用途 | 加载时机 |
|------|------|----------|
| `memory/YYYY-MM-DD.md` | 每日原始记录 | 每次会话（今天+昨天） |
| `MEMORY.md` | 长期精炼记忆 | 仅主会话（安全考虑） |
| `~/self-improving/memory.md` | 执行改进经验 | 非平凡任务前 |
| `~/self-improving/domains/<domain>.md` | 领域经验 | 相关任务前 |
| `~/self-improving/projects/<project>.md` | 项目经验 | 相关项目前 |
| `~/self-improving/corrections.md` | 用户纠正记录 | 被纠正后立即写入 |

## 写入规则

**文字 > 大脑** 📝 — "心理笔记"不会在会话重启后存活，文件会。

| 场景 | 写入位置 |
|------|----------|
| 事实性事件/上下文 | `memory/YYYY-MM-DD.md` |
| 用户明确纠正 | `~/self-improving/corrections.md` |
| 可复用的全局规则/偏好 | `~/self-improving/memory.md` |
| 领域特定经验 | `~/self-improving/domains/<domain>.md` |
| 项目特定覆盖 | `~/self-improving/projects/<project>.md` |
| 值得长期保留的精炼见解 | `MEMORY.md` |

## 加载规则

非平凡任务前：

1. 读 `~/self-improving/memory.md`
2. 列出可用的 domains/ 和 projects/ 文件
3. 读最多 3 个匹配的 domains 文件
4. 如果有明确活跃的项目，也读对应的 projects 文件
5. 不要"以防万一"读不相关的文件

## MEMORY.md 安全规则

- **仅在主会话加载**（与用户直接对话）
- **不在共享上下文加载**（Discord、群聊、与其他人的会话）
- 包含个人上下文，不应泄露给陌生人

## 条目格式

保持简短、具体、每条一个教训：

```markdown
- [2026-03-16] 训练时排除 open_oi/close_oi，实时数据没有这两列
- [2026-03-16] PowerShell 不支持 &&，cron message 中用 ; 连接命令
```

如果推断新规则，标记为**暂定**直到用户验证。

---

**原则**: 被纠正或学到可复用经验后，在最终回复之前先写入文件。
