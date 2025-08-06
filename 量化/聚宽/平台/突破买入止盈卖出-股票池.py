from datetime import datetime

import pandas as pd
# 导入函数库
from jqdata import *

"""
策略简要
计算频率：分钟/tick
交易品种：恒瑞医药，600276.XSHG
医药行业：
恒瑞医药：600276.XSHG        上海               
华东医药：000963.XSHE        深圳               
白酒：
五粮液：000858.XSHE             深圳              
山西汾酒：600809.XSHG        上海               
泸州老窖：000568.XSHE         深圳
买入头寸：单只股买入金额20000，按照最大手数买

买入：当日价格大于过去4日收盘价最高点时，即当前价格突破5日高点，当日立刻执行买入
止盈卖出1：买入第二天开始，当最高价/买入价>1.2时，且价格<最高价-（最高价-买入价）*20%时，立刻执行卖出
止盈卖出2：买入第二天开始，当价格<前一日最低价，且价格<最高价-（最高价-买入价）*30%时，立刻执行卖出
止损卖出：买入第二天开始，亏损到买入价的95%立刻执行卖出


当周k线dkx>masks时，才进行买入，周k线dkx<masks时，不做买入
买入：当周k线dkx>masks时 ,当日价格大于过去10日收盘价最高点时，即当前价格突破10日高点，当日立刻执行买入
止盈卖出1：买入第二天开始，当价格<前4日收盘价时，且价格<最高价-（最高价-买入价）*20%时，立刻执行卖出
止盈卖出2：买入第二天开始，当价格<前一日最低价，且价格<最高价-（最高价-买入价）*50%时，立刻执行卖出
止损卖出：买入第二天开始，亏损到买入价的95%立刻执行卖出
"""

# 全局变量存储数据
_data_proxy = None


# log.set_level('order', 'error')

def initialize(context):
    # 设置参数
    set_params(context)

    # g.stocks = ['600276.XSHG','000963.XSHE','000858.XSHE','600809.XSHG','000568.XSHE']
    g.stocks = ['600276.XSHG']

    # 设置基准 沪：XSHG 深：XSHE
    set_benchmark('600276.XSHG')

    context.highest_price = 0

    # 设置交易相关参数
    set_option('use_real_price', True)

    # 设置交易成本和滑点
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), 'stock')
    set_slippage(FixedSlippage(0.02))

    # 设置每日开盘前的函数
    # run_daily(before_trading_start, time='every_bar')

    # 注册交易处理函数
    run_daily(handle_data_wrapper, time='every_bar')


def set_params(context):
    # 止盈1比例
    context.stop_profit_ratio1 = 0.2
    # 止盈2比例
    context.stop_profit_ratio2 = 0.5
    # 止损比例
    context.stop_loss_ratio = 0.95
    # 止盈涨幅比例
    context.stop_profit_ratio_change = 1.2
    # MADKX是DKX的N日简单移动平均
    context.madk_period = 10


def handle_data_wrapper(context):
    for security in g.stocks:
        # 设置交易品种
        context.security = security
        # 获取当天股票数据
        data_df = get_data(context)

        # 判断是否应该交易
        signal = should_trade(context, data_df)

        # 执行交易
        if signal:
            execute_trade(context, signal, data_df)


