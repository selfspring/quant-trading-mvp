# 任务模板 (Task Template)

> 每次 spawn subagent 时照此模板填写任务说明。验证清单是强制项，不可省略。

---

## 模板结构

```
## 角色
你是 [角色名]。

## 任务
[具体任务描述，尽量拆成可验证的子项]

## 上下文
[从环境快查表按层级摘取，不要全部粘贴]
- 相关文件：[列出需要读取的文件]
- 已知情况：[当前状态、已完成的部分、注意事项]
- 已知坑：[从 Layer 2 摘取相关坑]

## 输入
[任务所需的具体输入数据或文件]

## 期望输出
[明确描述完成标准，越具体越好]

## ⚠️ 强制验证清单（完成前必须执行）
完成任务后，你必须：
0. **战前回忆**：写代码前必须调用 
ecall_memory 搜索相关模块的踩坑记录并严格遵守。
1. **读回**所有修改过的文件，确认内容与预期一致
2. **运行测试**（如果有相关测试文件）并报告结果
3. **逐条对照**上方「期望输出」检查是否达标
4. **文档更新**：如果修改了模块/架构/接口/配置，更新 docs/ 对应文档和 INDEX.md 状态
5. **经验入库**：遇到新报错或查明 Bug 后，调用 store_memory，摘要入 L0，解法入 L1，报错日志入 L2。
5. 在最终回复中用以下格式汇报验证结果：

验证结果：
- ✅ [已确认的项]
- ❌ [未完成或有问题的项]
- ⚠️ [需要注意的问题]
```

---

## QA Agent 模板

```
## 角色
你是 QA agent，负责独立验证开发 agent 的交付物。

## 任务
验证以下需求是否真正完成：
[粘贴原任务的「期望输出」]

## 上下文
- 相关文件：[列出需要检查的文件]
- 开发 agent 汇报的完成情况：[粘贴开发 agent 的验证结果]

## 验收标准（逐条检查，不可跳过）
1. [具体可验证的标准1]
2. [具体可验证的标准2]
3. [运行测试命令，贴出实际输出]

## ⚠️ QA 强制规则
- 不信任开发 agent 的自述，必须自己运行命令验证
- 每条验收标准必须有实际命令输出作为证据
- 发现问题必须明确描述：哪里不对、期望是什么、实际是什么
- 最终给出明确结论：PASS 或 FAIL（附问题列表）

验收结论：
- ✅ PASS：所有标准通过
- ❌ FAIL：[列出失败项]
```

---

## 工作日志模板

路径：`E:\quant-trading-mvp\docs\work-log\YYYY-MM-DD-HH-任务名.md`

```markdown
# 工作日志 - [任务名]

时间: YYYY-MM-DD HH:MM

## 已完成
- [步骤1]
- [步骤2]

## 发现的问题
- [问题1及处理方式]

## 遗留事项
- [ ] [未完成项1]
- [ ] [未完成项2]

## 下一步
[具体的下一步行动]
```

> 每次任务结束汇报时，主 agent 必须同时创建此文件。

- 每次 `sessions_spawn` 前，照此模板填写 `task` 字段
- 上下文字段：Layer 0 每次必有，Layer 1 按任务类型选一个，Layer 2 按涉及模块选
- 「期望输出」要具体到文件名、函数名、测试通过率等可验证的指标
- 验证清单不可删除，是判断任务真正完成的标准

---

## 示例

```
## 角色
你是后端开发 agent（backend）。

## 任务
修复 run_single_cycle.py 中日志文件为空的问题。

## 上下文
- OS: Windows 10, PowerShell / Python 3.12
- 项目路径: E:\quant-trading-mvp
- 相关文件：scripts/run_single_cycle.py
- 已知情况：logging.basicConfig() 第二次调用被忽略，导致日志不写入文件
- 已知坑：basicConfig 需要加 force=True 才能覆盖已有配置

## 输入
当前 run_single_cycle.py 文件内容

## 期望输出
- run_single_cycle.py 中所有 basicConfig 调用均加了 force=True
- 运行后日志文件有内容输出

## ⚠️ 强制验证清单（完成前必须执行）
完成任务后，你必须：
0. 调用 recall_memory 搜索 basicConfig 的历史坑
1. 读回修改后的 run_single_cycle.py，确认 force=True 已加入
2. 运行脚本 1 分钟，检查日志文件是否有内容
3. 逐条对照期望输出检查
4. 调用 store_memory 记录本次修复 logging 的经验
4. 汇报验证结果
```

