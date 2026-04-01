"""
CTP 模拟盘交易测试脚本
测试买入和卖出一笔黄金期货 au2606
"""
import sys
import os
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openctp_ctp import tdapi, mdapi
from quant.common.config import config

# ============================================================
# 全局状态
# ============================================================
broker_id   = config.ctp.broker_id
account_id  = config.ctp.account_id
password    = config.ctp.password.get_secret_value()
td_address  = config.ctp.td_address
md_address  = config.ctp.md_address
app_id      = config.ctp.app_id
auth_code   = config.ctp.auth_code
symbol      = "au2606"

# 事件
ev_connected   = threading.Event()
ev_authed      = threading.Event()
ev_loggedin    = threading.Event()
ev_settled     = threading.Event()
ev_account     = threading.Event()
ev_order_buy   = threading.Event()
ev_trade_buy   = threading.Event()
ev_position    = threading.Event()
ev_order_sell  = threading.Event()
ev_trade_sell  = threading.Event()
ev_md_price    = threading.Event()

last_price     = None
buy_order_ref  = "1"
sell_order_ref = "2"
order_ref_seq  = [1]   # 用 list 方便在回调里修改


# ============================================================
# 行情 SPI（只用于获取最新价）
# ============================================================
class MdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api

    def OnFrontConnected(self):
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = broker_id
        req.UserID   = account_id
        req.Password = password
        self.api.ReqUserLogin(req, 1)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        self.api.SubscribeMarketData([symbol.encode()], 1)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        global last_price
        if last_price is None:
            last_price = pDepthMarketData.LastPrice
            print(f"   [行情] {symbol} 最新价: {last_price}")
            ev_md_price.set()


# ============================================================
# 交易 SPI
# ============================================================
class TdSpi(tdapi.CThostFtdcTraderSpi):
    def __init__(self, api):
        super().__init__()
        self.api        = api
        self.front_id   = 0
        self.session_id = 0

    def OnFrontConnected(self):
        print("   [OK] 交易前置连接成功，开始认证...")
        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID  = broker_id
        req.UserID    = account_id
        req.AppID     = app_id
        req.AuthCode  = auth_code
        self.api.ReqAuthenticate(req, 1)

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"   [ERROR] 认证失败: {pRspInfo.ErrorMsg}")
            return
        print("   [OK] 客户端认证成功，开始登录...")
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = broker_id
        req.UserID   = account_id
        req.Password = password
        self.api.ReqUserLogin(req, 2)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"   [ERROR] 登录失败: {pRspInfo.ErrorMsg}")
            return
        self.front_id   = pRspUserLogin.FrontID
        self.session_id = pRspUserLogin.SessionID
        print(f"   [OK] 登录成功! FrontID={self.front_id} SessionID={self.session_id}")
        ev_loggedin.set()

        # 确认结算单
        req = tdapi.CThostFtdcSettlementInfoConfirmField()
        req.BrokerID   = broker_id
        req.InvestorID = account_id
        self.api.ReqSettlementInfoConfirm(req, 3)

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        print("   [OK] 结算单确认完成")
        ev_settled.set()

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        if pTradingAccount:
            print(f"   [账户] 可用资金: {pTradingAccount.Available:,.2f} 元  | 权益: {pTradingAccount.Balance:,.2f} 元")
        if bIsLast:
            ev_account.set()

    def OnRtnOrder(self, pOrder):
        ref = pOrder.OrderRef.strip() if pOrder.OrderRef else ""
        status_map = {
            tdapi.THOST_FTDC_OST_NoTradeQueueing : "排队中",
            tdapi.THOST_FTDC_OST_AllTraded       : "全部成交",
            tdapi.THOST_FTDC_OST_Canceled        : "已撤单",
            tdapi.THOST_FTDC_OST_PartTradedQueueing: "部分成交",
        }
        status = status_map.get(pOrder.OrderStatus, f"未知状态({pOrder.OrderStatus})")
        direction = "买入" if pOrder.Direction == tdapi.THOST_FTDC_D_Buy else "卖出"
        print(f"   [委托] {direction} {pOrder.InstrumentID} {pOrder.VolumeTotalOriginal}手 "
              f"@{pOrder.LimitPrice} -> {status}")
        if pOrder.OrderStatus == tdapi.THOST_FTDC_OST_Canceled:
            print(f"   [撤单原因] StatusMsg={pOrder.StatusMsg}")
        if ref == buy_order_ref and pOrder.OrderStatus == tdapi.THOST_FTDC_OST_AllTraded:
            ev_order_buy.set()
        if ref == sell_order_ref and pOrder.OrderStatus == tdapi.THOST_FTDC_OST_AllTraded:
            ev_order_sell.set()

    def OnRtnTrade(self, pTrade):
        direction = "买入" if pTrade.Direction == tdapi.THOST_FTDC_D_Buy else "卖出"
        print(f"   [成交OK] {direction} {pTrade.InstrumentID} {pTrade.Volume}手 "
              f"@成交价 {pTrade.Price}")
        ref = pTrade.OrderRef.strip() if pTrade.OrderRef else ""
        if ref == buy_order_ref:
            ev_trade_buy.set()
        if ref == sell_order_ref:
            ev_trade_sell.set()

    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"   [ERROR] 下单失败: {pRspInfo.ErrorMsg}")

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        if pRspInfo:
            print(f"   [ERROR] 下单错误: {pRspInfo.ErrorMsg}")

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        if pInvestorPosition and pInvestorPosition.InstrumentID:
            direction = "多" if pInvestorPosition.PosiDirection == tdapi.THOST_FTDC_PD_Long else "空"
            print(f"   [持仓] {pInvestorPosition.InstrumentID} {direction}头 "
                  f"总持仓={pInvestorPosition.Position}手 "
                  f"今仓={pInvestorPosition.TodayPosition}手")
        if bIsLast:
            ev_position.set()


