@echo off
chcp 65001 >nul
echo ========================================
echo 宏观数据定时采集器
echo ========================================
echo.
echo 采集频率: 每天 09:00
echo 数据源: yfinance + AKShare + FRED
echo.
echo 按 Ctrl+C 停止
echo.

cd /d %~dp0..
python scripts\scheduled_macro_collector.py

pause
