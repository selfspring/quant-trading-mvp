"""
CTP 常量统一定义
避免在多个模块中重复定义相同的 CTP 常量
"""
try:
    from openctp_ctp import tdapi
    THOST_FTDC_D_Buy = tdapi.THOST_FTDC_D_Buy
    THOST_FTDC_D_Sell = tdapi.THOST_FTDC_D_Sell
    THOST_FTDC_OF_Open = tdapi.THOST_FTDC_OF_Open
    THOST_FTDC_OF_Close = tdapi.THOST_FTDC_OF_Close
    THOST_FTDC_OF_CloseToday = tdapi.THOST_FTDC_OF_CloseToday
    THOST_FTDC_OF_CloseYesterday = tdapi.THOST_FTDC_OF_CloseYesterday
    THOST_FTDC_OPT_LimitPrice = tdapi.THOST_FTDC_OPT_LimitPrice
    THOST_FTDC_OPT_AnyPrice = tdapi.THOST_FTDC_OPT_AnyPrice
    THOST_FTDC_TC_GFD = tdapi.THOST_FTDC_TC_GFD
    THOST_FTDC_TC_IOC = tdapi.THOST_FTDC_TC_IOC
    THOST_FTDC_VC_AV = tdapi.THOST_FTDC_VC_AV
    THOST_FTDC_FCC_NotForceClose = tdapi.THOST_FTDC_FCC_NotForceClose
except ImportError:
    import logging
    logging.getLogger(__name__).warning('openctp-ctp 未安装，使用字符常量代替')
    THOST_FTDC_D_Buy = '0'
    THOST_FTDC_D_Sell = '1'
    THOST_FTDC_OF_Open = '0'
    THOST_FTDC_OF_Close = '1'
    THOST_FTDC_OF_CloseToday = '3'
    THOST_FTDC_OF_CloseYesterday = '4'
    THOST_FTDC_OPT_LimitPrice = '2'
    THOST_FTDC_OPT_AnyPrice = '1'
    THOST_FTDC_TC_GFD = '3'
    THOST_FTDC_TC_IOC = '1'
    THOST_FTDC_VC_AV = '1'
    THOST_FTDC_FCC_NotForceClose = '5'
