"""
宏观数据定时采集脚本
每5分钟运行一次，采集最新的宏观经济数据并存入数据库

使用 APScheduler 实现定时任务
"""
import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from apscheduler.schedulers.blocking import BlockingScheduler
from quant.data_collector.fundamental_collector import FundamentalCollector
from quant.common.config import config
from quant.common.db import db_connection
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/macro_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def collect_and_save():
    """采集宏观数据并保存到数据库"""
    logger.info("=" * 60)
    logger.info("开始定时采集宏观数据")
    logger.info("=" * 60)
    
    try:
        collector = FundamentalCollector()
        
        # 采集最近30天的数据（避免重复采集历史数据）
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 1. 美元指数
        logger.info("采集美元指数...")
        df_dollar = collector.fetch_dollar_index(start_date=start_date, end_date=end_date)
        
        # 2. 美债收益率
        logger.info("采集美债收益率...")
        df_treasury = collector.fetch_treasury_yield(start_date=start_date, end_date=end_date)
        
        # 3. 美联储利率（全量，因为是月度数据）
        logger.info("采集美联储利率...")
        df_fed = collector.fetch_fed_rate()
        
        # 4. 非农就业
        logger.info("采集非农就业数据...")
        df_nonfarm = collector.fetch_non_farm()
        
        # 5. CPI
        logger.info("采集CPI数据...")
        df_cpi = collector.fetch_cpi()
        
        # 保存到数据库
        logger.info("保存数据到数据库...")
        save_to_macro_data(df_dollar, df_treasury, df_fed, df_nonfarm, df_cpi)
        
        logger.info("=" * 60)
        logger.info("宏观数据采集完成")
        logger.info(f"  美元指数: {len(df_dollar)} 条")
        logger.info(f"  美债收益率: {len(df_treasury)} 条")
        logger.info(f"  美联储利率: {len(df_fed)} 条")
        logger.info(f"  非农就业: {len(df_nonfarm)} 条")
        logger.info(f"  CPI: {len(df_cpi)} 条")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"宏观数据采集失败: {e}", exc_info=True)


def save_to_macro_data(df_dollar, df_treasury, df_fed, df_nonfarm, df_cpi):
    """将数据保存到 macro_data 表"""
    with db_connection(config) as conn:
        try:
            cur = conn.cursor()
            
            # 合并所有数据源（按日期）
            import pandas as pd
            
            # 准备数据字典
            data_dict = {}
            
            # 美元指数
            if not df_dollar.empty:
                for _, row in df_dollar.iterrows():
                    date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    if date not in data_dict:
                        data_dict[date] = {}
                    data_dict[date]['dollar_index'] = row['dollar_index']
            
            # 美债收益率
            if not df_treasury.empty:
                for _, row in df_treasury.iterrows():
                    date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    if date not in data_dict:
                        data_dict[date] = {}
                    data_dict[date]['treasury_yield'] = row['treasury_yield_10y']
            
            # 美联储利率
            if not df_fed.empty:
                for _, row in df_fed.iterrows():
                    date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    if date not in data_dict:
                        data_dict[date] = {}
                    data_dict[date]['fed_rate'] = row['fed_rate']
            
            # 非农就业
            if not df_nonfarm.empty:
                for _, row in df_nonfarm.iterrows():
                    date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    if date not in data_dict:
                        data_dict[date] = {}
                    data_dict[date]['non_farm'] = row['non_farm']
            
            # CPI
            if not df_cpi.empty:
                for _, row in df_cpi.iterrows():
                    date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    if date not in data_dict:
                        data_dict[date] = {}
                    data_dict[date]['cpi'] = row['cpi']
            
            # 插入数据库
            count = 0
            for date, values in data_dict.items():
                # 构建动态 SQL
                indicators = []
                if 'dollar_index' in values:
                    indicators.append(('DOLLAR_INDEX', values['dollar_index'], 'index', 'yfinance'))
                if 'treasury_yield' in values:
                    indicators.append(('US10Y_YIELD', values['treasury_yield'], 'percent', 'US Treasury'))
                if 'fed_rate' in values:
                    indicators.append(('FED_FUNDS_RATE', values['fed_rate'], 'percent', 'Federal Reserve'))
                if 'non_farm' in values:
                    indicators.append(('NON_FARM_PAYROLL', values['non_farm'], 'thousands', 'BLS'))
                if 'cpi' in values:
                    indicators.append(('CPI_USA', values['cpi'], 'index', 'BLS'))
                
                for indicator, value, unit, source in indicators:
                    cur.execute("""
                        INSERT INTO macro_data (time, indicator, value, unit, source)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (time, indicator) DO UPDATE SET
                            value = EXCLUDED.value,
                            unit = EXCLUDED.unit,
                            source = EXCLUDED.source
                    """, (date, indicator, value, unit, source))
                    count += 1
            
            conn.commit()
            logger.info(f"成功写入/更新 {count} 条宏观数据记录")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存数据失败: {e}", exc_info=True)
            raise
        finally:
            cur.close()


def main():
    """主函数：启动定时任务"""
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    logger.info("宏观数据定时采集器启动")
    logger.info("采集频率: 每天 09:00")
    
    # 立即执行一次
    logger.info("执行首次采集...")
    collect_and_save()
    
    # 创建调度器
    scheduler = BlockingScheduler()
    
    # 添加定时任务：每天早上9点执行一次（宏观数据通常是日度/月度更新）
    scheduler.add_job(
        collect_and_save,
        'cron',
        hour=9,
        minute=0,
        id='macro_collector',
        name='宏观数据采集',
        replace_existing=True
    )
    
    logger.info("定时任务已启动（每天09:00执行），按 Ctrl+C 停止")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("定时采集器已停止")


if __name__ == '__main__':
    main()
