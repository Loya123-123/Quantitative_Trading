# coding: gbk
from xtquant import xtconstant

def init(ContextInfo):
    ContextInfo.account_id = "您的期货账号"

def handlebar(ContextInfo):
    if ContextInfo.is_last_bar():
        orders = ContextInfo.get_trade_detail_data(ContextInfo.account_id, "FUTURE", "order")
        for order in orders:
            if order.m_nOrderStatus in [48, 49, 50, 51, 52, 55, 86, 255]:
                ContextInfo.cancel_task(order.m_strOrderSysID, ContextInfo.account_id, "FUTURE", ContextInfo)
                print(f"撤单: {order.m_strStockCode}")
