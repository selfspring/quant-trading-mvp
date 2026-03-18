"""
数据采集模块
"""
from .ctp_market import run_collector, start_collector, get_recent_klines

__all__ = ['run_collector', 'start_collector', 'get_recent_klines']
