"""
测试 CTP 订阅不同合约，看哪个有行情
"""
import time
from openctp_ctp import mdapi
import structlog

logger = structlog.get_logger()

# SimNow 配置
BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"
MD_ADDRESS = "tcp://182.254.243.31:30011"

# 要测试的合约列表
TEST_SYMBOLS = [
    "au2604", "au2606", "au2608", "au2612",  # 黄金
    "ag2604", "ag2606", "ag2612",  # 白银
    "cu2604", "cu2605", "cu2606",  # 铜
    "rb2604", "rb2605", "rb2610",  # 螺纹钢
]

received_ticks = {}

class TestMdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self):
        super().__init__()
        self.connected = False
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
    
    def OnRtnDepthMarketData(self, pDepthMarketData):
        if not pDepthMarketData:
            return
        
        symbol = pDepthMarketData.InstrumentID
        price = pDepthMarketData.LastPrice
        volume = pDepthMarketData.Volume
        
        if symbol not in received_ticks:
            received_ticks[symbol] = 0
        received_ticks[symbol] += 1
        
        if received_ticks[symbol] <= 3:  # 只打印前3条
            print(f"[TICK] {symbol}: 价格={price}, 成交量={volume}")
    
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[ERROR] 订阅失败 {symbol}: {pRspInfo.ErrorMsg}")
        else:
            symbol = pSpecificInstrument.InstrumentID if pSpecificInstrument else "未知"
            print(f"[OK] 订阅成功: {symbol}")

def main():
    print("=" * 60)
    print("SimNow 合约行情测试")
    print("=" * 60)
    
    # 创建 API
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi()
    spi = TestMdSpi()
    spi.api = api
    api.RegisterSpi(spi)
    api.RegisterFront(MD_ADDRESS)
    api.Init()
    
    # 等待登录
    print("等待连接和登录...")
    for i in range(10):
        time.sleep(1)
        if spi.logged_in:
            break
    
    if not spi.logged_in:
        print("[ERROR] 登录超时")
        return
    
    print("\n开始订阅合约...")
    for symbol in TEST_SYMBOLS:
        instrument_id = symbol.upper().encode('utf-8')
        api.SubscribeMarketData([instrument_id], 1)
        time.sleep(0.5)
    
    print(f"\n已订阅 {len(TEST_SYMBOLS)} 个合约，等待行情数据...")
    print("等待 30 秒...\n")
    
    time.sleep(30)
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    if received_ticks:
        print(f"\n[OK] 收到行情的合约 ({len(received_ticks)} 个):")
        for symbol, count in sorted(received_ticks.items(), key=lambda x: x[1], reverse=True):
            print(f"  {symbol}: {count} 条 Tick")
    else:
        print("\n[ERROR] 没有收到任何行情数据")
        print("\n可能的原因:")
        print("  1. 当前不在交易时段")
        print("  2. 这些合约在 SimNow 上不活跃")
        print("  3. SimNow 仿真环境配置问题")
    
    print("\n按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出")

if __name__ == "__main__":
    main()
