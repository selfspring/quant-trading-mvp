# Runtime Note - verify_news_price_impact.py 标准运行方式

## 时间
- 2026-03-24 20:49 GMT+8

## 背景
在 QA 复核本轮“最小时间语义落地”时，直接执行：
- `python scripts/verify_news_price_impact.py --dry-run`
- `python scripts/verify_news_price_impact.py --dry-run --anchor-time published_time`

在当前会话环境中出现：
- `ModuleNotFoundError: No module named 'quant'`

该问题说明：脚本运行依赖项目标准启动方式，而不是在任意上下文中裸跑。

## 建议的标准运行方式
从项目根目录 `E:\quant-trading-mvp` 启动，并保证 Python 解释器能够解析项目根包路径。

推荐选项：

### 方案 A：在项目根目录设置 `PYTHONPATH`
PowerShell 示例：
```powershell
$env:PYTHONPATH = 'E:\quant-trading-mvp'
python scripts/verify_news_price_impact.py --dry-run
python scripts/verify_news_price_impact.py --dry-run --anchor-time published_time
```

### 方案 B：后续考虑改造成 `python -m ...` 启动
如果后续要提高可复现性，可将相关脚本逐步改造成模块化入口，避免对裸脚本路径运行过于敏感。

## 说明
- 本记录用于补齐 QA 的运行方式说明缺口。
- 这不是对本轮时间语义实现的否定，而是对运行环境要求的明确化。
