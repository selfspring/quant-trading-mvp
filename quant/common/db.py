"""
数据库连接工厂函数
统一管理数据库连接的创建，避免硬编码密码和重复代码
"""
from contextlib import contextmanager
from typing import Any, Generator
import logging

logger = logging.getLogger(__name__)


def get_db_url(config: Any) -> str:
    """
    根据 config.database 构建 SQLAlchemy 连接 URL
    
    Args:
        config: 全局配置对象（需包含 config.database）
    
    Returns:
        SQLAlchemy 连接 URL 字符串
    """
    db = config.database
    password = db.password.get_secret_value() if hasattr(db.password, 'get_secret_value') else db.password
    from urllib.parse import quote_plus
    return f"postgresql+psycopg2://{db.user}:{quote_plus(password)}@{db.host}:{db.port}/{db.database}"


def get_db_dsn(config: Any) -> str:
    """
    根据 config.database 构建 psycopg2 DSN 字符串（用于非 pandas 场景）
    """
    db = config.database
    password = db.password.get_secret_value() if hasattr(db.password, 'get_secret_value') else db.password
    return f"host={db.host} port={db.port} dbname={db.database} user={db.user} password={password}"


@contextmanager
def db_engine(config: Any) -> Generator[Any, None, None]:
    """
    SQLAlchemy engine 上下文管理器（用于 pd.read_sql）
    
    用法：
        with db_engine(config) as engine:
            df = pd.read_sql(sql, engine, params=(...))
    """
    from sqlalchemy import create_engine
    engine = create_engine(get_db_url(config), pool_pre_ping=True)
    try:
        yield engine
    finally:
        try:
            engine.dispose()
        except Exception as e:
            logger.warning(f'数据库 engine 关闭异常（忽略）: {e}')


@contextmanager
def db_connection(config: Any) -> Generator[Any, None, None]:
    """
    psycopg2 原生连接上下文管理器（用于非 pandas 场景）
    
    用法：
        with db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute(sql)
    """
    import psycopg2
    conn = psycopg2.connect(get_db_dsn(config))
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.warning(f'数据库连接关闭异常（忽略）: {e}')
