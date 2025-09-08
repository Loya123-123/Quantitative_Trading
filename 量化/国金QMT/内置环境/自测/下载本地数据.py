# coding:gbk


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

class G(): pass


g = G()


def init(ContextInfo):
    code_list = ['600276.SH']
    for code in code_list:
        for i in ['1d', '1m']:
            re = download_history_data(code, i, "20240101", "")
            print(f"下载完成 : {re} , code : {code}, 周期 ： {i}")


def handlebar(ContextInfo):
    pass
