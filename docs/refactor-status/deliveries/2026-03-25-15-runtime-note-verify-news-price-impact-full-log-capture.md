# Runtime Note - verify_news_price_impact dry-run full log capture

## 摘要
本轮仅做 `scripts/verify_news_price_impact.py --dry-run --anchor-time effective_time` 的完整日志取证，不做业务修复。

## 已知执行坑（本次已遵守）
- Windows 10 / PowerShell 环境，不能使用 `&&`，命令需用 PowerShell 语法串接。
- 需显式设置 `PYTHONPATH=E:\quant-trading-mvp`，否则脚本可能因项目模块导入失败而无法进入目标路径。
- 为避免 PowerShell 管道 / Tee 缓冲干扰，本次最终采用 `Start-Process` + `-RedirectStandardOutput` / `-RedirectStandardError` 单独落盘。

## 读取的前序材料
- `scripts/verify_news_price_impact.py`
- `docs/refactor-status/deliveries/2026-03-24-21-backend-verification-layering-minimal-implementation.md`
- 目标 runtime note 文件名在当前仓库中未找到：
  - `docs/refactor-status/deliveries/2026-03-24-20-runtime-note-verify-news-price-impact-dry-run.md`

## 实际执行命令
### 1) 首次尝试（PowerShell Tee 方式）
```powershell
$ErrorActionPreference='Continue'; $env:PYTHONPATH='E:\quant-trading-mvp'; New-Item -ItemType Directory -Force -Path 'E:\quant-trading-mvp\logs' | Out-Null; $ts=Get-Date -Format 'yyyyMMdd-HHmmss'; $log='E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_'+$ts+'.log'; python 'E:\quant-trading-mvp\scripts\verify_news_price_impact.py' --dry-run --anchor-time effective_time *>&1 | Tee-Object -FilePath $log; $code=$LASTEXITCODE; Write-Output ('__LOG_PATH__='+$log); Write-Output ('__EXIT_CODE__='+$code); exit $code
```
结果：进程启动后长时间无输出，也未见日志文件成功落地，未作为最终证据使用。

### 2) 第二次尝试（cmd 重定向）
```powershell
$env:PYTHONPATH='E:\quant-trading-mvp'; New-Item -ItemType Directory -Force -Path 'E:\quant-trading-mvp\logs' | Out-Null; $ts=Get-Date -Format 'yyyyMMdd-HHmmss'; $log="E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_full_$ts.log"; cmd /c "python E:\quant-trading-mvp\scripts\verify_news_price_impact.py --dry-run --anchor-time effective_time 1>>\"$log\" 2>>&1"; $code=$LASTEXITCODE; Write-Output ('__LOG_PATH__='+$log); Write-Output ('__EXIT_CODE__='+$code)
```
结果：命令本身因 Windows 引号/重定向语法失败，退出码 `1`，不是目标 Python 脚本的业务退出码。

### 3) 最终取证执行（采用）
```powershell
$env:PYTHONPATH='E:\quant-trading-mvp'; New-Item -ItemType Directory -Force -Path 'E:\quant-trading-mvp\logs' | Out-Null; $ts=Get-Date -Format 'yyyyMMdd-HHmmss'; $stdout="E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_$ts.stdout.log"; $stderr="E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_$ts.stderr.log"; $combined="E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_$ts.combined.log"; $p=Start-Process -FilePath python -ArgumentList 'E:\quant-trading-mvp\scripts\verify_news_price_impact.py','--dry-run','--anchor-time','effective_time' -WorkingDirectory 'E:\quant-trading-mvp' -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait; $lines=@(); $lines += '===== STDOUT ====='; if (Test-Path $stdout) { $lines += Get-Content $stdout }; $lines += ''; $lines += '===== STDERR ====='; if (Test-Path $stderr) { $lines += Get-Content $stderr }; Set-Content -Path $combined -Value $lines; Write-Output ('__STDOUT__='+$stdout); Write-Output ('__STDERR__='+$stderr); Write-Output ('__COMBINED__='+$combined); Write-Output ('__EXIT_CODE__='+$p.ExitCode)
```

## 过程观察
- 确认 Python 进程真实启动：
  - `python.exe E:\quant-trading-mvp\scripts\verify_news_price_impact.py --dry-run --anchor-time effective_time`
- 观察窗口内（约 150 秒以上），stdout/stderr 文件始终为 0 字节。
- 在该观察窗口内，未打印：
  - `Processing ... news_analysis records...`
  - 任何 `[i/n] id=...` 进度行
  - 任何 traceback / exception 文本
- 因无自然退出且无新输出，为了拿到明确结束状态，对 Python 子进程执行了人工终止：
```powershell
Stop-Process -Id 7680 -Force
```

## 日志文件
- stdout: `E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_20260325-151713.stdout.log`
- stderr: `E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_20260325-151713.stderr.log`
- combined: `E:\quant-trading-mvp\logs\verify_news_price_impact_dry_run_effective_time_20260325-151713.combined.log`

## 退出码
- Python 进程自然退出码：**未取得**（因人工终止）
- 最终包装层记录：`__EXIT_CODE__=-1`
  - 该值对应本次取证包装进程在 Python 子进程被强制终止后的记录结果，不应误判为脚本业务逻辑自身的自然 exit code。

## 最后可见处理位置 / analysis_id
- **未能提取**。
- 原因：脚本在观察窗口内没有产生任何 stdout/stderr 输出，因此无法从日志中识别最后成功处理的记录、序号或 `analysis_id`。

## 最后一段异常输出 / 栈信息
- **未捕获到任何异常输出或 traceback**。
- 合并日志内容仅为：
```text
===== STDOUT =====

===== STDERR =====
```

## 对 backend 下一轮修复的直接价值
- 本轮已确认：当前 dry-run 现场不是“跑到某条记录后明确打印异常”的形态；在本次环境下更像是**脚本启动后在早期阶段阻塞/挂起，且未向 stdout/stderr 发出任何可见信号**。
- 若 backend 下一轮继续取因，建议优先检查：
  - 脚本启动早期的数据库连接 / 配置读取 / 首次 SQL 阻塞点
  - 是否存在无超时的数据库等待、锁等待或网络阻塞
  - 是否需要在 `get_connection()`、首个查询前后补更早期的启动日志
- 本 note 不包含业务修复，仅提供运行现场证据。
