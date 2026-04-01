"""
紧急平仓 v5 - 使用限价单（当前价 ± 滑点）
"""
import sys, os, time, threading
sys.path.insert(0, 'E:\\quant-trading-mvp')

from quant.common.config import config
from quant.common.db import db_connection
from openctp_ctp import tdapi

def get_current_price():
    """从数据库获取最新价格"""
    with db_connection(config) as conn:
        cur = conn.cursor()
        cur.execute("SELECT close FROM kline_data WHERE symbol='au2606' AND interval='1m' ORDER BY time DESC LIMIT 1")
        row = cur.fetchone()
        return float(row[0]) if row else None

class CloseSpi(tdapi.CThostFtdcTraderSpi):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.ev_login = threading.Event()
        self.ev_position = threading.Event()
        self.ev_order = threading.Event()
        self.positions = []
        self.order_results = []
        self.broker_id = config.ctp.broker_id
        self.account_id = config.ctp.account_id
        self.order_ref_seq = 0

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
            direction = '多' if pPos.PosiDirection == '2' else '空'
            print(f"[持仓] {pPos.InstrumentID} {direction} 总={pPos.Position} 今={pPos.TodayPosition} 昨={pPos.YdPosition}")
            self.positions.append({
                'instrument': pPos.InstrumentID,
                'direction': pPos.PosiDirection,
                'total': pPos.Position,
                'today': pPos.TodayPosition,
                'yd': pPos.YdPosition,
            })
        if bLast:
            self.ev_position.set()

    def OnRtnOrder(self, pOrder):
        status_map = {'0': '未成交', '1': '部分成交', '2': '全部成交', '3': '已撤单', '5': '已撤单', 'a': '已提交'}
        status = status_map.get(pOrder.OrderStatus, pOrder.OrderStatus)
        print(f"[委托回报] {pOrder.InstrumentID} 状态={status} 价={pOrder.LimitPrice} Ref={pOrder.OrderRef}")
        if pOrder.OrderStatus == '2':
            self.ev_order.set()

    def OnRtnTrade(self, pTrade):
        print(f"[成交回报] {pTrade.InstrumentID} {pTrade.Volume}手 @{pTrade.Price} ✅")
        self.order_results.append(('trade', pTrade.Price, pTrade.Volume))
        self.ev_order.set()

    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nReq, bLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[报单被拒] ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")
            self.ev_order.set()

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[报单错误] ErrorID={pRspInfo.ErrorID} Msg={pRspInfo.ErrorMsg}")
            self.ev_order.set()

    def send_limit_close(self, instrument, direction_char, offset_flag, volume, price):
        self.order_ref_seq += 1
        order_ref = str(self.order_ref_seq)
        self.ev_order.clear()

        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = self.broker_id
        req.InvestorID = self.account_id
        req.InstrumentID = instrument
        req.ExchangeID = 'SHFE'
        req.OrderRef = order_ref
        req.UserID = self.account_id
        req.OrderPriceType = tdapi.THOST_FTDC_OPT_LimitPrice  # 限价单
        # 多头平仓 = 卖出
        req.Direction = tdapi.THOST_FTDC_D_Sell if direction_char == '2' else tdapi.THOST_FTDC_D_Buy
        req.CombOffsetFlag = offset_flag
        req.CombHedgeFlag = tdapi.THOST_FTDC_HF_Speculation
        req.LimitPrice = round(price, 2)
        req.VolumeTotalOriginal = volume
        req.TimeCondition = tdapi.THOST_FTDC_TC_GFD  # 当日有效
        req.VolumeCondition = tdapi.THOST_FTDC_VC_AV
        req.MinVolume = 1
        req.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
        req.ForceCloseReason = tdapi.THOST_FTDC_FCC_NotForceClose
        req.IsAutoSuspend = 0

        ret = self.api.ReqOrderInsert(req, self.order_ref_seq)
        offset_name = {tdapi.THOST_FTDC_OF_CloseToday: '平今', tdapi.THOST_FTDC_OF_CloseYesterday: '平昨', tdapi.THOST_FTDC_OF_Close: '平仓'}.get(offset_flag, str(offset_flag))
        print(f"发单 {offset_name} {volume}手 限价={price} ret={ret} Ref={order_ref}")
        return order_ref


def main():
    # 获取当前价格
    price = get_current_price()
    if not price:
        print("无法获取当前价格")
        return
    # 平仓价略低于当前价（卖出），给 -3 个点的滑点
    close_price = price - 3
    print(f"当前价: {price}，平仓限价: {close_price}")

    api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("close_v5_")
    spi = CloseSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(config.ctp.td_address)
    api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
    api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
    api.Init()

    if not spi.ev_login.wait(timeout=15):
        print("登录超时")
        return

    time.sleep(0.5)
    req = tdapi.CThostFtdcQryInvestorPositionField()
    req.BrokerID = config.ctp.broker_id
    req.InvestorID = config.ctp.account_id
    api.ReqQryInvestorPosition(req, 99)

    if not spi.ev_position.wait(timeout=10):
        print("查询持仓超时")
        return

    if not spi.positions:
        print("无持仓，无需平仓")
        api.Release()
        return

    print(f"\n共 {len(spi.positions)} 条持仓，开始平仓...")
    time.sleep(0.5)

    for pos in spi.positions:
        instrument = pos['instrument']
        direction_char = pos['direction']
        today_vol = pos['today']
        yd_vol = pos['yd']

        if today_vol > 0:
            print(f"\n平今仓 {instrument} {today_vol}手 @{close_price}")
            spi.send_limit_close(instrument, direction_char, tdapi.THOST_FTDC_OF_CloseToday, today_vol, close_price)
            spi.ev_order.wait(timeout=10)
            time.sleep(0.5)

        if yd_vol > 0:
            print(f"\n平昨仓 {instrument} {yd_vol}手 @{close_price}")
            spi.send_limit_close(instrument, direction_char, tdapi.THOST_FTDC_OF_CloseYesterday, yd_vol, close_price)
            spi.ev_order.wait(timeout=10)
            time.sleep(0.5)

    print("\n等待确认...")
    time.sleep(2)

    spi.positions = []
    spi.ev_position.clear()
    req2 = tdapi.CThostFtdcQryInvestorPositionField()
    req2.BrokerID = config.ctp.broker_id
    req2.InvestorID = config.ctp.account_id
    api.ReqQryInvestorPosition(req2, 100)
    spi.ev_position.wait(timeout=10)

    if spi.positions:
        for p in spi.positions:
            if p['total'] > 0:
                print(f"  剩余: {p['instrument']} 总={p['total']} 今={p['today']} 昨={p['yd']}")
    else:
        print("  持仓已全部清零 ✅")

    api.Release()

if __name__ == '__main__':
    main()
