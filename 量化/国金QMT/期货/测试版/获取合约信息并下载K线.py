
import pandas as pd

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
    stock_codes_dict = {
        "FG": {"code": "FG00", "market": "ZF", "size": 6}  # 玻璃 1
        , "jm": {"code": "jm00", "market": "DF", "size": 2}  # 焦煤 1
        , "ao": {"code": "ao00", "market": "SF", "size": 2}  # 氧化铝 1
        , "CF": {"code": "CF00", "market": "ZF", "size": 3}  # 棉花
        , "sp": {"code": "sp00", "market": "SF", "size": 4}  # 纸浆
    }
    ProductID_list = [stock_code for stock_code, stock_info in stock_codes_dict.items()]

    print(f"[数据获取] 合约产品ID集合: {ProductID_list}")

    market_list = [stock_info["market"] for stock_code, stock_info in stock_codes_dict.items()]

    stock_codes_list = []
    # 根据 市场编码获取所有合约
    for market in market_list:
        stock_list = ContextInfo.get_stock_list_in_sector(market)
        # 创建一个列表用于存储所有合约信息

        for stock_code in stock_list:
            # print(stock_code)
            # 获取合约基础信息

            g.stock_contract_info = ContextInfo.get_instrument_detail(stock_code)

            ProductID = g.stock_contract_info.get("ProductID")

            if ProductID not in ProductID_list:
                continue

            ExchangeCode = g.stock_contract_info.get("ExchangeCode")
            print(f"[数据获取] 合约产品ID: {ProductID}")
            print(f"[数据获取] 主合约基础信息: {g.stock_contract_info}")
            stock_codes = ExchangeCode + '.' + market
            # 将字典数据添加到列表中
            stock_codes_list.append(stock_codes)

    stock_codes_list = list(set(stock_codes_list))
    print(f"去重{stock_codes_list}")

    for code in stock_codes_list:
        for i in ['1m', '1d']:
            re = download_history_data(code, i, "20250101", "")
            print(f"\n下载完成 : {re} , code : {code}, 周期 ： {i}")

def handlebar(ContextInfo):
    pass
