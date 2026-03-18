"""
数据库连接池管理模块
使用 psycopg2 连接池实现高性能数据库访问
"""
from psycopg2 import pool
from contextlib import contextmanager
from typing import Optional
import logging

from .config import config

logger = logging.getLogger(__name__)


class DatabasePool:
    """数据库连接池管理器"""
    
    _instance: Optional['DatabasePool'] = None
    _pool: Optional[pool.ThreadedConnectionPool] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化连接池"""
        if self._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """创建连接池"""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=config.database.pool_size,
                host=config.database.host,
                port=config.database.port,
                user=config.database.user,
                password=config.database.password.get_secret_value(),
                database=config.database.database,
                connect_timeout=config.database.pool_timeout
            )
            logger.info(
                f"database_pool_initialized host={config.database.host} "
                f"database={config.database.database} pool_size={config.database.pool_size}"
            )
        except Exception as e:
            logger.error(f"database_pool_init_failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        从连接池获取连接（上下文管理器）
        
        使用示例:
            with db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"database_connection_error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def close_all(self):
        """关闭所有连接"""
        if self._pool:
            self._pool.closeall()
            logger.info("database_pool_closed")


# 全局连接池实例
db_pool = DatabasePool()


@contextmanager
def get_db_connection():
    """
    便捷函数：获取数据库连接
    
    使用示例:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
    """
    with db_pool.get_connection() as conn:
        yield conn
