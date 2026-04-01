"""
数据采集模块
"""
from .ctp_market import get_recent_klines, run_collector, start_collector

__all__ = ['run_collector', 'start_collector', 'get_recent_klines']
