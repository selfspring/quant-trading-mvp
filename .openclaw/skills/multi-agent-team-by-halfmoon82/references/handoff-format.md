# Handoff File 标准格式

> 当 workflow step 标记 `contextReset: true` 时，agent 必须在完成工作后写入此格式的 handoff 文件。
> 文件路径: `teamtask/tasks/{task-id}/handoff-{step}-{role}.md`

---

## 模板

```markdown
# Handoff: Step {N} — {Role Name}

> Task ID: {task-id}
> Sprint/Step: {step-number} / {workflow-name}
> Role: {role-id} ({role-emoji} {role-name})
> Timestamp: {ISO-8601}
> Iteration: {iteration-number} (如果在迭代循环中)

---

## 1. 已完成的工作 (Completed Work)

| 文件路径 | 改动类型 | 描述 |
|---------|---------|------|
| `src/api/users.ts` | 新增 | 用户 CRUD API |
| `src/models/user.ts` | 新增 | 用户数据模型 |
| `tests/api/users.test.ts` | 新增 | API 单元测试 |

## 2. 当前状态摘要 (Current Status)

- **能跑吗？** ✅ 是 / ❌ 否 / ⚠️ 部分可用
- **测试通过？** X/Y 通过（列出失败的测试）
- **构建状态？** ✅ 成功 / ❌ 失败（附错误信息）
- **已知问题:**
  - [ ] Issue 1: 描述
  - [ ] Issue 2: 描述

## 3. 未完成的待办 (Remaining TODOs)

- [ ] 待办事项 1（优先级: 高/中/低）
- [ ] 待办事项 2
- [ ] 待办事项 3

## 4. 踩过的坑 & 技术决策 (Pitfalls & Decisions)

### 踩过的坑
- **坑 1:** 描述问题 → 如何解决/绕过
- **坑 2:** 描述问题 → 如何解决/绕过

### 技术决策
- **决策 1:** 选择了 X 而不是 Y，因为 {原因}
- **决策 2:** 采用了 Z 方案，权衡是 {trade-off}

## 5. 下一步指令 (Instructions for Next Agent)

> 给接力 agent 的明确方向。要具体，不要含糊。

1. 首先做 X（参考文件 `path/to/file`）
2. 然后做 Y，注意 Z 的约束
3. 完成后运行 `npm test` 验证

### 特别注意
- ⚠️ 不要改动 `path/to/critical-file`，它已经稳定
- ⚠️ 环境变量 `API_KEY` 需要在 `.env` 中配置

## 6. 关键文件索引 (Key File Index)

| 文件/目录 | 用途 |
|----------|------|
| `src/api/` | API 路由定义 |
| `src/models/` | 数据模型 |
| `src/services/` | 业务逻辑层 |
| `tests/` | 测试文件 |
| `docs/api-spec.md` | API 规范文档 |
| `teamtask/tasks/{task-id}/` | 任务工作目录 |
```

---

## 使用规则

1. **必须写**: 当 step 配置了 `contextReset: true` 时，agent 完成工作后**必须**写 handoff
2. **写完即止**: 写完 handoff 后，你的任务就结束了。不要继续做下一步
3. **具体 > 抽象**: "实现了用户注册 API，使用 bcrypt 加密密码" 比 "完成了后端开发" 好
4. **路径要准确**: 所有文件路径必须是真实存在的，不要凭记忆写
5. **坑要说透**: 踩过的坑比成功的代码更有传承价值
6. **指令要可执行**: 下一步指令应该是 agent 拿到就能开始干的，不需要再猜

## Evaluator Handoff 扩展

当 agent 作为 evaluator 角色写 handoff 时，额外包含：

```markdown
## 评估结果 (Evaluation Result)

| 维度 | 分数 (1-10) | 说明 |
|------|------------|------|
| 代码质量 | 8 | 结构清晰，命名规范 |
| 功能完整性 | 6 | 缺少错误处理 |
| 测试覆盖 | 5 | 只有 happy path |
| 安全性 | 7 | 基本防护到位 |
| **综合** | **6.5** | — |

## 具体批评 (Specific Feedback)

### 必须修复 (Must Fix)
1. `src/api/users.ts:45` — 缺少输入验证，可能导致 SQL 注入
2. `src/services/auth.ts:23` — token 过期时间硬编码

### 建议改进 (Should Fix)
1. 建议将数据库查询抽象到 repository 层
2. 错误消息应该国际化

### 锦上添花 (Nice to Have)
1. 可以加入请求速率限制
2. API 响应可以支持分页
```
