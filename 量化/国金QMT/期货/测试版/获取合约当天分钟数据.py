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
    # 当日K线集合

    # 当日K线集合
    current_market_data_more = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [g.current_stock_code],
        start_time=get_futures_start_time(g.current_date_bar),  # 根据期货交易时间规则确定开始时间
        end_time=g.current_date_bar,
        period=ContextInfo.period,  # 使用1分钟周期
        dividend_type=ContextInfo.dividend_type,
        subscribe=True
    )

    if not current_market_data_more or g.current_stock_code not in current_market_data_more:
        message = "  [异常处理] 获取当日市场数据为空"
        log_info(message)
        # send_feishu_message(message)
        return None

    current_df_more = current_market_data_more[g.current_stock_code]

    current_df_more['time'] = current_df_more['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

    open_price = current_df_more['open'].iloc[0]
    high_price = current_df_more['high'].max()
    low_price = current_df_more['low'].min()
    close_price = current_df_more['close'].iloc[-1]

    # 构造新的DataFrame，只包含一条记录
    current_data_dict = {
        'time': [current_df_more['time'].iloc[-1]],
        'open': [open_price],
        'high': [high_price],
        'low': [low_price],
        'close': [close_price]
    }
    current_df = pd.DataFrame(current_data_dict)
    log_info(f"  获取当天数据: \n {current_df}")


def get_futures_start_time(current_date):
    """
    根据当前时间确定期货交易起始时间
    如果current_date的小时在21点之后，那么期货的交易时间从今天晚上九点开始
    否则期货交易时间从昨天晚上9点开始
    """

    current_time = datetime.strptime(current_date, '%Y%m%d%H%M%S')
    current_hour = current_time.hour

    # 期货交易日从晚上9点开始
    start_time = current_time.replace(hour=21, minute=0, second=0)

    # 如果当前时间在21点之前，说明是当天的日盘交易，需要从前一晚的夜盘开始
    if current_hour < 21:
        # 往前推一天
        start_time = start_time - pd.Timedelta(days=1)

    return start_time.strftime('%Y%m%d%H%M%S')
