# HOT Memory — 量化交易系统助理

## 技术规则（已确认）

### PowerShell
- 不支持 `&&`，用 `;` 连接命令
- **禁止**用 PowerShell `-replace` / `Set-Content` 操作含中文的文件 → 用 write/edit 工具
- 文件写入必须指定 UTF-8 编码，或用 write 工具代替

### tqsdk
- 区分 TqSim（本地，重启清零）和 TqKq（快期模拟盘，持久）
- 交易必须用：`TqApi(TqKq(), auth=TqAuth(account, password))`
- `is_changing(obj)` 只感知 wait_update 后的**变化**，不感知初始快照
- 缓存 pos/account 对象（login 时订阅），避免每次 get_position 新建对象
- 关闭 TqApi 时自动撤销所有未成交单

### 交易时段
- 午休：12:15-13:30（限价单无法成交）
- 夜盘：21:00-23:00（次日凌晨 2:30）
- 测试下单必须在开盘时段内

### CTP / SimNow
- SimNow 白天某些时段不推 Tick（已用天勤采集器替代）
- 合约代码：订阅用大写 AU2606，发单用小写 au2606

## 工作习惯
- 文件操作优先用 read/write/edit 工具，不用 exec+PowerShell 字符串处理
- 多次 edit 失败时直接 write 重写整个文件
- 子 agent 完成后检查结果再告知用户
- 记忆更新：先写文件，再回复用户

## 项目状态（2026-03-19）
- 行情：天勤采集器（1m+30m K线入库）✅
- 交易：天勤快期模拟盘 TqKq ✅
- 策略：run_single_cycle.py（每5分钟 cron，待验证）
- 账号：17340696348 / @Cmx1454697261
