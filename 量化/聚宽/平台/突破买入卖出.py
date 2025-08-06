from datetime import datetime

import pandas as pd
# 导入函数库
from jqdata import *

"""
策略简要
计算频率：分钟/tick
交易品种：恒瑞医药，600276.XSHG
买入：当日价格大于过去4日收盘价最高点时，即当前价格突破5日高点，当日立刻执行买入
买入头寸：全仓买入
止盈卖出：买入第二天开始，盈利时一直持有，当价格从最高价与买入价回落20%时，立刻执行卖出
止损卖出：买入第二天开始，亏损到买入价的95%立刻执行卖出
"""

# 全局变量存储数据
_data_proxy = None
# log.set_level('order', 'error')

def initialize(context):
    # 设置参数
    # set_params(context)

    # 设置交易品种
    context.security = '600276.XSHG'
    # 设置基准 沪：XSHG 深：XSHE
    set_benchmark('600276.XSHG')

    context.buy_price = 0
    context.highest_price = 0
    context.buy_date = None

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


# def set_params(context):


def handle_data_wrapper(context):

    # 获取当天股票数据
    data_df = get_data(context)

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_high = data_df['past_4_days_high'].iloc[-1]
    past_4_days_low = data_df['past_4_days_low'].iloc[-1]
    # 获取当前持仓
    position = context.portfolio.positions.get(context.security)
    log.info(f"获取当前持仓 : {position}")
    has_position = position is not None and position.amount > 0

    # 判断是否应该交易
    signal = should_trade(context, current_price, past_4_days_high,past_4_days_low, has_position)

    # 执行交易
    if signal:
        execute_trade(context, signal, current_price, past_4_days_high,past_4_days_low)


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

    # context.yesterday = context.current_date - datetime.timedelta(days=1)
    # log.info(f"当前时间： {context.yesterday}")

    # 获取历史数据 - 需要足够的数据来计算5日高点
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=5,  # 过去4日数据 + 今日数据
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )
    log.info(f"获取历史数据：\n {hist_daily}")

    past_4_days_high = hist_daily['high'].iloc[-5:-1].max()
    past_4_days_low = hist_daily['low'].iloc[-5:-1].min()
    log.info(f"获取最近几天的最小值数据：\n {past_4_days_low}")

    # # 获取最新bars数据
    # bars_df = get_bars(context.security,
    #                   end_dt=context.current_time,
    #                   count=1,
    #                   unit='1m',
    #                   # 返回标的的开盘价、收盘价、最高价、最低价，成交的数量,时段中成交的金额、复权因子、时间段中的涨停价、时段中跌停价、时段中平均价，是否停牌，前一天收盘价等
    #                   fields=['date', 'open', 'close', 'low', 'high', 'volume', 'money'])
    # log.info(f"获取当前bar数据: \n {bars_df}")

    # context.current_time = bars_df['date']

    ticks_df = get_ticks(context.security,
                         end_dt=context.current_time,
                         count=1,
                         fields=['time', 'current', 'high', 'low', 'volume', 'money'], skip=True, df=True)

    log.info(f"获取当前数据：\n {ticks_df}")

    # 获取最新价格
    security_data = _data_proxy[context.security]

    # 获取价格
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"无法获取价格: {e}")

    # log.info(f"获取最新价格：\n {current_price}")

    # 检查数据是否有效
    if current_price is None or past_4_days_high is None:
        return

    data_df = pd.DataFrame({
        'current_time': [context.current_time]  # 当前时间
        ,'past_4_days_high': [past_4_days_high]  # 前四天最高价
        ,'past_4_days_low':[past_4_days_low]     # 前四天最低价
        ,'current_price': [ticks_df['current'].iloc[-1]]  # 当前价格（ticks_df中current列的最后一个值）
        ,'current_high': [ticks_df['high'].iloc[-1]]
    })
    log.info(f"获取最新数据：\n {data_df}")

    return data_df

# updated_df = pd.concat([existing_df, new_row], ignore_index=True)


def should_trade(context, current_price, past_4_days_high,past_4_days_low, has_position):
    """
    3. 基于策略要求判断当前数据是买入还是卖出
    """
    # 交易信号
    signal = None

    if not has_position:  # 没有持仓时寻找买入机会
        # 当前价格大于过去4日收盘价最高点时买入
        if current_price >= past_4_days_high:
            log.info(f"当前价格 {current_price} 大于等于过去4日收盘价最高点 {past_4_days_high}，准备买入")
            signal = "BUY"

    else :  # 持仓时寻找卖出机会
        # 当前价格大于过去4日收盘价最高点时买入
        if current_price <= past_4_days_low:
            log.info(f"当前价格 {current_price} 小于等于过去4日收盘价最低点 {past_4_days_low}，准备卖出")
            signal = "SELL"

    # else:  # 有持仓时处理止盈止损
    #     # 更新最高价
    #     if current_price > context.highest_price:
    #         context.highest_price = current_price
    #
    #     # 买入第二天开始才能止盈止损
    #     if context.buy_date and context.current_date > context.buy_date:
    #         # 止盈条件：价格从最高价回落20%
    #         stop_profit_price = context.highest_price * 0.8
    #
    #         # 止损条件：价格跌至买入价的95%
    #         stop_loss_price = context.buy_price * 0.95
    #
    #         # 检查是否触发止盈或止损
    #         if current_price <= stop_profit_price or current_price <= stop_loss_price:
    #             log.info(f"当前价格 {current_price} ,价格已跌至止盈或止损条件，准备卖出")
    #             signal = "SELL"

    return signal


def execute_trade(context, signal, current_price, past_4_days_high,past_4_days_low):
    """
    4. 执行买入或卖出操作
    """
    if signal == "BUY":
        # 全仓买入
        cash = context.portfolio.cash
        amount = int(cash * 0.98 / current_price / 100) * 100  # 确保买卖数量是100的整数倍
        qty = amount/100

        if amount > 0:
            # 执行买入
            order(context.security, amount)
            context.buy_price = current_price
            context.highest_price = current_price
            context.buy_date = context.current_date
            log.info(f"买入 {context.security}: {qty} 股，价格: {amount} , 买入价 {current_price}，过去4日最高收盘价: {past_4_days_high}")
            signal = None
    elif signal == "SELL":
        # 执行卖出
        position = context.portfolio.positions.get(context.security)
        order_target_value(context.security, 0)

        log.info(f"卖出 {context.security}: {position.amount} 股，价格: {current_price}，买入价: {context.buy_price}，最高价: {context.highest_price}")
        # 重置状态
        context.buy_price = 0
        context.highest_price = 0
        context.buy_date = None
        signal = None





