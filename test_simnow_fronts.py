"""
测试 SimNow 不同前置地址的连通性
"""
import time
from openctp_ctp import mdapi

BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"

# SimNow 已知的前置地址列表
FRONT_ADDRESSES = [
    ("当前使用", "tcp://182.254.243.31:30011"),
    ("SimNow 7x24-1", "tcp://180.168.146.187:10211"),
    ("SimNow 7x24-2", "tcp://218.202.237.33:10212"),
    ("SimNow 标准-1", "tcp://180.168.146.187:10131"),
    ("SimNow 标准-2", "tcp://218.202.237.33:10132"),
]

class TestMdSpi(mdapi.CThostFtdcMdSpi):
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
            print(f"[{self.name}] 登录失败: {pRspInfo.ErrorMsg}")
            return
        print(f"[{self.name}] 登录成功")
        self.logged_in = True
        
        # 订阅 au2604
        instrument_id = b'AU2604'
        self.api.SubscribeMarketData([instrument_id], 1)
        print(f"[{self.name}] 已订阅 AU2604")
    
    def OnRtnDepthMarketData(self, pDepthMarketData):
        if not pDepthMarketData:
            return
        print(f"[{self.name}] 收到 Tick: {pDepthMarketData.InstrumentID} 价格={pDepthMarketData.LastPrice}")

def test_front(name, address):
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"地址: {address}")
    print(f"{'='*60}")
    
    try:
        api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi()
        spi = TestMdSpi(api, name)
        api.RegisterSpi(spi)
        api.RegisterFront(address)
        api.Init()
        
        # 等待 15 秒
        for i in range(15):
            time.sleep(1)
            if spi.logged_in:
                print(f"[{name}] 等待 Tick 数据...")
                time.sleep(10)  # 再等 10 秒看是否有 Tick
                break
        
        if not spi.connected:
            print(f"[{name}] ❌ 连接失败")
            return False
        elif not spi.logged_in:
            print(f"[{name}] ❌ 登录失败")
            return False
        else:
            print(f"[{name}] ✓ 连接和登录成功")
            return True
            
    except Exception as e:
        print(f"[{name}] 异常: {e}")
        return False

if __name__ == "__main__":
    print("SimNow 前置地址连通性测试")
    print("账户:", ACCOUNT_ID)
    
    results = {}
    for name, address in FRONT_ADDRESSES:
        success = test_front(name, address)
        results[name] = success
        time.sleep(2)  # 间隔 2 秒
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    for name, success in results.items():
        status = "✓ 可用" if success else "✗ 不可用"
        print(f"{name:20s} {status}")