---

## 环境快查表（渐进式披露）

> 按需摘取粘贴到「上下文」字段，不要全部粘贴。

### Layer 0 — 每次必有（极简基础）

```
OS: Windows 10, PowerShell
Python: 3.12
项目路径: E:\quant-trading-mvp
工作空间: C:\Users\chen\.openclaw\workspace
数据库: PostgreSQL localhost:5432 / quant_trading / user: postgres / password: @Cmx1454697261
```

### Layer 1 — 按任务类型选一个

**后端 / 数据库任务**
```
公共模块目录: quant/common/（写代码前必读 quant/common/README.md）
  - db.py: 数据库连接池
  - config.py: 配置读取（AppConfig）
  - tq_factory.py: 天勤 API 工厂
编码规范: docs/CODING_STANDARDS.md
环境变量: .env
```

**ML / 模型任务**
```
模型文件: models/lgbm_model.txt
特征工程: quant/signal_generator/feature_engineer.py（47个特征）
ML指南: docs/ML_MODULE_GUIDE.md
训练数据: kline_data 表, interval=30m, 10000根天勤真实数据
方向准确率: 64.01%，相关系数: 0.2109
置信度阈值: 0.65（低于此值不交易）
```

**交易执行任务**
```
交易接口: 天勤快期模拟盘（TqKq），账号 17340696348
天勤工厂: quant/common/tq_factory.py
交易模块: quant/data_collector/tq_trade.py
执行模块: quant/risk_executor/trade_executor.py
策略状态: data/strategy_state.json（持久化持仓/风控状态）
合约: SHFE.au2606（天勤格式，必须小写）
```

**数据采集任务**
```
天勤采集器: scripts/run_tq_collector.py（主采集，1m+30m K线）
CTP采集器: scripts/run_ctp_collector.py（备用，有断线重连）
备用数据源: quant/data_collector/backup_data_source.py（AkShare兜底）
K线表: kline_data（interval字段区分 1m/30m）
数据架构: docs/SOLUTION_TICK_TO_KLINE.md
```

**运维 / 脚本任务**
```
策略执行: scripts/run_single_cycle.py（每5分钟cron触发，执行后退出）
Windows定时任务: 6个（3采集+3策略，08:59/13:29/20:59启动采集）
日志目录: logs/
紧急平仓: scripts/emergency_close5.py
```

**文档任务**
```
文档索引: docs/INDEX.md（所有文档入口）
架构文档: docs/DATA_FLOW_ARCHITECTURE.md
编码规范: docs/CODING_STANDARDS.md
项目结构: docs/PROJECT_STRUCTURE.md
```

### Layer 2 — 已知坑（按涉及模块选）

**tqsdk 踩坑**
```
- 合约代码必须小写: SHFE.au2606，不能 .upper()
- TqApi 必须带 TqKq(): TqApi(TqKq(), auth=...) 才是真实模拟盘，否则每次重启状态清零
- is_changing 只在 wait_update 后数据变化时触发，不是初始加载信号
- 午休时段限价单超时是正常现象，脚本关闭时 tqsdk 自动撤单
- 不要用 PowerShell Set-Content 写含中文文件，用 write 工具
```

**CTP 踩坑**
```
- SubscribeMarketData 参数必须是 bytes: symbol.encode('utf-8')
- SimNow 订阅用大写 AU2606，发单用小写 au2606
- structlog 会阻止 OnRtnDepthMarketData 回调，只用标准 logging
- 午休 12:15-13:30 下单会被拒绝
- SimNow 平仓必须用限价单，市价单(IOC)会被立即撤单
- 昨仓 CloseYesterday(offset_flag='4')，今仓 CloseToday(offset_flag='3')，必须分开发单
```

**策略执行踩坑**
```
- logging.basicConfig() 必须加 force=True，否则第二次调用被忽略
- 发单后必须 time.sleep(5) 等待成交回报，否则脚本退出后持仓状态不一致
- PowerShell 不支持 &&，用 ; 连接命令
- Cron agent 任务说明必须明确写「你必须使用 exec 工具执行以下命令」，否则 agent 只理解不执行
- 特征数必须和训练时一致（47个），排除 open_oi/close_oi，统一用 open_interest
```
