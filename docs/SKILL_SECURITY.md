# Skill 安全审查流程

## 安装前审查（必须）

### 1. 自动扫描
运行 `scripts/audit_skill.py <skill_dir>` 检查：

- [ ] 搜索 `os.environ`、`dotenv`、`getenv` — 是否读取环境变量/密码
- [ ] 搜索 `requests`、`urllib`、`http.client`、`curl`、`socket` — 是否有网络外发
- [ ] 搜索 `eval`、`exec`、`compile`、`__import__` — 是否有动态代码执行
- [ ] 搜索 `subprocess`、`os.system`、`Popen` — 是否执行系统命令
- [ ] 搜索 `open(`、`shutil`、`os.remove`、`os.rename` — 文件操作范围
- [ ] 搜索 `base64`、`encode`、`decode` — 是否有编码/混淆
- [ ] 检查是否修改 AGENTS.md、SOUL.md、openclaw.json 等核心文件

### 2. 人工审查
- [ ] 阅读 SKILL.md，确认功能描述与代码一致
- [ ] 检查所有 .py/.sh 文件，确认无隐藏逻辑
- [ ] 确认依赖列表合理（不引入可疑包）

### 3. 审查结论
- ✅ 安全 — 可以安装
- ⚠️ 有风险 — 需要修改后安装（列出需要删除/修改的部分）
- ❌ 危险 — 不安装

## 安装后控制

### 运行时限制
- Skill 只能被指定的 agent 使用（通过 allowAgents 控制）
- Skill 执行的命令记录到日志
- 定期审查 skill 的实际行为

## 审查记录

| Skill | 审查日期 | 审查人 | 结论 | 备注 |
|-------|----------|--------|------|------|
| (待填) | | | | |
