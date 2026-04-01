@echo off
set PYTHONIOENCODING=utf-8
cd /d E:\quant-trading-mvp
python scripts\auto_factor_discovery.py >> logs\auto_factor_discovery.log 2>&1
