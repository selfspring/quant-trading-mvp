"""
CTP 交易接口封装
将底层 openctp-ctp 的交易 API 封装为简洁的 send_order / get_current_position 接口
"""
import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# CTP 常量（安全导入）
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Buy = tdapi.THOST_FTDC_D_Buy
    THOST_FTDC_D_Sell = tdapi.THOST_FTDC_D_Sell
    THOST_FTDC_OF_Open = tdapi.THOST_FTDC_OF_Open
    THOST_FTDC_OF_Close = tdapi.THOST_FTDC_OF_Close
    THOST_FTDC_OF_CloseToday = tdapi.THOST_FTDC_OF_CloseToday
    THOST_FTDC_OF_CloseYesterday = tdapi.THOST_FTDC_OF_CloseYesterday
    THOST_FTDC_OPT_LimitPrice = tdapi.THOST_FTDC_OPT_LimitPrice
    THOST_FTDC_OPT_AnyPrice = tdapi.THOST_FTDC_OPT_AnyPrice
    THOST_FTDC_TC_GFD = tdapi.THOST_FTDC_TC_GFD
    THOST_FTDC_VC_AV = tdapi.THOST_FTDC_VC_AV
    THOST_FTDC_CC_Immediately = tdapi.THOST_FTDC_CC_Immediately
    THOST_FTDC_FCC_NotForceClose = tdapi.THOST_FTDC_FCC_NotForceClose
    THOST_FTDC_HF_Speculation = tdapi.THOST_FTDC_HF_Speculation
    THOST_FTDC_PD_Long = tdapi.THOST_FTDC_PD_Long
    THOST_FTDC_PD_Short = tdapi.THOST_FTDC_PD_Short
    _CTP_SPI_BASE: Any = tdapi.CThostFtdcTraderSpi
    HAS_CTP = True
except ImportError:
    logger.warning("openctp-ctp 未安装，CTPTradeApi 将不可用")
    _CTP_SPI_BASE = object
    HAS_CTP = False


class TradeSpi(_CTP_SPI_BASE):
    """CTP 交易回调"""

    def __init__(self, api: Any, trade_api: 'CTPTradeApi') -> None:
        if HAS_CTP:
            super().__init__()
        self.api = api
        self.trade_api = trade_api
        self.front_id: int = 0
        self.session_id: int = 0

    # ---------- 连接 / 认证 / 登录 ----------

    def OnFrontConnected(self):
        logger.info("交易前置连接成功，开始客户端认证...")
        self.trade_api._ev_connected.set()
        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID = self.trade_api.broker_id
        req.UserID = self.trade_api.account_id
        req.AppID = self.trade_api.app_id
        req.AuthCode = self.trade_api.auth_code
        self.api.ReqAuthenticate(req, 1)

    def OnFrontDisconnected(self, nReason):
        logger.warning(f"交易前置断开，原因代码: {nReason}")
        self.trade_api._connected = False

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            logger.error(f"客户端认证失败: ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")
            self.trade_api._ev_login.set()  # 解除等待
            return
        logger.info("客户端认证成功，开始登录...")
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.trade_api.broker_id
        req.UserID = self.trade_api.account_id
        req.Password = self.trade_api.password
        self.api.ReqUserLogin(req, 2)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            logger.error(f"交易登录失败: ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")
            self.trade_api._ev_login.set()
            return
        self.front_id = pRspUserLogin.FrontID
        self.session_id = pRspUserLogin.SessionID
        logger.info(f"交易登录成功 FrontID={self.front_id} SessionID={self.session_id}")
        self.trade_api._connected = True
        self.trade_api._ev_login.set()

        # 确认结算单
        req = tdapi.CThostFtdcSettlementInfoConfirmField()
        req.BrokerID = self.trade_api.broker_id
        req.InvestorID = self.trade_api.account_id
        self.api.ReqSettlementInfoConfirm(req, 3)

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        logger.info("结算单确认完成")
        self.trade_api._ev_settled.set()

    # ---------- 报单回报 ----------

    def OnRtnOrder(self, pOrder):
        ref = pOrder.OrderRef.strip() if pOrder.OrderRef else ""
        direction = "买" if pOrder.Direction == THOST_FTDC_D_Buy else "卖"
        logger.info(
            f"[委托回报] {direction} {pOrder.InstrumentID} "
            f"{pOrder.VolumeTotalOriginal}手 @{pOrder.LimitPrice} "
            f"状态={pOrder.OrderStatus} Ref={ref}"
        )
        # 通知等待者
        cb = self.trade_api._order_callbacks.get(ref)
        if cb:
            cb('order', pOrder)

    def OnRtnTrade(self, pTrade):
        ref = pTrade.OrderRef.strip() if pTrade.OrderRef else ""
        direction = "买" if pTrade.Direction == THOST_FTDC_D_Buy else "卖"
        logger.info(
            f"[成交回报] {direction} {pTrade.InstrumentID} "
            f"{pTrade.Volume}手 @{pTrade.Price} Ref={ref}"
        )
        cb = self.trade_api._order_callbacks.get(ref)
        if cb:
            cb('trade', pTrade)

    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            logger.error(f"报单被拒: ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")
            ref = pInputOrder.OrderRef.strip() if pInputOrder and pInputOrder.OrderRef else ""
            cb = self.trade_api._order_callbacks.get(ref)
            if cb:
                cb('rejected', pRspInfo)

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        if pRspInfo:
            logger.error(f"报单错误: ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")

    # ---------- 持仓查询 ----------

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        if pInvestorPosition and pInvestorPosition.InstrumentID:
            self.trade_api._position_buffer.append(pInvestorPosition)
        if bIsLast:
            self.trade_api._ev_position.set()


