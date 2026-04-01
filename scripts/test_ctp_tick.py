"""
CTP 实时数据测试脚本
测试多个前置地址和合约，检查 Tick 推送
"""
import sys
import os
import time
import ctypes

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from openctp_ctp import mdapi

# SimNow 行情前置地址
MD_ADDRESSES = [
    "tcp://182.254.243.31:30011",   # 30011
    "tcp://182.254.243.31:30012",   # 30012
    "tcp://182.254.243.31:30013",   # 30013
    "tcp://180.168.146.187:10211",  # 7x24 测试
    "tcp://180.168.146.187:10131",  # 标准
]

# 测试合约
SYMBOLS = ["au2606", "au2604", "IF2604", "rb2605"]

BROKER_ID = "9999"
ACCOUNT_ID = "256693"
PASSWORD = "@Cmx1454697261"


class TestMdSpi(mdapi.CThostFtdcMdSpi):
    def __init__(self, api, address, symbols):
        super().__init__()
        self.api = api
        self.address = address
        self.symbols = symbols
        self.connected = False
        self.logged_in = False
        self.tick_count = 0

    def OnFrontConnected(self):
        self.connected = True
        print(f"  [CONNECTED] {self.address}")
        # 登录
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKER_ID
        req.UserID = ACCOUNT_ID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)

    def OnFrontDisconnected(self, nReason):
        print(f"  [DISCONNECTED] {self.address}, reason={nReason}")

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"  [LOGIN FAILED] error={pRspInfo.ErrorID} msg={pRspInfo.ErrorMsg}")
            return
        self.logged_in = True
        print(f"  [LOGIN OK] TradingDay={pRspUserLogin.TradingDay}")
        
        # 订阅所有测试合约
        for sym in self.symbols:
            ret = self.api.SubscribeMarketData([sym.encode('utf-8')], 1)
            print(f"  [SUBSCRIBE] {sym} -> ret={ret}")

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            sym = pSpecificInstrument.InstrumentID if pSpecificInstrument else "?"
            print(f"  [SUB FAILED] {sym} error={pRspInfo.ErrorID}")
        else:
            sym = pSpecificInstrument.InstrumentID if pSpecificInstrument else "?"
            print(f"  [SUB OK] {sym}")

    def OnRtnDepthMarketData(self, pDepthMarketData):
        self.tick_count += 1
        sym = pDepthMarketData.InstrumentID
        price = pDepthMarketData.LastPrice
        vol = pDepthMarketData.Volume
        update_time = pDepthMarketData.UpdateTime
        print(f"  [TICK #{self.tick_count}] {sym} price={price:.2f} vol={vol} time={update_time}")


def test_address(address, symbols, wait_seconds=15):
    """测试单个前置地址"""
    print(f"\n{'='*60}")
    print(f"[TEST] {address}")
    print(f"       symbols={symbols}")
    print(f"{'='*60}")
    
    flow_path = f"./ctp_test_flow/"
    os.makedirs(flow_path, exist_ok=True)
    
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi(flow_path)
    spi = TestMdSpi(api, address, symbols)
    api.RegisterSpi(spi)
    api.RegisterFront(address)
    api.Init()
    
    # 等待连接+登录+tick
    print(f"  [WAIT] Waiting {wait_seconds}s for ticks...")
    time.sleep(wait_seconds)
    
    result = {
        "address": address,
        "connected": spi.connected,
        "logged_in": spi.logged_in,
        "tick_count": spi.tick_count,
    }
    
    api.Release()
    return result


def main():
    print("=" * 60)
    print("[CTP TEST] SimNow Tick Data Test")
    print(f"[TIME] {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[NOTE] Trading hours: 21:00-02:30, 09:00-11:30, 13:30-15:00")
    print("=" * 60)
    
    results = []
    for addr in MD_ADDRESSES:
        try:
            r = test_address(addr, SYMBOLS, wait_seconds=15)
            results.append(r)
        except Exception as e:
            print(f"  [ERROR] {addr}: {e}")
            results.append({"address": addr, "connected": False, "logged_in": False, "tick_count": 0})
    
    # Summary
    print("\n" + "=" * 60)
    print("[SUMMARY]")
    print("=" * 60)
    for r in results:
        status = "TICK!" if r["tick_count"] > 0 else ("LOGIN OK" if r["logged_in"] else ("CONNECTED" if r["connected"] else "FAILED"))
        print(f"  {r['address']:40s} | {status:10s} | ticks={r['tick_count']}")
    
    has_ticks = any(r["tick_count"] > 0 for r in results)
    if has_ticks:
        print("\n[RESULT] Found working address with tick data!")
    else:
        print("\n[RESULT] No tick data from any address.")
        print("         This is a known SimNow issue - ticks only push during trading hours.")
        print("         Trading hours: 21:00-02:30 (night), 09:00-11:30, 13:30-15:00")


if __name__ == "__main__":
    main()
