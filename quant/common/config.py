"""
配置管理模块
使用 pydantic-settings 实现类型安全的配置加载
"""
import os
from typing import Any, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, ge=1, le=65535, description="数据库端口")
    database: str = Field(default="quant_trading", description="数据库名称")
    user: str = Field(default="postgres", description="数据库用户")
    password: SecretStr = Field(description="数据库密码")

    # 连接池配置（多进程场景）
    pool_size: int = Field(default=5, ge=1, le=100, description="连接池大小（每个进程）")
    max_overflow: int = Field(default=10, ge=0, le=100, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, ge=1, description="连接超时（秒）")
    pool_recycle: int = Field(default=3600, ge=1, description="连接回收时间（秒）")

    # 注释：5个进程 × (5 pool + 10 overflow) = 最多 75 个连接
    # PostgreSQL 默认 max_connections=100，留有余量

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """验证密码不能为空"""
        if not v.get_secret_value():
            raise ValueError("数据库密码不能为空，请设置环境变量 DB_PASSWORD")
        return v

    class Config:
        env_prefix = "DB_"


class RedisConfig(BaseSettings):
    """Redis 配置"""
    host: str = Field(default="localhost", description="Redis 主机")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis 端口")
    db: int = Field(default=0, ge=0, le=15, description="Redis 数据库编号")
    password: Optional[SecretStr] = Field(default=None, description="Redis 密码")

    # 连接池配置
    max_connections: int = Field(default=50, ge=1, description="最大连接数")
    socket_timeout: int = Field(default=5, ge=1, description="Socket 超时（秒）")

    class Config:
        env_prefix = "REDIS_"


class ChromaConfig(BaseSettings):
    """Chroma 向量数据库配置"""
    host: str = Field(default="localhost", description="Chroma 主机")
    port: int = Field(default=8000, description="Chroma 端口")
    collection_name: str = Field(default="news_embeddings", description="集合名称")


class CTPConfig(BaseSettings):
    """CTP 交易接口配置"""
    broker_id: str = Field(default="9999", description="券商代码")
    account_id: str = Field(description="账户ID")
    password: SecretStr = Field(description="密码")
    md_address: str = Field(default="tcp://182.254.243.31:30011", description="行情服务器（SimNow 仿真环境，已测试可用）")
    td_address: str = Field(default="tcp://182.254.243.31:30001", description="交易服务器（SimNow 仿真环境，已测试可用）")
    app_id: str = Field(default="simnow_client_test", description="应用ID")
    auth_code: str = Field(default="0000000000000000", description="授权码")

    @classmethod
    def simnow_7x24(cls, account_id: str, password: str) -> 'CTPConfig':
        """SimNow 仿真环境配置（使用第一组服务器，已测试可用）"""
        return cls(
            broker_id="9999",
            account_id=account_id,
            password=SecretStr(password),
            md_address="tcp://182.254.243.31:30011",
            td_address="tcp://182.254.243.31:30001",
            app_id="simnow_client_test",
            auth_code="0000000000000000"
        )

    @classmethod
    def simnow_trading(cls, account_id: str, password: str, group: int = 1) -> 'CTPConfig':
        """SimNow 仿真环境配置（与实盘同步）

        Args:
            account_id: 账户ID
            password: 密码
            group: 服务器组号 (1, 2, 3)，默认第一组（已测试可用）
        """
        md_ports = {1: 30011, 2: 30012, 3: 30013}
        td_ports = {1: 30001, 2: 30002, 3: 30003}

        md_port = md_ports.get(group, 30011)
        td_port = td_ports.get(group, 30001)

        return cls(
            broker_id="9999",
            account_id=account_id,
            password=SecretStr(password),
            md_address=f"tcp://182.254.243.31:{md_port}",
            td_address=f"tcp://182.254.243.31:{td_port}",
            app_id="simnow_client_test",
            auth_code="0000000000000000"
        )

    @classmethod
    def openctp_7x24(cls, account_id: str, password: str) -> 'CTPConfig':
        """OpenCTP 7x24 环境配置（当前不可用）"""
        return cls(
            broker_id="9999",
            account_id=account_id,
            password=SecretStr(password),
            md_address="tcp://trading.openctp.cn:30011",
            td_address="tcp://trading.openctp.cn:30001",
            app_id="simnow_client_test",
            auth_code="0000000000000000"
        )

    @field_validator('account_id', 'password')
    @classmethod
    def validate_credentials(cls, v: Any) -> Any:
        """验证账户信息不能为空"""
        if isinstance(v, SecretStr):
            if not v.get_secret_value():
                raise ValueError("CTP 密码不能为空，请设置环境变量 CTP_PASSWORD")
        elif not v:
            raise ValueError("CTP 账户ID不能为空，请设置环境变量 CTP_ACCOUNT_ID")
        return v

    class Config:
        env_prefix = "CTP_"


