"""
CTP 行情实时测试 - 夜盘专用
实时输出每个 Tick，不等待
"""
import time
import sys
from datetime import datetime
from openctp_ctp import mdapi

BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"
MD_ADDRESS = "tcp://182.254.243.31:30011"

tick_count = 0

class TestMdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
        
    def OnFrontConnected(self):
        print(f"✅ 连接成功", flush=True)
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKER_ID
        req.UserID = ACCOUNT_ID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)
    
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"❌ 登录失败：{pRspInfo.ErrorMsg}", flush=True)
            return
        print(f"✅ 登录成功", flush=True)
        ret = self.api.SubscribeMarketData([b'AU2604'], 1)
        print(f"订阅 AU2604, ret={ret}", flush=True)
    
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"❌ 订阅失败", flush=True)
        else:
            print(f"✅ 订阅确认", flush=True)
    
    def OnRtnDepthMarketData(self, p):
        global tick_count
        if not p:
            return
        tick_count += 1
        t = datetime.now().strftime("%H:%M:%S")
        print(f"[{t}] 📊 TICK #{tick_count}: {p.InstrumentID} 价格={p.LastPrice} 成交量={p.Volume}", flush=True)

print("="*50)
print("CTP 行情实时测试")
print(f"地址：{MD_ADDRESS}")
print(f"合约：AU2604")
print("="*50)
print(flush=True)

api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi()
spi = TestMdSpi(api)
api.RegisterSpi(spi)
api.RegisterFront(MD_ADDRESS)
api.Init()

print("等待行情...", flush=True)

# 运行 5 分钟，实时输出
try:
    for i in range(300):
        time.sleep(1)
        if i % 30 == 0:
            print(f"... {i}秒，已收 {tick_count} 条 Tick", flush=True)
except KeyboardInterrupt:
    pass

print(f"\n========== 结果 ==========")
print(f"Tick 总数：{tick_count}")
print(f"========================")
