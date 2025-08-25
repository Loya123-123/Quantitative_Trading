# coding:gbk


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
    code_list = ['sp2511.SF', 'FG601.ZF', 'c2511.DF', 'a2511.DF', 'CF601.ZF', 'si2511.GF']
    for code in code_list:
        for i in ['id', '1m']:
            re = download_history_data(code, i, "20230101", "")
            print(f"下载完成 : {re} , code : {code}, 周期 ： {i}")


def handlebar(ContextInfo):
    pass
