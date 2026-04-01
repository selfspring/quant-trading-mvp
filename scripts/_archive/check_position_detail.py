"""
详细查询 CTP 持仓结构（昨仓/今仓）
"""
import sys, os, time, threading
sys.path.insert(0, 'E:\\quant-trading-mvp')

from quant.common.config import config
from openctp_ctp import tdapi

class DetailSpi(tdapi.CThostFtdcTraderSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.ev_login = threading.Event()
        self.ev_settled = threading.Event()
        self.ev_position = threading.Event()
        self.positions = []
        self.broker_id = config.ctp.broker_id
        self.account_id = config.ctp.account_id

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
        print(f"Login OK FrontID={p.FrontID} SessionID={p.SessionID}")
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
            print(f"\n[持仓] {pPos.InstrumentID}")
            print(f"  方向: {'多' if pPos.PosiDirection == '2' else '空'}")
            print(f"  总持仓: {pPos.Position}")
            print(f"  今仓(TodayPosition): {pPos.TodayPosition}")
            print(f"  昨仓(YdPosition): {pPos.YdPosition}")
            print(f"  可平量(CloseVolume): {pPos.CloseVolume}")
            print(f"  冻结量(ShortFrozen/LongFrozen): {pPos.ShortFrozen}/{pPos.LongFrozen}")
            print(f"  开仓量(OpenVolume): {pPos.OpenVolume}")
        if bLast:
            self.ev_position.set()

api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("td_detail_")
spi = DetailSpi(api)
api.RegisterSpi(spi)
api.RegisterFront(config.ctp.td_address)
api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
api.Init()

if not spi.ev_login.wait(10):
    print("Login timeout")
    sys.exit(1)

time.sleep(0.5)

req = tdapi.CThostFtdcQryInvestorPositionField()
req.BrokerID = config.ctp.broker_id
req.InvestorID = config.ctp.account_id
api.ReqQryInvestorPosition(req, 10)

if not spi.ev_position.wait(10):
    print("Position query timeout")
else:
    print(f"\n共 {len(spi.positions)} 条持仓记录")
    if not spi.positions:
        print("无持仓")

api.Release()
