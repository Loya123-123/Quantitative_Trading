
import pandas as pd
from datetime import datetime

# 全局变量存储数据
_data_proxy = None

# 恒瑞医药  600276.XSHG
# 华东医药  000963.XSHE

def initialize(context):
    # 设置策略参数
    set_params(context)

    context.current_date = context.current_dt.date()

    # 设置交易品种
    context.security = '600276.XSHG'
    # 设置基准 沪：XSHG  深：XSHE
    set_benchmark('600276.XSHG')
    # 设置交易相关参数
    set_option('use_real_price', True)

    # 设置交易成本和滑点
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), 'stock')
    set_slippage(FixedSlippage(0.02))

    # 定义每日运行的函数
    run_daily(before_trading_start, time='before_open')

    # 直接注册全局函数
    run_daily(handle_data_wrapper, time='every_bar')


def set_params(context):
    # 定义DKX参数
    context.dk_period = 10  # DKX计算周期
    context.madk_period = 10  # MADKX计算周期
    context.buy_date = None  # 记录买入日期




def before_trading_start(context):
    # 获取当前日期
    context.current_date = context.current_dt.date()
    log.info(f"获取当前日期: {context.current_date}")

    # 获取历史日K线数据 - 增加足够的天数用于计算DKX
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=context.dk_period * 4,  # 增加数据量以确保指标计算准确
        frequency='1d',
        # fq='pre',
        fields=['open', 'high', 'low', 'close'],  # 需要更多字段计算DKX
        skip_paused=True
    )

    # 计算DKX和MADKX
    hist_daily = calculate_dkx(hist_daily, context.madk_period)
    log.info("历史日K线数据:")
    for index, row in hist_daily[['open', 'high', 'low', 'close', 'DKX', 'MADKX', 'DKX_prev', 'MADKX_prev']].iterrows():
        log.info(
            f"日期   {index}, 开盘价:    {row['open']}, 最高价:    {row['high']}, 最低价:    {row['low']}, 收盘价: {row['close']}, DKX:    {row['DKX']}, MADKX:  {row['MADKX']},DKX_prev: {row['DKX_prev']} , MADKX_prev :  {row['MADKX_prev']}")

    # 保存数据
    context.hist_daily = hist_daily


# 计算DKX和MADKX指标
def calculate_dkx(df, madk_period):
    # 计算DKX
    # MID = (3*CLOSE + OPEN + HIGH + LOW)/6
    df['MID'] = (3 * df['close'] +  df['open'] + df['high'] + df['low']) / 6
    # df['DKX'] = df.apply(lambda row: row['open'] if row.name.date() == context.current_date else (3 * row['close'] + 2 * row['open'] + row['high'] + row['low']) / 7, axis=1)
    # (20×MID+19×昨日MID+18×2日前的MID+17×3日前的MID+16×4日前的MID+15×5日前的MID+14×6日前的MID+13×7日前的MID+12×8日前的MID+11×9日前的MID十10×10日前的MID+9×U日前的MID+8×12日前的MID+7×13日前的M1D+6×14日前的MID+5×15日前的MID+4×16日前的MID+3×17日前的MID+2×18日前的MID+20日前的MID)÷210
    df['DKX'] = (20 * df['MID'] + 19 * df['MID'].shift(1) + 18 * df['MID'].shift(2) + 17 * df['MID'].shift(3)
                 + 16 * df['MID'].shift(4) + 15 * df['MID'].shift(5) + 14 * df['MID'].shift(6) + 13 * df['MID'].shift(7)
                 + 12 * df['MID'].shift(8) + 11 * df['MID'].shift(9) + 10 * df['MID'].shift(10) + 9 * df['MID'].shift(11)
                 + 8 * df['MID'].shift(12) + 7 * df['MID'].shift(13) + 6 * df['MID'].shift(14) + 5 * df['MID'].shift(15)
                 + 4 * df['MID'].shift(16) + 3 * df['MID'].shift(17) + 2 * df['MID'].shift(18) + df['MID'].shift(19)) / 210
    # 计算MADKX - MADKX是DKX的N日简单移动平均
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # 计算DKX和MADKX的前一天值，用于判断金叉死叉
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df


# 全局函数包装器
def handle_data_wrapper(context):
    global _data_proxy
    _data_proxy = get_current_data()
    handle_data(context, _data_proxy)


# 交易决策函数
def handle_data(context, data):
    # 获取最新价格
    security_data = data[context.security]

    # 获取价格
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"无法获取价格: {e}")
        return

    # 获取历史数据
    hist_daily = context.hist_daily

    # 确保有足够的数据计算指标
    if len(hist_daily) < context.dk_period * 3:
        return

    # 获取最新的DKX和MADKX值
    dkx_now = hist_daily['DKX'].iloc[-2]
    madkx_now = hist_daily['MADKX'].iloc[-2]
    dkx_prev = hist_daily['DKX_prev'].iloc[-2]
    madkx_prev = hist_daily['MADKX_prev'].iloc[-2]

    # 获取当前持仓
    position = context.portfolio.positions.get(context.security)
    has_position = position is not None and position.amount > 0

    # 交易策略逻辑
    if not has_position:  # 没有持仓时考虑买入
        # 买入条件：当日DKX金叉，即DKX线上穿MADKX线
        if dkx_prev <= madkx_prev and dkx_now > madkx_now:
            # 计算买入数量 - 全仓买入
            cash = context.portfolio.cash
            amount = int(cash * 0.98 / current_price / 100) * 100  # 确保买入股数是100的整数倍

            if amount > 0:
                # 执行买入
                order(context.security, amount)
                context.buy_date = context.current_date
                log.info(
                    f"买入 {context.security}: {amount} 股，价格: {current_price}，DKX: {dkx_now:.2f}，MADKX: {madkx_now:.2f}")
    else:  # 有持仓时考虑卖出
        # 卖出条件：买日第二天开始，当日DKX死叉，即DKX线下穿MADKX线
        if context.buy_date and context.current_date > context.buy_date:
            if dkx_prev >= madkx_prev and dkx_now < madkx_now:
                # 执行卖出
                order_target_value(context.security, 0)
                log.info(
                    f"卖出 {context.security}: {position.amount} 股，价格: {current_price}，DKX: {dkx_now:.2f}，MADKX: {madkx_now:.2f}")
                context.buy_date = None
