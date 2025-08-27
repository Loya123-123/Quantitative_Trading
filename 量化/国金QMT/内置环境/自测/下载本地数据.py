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
    code_list = ['CF07.ZF', 'CF05.ZF', 'CF03.ZF', 'CF09.ZF', 'CF001.ZF', 'CF511.ZF', 'CF509.ZF', 'CFL0.ZF', 'CFL1.ZF',
                 'CF603.ZF', 'CF601.ZF', 'CF607.ZF', 'CF605.ZF', 'CF11.ZF', 'CF00.ZF', 'CF01.ZF', 'CFL9.ZF']
    for code in code_list:
        for i in ['1d', '1m']:
            re = download_history_data(code, i, "20230101", "")
            print(f"下载完成 : {re} , code : {code}, 周期 ： {i}")


def handlebar(ContextInfo):
    pass
