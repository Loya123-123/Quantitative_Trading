# coding:gbk
import pandas as pd


# 市场	市场代码	迅投市场代码
# 上期所	SHFE	SF
# 大商所	DCE	DF
# 郑商所	CZCE	ZF
# 中金所	CFFEX	IF
# 能源中心	INE	INE
# 广期所	GFEX	GF

class G(): pass


g = G()

def init(ContextInfo):

    order_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ORDER')
    if order_details:
        order_len = 0
        for order in order_details:
            # log_info(f"  [账户信息] 获取到委托记录：\n {to_dict(order)}")
            # 获取委托状态，50-54表示未成交状态
            order_status = order.m_nOrderStatus
            print(order_status)
            symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID
            print( symbol)
            msg = order.m_strErrorMsg
            print( msg)
            sub = order.m_nOrderSubmitStatus
            print( sub)
def handlebar(ContextInfo):
    pass
