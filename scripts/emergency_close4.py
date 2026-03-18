"""
紧急平仓 v4 - 基于 check_position_detail.py 验证的持仓读取方式
分别平昨仓(CloseYesterday)和今仓(CloseToday)
"""
import sys, os, time, threading
sys.path.insert(0, 'E:\\quant-trading-mvp')

from quant.common.config import config
from openctp_ctp import tdapi

ORDER_REF_SEQ = 0

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
        self.front_id = 0
        self.session_id = 0
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
        self.front_id = p.FrontID
        self.session_id = p.SessionID
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
            # 用字符 '2' 比较（与 check_position_detail.py 一致）
            direction = '多' if pPos.PosiDirection == '2' else '空'
            print(f"[持仓] {pPos.InstrumentID} {direction} 总={pPos.Position} 今={pPos.TodayPosition} 昨={pPos.YdPosition}")
            self.positions.append({
                'instrument': pPos.InstrumentID,
                'direction': pPos.PosiDirection,  # '2'=多, '3'=空
                'total': pPos.Position,
                'today': pPos.TodayPosition,
                'yd': pPos.YdPosition,
            })
        if bLast:
            self.ev_position.set()

    def OnRtnOrder(self, pOrder):
        status_map = {'0': '未成交', '1': '部分成交', '2': '全部成交', '3': '已撤单', '5': '已撤单'}
        status = status_map.get(pOrder.OrderStatus, pOrder.OrderStatus)
        print(f"[委托回报] {pOrder.InstrumentID} 状态={status} Ref={pOrder.OrderRef}")
        self.order_results.append(('order', pOrder.OrderStatus))

    def OnRtnTrade(self, pTrade):
        print(f"[成交回报] {pTrade.InstrumentID} {pTrade.Volume}手 @{pTrade.Price}")
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

    def send_close_order(self, instrument, direction_char, offset_flag, volume):
        """发平仓单"""
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
        req.OrderPriceType = tdapi.THOST_FTDC_OPT_AnyPrice  # 市价
        req.Direction = tdapi.THOST_FTDC_D_Sell if direction_char == '2' else tdapi.THOST_FTDC_D_Buy  # 多头平仓=卖
        req.CombOffsetFlag = offset_flag
        req.CombHedgeFlag = tdapi.THOST_FTDC_HF_Speculation
        req.LimitPrice = 0.0
        req.VolumeTotalOriginal = volume
        req.TimeCondition = tdapi.THOST_FTDC_TC_IOC  # 立即成交否则撤销
        req.VolumeCondition = tdapi.THOST_FTDC_VC_AV
        req.MinVolume = 1
        req.ContingentCondition = tdapi.THOST_FTDC_CC_Immediately
        req.ForceCloseReason = tdapi.THOST_FTDC_FCC_NotForceClose
        req.IsAutoSuspend = 0

        ret = self.api.ReqOrderInsert(req, self.order_ref_seq)
        print(f"发单 {offset_flag} {volume}手 ret={ret} Ref={order_ref}")
        return order_ref


def main():
    api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("close_v4_")
    spi = CloseSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(config.ctp.td_address)
    api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)
    api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
    api.Init()

    if not spi.ev_login.wait(timeout=15):
        print("登录超时")
        return

    # 查询持仓
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
        direction_char = pos['direction']  # '2'=多, '3'=空
        today_vol = pos['today']
        yd_vol = pos['yd']

        # 平今仓
        if today_vol > 0:
            print(f"\n平今仓 {instrument} {today_vol}手")
            spi.send_close_order(instrument, direction_char, tdapi.THOST_FTDC_OF_CloseToday, today_vol)
            spi.ev_order.wait(timeout=8)
            time.sleep(0.5)

        # 平昨仓
        if yd_vol > 0:
            print(f"\n平昨仓 {instrument} {yd_vol}手")
            spi.send_close_order(instrument, direction_char, tdapi.THOST_FTDC_OF_CloseYesterday, yd_vol)
            spi.ev_order.wait(timeout=8)
            time.sleep(0.5)

    # 确认最终持仓
    print("\n确认最终持仓...")
    time.sleep(1)
    spi.positions = []
    spi.ev_position.clear()
    req2 = tdapi.CThostFtdcQryInvestorPositionField()
    req2.BrokerID = config.ctp.broker_id
    req2.InvestorID = config.ctp.account_id
    api.ReqQryInvestorPosition(req2, 100)
    spi.ev_position.wait(timeout=10)
    if spi.positions:
        for p in spi.positions:
            print(f"  剩余: {p['instrument']} 总={p['total']} 今={p['today']} 昨={p['yd']}")
    else:
        print("  持仓已全部清零 ✅")

    api.Release()

if __name__ == '__main__':
    main()