def get_data(context):
    """
    获取并整合当前获取到的数据
    :param context:
    :return:
    """
    global _data_proxy
    _data_proxy = get_current_data()
    # 当前日期
    context.current_date = context.current_dt.date()

    # log.info(f"当前时间： {context.current_date}")

    # 当前日期
    context.current_time = datetime.datetime.combine(context.current_date, context.current_dt.time())

    # log.info(f"当前时间： {context.current_time}")

    # 获取历史数据 - 需要足够的数据来计算5日高点
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=365,  # 过去4日数据 + 今日数据
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )
    ticks_df = get_ticks(context.security,
                         end_dt=context.current_time,
                         count=1,
                         fields=['time', 'current', 'high', 'low', 'volume', 'money'], skip=True, df=True)

    # log.info(f"股票代码： {context.security} 。 获取历史数据：\n {hist_daily}")

    # 获取最后一天的索引
    last_day_index = hist_daily.index[-1]

    hist_daily.loc[last_day_index, 'close'] = ticks_df['current'].iloc[-1]
    hist_daily.loc[last_day_index, 'low'] = ticks_df['low'].iloc[-1]
    hist_daily.loc[last_day_index, 'high'] = ticks_df['high'].iloc[-1]

    weekly_df = hist_daily.resample('W').agg({
        'open': 'first',  # 周开盘价 = 周一的开盘价
        'high': 'max',  # 周最高价 = 一周内的最高价
        'low': 'min',  # 周最低价 = 一周内的最低价
        'close': 'last',  # 周收盘价 = 周五的收盘价
    })
    # log.info(f"周K数据：\n {weekly_df}")


    # 删除所有NaN行
    weekly_df = weekly_df.dropna()

    weekly_dkx_df = calculate_dkx(weekly_df, context.madk_period)

    # 获取最新的DKX和MADKX值
    dkx_now = weekly_dkx_df['DKX'].iloc[-1]
    madkx_now = weekly_dkx_df['MADKX'].iloc[-1]
    dkx_prev = weekly_dkx_df['DKX_prev'].iloc[-1]
    madkx_prev = weekly_dkx_df['MADKX_prev'].iloc[-1]

    # 获取前4日收盘价最高点
    past_4_days_close_max = hist_daily['close'].iloc[-5:-1].max()
    # 获取前4日收盘价最低点
    past_4_days_close_min = hist_daily['close'].iloc[-5:-1].min()
    # 获取5日低点
    past_4_days_low_min = hist_daily['low'].iloc[-5:-1].min()
    # 获取10日收盘最高点
    past_10_days_high = hist_daily['close'].iloc[-11:-1].max()
    # log.info(f"获取最近几天的最小值数据：\n {past_4_days_low_min}")

    # 前一日最低价
    past_yest_days_low = hist_daily['low'].iloc[-2]

    # log.info(f"前一日最低价 : {past_yest_days_low}")

    # log.info(f"获取当前数据：\n {ticks_df}")

    # 获取最新价格
    security_data = _data_proxy[context.security]

    # 获取价格
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"无法获取价格: {e}")

    # log.info(f"股票代码： {context.security} 。获取最新价格：\n {current_price}")

    # 检查数据是否有效
    if current_price is None or past_4_days_close_max is None:
        return

    data_df = pd.DataFrame({
        'current_time': [context.current_time]  # 当前时间
        , 'past_4_days_close_max': [past_4_days_close_max]  # 前四天最高价
        , 'past_4_days_close_min': [past_4_days_close_min]  # 前四天最低价
        , 'past_4_days_low_min': [past_4_days_low_min]  # 前四天最低价
        , 'past_10_days_high': [past_10_days_high] # 前十天收盘价最高价
        , 'current_price': [ticks_df['current'].iloc[-1]]  # 当前价格（ticks_df中current列的最后一个值）
        , 'current_high': [ticks_df['high'].iloc[-1]]
        , 'past_yest_days_low': [past_yest_days_low]
        , 'dkx_now': [dkx_now]
        , 'madkx_now': [madkx_now]
        , 'dkx_prev': [dkx_prev]
        , 'madkx_prev': [madkx_prev]
    })

    # log.info(f"股票代码： {context.security} \n ; 获取最新数据：\n {data_df}")

    return data_df


