# coding:gbk
import pandas as pd


class G(): pass


g = G()


def init(ContextInfo):
    ContextInfo.stock_list = ["rb00.SF"]  # 指定获取的标的

    ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market


def handlebar(ContextInfo):
    # 获取历史数据 获取数据的截止时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    g.current_date = bar_date
    print(f"  获取截止时间: {g.current_date}")
    current_market_data_more = ContextInfo.get_market_data_ex(
        ['time', 'open', 'high', 'low', 'close'],
        [ContextInfo.stock_code],
        start_time=g.current_date[:8] + '000000',  # 当天00:00:00开始
        end_time=g.current_date,
        period=ContextInfo.period,  # 使用1分钟周期
        dividend_type=ContextInfo.dividend_type,
        subscribe=True
    )

    current_df_more = current_market_data_more[ContextInfo.stock_code]

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
    current_df_single = pd.DataFrame(current_data_dict)
    print(f"  更新当天数据: \n {current_df_single}")
