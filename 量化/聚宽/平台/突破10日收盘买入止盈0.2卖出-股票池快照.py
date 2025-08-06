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

买入：当日价格大于过去10日收盘价最高点时，即当前价格突破10日高点，当日立刻执行买入
止盈卖出1：买入第二天开始，当价格<前4日收盘价时，且价格<最高价-（最高价-买入价）*20%时，立刻执行卖出
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

    # 注册交易处理函数
    run_daily(handle_data_wrapper, time='every_bar')


def set_params(context):
    # 止盈1比例
    context.stop_profit_ratio1 = 0.2
    # 止损比例
    context.stop_loss_ratio = 0.95




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
        count=20,  # 过去4日数据 + 今日数据
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

    # 最后一天为采集数据的当前
    hist_daily.loc[last_day_index, 'close'] = ticks_df['current'].iloc[-1]
    hist_daily.loc[last_day_index, 'low'] = ticks_df['low'].iloc[-1]
    hist_daily.loc[last_day_index, 'high'] = ticks_df['high'].iloc[-1]

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
        , 'past_10_days_high': [past_10_days_high]  # 前十天收盘价最高价
        , 'current_price': [ticks_df['current'].iloc[-1]]  # 当前价格（ticks_df中current列的最后一个值）
        , 'current_high': [ticks_df['high'].iloc[-1]]
        , 'past_yest_days_low': [past_yest_days_low]
    })

    # log.info(f"股票代码： {context.security} \n ; 获取最新数据：\n {data_df}")

    return data_df


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

    # 获取当前持仓
    position = context.portfolio.positions.get(context.security)
    # log.info(f"股票代码： {context.security} ; 获取当前持仓 : {position}")

    # 获取是否当前持仓
    has_position = position is not None and position.total_amount > 0
    # log.info(f"股票代码： {context.security} ; 当前是否持仓 : {has_position}")

    # 最后一次交易时间
    transact_time = position.transact_time
    # log.info(f"股票代码： {context.security} ; 获取最后交易时间 : {transact_time}")

    if not has_position:  # 没有持仓时寻找买入机会
        # 当日价格大于过去10日收盘价最高点
        if current_price >= past_10_days_high:
            log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 当前价格 {current_price} ; 10日收盘价最高点 {past_10_days_high} ，准备买入 \n "
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

        # 止盈卖出1： 止买入第二天开始，当价格<最小的前4日收盘价时，且价格<最高价-（最高价-买入价）*20%，立刻执行卖出
        if current_price <= past_4_days_close_min and current_price <= stop_profit_price1:
            log_info = f"当前日期： {context.current_date} ; 股票代码： {context.security} ; 触发止盈条件1： 前4日收盘价最低点位：{past_4_days_close_min} ,止盈点： {stop_profit_price1} ,当前价为： {current_price} , 准备卖出 \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)
            signal = "SELL"

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