class ClaudeConfig(BaseSettings):
    """Claude API 配置"""
    api_key: SecretStr = Field(description="API Key")
    model: str = Field(default="claude-opus-4-6", description="模型名称")
    base_url: str = Field(default="https://api.anthropic.com", description="API 地址")
    timeout: int = Field(default=60, ge=1, le=120, description="超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: SecretStr) -> SecretStr:
        """验证 API Key 不能为空"""
        if not v.get_secret_value():
            raise ValueError("Claude API Key 不能为空，请设置环境变量 CLAUDE_API_KEY")
        return v

    class Config:
        env_prefix = "CLAUDE_"


class StrategyConfig(BaseSettings):
    """策略配置"""
    symbol: str = Field(default="au2606", description="交易品种")
    interval: str = Field(default="30m", description="K线周期")

    # 信号融合权重（固定权重，后续可改为动态）
    signal_weights_technical: float = Field(default=0.3, description="技术指标权重")
    signal_weights_ml: float = Field(default=0.5, description="ML模型权重")
    signal_weights_news: float = Field(default=0.2, description="新闻权重")

    # 风控参数
    max_position_ratio: float = Field(default=0.7, description="最大仓位比例")
    max_weekly_drawdown: float = Field(default=0.25, description="最大周回撤")
    consecutive_loss_limit: int = Field(default=3, description="连败熔断次数")
    circuit_break_minutes: int = Field(default=60, description="连败熔断暂停时长（分钟）")
    atr_multiplier: float = Field(default=2.0, description="ATR波动率过滤倍数")

    # 报单参数
    tick_size: float = Field(default=0.02, description="最小变动价位（黄金期货 0.02 元）")
    slippage_ticks: int = Field(default=5, description="限价单滑点跳数，买入价加、卖出价减")


class LoggingConfig(BaseSettings):
    """日志配置"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    file: str = Field(default="logs/quant_trading.log", description="日志文件路径")
    max_bytes: int = Field(default=10485760, description="单个日志文件最大大小（10MB）")
    backup_count: int = Field(default=5, description="日志文件备份数量")


class MLConfig(BaseSettings):
    """ML 模型配置"""
    model_path: str = Field(default="E:/quant-trading-mvp/models/lgbm_model.txt", description="模型文件路径")
    feature_window: int = Field(default=60, ge=10, le=240, description="特征窗口（分钟）")
    prediction_horizon: int = Field(default=60, ge=30, le=240, description="预测时长（分钟）")
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0, description="置信度阈值")

    # LightGBM 参数
    learning_rate: float = Field(default=0.05, ge=0.001, le=0.3, description="学习率")
    num_leaves: int = Field(default=31, ge=10, le=100, description="叶子节点数")
    max_depth: int = Field(default=6, ge=3, le=15, description="最大深度")
    min_data_in_leaf: int = Field(default=20, ge=10, le=100, description="叶子最小样本数")

    class Config:
        env_prefix = "ML_"


class AppConfig(BaseSettings):
    """主配置类"""
    # 环境
    env: Literal["dev", "test", "prod"] = Field(default="dev", description="运行环境")

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)  # type: ignore[arg-type]
    redis: RedisConfig = Field(default_factory=RedisConfig)
    chroma: ChromaConfig = Field(default_factory=ChromaConfig)
    ctp: CTPConfig = Field(default_factory=CTPConfig)  # type: ignore[arg-type]
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)  # type: ignore[arg-type]
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

    def validate_production(self) -> None:
        """
        生产环境安全检查
        确保生产环境必须使用 .env 文件，禁止使用默认密码
        """
        if self.env != "prod":
            return

        # 检查 .env 文件是否存在
        if not os.path.exists(".env"):
            raise ValueError(
                "生产环境必须提供 .env 文件！"
                "请创建 .env 文件并配置所有敏感信息。"
            )

        # 检查数据库密码是否为默认值
        db_password = self.database.password.get_secret_value()
        if db_password in ["postgres", "password", "123456", ""]:
            raise ValueError(
                "生产环境禁止使用默认数据库密码！"
                "请在 .env 文件中设置强密码：DB_PASSWORD=<strong_password>"
            )

        # 检查 CTP 密码是否为默认值
        ctp_password = self.ctp.password.get_secret_value()
        if ctp_password in ["123456", "password", ""]:
            raise ValueError(
                "生产环境禁止使用默认 CTP 密码！"
                "请在 .env 文件中设置真实密码：CTP_PASSWORD=<real_password>"
            )

        # 检查 Claude API Key 是否为测试值
        claude_key = self.claude.api_key.get_secret_value()
        if claude_key.startswith("sk-test-") or claude_key == "":
            raise ValueError(
                "生产环境禁止使用测试 API Key！"
                "请在 .env 文件中设置生产 API Key：CLAUDE_API_KEY=<prod_key>"
            )

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> 'AppConfig':
        """加载配置"""
        # 默认使用 .env 文件
        if env_file is None:
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')

        if os.path.exists(env_file):
            config_instance = cls(_env_file=env_file)  # type: ignore[call-arg]
        else:
            config_instance = cls()

        # 生产环境强制校验
        config_instance.validate_production()

        return config_instance


# 全局配置实例
config: AppConfig = AppConfig.load()
