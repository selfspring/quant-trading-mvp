"""
紧急平仓 - 分别平今仓和昨仓
"""
import sys, os, time, threading
sys.path.insert(0, 'E:\\quant-trading-mvp')

from quant.common.config import config
from openctp_ctp import tdapi

class CloseSpi(tdapi.CThostFtdcTraderSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.ev_login = threading.Event()
        self.ev_position = threading.Event()
        self.positions = []
        self.broker_id = config.ctp.broker_id
        self.account_id = config.ctp.account_id
        self.order_ref = 0
        self.callbacks = []

    def next_ref(self):
        self.order_ref += 1
        return str(self.order_ref)

    def OnFrontConnected(self):
        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID = self.broker_id
        req.UserID = self.account_id
        req.AppID = config.ctp.app_id
        req.AuthCode = config.ctp.auth_code
        self.api.ReqAuthenticate(req, 1)

    def OnRspAuthenticate(self, p, info, rid, last):
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.broker_id
        req.UserID = self.account_id
        req.Password = config.ctp.password.get_secret_value()
        self.api.ReqUserLogin(req, 2)

    def OnRspUserLogin(self, p, info, rid, last):
        self.front_id = p.FrontID
        self.session_id = p.SessionID
        print(f"Login OK")
        req = tdapi.CThostFtdcSettlementInfoConfirmField()
        req.BrokerID = self.broker_id
        req.InvestorID = self.account_id
        self.api.ReqSettlementInfoConfirm(req, 3)

    def OnRspSettlementInfoConfirm(self, p, info, rid, last):
        print("Settled OK")
        self.ev_login.set()

    def OnRspQryInvestorPosition(self, pPos, pInfo, nReq, bLast):
        if pPos and pPos.InstrumentID:
            self.positions.append(pPos)
        if bLast:
            self.ev_position.set()

    def OnRspOrderInsert(self, pOrder, pInfo, nReq, bLast):
        if pInfo and pInfo.ErrorID != 0:
            print(f"[报单被拒] ErrorID={pInfo.ErrorID} Msg={pInfo.ErrorMsg}")

    def OnRtnOrder(self, pOrder):
        status_map = {'0': '全部成交', '3': '未成交', '4': '部分成交', '5': '撤单', 'a': '已提交'}
        status = status_map.get(pOrder.OrderStatus, pOrder.OrderStatus)
        print(f"[委托回报] 状态={status} 价格={pOrder.LimitPrice} Ref={pOrder.OrderRef.strip()}")

    def OnRtnTrade(self, pTrade):
        print(f"[成交回报] {pTrade.InstrumentID} {pTrade.Volume}手 @{pTrade.Price} Ref={pTrade.OrderRef.strip()}")

api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("td_close3_")
spi = CloseSpi(api)
api.RegisterSpi(spi)
api.RegisterFront(config.ctp.td_address)
api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
api.Init()

if not spi.ev_login.wait(10):
    print("Login timeout")
    sys.exit(1)

time.sleep(0.5)

# 查询持仓
req = tdapi.CThostFtdcQryInvestorPositionField()
req.BrokerID = config.ctp.broker_id
req.InvestorID = config.ctp.account_id
api.ReqQryInvestorPosition(req, 10)
spi.ev_position.wait(10)
time.sleep(0.3)

print(f"\n共 {len(spi.positions)} 条持仓记录")
for p in spi.positions:
    direction = '多' if p.PosiDirection == '2' else '空'
    print(f"  {p.InstrumentID} {direction} 总={p.Position} 今={p.TodayPosition} 昨={p.YdPosition}")

# 分别平今仓和昨仓
for pos in spi.positions:
    if pos.PosiDirection != '2':  # 只平多头
        continue
    
    # 平今仓
    if pos.TodayPosition > 0:
        print(f"\n平今仓 {pos.TodayPosition} 手...")
        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = config.ctp.broker_id
        req.InvestorID = config.ctp.account_id
        req.InstrumentID = pos.InstrumentID
        req.ExchangeID = "SHFE"
        req.OrderRef = spi.next_ref()
        req.UserID = config.ctp.account_id
        req.OrderPriceType = tdapi.THOST_FTDC_OPT_AnyPrice
        req.Direction = tdapi.THOST_FTDC_D_Sell
        req.CombOffsetFlag = tdapi.THOST_FTDC_OF_CloseToday
        req.CombHedgeFlag = tdapi.THOST_FTDC_HF_Speculation
        req.LimitPrice = 0.0
        req.VolumeTotalOriginal = pos.TodayPosition
        req.TimeCondition = tdapi.THOST_FTDC_TC_IOC
        req.VolumeCondition = tdapi.THOST_FTDC_VC_AV
        req.MinVolume = 1
        req.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
        req.ForceCloseReason = tdapi.THOST_FTDC_FCC_NotForceClose
        req.IsAutoSuspend = 0
        api.ReqOrderInsert(req, int(spi.order_ref))
        time.sleep(3)

    # 平昨仓
    if pos.YdPosition > 0:
        print(f"\n平昨仓 {pos.YdPosition} 手...")
        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = config.ctp.broker_id
        req.InvestorID = config.ctp.account_id
        req.InstrumentID = pos.InstrumentID
        req.ExchangeID = "SHFE"
        req.OrderRef = spi.next_ref()
        req.UserID = config.ctp.account_id
        req.OrderPriceType = tdapi.THOST_FTDC_OPT_AnyPrice
        req.Direction = tdapi.THOST_FTDC_D_Sell
        req.CombOffsetFlag = tdapi.THOST_FTDC_OF_CloseYesterday
        req.CombHedgeFlag = tdapi.THOST_FTDC_HF_Speculation
        req.LimitPrice = 0.0
        req.VolumeTotalOriginal = pos.YdPosition
        req.TimeCondition = tdapi.THOST_FTDC_TC_IOC
        req.VolumeCondition = tdapi.THOST_FTDC_VC_AV
        req.MinVolume = 1
        req.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
        req.ForceCloseReason = tdapi.THOST_FTDC_FCC_NotForceClose
        req.IsAutoSuspend = 0
        api.ReqOrderInsert(req, int(spi.order_ref))
        time.sleep(3)

print("\n等待回报...")
time.sleep(3)

# 最终持仓
spi.ev_position.clear()
spi.positions = []
req2 = tdapi.CThostFtdcQryInvestorPositionField()
req2.BrokerID = config.ctp.broker_id
req2.InvestorID = config.ctp.account_id
api.ReqQryInvestorPosition(req2, 20)
spi.ev_position.wait(10)
time.sleep(0.3)
print(f"\n平仓后持仓:")
if not spi.positions:
    print("  无持仓 ✅")
for p in spi.positions:
    direction = '多' if p.PosiDirection == '2' else '空'
    print(f"  {p.InstrumentID} {direction} 总={p.Position} 今={p.TodayPosition} 昨={p.YdPosition}")

api.Release()
