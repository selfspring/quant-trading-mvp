"""
测试 SimNow 三组看穿式前置地址
"""
import time
from openctp_ctp import mdapi

BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"

FRONTS = [
    ("第1组 30011", "tcp://182.254.243.31:30011"),
    ("第2组 30012", "tcp://182.254.243.31:30012"),
    ("第3组 30013", "tcp://182.254.243.31:30013"),
]

tick_counts = {}

class TestSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api, name):
        super().__init__()
        self.api = api
        self.name = name
        self.connected = False
        self.logged_in = False
        
    def OnFrontConnected(self):
        print(f"[{self.name}] 前置连接成功")
        self.connected = True
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKER_ID
        req.UserID = ACCOUNT_ID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)
    
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[{self.name}] 登录失败: ErrorID={pRspInfo.ErrorID} {pRspInfo.ErrorMsg}")
            return
        print(f"[{self.name}] 登录成功")
        self.logged_in = True
        
        # 立即订阅
        ret = self.api.SubscribeMarketData([b'AU2604'], 1)
        print(f"[{self.name}] 订阅 AU2604, ret={ret}")
    
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            sym = pSpecificInstrument.InstrumentID if pSpecificInstrument else "?"
            print(f"[{self.name}] 订阅失败 {sym}: {pRspInfo.ErrorMsg}")
        else:
            sym = pSpecificInstrument.InstrumentID if pSpecificInstrument else "?"
            print(f"[{self.name}] 订阅确认: {sym}")
    
    def OnRtnDepthMarketData(self, p):
        if not p:
            return
        name = self.name
        if name not in tick_counts:
            tick_counts[name] = 0
        tick_counts[name] += 1
        if tick_counts[name] <= 3:
            print(f"[{name}] TICK #{tick_counts[name]}: {p.InstrumentID} price={p.LastPrice} vol={p.Volume}")

def test_front(name, address):
    print(f"\n{'='*50}")
    print(f"{name}: {address}")
    print(f"{'='*50}")
    
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi()
    spi = TestSpi(api, name)
    api.RegisterSpi(spi)
    api.RegisterFront(address)
    api.Init()
    
    for i in range(10):
        time.sleep(1)
        if spi.logged_in:
            break
    
    if not spi.connected:
        print(f"[{name}] 连接失败")
        return
    if not spi.logged_in:
        print(f"[{name}] 登录失败")
        return
    
    print(f"[{name}] 等待 Tick (20秒)...")
    time.sleep(20)
    
    count = tick_counts.get(name, 0)
    print(f"[{name}] 收到 {count} 条 Tick")

if __name__ == "__main__":
    for name, addr in FRONTS:
        test_front(name, addr)
        time.sleep(2)
    
    print(f"\n{'='*50}")
    print("汇总:")
    print(f"{'='*50}")
    for name, _ in FRONTS:
        count = tick_counts.get(name, 0)
        status = f"{count} 条 Tick" if count > 0 else "无 Tick"
        print(f"  {name}: {status}")