def calculate_dkx(df, madk_period):
    # 计算DKX
    # MID = (3*CLOSE + OPEN + HIGH + LOW)/6
    df['MID'] = (3 * df['close'] + df['open'] + df['high'] + df['low']) / 6
    # df['DKX'] = df.apply(lambda row: row['open'] if row.name.date() == context.current_date else (3 * row['close'] + 2 * row['open'] + row['high'] + row['low']) / 7, axis=1)
    # (20×MID+19×昨日MID+18×2日前的MID+17×3日前的MID+16×4日前的MID+15×5日前的MID+14×6日前的MID+13×7日前的MID+12×8日前的MID+11×9日前的MID十10×10日前的MID+9×U日前的MID+8×12日前的MID+7×13日前的M1D+6×14日前的MID+5×15日前的MID+4×16日前的MID+3×17日前的MID+2×18日前的MID+20日前的MID)÷210
    df['DKX'] = (20 * df['MID'] + 19 * df['MID'].shift(1) + 18 * df['MID'].shift(2) + 17 * df['MID'].shift(3)
                 + 16 * df['MID'].shift(4) + 15 * df['MID'].shift(5) + 14 * df['MID'].shift(6) + 13 * df['MID'].shift(7)
                 + 12 * df['MID'].shift(8) + 11 * df['MID'].shift(9) + 10 * df['MID'].shift(10) + 9 * df['MID'].shift(
                11)
                 + 8 * df['MID'].shift(12) + 7 * df['MID'].shift(13) + 6 * df['MID'].shift(14) + 5 * df['MID'].shift(15)
                 + 4 * df['MID'].shift(16) + 3 * df['MID'].shift(17) + 2 * df['MID'].shift(18) + df['MID'].shift(
                19)) / 210
    # 计算MADKX - MADKX是DKX的N日简单移动平均
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # 计算DKX和MADKX的前一天值，用于判断金叉死叉
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df


