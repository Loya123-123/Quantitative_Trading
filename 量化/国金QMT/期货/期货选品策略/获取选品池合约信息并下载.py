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
work_dir = 'C:\\合约选品\\'
# 品种池文件路径
g.excel_file = '期货品种池.xlsx'


def init(ContextInfo):
    ProductID_list = []
    market_list = []
    g.excel_path = f'{work_dir}期货品种池.xlsx'
    g.pools_df = pd.read_excel(g.excel_path)
    pools_df = g.pools_df
    for idx, row in pools_df.iterrows():
        # 获取品种信息
        ProductID_list.append(row['代码'])  # 品种代码，如 rb
        market_list.append(row['交易所代码'])  # 交易所代码，如 SF


    print(f"[数据获取] 合约产品ID集合: {ProductID_list}")
    # market_list 去重
    market_list = list(set(market_list))

    stock_codes_list_info = []
    # 根据 市场编码获取所有合约
    for market in market_list:
        stock_list = ContextInfo.get_stock_list_in_sector(market)
        # 创建一个列表用于存储所有合约信息

        for stock_code in stock_list:
            # print(stock_code)
            # 获取合约基础信息

            g.stock_contract_info = ContextInfo.get_instrument_detail(stock_code)

            productid = g.stock_contract_info.get("ProductID")

            if productid not in ProductID_list:
                continue
            # 将字典数据添加到列表中
            stock_codes_list_info.append(g.stock_contract_info)
    # 创建DataFrame
    stock_codes_list_info = pd.DataFrame(stock_codes_list_info)
    # 下载 数据
    stock_codes_list_info.to_csv(f'{work_dir}期货合约信息.csv', index=False)
def handlebar(ContextInfo):
    pass