class CTPTradeApi:
    """
    CTP 交易接口封装

    提供两个核心方法:
        send_order(instrument_id, direction, offset_flag, volume, price, exchange_id)
        get_current_position() -> dict
    """

    def __init__(
        self,
        broker_id: str,
        account_id: str,
        password: str,
        td_address: str,
        app_id: str = "simnow_client_test",
        auth_code: str = "0000000000000000",
    ):
        if not HAS_CTP:
            raise RuntimeError("openctp-ctp 未安装，无法创建 CTPTradeApi")

        self.broker_id = broker_id
        self.account_id = account_id
        self.password = password
        self.td_address = td_address
        self.app_id = app_id
        self.auth_code = auth_code

        # 内部状态
        self._api: Any = None
        self._spi: Any = None
        self._connected = False
        self._order_ref_seq = 0
        self._order_ref_lock = threading.Lock()

        # 同步事件
        self._ev_connected = threading.Event()
        self._ev_login = threading.Event()
        self._ev_settled = threading.Event()
        self._ev_position = threading.Event()

        # 回调注册 {order_ref: callback}
        self._order_callbacks: Dict[str, Callable] = {}

        # 持仓查询缓冲
        self._position_buffer: list[Any] = []

    # =========================================================
    # 连接管理
    # =========================================================

    def connect(self, timeout: int = 15) -> bool:
        """
        连接 CTP 交易前置，完成认证、登录、结算确认。

        Returns:
            是否连接成功
        """
        logger.info(f"正在连接 CTP 交易前置 {self.td_address} ...")
        self._api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("td_executor_")
        self._spi = TradeSpi(self._api, self)
        self._api.RegisterSpi(self._spi)
        self._api.RegisterFront(self.td_address)
        self._api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
        self._api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
        self._api.Init()

        if not self._ev_login.wait(timeout=timeout):
            logger.error("CTP 交易登录超时")
            return False

        if not self._connected:
            logger.error("CTP 交易登录失败")
            return False

        # 等结算单确认（非关键，可短暂等待）
        self._ev_settled.wait(timeout=5)
        logger.info("CTP 交易接口就绪")
        return True

    def disconnect(self):
        """断开连接"""
        if self._api:
            try:
                self._api.Release()
            except Exception as e:
                logger.warning(f"释放交易 API 时异常: {e}")
            self._api = None
        self._connected = False
        logger.info("CTP 交易接口已断开")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # =========================================================
    # 报单
    # =========================================================

    def _next_order_ref(self) -> str:
        with self._order_ref_lock:
            self._order_ref_seq += 1
            return str(self._order_ref_seq)

    def send_order(
        self,
        instrument_id: str,
        direction: str,
        offset_flag: str,
        volume: int,
        price: float = 0.0,
        exchange_id: str = "SHFE",
        order_price_type: Optional[str] = None,
    ) -> str:
        """
        发送报单到 CTP。

        Args:
            instrument_id: 合约代码，如 "au2606"
            direction: CTP 方向常量 (THOST_FTDC_D_Buy / THOST_FTDC_D_Sell)
            offset_flag: CTP 开平标志 (THOST_FTDC_OF_Open / Close / CloseToday / ...)
            volume: 手数（正整数）
            price: 限价价格，0 表示市价
            exchange_id: 交易所代码，默认 "SHFE"（上期所/黄金）
            order_price_type: 报单价格类型，None 时自动根据 price 判断

        Returns:
            order_ref: 本次报单的引用号，可用于追踪回报

        Raises:
            RuntimeError: 未连接时调用
        """
        if not self._connected:
            raise RuntimeError("CTP 交易接口未连接，请先调用 connect()")

        order_ref = self._next_order_ref()

        # 自动判断报单价格类型
        if order_price_type is None:
            if price and price > 0:
                opt = THOST_FTDC_OPT_LimitPrice
            else:
                opt = THOST_FTDC_OPT_AnyPrice
        else:
            opt = order_price_type

        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = self.broker_id
        req.InvestorID = self.account_id
        req.InstrumentID = instrument_id
        req.ExchangeID = exchange_id
        req.OrderRef = order_ref
        req.UserID = self.account_id
        req.OrderPriceType = opt
        req.Direction = direction
        req.CombOffsetFlag = offset_flag
        req.CombHedgeFlag = THOST_FTDC_HF_Speculation
        req.LimitPrice = float(price) if price else 0.0
        req.VolumeTotalOriginal = int(volume)
        req.TimeCondition = THOST_FTDC_TC_GFD
        req.VolumeCondition = THOST_FTDC_VC_AV
        req.MinVolume = 1
        req.ContingentCondition = THOST_FTDC_CC_Immediately
        req.StopPrice = 0
        req.ForceCloseReason = THOST_FTDC_FCC_NotForceClose
        req.IsAutoSuspend = 0

        dir_str = "买" if direction == THOST_FTDC_D_Buy else "卖"
        offset_str = {
            THOST_FTDC_OF_Open: "开仓",
            THOST_FTDC_OF_Close: "平仓",
            THOST_FTDC_OF_CloseToday: "平今",
            THOST_FTDC_OF_CloseYesterday: "平昨",
        }.get(offset_flag, offset_flag)
        logger.info(
            f"[发单] {dir_str}{offset_str} {instrument_id} {volume}手 "
            f"@{'市价' if not price else price} Ref={order_ref}"
        )

        ret = self._api.ReqOrderInsert(req, int(order_ref))
        if ret != 0:
            logger.error(f"ReqOrderInsert 返回错误码: {ret}")

        return order_ref

    def wait_for_order(self, order_ref: str, timeout: float = 10.0) -> dict:
        """
        等待指定 order_ref 的成交/撤单/拒绝回报。

        Returns:
            {
                'status': 'filled' | 'cancelled' | 'rejected' | 'timeout',
                'filled_volume': int,   # 成交手数
                'filled_price': float,  # 成交价（OnRtnTrade）
                'error_id': int,        # 拒绝时的错误码
            }
        """
        import threading
        result = {'status': 'timeout', 'filled_volume': 0, 'filled_price': 0.0, 'error_id': 0}
        ev = threading.Event()

        # CTP 委托状态常量
        ORDER_STATUS_FILLED = '0'       # 全部成交
        ORDER_STATUS_CANCELLED = '5'    # 已撤单

        def callback(event_type, data):
            if event_type == 'trade':
                result['filled_volume'] += data.Volume
                result['filled_price'] = data.Price
                result['status'] = 'filled'
                ev.set()
            elif event_type == 'order':
                status = data.OrderStatus
                if status == ORDER_STATUS_CANCELLED:
                    if result['filled_volume'] == 0:
                        result['status'] = 'cancelled'
                    ev.set()
                elif status == ORDER_STATUS_FILLED:
                    result['status'] = 'filled'
                    ev.set()
            elif event_type == 'rejected':
                result['status'] = 'rejected'
                result['error_id'] = data.ErrorID
                ev.set()

        self._order_callbacks[order_ref] = callback
        try:
            ev.wait(timeout=timeout)
        finally:
            self._order_callbacks.pop(order_ref, None)

        logger.info(f"[wait_for_order] Ref={order_ref} 结果: {result}")
        return result

    # =========================================================
    # 持仓查询
    # =========================================================

    def get_current_position(self, instrument_id: str = "") -> Dict[str, int]:
        """
        查询当前持仓。

        Args:
            instrument_id: 可选，指定合约（空字符串查全部）

        Returns:
            {"long_volume": int, "short_volume": int}
        """
        if not self._connected:
            raise RuntimeError("CTP 交易接口未连接")

        self._position_buffer = []
        self._ev_position.clear()

        req = tdapi.CThostFtdcQryInvestorPositionField()
        req.BrokerID = self.broker_id
        req.InvestorID = self.account_id
        if instrument_id:
            req.InstrumentID = instrument_id

        self._api.ReqQryInvestorPosition(req, 99)

        if not self._ev_position.wait(timeout=10):
            logger.error("查询持仓超时")
            return {"long_volume": 0, "short_volume": 0}

        long_vol = 0
        short_vol = 0
        for pos in self._position_buffer:
            if pos.PosiDirection == THOST_FTDC_PD_Long:
                long_vol += pos.Position
            elif pos.PosiDirection == THOST_FTDC_PD_Short:
                short_vol += pos.Position

        logger.info(f"当前持仓: 多头={long_vol}手, 空头={short_vol}手")
        return {"long_volume": long_vol, "short_volume": short_vol}
