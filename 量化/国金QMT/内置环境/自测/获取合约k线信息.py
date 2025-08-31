# coding:gbk


# 市场	市场代码	迅投市场代码
# 上期所	SHFE	SF
# 大商所	DCE	DF
# 郑商所	CZCE	ZF
# 中金所	CFFEX	IF
# 能源中心	INE	INE
# 广期所	GFEX	GF

import pandas as pd


class G(): pass


g = G()


def init(ContextInfo):
    g.current_stock_code = 'si2511.GF'
    g.current_date = '20250827'
    print(f"  获取截止时间: {g.current_date}")
    # 获取非当日的历史数据，使用1d周期
    history_market_data = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [g.current_stock_code],
        end_time=g.current_date,
        period='1d',
        count=20,
        subscribe=True
    )
    history_df = history_market_data[g.current_stock_code]

    history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

    print(f"  获取历史数据: \n {history_df}")

    current_market_data_more = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [g.current_stock_code],
        start_time=g.current_date[:8] + '000000',  # 当天00:00:00开始
        end_time=g.current_date,
        period='1m',  # 使用1分钟周期
        subscribe=True
    )
    current_df_more = current_market_data_more[g.current_stock_code]
    current_df_more['time'] = current_df_more['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

    print(f"  获取当天数据: \n {current_df_more}")

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
    print(f"  获取当天数据: \n {current_df}")

    # 替换历史数据中的最后一条为当日最新数据
    if len(history_df) > 0 and len(current_df) > 0:
        # 删除历史数据中的最后一条（当天数据）
        history_df = history_df[:-1]
        # 将当日最新数据添加到历史数据末尾
        df = pd.concat([history_df, current_df], ignore_index=True)
    else:
        df = history_df

    print(f"  获取数据: \n {df}")
def handlebar(ContextInfo):
    pass
