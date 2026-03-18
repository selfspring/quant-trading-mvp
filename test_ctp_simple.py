"""
最简单的 CTP 行情订阅测试
"""
import time
from openctp_ctp import mdapi

BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"
MD_ADDRESS = "tcp://182.254.243.31:30011"
SYMBOL = "au2604"

tick_count = 0

class SimpleMdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.logged_in = False
        
    def OnFrontConnected(self):
        print("[OK] 行情前置连接成功")
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKER_ID
        req.UserID = ACCOUNT_ID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)
    
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[ERROR] 登录失败: {pRspInfo.ErrorMsg}")
            return
        print("[OK] 登录成功")
        self.logged_in = True
        
        # 立即订阅
        print(f"[INFO] 订阅合约: {SYMBOL}")
        instrument_id = SYMBOL.upper().encode('utf-8')
        self.api.SubscribeMarketData([instrument_id], 1)
    
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[ERROR] 订阅失败 {symbol}: {pRspInfo.ErrorMsg}")
        else:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[OK] 订阅确认: {symbol}")
    
    def OnRtnDepthMarketData(self, pDepthMarketData):
        global tick_count
        if not pDepthMarketData:
            print("[WARN] 收到空行情数据")
            return
        
        tick_count += 1
        symbol = pDepthMarketData.InstrumentID
        price = pDepthMarketData.LastPrice
        volume = pDepthMarketData.Volume
        
        if tick_count <= 10:  # 只打印前10条
            print(f"[TICK #{tick_count}] {symbol}: 价格={price}, 成交量={volume}")

def main():
    print("=" * 60)
    print("CTP 行情订阅测试")
    print("=" * 60)
    
    # 创建 API
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi()
    spi = SimpleMdSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(MD_ADDRESS)
    
    print("[INFO] 初始化 API...")
    api.Init()
    
    # 等待登录
    print("[INFO] 等待连接和登录...")
    for i in range(10):
        time.sleep(1)
        if spi.logged_in:
            break
    
    if not spi.logged_in:
        print("[ERROR] 登录超时")
        return
    
    print(f"\n[INFO] 等待行情数据（60秒）...")
    print(f"[INFO] 如果快期客户端有行情，这里也应该有\n")
    
    time.sleep(60)
    
    print("\n" + "=" * 60)
    print(f"测试结果: 收到 {tick_count} 条 Tick 数据")
    print("=" * 60)
    
    if tick_count == 0:
        print("\n[ERROR] 没有收到任何 Tick 数据！")
        print("可能的原因:")
        print("  1. OnRtnDepthMarketData 回调没有被触发")
        print("  2. CTP API 版本或配置问题")
        print("  3. 需要调用 api.Join() 保持事件循环")
    else:
        print(f"\n[OK] 成功接收到 {tick_count} 条行情数据")

if __name__ == "__main__":
    main()
