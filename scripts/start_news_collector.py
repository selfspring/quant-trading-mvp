"""
新闻数据定时采集启动脚本
每5分钟采集一次，数据源：金十数据、新浪财经、RSS、东方财富
"""
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from quant.data_collector.news_collector import NewsCollector

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/news_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

if __name__ == '__main__':
    collector = NewsCollector(request_interval=2.0)
    collector.run_loop(interval=300)  # 每5分钟
