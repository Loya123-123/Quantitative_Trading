# coding:gbk

import pandas as pd


# 市场	市场代码	迅投市场代码
# 上海证券交易所	SH	SH
# 深圳证券交易所	SZ	SZ
# 北京证券交易所	BJ	BJ
# 香港证券交易所	HK	HK
# 沪港通	HGT	HGT
# 深港通	SGT	SGT
# 中国金融期货交易所	IF	CFFEX
# 上海期货交易所	SF	SHFE
# 大连商品交易所	DF	DCE
# 郑州商品交易所	ZF	CZCE
# 上海国际能源交易中心	INE	INE
# 广州期货交易所	GF	GFEX

# 'FUTURE'：期货
# 'STOCK'：股票
class G(): pass


g = G()


def to_dict(obj):
    attr_dict = {}
    for attr in dir(obj):
        try:
            if attr[:2] == 'm_':
                attr_dict[attr] = getattr(obj, attr)
        except:
            pass
    return attr_dict


def init(ContextInfo):
    print("初始化...")
    ContextInfo.account_id = account  # 期货账户ID
    position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ORDER')
    position_list = []
    for pos in position_details:
        g.position_details = to_dict(pos)
        position_list.append(g.position_details)
        print(g.position_details)
    # 字典数据整合到DF里面并下载的本地
    position_df = pd.DataFrame(g.position_list)
    position_df.to_csv('C:\\Users\\Administrator\\Desktop\\持仓信息.csv', index=False, encoding='gbk')


def handlebar(ContextInfo):
    pass