def should_trade(context, data_df):
    """
    3. 基于策略要求判断当前数据是买入还是卖出
    """
    # 交易信号
    signal = None

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_close_max = data_df['past_4_days_close_max'].iloc[-1]
    past_4_days_close_min = data_df['past_4_days_close_min'].iloc[-1]
    current_high = data_df['current_high'].iloc[-1]
    past_yest_days_low = data_df['past_yest_days_low'].iloc[-1]
    past_10_days_high = data_df['past_10_days_high'].iloc[-1]
    dkx_now = data_df['dkx_now'].iloc[-1]
    madkx_now = data_df['madkx_now'].iloc[-1]


    # 获取当前持仓
    position = context.portfolio.positions.get(context.security)
    # log.info(f"股票代码： {context.security} ; 获取当前持仓 : {position}")

    # 获取是否当前持仓
    has_position = position is not None and position.total_amount > 0
    # log.info(f"股票代码： {context.security} ; 当前是否持仓 : {has_position}")

    # 得到当天所有成交记录
    # {1753598792: UserTrade({'trade_id': 1753598792, 'order_id': 1753599023, 'time': datetime.datetime(2025, 3, 14, 9, 46), 'amount': 1000, 'price': 45.56})}
    # trades = get_trades()
    # log.info(f"股票代码： {context.security} ; 获取所有成交记录 : {trades}")
    # for trade_id, trade in trades.items():
    #     time_variable = trade.time
    # log.info(f"股票代码： {context.security} ; 获取所有成交记录时间 : {time_variable}")
    # if time_variable.date() == context.current_date :
    #     log.info(f"当天有交易， 跳过")
    #     return

    # 最后一次交易时间
    transact_time = position.transact_time
    # log.info(f"股票代码： {context.security} ; 获取最后交易时间 : {transact_time}")

    if not has_position:  # 没有持仓时寻找买入机会
        # # 当周k线dkx>masks时 ,当日价格大于过去10日收盘价最高点
        # if current_price >= past_10_days_high and dkx_now >= madkx_now:
        # 当日价格大于过去10日收盘价最高点
        if current_price >= past_10_days_high :
            log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 当前价格 {current_price} ; 10日收盘价最高点 {past_10_days_high} , 周期DKX： {dkx_now}，周MADKX： {madkx_now} ，准备买入 \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)
            signal = "BUY"

    elif not transact_time.date() == context.current_date:  # 持仓时寻找卖出机会 当天有买入，就不能卖出了

        # 当价格从最高价(最后一次买入点开始算的历史价位最高点)与买入价回落20%时，立刻执行卖出
        high_hist_daily = get_price(
            context.security,
            start_date=transact_time,
            end_date=context.current_date,
            frequency='1d',
            fields=['open', 'close', 'low', 'high', 'volume', 'money'],
            skip_paused=True
        )
        # 历史最高价
        high_hist_price_tmp = high_hist_daily['high'].iloc[:-1].max()
        # 历史最高价 和 当日最高价比较
        high_hist_price = high_hist_price_tmp if high_hist_price_tmp > current_high else current_high

        context.highest_price = high_hist_price

        # 是当前持仓成本
        avg_cost = position.avg_cost
        # log.info(f"股票代码： {context.security} ; 当前持仓成本 : {avg_cost}")

        # 止盈点1位最高价回落止盈比例   最高点 - (（最高点-成本价）* 0.2 )
        stop_profit_price1 = high_hist_price - ((high_hist_price - avg_cost) * context.stop_profit_ratio1)

        # 止盈点2位最高价回落止盈比例   最高点 - (（最高点-成本价）* 0.3 )
        stop_profit_price2 = high_hist_price - ((high_hist_price - avg_cost) * context.stop_profit_ratio2)

        # 止盈卖出1： 止买入第二天开始，当价格<最小的前4日收盘价时，且价格<最高价-（最高价-买入价）*20%，立刻执行卖出
        if current_price <= past_4_days_close_min and current_price <= stop_profit_price1:
            log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 触发止盈条件1： 前4日收盘价最低点位：{past_4_days_close_min} ,止盈点： {stop_profit_price1} ,当前价为： {current_price} , 准备卖出 \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)
            signal = "SELL"

        # # 止盈卖出2：买入第二天开始，当价格<前一日最低价，且价格<最高价-（最高价-成本价）*50%时，立刻执行卖出
        # if current_price <= past_yest_days_low and current_price <= stop_profit_price2:
        #     log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 触发止盈条件2： 最高点位：{high_hist_price} ,成本价：{avg_cost} ,止盈点: {stop_profit_price2} ,当前价为： {current_price},昨日最低价：{past_yest_days_low}  , 准备卖出 \n "
        #     log.info(log_info)
        #     write_file('log.txt', str((log_info)), append=True)
        #     signal = "SELL"

        # 止损条件：价格跌至买入价的95%
        stop_loss_price = avg_cost * context.stop_loss_ratio

        # 止损判断 买入第二天开始，亏损到买入价的95%立刻执行卖出
        if current_price <= stop_loss_price:
            log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 触发止损条件： 成本价：{avg_cost} ,止损点： {stop_loss_price} ,当前价为： {current_price} , 准备卖出 \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)

            signal = "SELL"

    return signal


def execute_trade(context, signal, data_df):
    """
    4. 执行买入或卖出操作
    """

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_close_max = data_df['past_4_days_close_max'].iloc[-1]

    if signal == "BUY":
        # 全仓买入
        # cash = context.portfolio.cash
        cash = 20000
        amount = int(cash * 0.98 / current_price / 100) * 100  # 确保买卖数量是100的整数倍
        # 手
        qty = amount / 100
        # 买入总价
        total_amount = current_price * amount

        if amount > 0:
            # 执行买入
            order(context.security, amount)
            log_info = f"当前日期： {context.current_date} ;  买入 {context.security} ; {qty} 手，股数: {amount} , 买入总价 {total_amount}, 买入价 {current_price}，过去4日最高收盘价: {past_4_days_close_max} \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)

            signal = None

    elif signal == "SELL":
        # 执行卖出
        position = context.portfolio.positions.get(context.security)

        order_target_value(context.security, 0)

        log_info = f"当前日期： {context.current_date} ; 卖出 {context.security};  {position.total_amount} 股，价格: {current_price} ，最高价: {context.highest_price} \n "
        log.info(log_info)
        write_file('log.txt', str((log_info)), append=True)
        signal = None
