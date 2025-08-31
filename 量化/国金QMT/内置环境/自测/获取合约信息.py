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

    stock_list = ContextInfo.get_stock_list_in_sector("SF")
    # 创建一个列表用于存储所有合约信息
    contract_data_list = []
    for stock_code in stock_list:
        print(stock_code)
        # 获取合约基础信息

        g.stock_contract_info = ContextInfo.get_instrument_detail(stock_code)
        print(f"[数据获取] 主合约基础信息: {g.stock_contract_info}")

        # 将字典数据添加到列表中
        contract_data_list.append(g.stock_contract_info)

        # LongMarginRatio	float	多头保证金率
        # ShortMarginRatio	float	空头保证金率
        g.long_margin_ratio = g.stock_contract_info.get('LongMarginRatio', 0.0)
        g.short_margin_ratio = g.stock_contract_info.get('ShortMarginRatio', 0.0)
        print(f"[数据获取] 多头保证金率: {g.long_margin_ratio}, 空头保证金率: {g.short_margin_ratio}")
    df = pd.DataFrame(contract_data_list)
    print(f"[数据获取] 数据框信息\n{df}")


def handlebar(ContextInfo):
    pass
