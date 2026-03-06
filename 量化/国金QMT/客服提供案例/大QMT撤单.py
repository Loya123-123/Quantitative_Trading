#coding:gbk
from xtquant.qmttools.functions import get_trade_detail_data


def init(ContextInfo):
    ContextInfo.account = "229682"
    ContextInfo.account_type = "FUTURE"

def handlebar(ContextInfo):
    # 鍙湪鏈?鍚庝竴鏍筀绾挎墽琛?
    if not ContextInfo.is_last_bar():
        return
    
    # 鑾峰彇骞舵挙娑堟墍鏈夊彲鎾ゅ鎵?
    orders = get_trade_detail_data(ContextInfo.account, ContextInfo.account_type, "order")
    for order in orders:
        if order.m_nOrderStatus in [48, 49, 50, 51]:
            cancel(order.m_strOrderSysID, ContextInfo.account, ContextInfo.account_type, ContextInfo)