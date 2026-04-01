"""
使用 vnpy_ctp 的 CTP 行情数据采集模块
"""
import threading
import time
from collections import defaultdict
from typing import Dict

import structlog
from vnpy_ctp.api import MdApi

from quant.common.config import config
from quant.common.tracer import generate_trace_id
from quant.data_collector.kline_aggregator import KlineAggregator

logger = structlog.get_logger()


class VnpyCtpMarketCollector(MdApi):
    """vnpy_ctp 行情采集器"""

    def __init__(self):
        # 创建临时目录用于存放 CTP 流文件
        import os
        temp_dir = "temp_ctp_md"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 初始化父类
        super().__init__()

        # 创建底层 API（vnpy_ctp 特有）
        self.createFtdcMdApi(temp_dir, False)

        self.config = config
        self.connected = False
        self.logged_in = False

        # K线聚合器
        self.kline_aggregator = KlineAggregator()

        # Tick 缓存
        self._tick_cache: Dict[str, list] = defaultdict(list)
        self._tick_cache_max = 12000
        self._tick_cache_lock = threading.Lock()

        logger.info("vnpy_ctp_market_collector_initialized")

    def onFrontConnected(self) -> None:
        """行情前置连接成功"""
        logger.info("ctp_front_connected")
        self.connected = True

        # 登录
        req = {
            "UserID": self.config.ctp.account_id,
            "Password": self.config.ctp.password.get_secret_value(),
            "BrokerID": self.config.ctp.broker_id
        }
        self.reqUserLogin(req, self.getReqID())

    def onFrontDisconnected(self, reason: int) -> None:
        """行情前置断开"""
        logger.error("ctp_front_disconnected", reason=reason)
        self.connected = False
        self.logged_in = False

    def onRspError(self, error: dict, reqid: int, last: bool) -> None:
        """通用错误响应"""
        logger.error("ctp_rsp_error", error_id=error.get("ErrorID"), error_msg=error.get("ErrorMsg"), reqid=reqid, last=last)
        # 继续保持运行，具体业务可根据 error_id 处理

    def onHeartBeatWarning(self, timeLapse: int) -> None:
        """心跳超时警告"""
        logger.warning("ctp_heartbeat_warning", time_lapse=timeLapse)

    def onRtnNotice(self, notice) -> None:
        """系统通知回调（可选）"""
        logger.info("ctp_notice", notice=notice)

    def onRtnErrorMsg(self, error) -> None:
        """错误信息回调（可选）"""
        logger.error("ctp_error_msg", error=error)


    def connect_and_login(self):
        """连接并登录"""
        trace_id = generate_trace_id()
        logger.info("connecting_to_ctp", trace_id=trace_id)

        # 注册前置
        self.registerFront(self.config.ctp.md_address)

        # 初始化
        self.init()

        # 等待登录成功
        max_wait = 15
        for i in range(max_wait):
            time.sleep(1)
            if self.logged_in:
                break

        if not self.logged_in:
            raise TimeoutError("CTP 登录超时")

        logger.info("ctp_connected", trace_id=trace_id)

        # 直接阻塞在 join()，保持回调运行（调试阶段）
        logger.info("entering join() to keep event loop")
        self.join()
        logger.info("join() exited")

        # 若需要后续代码，结束后返回
        return True

    def _run_join(self):
        """在后台线程中运行 join()"""
        try:
            logger.info("join_thread_running")
            self.join()
            logger.info("join_thread_exited")
        except Exception as e:
            logger.error("join_thread_error", error=str(e))

    def subscribe_symbol(self, symbol: str):
        """订阅合约"""
        trace_id = generate_trace_id()
        logger.info("subscribing", trace_id=trace_id, symbol=symbol)

        # vnpy_ctp 的订阅接口
        self.subscribeMarketData(symbol.upper())

        logger.info("subscribe_requested", symbol=symbol)

    def getReqID(self) -> int:
        """获取请求ID"""
        if not hasattr(self, '_reqid'):
            self._reqid = 0
        self._reqid += 1
        return self._reqid
