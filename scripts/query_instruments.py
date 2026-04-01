"""查询 SimNow 可用的黄金合约"""
import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openctp_ctp import tdapi
from quant.common.config import config

ev_login = threading.Event()
ev_done  = threading.Event()
instruments = []

class TdSpi(tdapi.CThostFtdcTraderSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
    def OnFrontConnected(self):
        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID = config.ctp.broker_id
        req.UserID   = config.ctp.account_id
        req.AppID    = config.ctp.app_id
        req.AuthCode = config.ctp.auth_code
        self.api.ReqAuthenticate(req, 1)
    def OnRspAuthenticate(self, p, info, rid, last):
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = config.ctp.broker_id
        req.UserID   = config.ctp.account_id
        req.Password = config.ctp.password.get_secret_value()
        self.api.ReqUserLogin(req, 2)
    def OnRspUserLogin(self, p, info, rid, last):
        ev_login.set()
    def OnRspQryInstrument(self, p, info, rid, last):
        if p and p.InstrumentID:
            instruments.append({
                'id': p.InstrumentID,
                'name': p.InstrumentName,
                'exchange': p.ExchangeID,
                'expire': p.ExpireDate
            })
        if last:
            ev_done.set()

api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("qry_inst")
spi = TdSpi(api)
api.RegisterSpi(spi)
api.RegisterFront(config.ctp.td_address)
api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
api.Init()
ev_login.wait(15)
time.sleep(1)

# 查询黄金合约
req = tdapi.CThostFtdcQryInstrumentField()
req.ProductID = "au"
api.ReqQryInstrument(req, 3)
ev_done.wait(15)

print(f"Found {len(instruments)} au contracts:")
for inst in sorted(instruments, key=lambda x: x['id']):
    print(f"  {inst['id']}  Exchange={inst['exchange']}  Expire={inst['expire']}")

api.Release()