# ============================================================
# 主流程
# ============================================================
def main():
    global last_price, buy_order_ref, sell_order_ref

    print("=" * 60)
    print("CTP 模拟盘交易测试")
    print(f"账户: {account_id}  合约: {symbol}")
    print("=" * 60)

    # ----------------------------------------------------------
    # Step 1: 获取行情最新价
    # ----------------------------------------------------------
    print("\n1. 获取行情最新价...")
    md_api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi("md_trade_test")
    md_spi = MdSpi(md_api)
    md_api.RegisterSpi(md_spi)
    md_api.RegisterFront(md_address)
    md_api.Init()
    if not ev_md_price.wait(timeout=15):
        print("   [WARN] 获取行情超时，使用默认价格 680")
        last_price = 680.0
    md_api.Release()

    # ----------------------------------------------------------
    # Step 2: 连接交易服务器
    # ----------------------------------------------------------
    print("\n2. 连接交易服务器...")
    td_api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("td_trade_test")
    td_spi = TdSpi(td_api)
    td_api.RegisterSpi(td_spi)
    td_api.RegisterFront(td_address)
    td_api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
    td_api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
    td_api.Init()

    if not ev_loggedin.wait(timeout=15):
        print("   [ERROR] 登录超时，退出")
        td_api.Release()
        return

    if not ev_settled.wait(timeout=5):
        print("   [WARN] 结算单确认超时，继续...")

    # ----------------------------------------------------------
    # Step 3: 查询资金
    # ----------------------------------------------------------
    print("\n3. 查询账户资金...")
    time.sleep(1)
    req = tdapi.CThostFtdcQryTradingAccountField()
    req.BrokerID   = broker_id
    req.InvestorID = account_id
    td_api.ReqQryTradingAccount(req, 4)
    ev_account.wait(timeout=10)

    # ----------------------------------------------------------
    # Step 4: 买入开仓
    # ----------------------------------------------------------
    buy_price = round(last_price + 2, 1)   # 稍高于市价确保成交
    print(f"\n4. 买入开仓 1手 {symbol} 限价={buy_price}...")
    time.sleep(1)
    order = tdapi.CThostFtdcInputOrderField()
    order.BrokerID            = broker_id
    order.InvestorID          = account_id
    order.InstrumentID        = symbol
    order.ExchangeID          = "SHFE"
    order.OrderRef            = buy_order_ref
    order.UserID              = account_id
    order.OrderPriceType      = tdapi.THOST_FTDC_OPT_LimitPrice
    order.Direction           = tdapi.THOST_FTDC_D_Buy
    order.CombOffsetFlag      = tdapi.THOST_FTDC_OF_Open
    order.CombHedgeFlag       = tdapi.THOST_FTDC_HF_Speculation
    order.LimitPrice          = buy_price
    order.VolumeTotalOriginal = 1
    order.TimeCondition       = tdapi.THOST_FTDC_TC_GFD
    order.VolumeCondition     = tdapi.THOST_FTDC_VC_AV
    order.MinVolume           = 1
    order.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
    order.StopPrice           = 0
    order.ForceCloseReason    = tdapi.THOST_FTDC_FCC_NotForceClose
    order.IsAutoSuspend       = 0
    td_api.ReqOrderInsert(order, 5)

    print("   等待成交回报（最多30秒）...")
    if not ev_trade_buy.wait(timeout=30):
        print("   [WARN] 买入超时未成交，可能在排队")
    else:
        print("   [OK] 买入成交！")

    # ----------------------------------------------------------
    # Step 5: 查询持仓
    # ----------------------------------------------------------
    print("\n5. 查询当前持仓...")
    time.sleep(1)
    req2 = tdapi.CThostFtdcQryInvestorPositionField()
    req2.BrokerID   = broker_id
    req2.InvestorID = account_id
    td_api.ReqQryInvestorPosition(req2, 6)
    ev_position.wait(timeout=10)

    # ----------------------------------------------------------
    # Step 6: 卖出平仓（平今）
    # ----------------------------------------------------------
    if ev_trade_buy.is_set():
        sell_price = round(last_price - 2, 1)   # 稍低于市价确保成交
        print(f"\n6. 卖出平今仓 1手 {symbol} 限价={sell_price}...")
        time.sleep(1)
        order2 = tdapi.CThostFtdcInputOrderField()
        order2.BrokerID            = broker_id
        order2.InvestorID          = account_id
        order2.InstrumentID        = symbol
        order2.ExchangeID          = "SHFE"
        order2.OrderRef            = sell_order_ref
        order2.UserID              = account_id
        order2.OrderPriceType      = tdapi.THOST_FTDC_OPT_LimitPrice
        order2.Direction           = tdapi.THOST_FTDC_D_Sell
        order2.CombOffsetFlag      = tdapi.THOST_FTDC_OF_CloseToday   # 平今
        order2.CombHedgeFlag       = tdapi.THOST_FTDC_HF_Speculation
        order2.LimitPrice          = sell_price
        order2.VolumeTotalOriginal = 1
        order2.TimeCondition       = tdapi.THOST_FTDC_TC_GFD
        order2.VolumeCondition     = tdapi.THOST_FTDC_VC_AV
        order2.MinVolume           = 1
        order2.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
        order2.StopPrice           = 0
        order2.ForceCloseReason    = tdapi.THOST_FTDC_FCC_NotForceClose
        order2.IsAutoSuspend       = 0
        td_api.ReqOrderInsert(order2, 7)

        print("   等待平仓成交（最多30秒）...")
        if not ev_trade_sell.wait(timeout=30):
            print("   [WARN] 卖出超时未成交，可能在排队")
        else:
            print("   [OK] 卖出平仓成交！")
    else:
        print("\n6. 跳过卖出（买入未成交）")

    # ----------------------------------------------------------
    # 完成
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    if ev_trade_buy.is_set() and ev_trade_sell.is_set():
        print("[SUCCESS] 完整买卖测试通过！买入 + 平仓 均已成交")
    elif ev_trade_buy.is_set():
        print("[PARTIAL] 买入成交，但平仓未确认成交（可能仍在排队）")
    else:
        print("[WARN] 本次测试未完全成交，请检查交易时间或价格")
    print("=" * 60)

    time.sleep(2)
    td_api.Release()


if __name__ == "__main__":
    main()
