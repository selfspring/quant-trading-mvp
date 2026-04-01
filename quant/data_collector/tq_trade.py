"""
天勤快期模拟盘交易接口
替代 CTP，使用 tqsdk + TqKq 进行交易
"""
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SYMBOL_TQ = "SHFE.au2606"


class TqTradeApi:
    """
    天勤快期模拟盘交易接口
    对外接口与 CTPTradeApi 保持一致

    关键设计：connect() 时就订阅持仓和账户对象并缓存，
    后续所有读取都用同一个对象，避免 is_changing 无法感知初始快照的问题。
    """

    def __init__(
        self,
        account_id: str,
        password: str,
        broker_id: str = "",
        td_address: str = "",
        app_id: str = "",
        auth_code: str = ""
    ):
        self.account_id = account_id
        self.password = password
        self.api = None
        self._connected = False
        self._logged_in = False
        self._order_ref = 0
        self._pos = None      # 缓存持仓对象，整个生命周期复用
        self._account = None  # 缓存账户对象

    def connect(self, address: str = "") -> bool:
        """连接天勤 API（快期模拟盘 TqKq）"""
        try:
            from tqsdk import TqApi, TqAuth, TqKq
            logger.info(f"使用天勤账号登录: {self.account_id}")
            self.api = TqApi(TqKq(), auth=TqAuth(self.account_id, self.password))
            # 立即订阅持仓和账户，缓存对象供后续复用
            self._pos = self.api.get_position(SYMBOL_TQ)
            self._account = self.api.get_account()
            self._connected = True
            logger.info("天勤 API 初始化成功")
            return True
        except Exception as e:
            logger.error(f"天勤 API 初始化失败: {e}")
            self._connected = False
            return False

    def login(self) -> bool:
        """登录（天勤在 connect 时已完成登录，此处等待初始快照就绪）"""
        if not self._connected or self.api is None:
            return False
        try:
            # 等待账户余额非零，表示初始快照已全部推送完成
            deadline = time.time() + 15
            while time.time() < deadline:
                self.api.wait_update(deadline=time.time() + 1)
                if self._account.balance > 0:
                    break

            long_vol = int(self._pos.pos_long) if hasattr(self._pos, 'pos_long') else 0
            short_vol = int(self._pos.pos_short) if hasattr(self._pos, 'pos_short') else 0
            self._logged_in = True
            logger.info(f"快期模拟盘连接成功，账户余额: {self._account.balance:.2f}")
            logger.info(f"当前持仓: 多={long_vol} 空={short_vol}")
            return True
        except Exception as e:
            logger.error(f"天勤登录验证失败: {e}")
            return False

    def get_position(self, symbol: str = None, direction: Optional[str] = None) -> Any:
        """
        获取持仓（直接读缓存对象，数据已在 login() 时就绪）
        direction: 'long'/'short'/None(返回全部)
        """
        if not self.api or self._pos is None:
            return 0 if direction else {'long': 0, 'short': 0, 'long_yd': 0, 'short_yd': 0, 'long_td': 0, 'short_td': 0}
        try:
            long_vol = int(self._pos.pos_long) if hasattr(self._pos, 'pos_long') else 0
            short_vol = int(self._pos.pos_short) if hasattr(self._pos, 'pos_short') else 0
            long_yd = int(self._pos.pos_long_his) if hasattr(self._pos, 'pos_long_his') else 0
            short_yd = int(self._pos.pos_short_his) if hasattr(self._pos, 'pos_short_his') else 0
            long_td = int(self._pos.pos_long_today) if hasattr(self._pos, 'pos_long_today') else 0
            short_td = int(self._pos.pos_short_today) if hasattr(self._pos, 'pos_short_today') else 0
            if direction == 'long':
                return long_vol
            elif direction == 'short':
                return short_vol
            else:
                return {
                    'long': long_vol, 'short': short_vol,
                    'long_yd': long_yd, 'short_yd': short_yd,
                    'long_td': long_td, 'short_td': short_td
                }
        except Exception as e:
            logger.error(f"持仓查询失败: {e}")
            return 0 if direction else {'long': 0, 'short': 0, 'long_yd': 0, 'short_yd': 0, 'long_td': 0, 'short_td': 0}

    def get_account(self) -> Dict:
        """获取账户资金（直接读缓存对象）"""
        if not self.api or self._account is None:
            return {'balance': 0, 'available': 0, 'frozen_margin': 0, 'commission': 0}
        try:
            return {
                'balance': float(self._account.balance),
                'available': float(self._account.available),
                'frozen_margin': float(self._account.frozen_margin),
                'commission': float(self._account.commission)
            }
        except Exception as e:
            logger.error(f"账户查询失败: {e}")
            return {'balance': 0, 'available': 0, 'frozen_margin': 0, 'commission': 0}

    def send_order(
        self,
        instrument_id: str,
        direction: str,
        offset: str,
        volume: int,
        price: float = 0,
        order_type: str = 'limit'
    ) -> Optional[str]:
        """
        发单，等待成交后再等持仓对象更新，确保 get_position() 能读到最新值
        direction: 'buy'/'sell'
        offset: 'open'/'close'
        price: 0 表示市价单（用当前价下限价单）
        返回 order_id
        """
        if not self.api:
            logger.error("API 未连接，无法发单")
            return None
        try:
            symbol_tq = f"SHFE.{instrument_id.lower()}"
            tq_direction = "BUY" if direction.lower() == 'buy' else "SELL"
            tq_offset = "OPEN" if offset.lower() == 'open' else "CLOSE"

            # 市价单：用当前最新价下限价单
            if price == 0:
                quote = self.api.get_quote(symbol_tq)
                deadline = time.time() + 5
                while time.time() < deadline:
                    self.api.wait_update(deadline=time.time() + 1)
                    if quote.last_price == quote.last_price:  # not nan
                        break
                price = quote.last_price
                logger.info(f"市价单使用当前价: {price}")

            logger.info(f"正在下单: {symbol_tq} {tq_direction} {tq_offset} {volume}手 价格={price:.2f}")
            order = self.api.insert_order(
                symbol=symbol_tq,
                direction=tq_direction,
                offset=tq_offset,
                limit_price=price,
                volume=volume
            )

            # 等待订单终结（FINISHED = 全成/撤单）
            deadline = time.time() + 15
            while order.status == "ALIVE" and time.time() < deadline:
                self.api.wait_update(deadline=deadline)

            order_id = order.order_id if hasattr(order, 'order_id') else str(self._order_ref)
            self._order_ref += 1

            if order.status == "FINISHED":
                filled = order.volume_orign - order.volume_left
                if filled > 0:
                    logger.info(f"订单成交 {filled}手 order_id={order_id}")
                    # 等待持仓对象更新（is_changing 在 wait_update 后检查缓存对象）
                    deadline = time.time() + 8
                    while time.time() < deadline:
                        self.api.wait_update(deadline=time.time() + 1)
                        if self.api.is_changing(self._pos):
                            logger.info("持仓已更新")
                            break
                else:
                    logger.warning(f"订单未成交（全撤）order_id={order_id}")
            else:
                logger.warning(f"订单超时，状态: {order.status} order_id={order_id}")

            return order_id
        except Exception as e:
            logger.error(f"发单失败: {e}", exc_info=True)
            return None

    def cancel_order(self, order_ref: str) -> bool:
        """撤单"""
        if not self.api:
            return False
        try:
            self.api.cancel_order(order_ref)
            logger.info(f"撤单成功: {order_ref}")
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.close()

    def close(self):
        """关闭 API"""
        if self.api:
            try:
                self.api.close()
                logger.info("天勤交易接口已关闭")
            except Exception:
                pass
            self.api = None
        self._pos = None
        self._account = None
        self._connected = False
        self._logged_in = False
