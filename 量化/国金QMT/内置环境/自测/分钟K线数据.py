# coding:gbk
import pandas as pd
from datetime import datetime


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
    g.current_date = '20250910090700'
    g.current_stock_code = 'jm2601.DF'

    current_market_data_more = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [g.current_stock_code],
        start_time=get_futures_start_time(g.current_date),  # 根据期货交易时间规则确定开始时间
        end_time=g.current_date,
        period=ContextInfo.period,  # 使用1分钟周期
        dividend_type=ContextInfo.dividend_type,
        subscribe=True
    )
    current_df_more = current_market_data_more[g.current_stock_code]
    current_df_more['time'] = current_df_more['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))
    print(current_df_more)
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
    print(current_df)

def get_futures_start_time(current_date):
    """
    根据当前时间确定期货交易起始时间
    如果current_date的小时在21点之后，那么期货的交易时间从今天晚上九点开始
    否则期货交易时间从昨天晚上9点开始
    """

    current_time = datetime.strptime(current_date, '%Y%m%d%H%M%S')
    current_hour = current_time.hour
    print(current_hour)
    # 期货交易日从晚上9点开始
    start_time = current_time.replace(hour=21, minute=0, second=0)

    # 如果当前时间在21点之前，说明是当天的日盘交易，需要从前一晚的夜盘开始
    if current_hour < 21:
        # 往前推一天
        start_time = start_time - pd.Timedelta(days=1)
    print(start_time)
    return start_time.strftime('%Y%m%d%H%M%S')


def handlebar(ContextInfo):
    pass
