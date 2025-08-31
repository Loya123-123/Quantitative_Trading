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
    code_list = ['sp001.SF', 'sp09.SF', 'spL9.SF', 'spL0.SF', 'spL1.SF', 'sp2512.SF', 'sp2509.SF'
        , 'sp2511.SF', 'sp2510.SF', 'sp02.SF', 'sp03.SF', 'sp04.SF', 'sp05.SF', 'sp06.SF', 'sp07.SF', 'sp08.SF',
                 'sp12.SF', 'sp01.SF', 'sp11.SF', 'sp10.SF', 'sp00.SF', 'sp2604.SF', 'sp2605.SF', 'sp2606.SF',
                 'sp2603.SF', 'sp2607.SF', 'sp2601.SF', 'sp2602.SF', 'sp2608.SF', 'FG606.ZF', 'FG601.ZF', 'FG603.ZF',
                 'FG605.ZF', 'FG607.ZF', 'FG604.ZF', 'FG608.ZF', 'FG602.ZF', 'FG03.ZF', 'FG06.ZF', 'FG12.ZF', 'FG07.ZF',
                 'FG08.ZF', 'FG11.ZF', 'FG04.ZF', 'FG01.ZF', 'FGL9.ZF', 'FG00.ZF', 'FG05.ZF', 'FG02.ZF', 'FG10.ZF',
                 'FG510.ZF', 'FG09.ZF', 'FG511.ZF', 'FG512.ZF', 'FG509.ZF', 'FGL0.ZF', 'FGL1.ZF', 'FG001.ZF', 'a05.DF',
                 'a07.DF', 'a11.DF', 'a09.DF', 'a00.DF', 'a01.DF', 'a03.DF', 'a2509.DF', 'a001.DF', 'a2607.DF',
                 'a2603.DF', 'a2601.DF', 'a2605.DF', 'aL0.DF', 'aL1.DF', 'a2511.DF', 'aL9.DF', 'CF07.ZF', 'CF05.ZF',
                 'CF03.ZF', 'CF09.ZF', 'CF001.ZF', 'CF511.ZF', 'CF509.ZF', 'CFL0.ZF', 'CFL1.ZF', 'CF603.ZF', 'CF601.ZF',
                 'CF607.ZF', 'CF605.ZF', 'CF11.ZF', 'CF00.ZF', 'CF01.ZF', 'CFL9.ZF', 'siL0.GF', 'siL1.GF', 'siL9.GF',
                 'si001.GF', 'si2604.GF', 'si2605.GF', 'si2606.GF', 'si2607.GF', 'si2601.GF', 'si2602.GF', 'si2608.GF',
                 'si2603.GF', 'si09.GF', 'si07.GF', 'si08.GF', 'si06.GF', 'si02.GF', 'si2510.GF', 'si2509.GF',
                 'si11.GF', 'si2512.GF', 'si12.GF', 'si03.GF', 'si04.GF', 'si2511.GF', 'si00.GF', 'si01.GF', 'si05.GF',
                 'si10.GF']
    for code in code_list:
        for i in ['1d', '1m']:
            re = download_history_data(code, i, "20240101", "")
            print(f"下载完成 : {re} , code : {code}, 周期 ： {i}")


def handlebar(ContextInfo):
    pass
