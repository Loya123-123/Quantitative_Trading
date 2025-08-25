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
    g.current_stock_code = 'FG601.ZF'
    g.current_date = '20250116'
    print(f"  获取截止时间: {g.current_date}")
    # 获取非当日的历史数据，使用1d周期
    history_market_data = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [g.current_stock_code],
        end_time=g.current_date,
        period='1d',
        count=20,
        dividend_type=ContextInfo.dividend_type,
        subscribe=True
    )
    history_df = history_market_data[g.current_stock_code]

    history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

    print(f"  获取数据: \n {history_df}")

def handlebar(ContextInfo):
    pass
