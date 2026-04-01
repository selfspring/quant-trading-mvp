# Corrections Log

## 2026-03-19

### tqsdk — is_changing 初始快照问题
- **Correction:** 新建的 pos 对象，`is_changing(pos)` 不感知初始数据加载，只在 wait_update 后数据**变化**时触发
- **Context:** get_position() 发单后读持仓返回 0
- **Root cause:** 每次 get_position() 都 new 一个 pos 对象，is_changing 从未见过它
- **Fix:** login() 时缓存 pos/account 对象，整个生命周期复用；send_order() 后等 is_changing(self._pos)
- **Count:** 1

### tqsdk — TqKq vs TqSim
- **Correction:** `TqApi(auth=...)` 不带 TqKq 时走本地 TqSim，持仓状态每次重启清零
- **Context:** 持仓看起来总是 0，重启后丢失
- **Fix:** 必须用 `TqApi(TqKq(), auth=TqAuth(...))`
- **Count:** 1

### PowerShell 写中文文件
- **Correction:** PowerShell `Set-Content` / `-replace` 操作含中文的文件会破坏编码
- **Context:** 修改 .py 文件后中文注释变乱码
- **Fix:** 始终用 write/edit 工具操作文件，不用 PowerShell 字符串替换
- **Count:** 2 → 接近 PROMOTE

### 交易时段判断
- **Correction:** 12:00-13:30 午休时段，限价单挂上去没有对手方，超时后 tqsdk 关闭自动撤单
- **Context:** 测试开仓，post_position=0，误以为代码 bug
- **Fix:** 时段外的单子超时属正常现象，不是 bug；需在开盘时段（9:00-11:30, 13:30-15:00, 21:00-23:00）测试
- **Count:** 1
