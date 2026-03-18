"""
交易执行器
将交易意图转换为 CTP 接口订单，并通过 td_api 真实发单
"""
from typing import Dict, Optional
import logging
from .signal_processor import TradeIntent

logger = logging.getLogger(__name__)

# CTP 常量（从 openctp-ctp-6.7.2 导入）
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Buy = tdapi.THOST_FTDC_D_Buy  # 买
    THOST_FTDC_D_Sell = tdapi.THOST_FTDC_D_Sell  # 卖
    THOST_FTDC_OF_Open = tdapi.THOST_FTDC_OF_Open  # 开仓
    THOST_FTDC_OF_Close = tdapi.THOST_FTDC_OF_Close  # 平仓
    THOST_FTDC_OF_CloseToday = tdapi.THOST_FTDC_OF_CloseToday  # 平今
    THOST_FTDC_OF_CloseYesterday = tdapi.THOST_FTDC_OF_CloseYesterday  # 平昨
except ImportError:
    # 如果 openctp-ctp 未安装，使用字符常量（用于测试）
    logger.warning("openctp-ctp 未安装，使用字符常量代替")
    THOST_FTDC_D_Buy = '0'
    THOST_FTDC_D_Sell = '1'
    THOST_FTDC_OF_Open = '0'
    THOST_FTDC_OF_Close = '1'
    THOST_FTDC_OF_CloseToday = '3'
    THOST_FTDC_OF_CloseYesterday = '4'


class Order:
    """订单对象"""
    
    def __init__(
        self,
        symbol: str,
        direction: str,  # CTP 方向常量
        offset_flag: str,  # CTP 开平标志
        volume: int,
        price: Optional[float] = None  # None 表示市价单
    ):
        """
        初始化订单

        Args:
            symbol: 合约代码
            direction: CTP 方向常量 (THOST_FTDC_D_Buy/Sell)
            offset_flag: CTP 开平标志 (THOST_FTDC_OF_Open/Close/...)
            volume: 交易量
            price: 价格（None 表示市价单）
        """
        self.symbol = symbol
        self.direction = direction
        self.offset_flag = offset_flag
        self.volume = volume
        self.price = price
        self.order_ref: Optional[str] = None  # 发单后由 CTP 返回
    
    def __repr__(self) -> str:
        price_str = f"{self.price:.2f}" if self.price else "市价"
        return f"Order(symbol={self.symbol}, direction={self.direction}, offset={self.offset_flag}, volume={self.volume}, price={price_str})"
    
    def to_ctp_params(self) -> Dict:
        """
        转换为 CTPTradeApi.send_order() 所需的参数字典

        Returns:
            与 CTPTradeApi.send_order() 签名匹配的关键字参数字典
        """
        return {
            'instrument_id': self.symbol,
            'direction': self.direction,
            'offset_flag': self.offset_flag,
            'volume': self.volume,
            'price': self.price if self.price else 0.0,
        }


class TradeExecutor:
    """交易执行器"""
    
    def __init__(self, config, td_api=None):
        """
        初始化交易执行器

        Args:
            config: 配置对象（需提供 config.strategy.symbol）
            td_api: CTPTradeApi 实例（可选）。
                    传入 None 时仅生成订单对象但不实际发单（dry-run 模式）。
        """
        self.symbol = config.strategy.symbol
        self.td_api = td_api
        self.last_order_time = None  # 上次发单时间
        self.min_order_interval = 300  # 最小发单间隔（秒），默认 5 分钟
        mode = "实盘发单" if td_api is not None else "dry-run（仅生成订单）"
        logger.info(f"TradeExecutor 初始化完成，交易品种: {self.symbol}，模式: {mode}")
        logger.info(f"订单冷却时间: {self.min_order_interval} 秒")
    
    def execute_order(self, intent: TradeIntent, price: Optional[float] = None) -> Optional[Order]:
        """
        执行订单：将 TradeIntent 转为 Order，并通过 td_api 发送到 CTP。

        Args:
            intent: 交易意图（经风控审核后的）
            price: 限价（None 表示市价单）

        Returns:
            Order 对象（包含 order_ref，如有实际发单）；如果在冷却期则返回 None
        """
        # 0. 检查订单冷却
        if self.last_order_time is not None:
            from datetime import datetime
            elapsed = (datetime.now() - self.last_order_time).total_seconds()
            if elapsed < self.min_order_interval:
                remaining = self.min_order_interval - elapsed
                logger.warning(f"⚠️ 订单冷却中，距离上次发单 {elapsed:.0f} 秒，还需等待 {remaining:.0f} 秒")
                return None
        
        # 1. 转换方向
        if intent.direction == 'buy':
            ctp_direction = THOST_FTDC_D_Buy
        elif intent.direction == 'sell':
            ctp_direction = THOST_FTDC_D_Sell
        else:
            raise ValueError(f"未知的交易方向: {intent.direction}")
        
        # 2. 转换开平标志
        if intent.action == 'open':
            ctp_offset = THOST_FTDC_OF_Open
        elif intent.action == 'close':
            ctp_offset = THOST_FTDC_OF_Close
        else:
            raise ValueError(f"未知的交易动作: {intent.action}")
        
        # 3. 创建订单对象
        order = Order(
            symbol=self.symbol,
            direction=ctp_direction,
            offset_flag=ctp_offset,
            volume=intent.volume,
            price=price
        )
        
        logger.info(f"生成订单: {order}")
        
        # 4. 通过 td_api 真实发单
        if self.td_api is not None:
            params = order.to_ctp_params()
            logger.info(f"发送报单到 CTP，参数: {params}")
            try:
                order_ref = self.td_api.send_order(**params)
                order.order_ref = order_ref
                logger.info(f"报单已提交，OrderRef={order_ref}")
                
                # 等待成交/撤单/拒绝回报（替代 time.sleep，有明确结果才更新 state）
                from datetime import datetime
                fill_result = self.td_api.wait_for_order(order_ref, timeout=10.0)
                order.fill_result = fill_result
                
                status = fill_result['status']
                if status == 'filled':
                    logger.info(f"✅ 成交确认: {fill_result['filled_volume']}手 @{fill_result['filled_price']}")
                    self.last_order_time = datetime.now()
                elif status == 'cancelled':
                    logger.warning(f"⚠️ 委托被撤单，未成交（Ref={order_ref}）")
                    return None  # 返回 None 表示未成交，调用方不应更新持仓 state
                elif status == 'rejected':
                    logger.error(f"❌ 委托被拒绝: ErrorID={fill_result['error_id']}")
                    return None
                elif status == 'timeout':
                    logger.warning(f"⚠️ 等待成交超时（Ref={order_ref}），委托可能仍在处理中，本轮不更新 state，下轮同步 CTP 持仓确认")
                    return None  # 超时也不更新 state，以 CTP 真实持仓为准
                
            except Exception as e:
                logger.error(f"报单失败: {e}")
                raise
        else:
            logger.warning("td_api 未配置，仅生成订单对象（dry-run）")
            logger.info(f"Dry-run CTP 参数: {order.to_ctp_params()}")
        
        return order
