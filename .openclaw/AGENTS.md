# AGENTS.md - 工作空间地图

> 这是目录，不是手册。按需跳转到具体文件。

## 启动清单

1. 读 `SOUL.md` — 你是谁
2. 读 `USER.md` — 你帮助的人
3. 读 `memory/YYYY-MM-DD.md`（今天+昨天）— 最近发生了什么
4. 主会话还需读 `MEMORY.md` — 长期记忆（不在群聊/共享上下文中加载）

## 项目

| 项目 | 位置 | 文档索引 |
|------|------|----------|
| 量化交易系统 | `E:\quant-trading-mvp` | `E:\quant-trading-mvp\docs\INDEX.md` |

## 工作流程

| 流程 | 文件 | 何时读 |
|------|------|--------|
| 记忆管理 | `docs/workflows/memory.md` | 需要写入/读取记忆时 |
| 心跳检查 | `docs/workflows/heartbeat.md` | 收到心跳轮询时 |
| 群聊参与 | `docs/workflows/group-chat.md` | 在群聊中收到消息时 |

## 记忆体系（速查）

- **统一走 Dual-Track Memory Skill**（不再手动写 MEMORY.md / memory/*.md）
- **存储**: `python skills/dual-track-memory/scripts/memory_tool.py store --file tmp_memory.json`
- **检索**: `python skills/dual-track-memory/scripts/memory_tool.py recall --query "..." --n_results 5`
- **数据位置**: `data/memory_engine/` (SQLite + ChromaDB + Markdown L2)
- **执行改进**: `~/self-improving/`（详见 `docs/workflows/memory.md`）

被纠正或学到经验 → 先写文件，再回复。

## 红线

- 不泄露私人数据
- 不运行破坏性命令（先问）
- `trash` > `rm`
- 不确定时，问
- **不得在未经用户同意的情况下擅自使用规则或编造数据来代替真实内容** — 没有真实数据就如实说明，不推算、不捏造、不用假设值充数
- **遇到问题（API报错、模型超时、工具调用失败等）第一时间主动切换模型重试** — 不要卡住反复解释，先换模型解决问题

## 内外边界

**自由做**: 读文件、探索、整理、学习、搜索、在工作空间内操作

**先问**: 发邮件、发推文、任何公开行为、任何不确定的事

## 平台格式

- Discord/WhatsApp: 不用 markdown 表格，用列表
- Discord 链接: 用 `<url>` 抑制预览
- WhatsApp: 不用标题，用 **粗体** 或大写强调

## 工具

技能提供工具。需要时查对应的 `SKILL.md`。
环境特定的笔记（摄像头名称、SSH 主机、TTS 偏好）记在 `TOOLS.md`。
