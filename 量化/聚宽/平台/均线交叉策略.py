from datetime import datetime
import pandas as pd
# 引入函数库
from jqdata import *

"""
策略要求
交易频率：分钟/tick
交易品种：医药行业股票，如恒瑞医药600276.XSHG  长江水电 '600900.XSHG'  中国石油 '601857.XSHG'
策略逻辑： 
买入条件：前2天的10日均线<20日均线，前一天的10日均线>=20日均线，则买入
卖出条件：前2天的10日均线>=20日均线，前一天的10日均线<20日均线，则卖出
"""

# 全局变量存储数据
_data_proxy = None

def initialize(context):
    # 设置参数
    set_params(context)

    # g.stocks = ['600276.XSHG','000963.XSHE','000858.XSHE','600809.XSHG','000568.XSHE']

    # g.stocks = ['600276.XSHG','600900.XSHG']

    g.stocks = ['601857.XSHG']

    # 设置基准 指数：XSHG 基准：XSHE
    set_benchmark('601857.XSHG')

    # 设置交易参数
    set_option('use_real_price', True)

    # 设置交易成本和滑点
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), 'stock')
    set_slippage(FixedSlippage(0.02))

    # 注册每日处理函数
    run_daily(handle_data_wrapper, time='09:30')


def set_params(context):
    # 设置均线周期
    context.short_period = 10
    context.long_period = 20


def log_message(message):
    """
    统一的日志处理函数，同时输出到控制台和文件
    :param context: 策略上下文
    :param message: 日志消息
    """
    # 输出到控制台
    log.info(message)

    # 写入到文件
    write_file('ma_cross_log.txt', message + '\n', append=True)


def handle_data_wrapper(context):
    for security in g.stocks:
        # 设置交易品种
        context.security = security
        # 获取交易数据
        data_df = get_data(context)

        if data_df is None:
            continue

        # 检查是否满足交易条件
        signal = should_trade(context, data_df)

        # 执行交易
        if signal:
            execute_trade(context, signal)


def get_data(context):
    """
    获取交易所需的数据
    :param context:
    :return:
    """
    global _data_proxy
    _data_proxy = get_current_data()
    # 当前日期
    context.current_date = context.current_dt.date()

    # 当前时间
    context.current_time = datetime.datetime.combine(context.current_date, context.current_dt.time())

    # 获取历史数据 - 需要足够数据来计算均线
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=context.long_period + 2,  # 多获取几天数据确保计算准确
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )

    if len(hist_daily) < context.long_period + 2:
        return None

    # 计算均线
    hist_daily['ma_short'] = hist_daily['close'].rolling(window=context.short_period).mean()
    hist_daily['ma_long'] = hist_daily['close'].rolling(window=context.long_period).mean()

    # 获取前2天和前一天的均线数据
    # 前2天的数据
    hist_daily['ma_short_2days_ago'] = hist_daily['ma_short'].iloc[-3]
    hist_daily['ma_long_2days_ago'] = hist_daily['ma_long'].iloc[-3]

    # 前一天的数据
    hist_daily['ma_short_1day_ago'] = hist_daily['ma_short'].iloc[-2]
    hist_daily['ma_long_1day_ago'] = hist_daily['ma_long'].iloc[-2]

    # 当前价格
    security_data = _data_proxy[context.security]
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"无法获取价格: {e}")
        return None

    data_df = pd.DataFrame({
        'current_time': [context.current_time],
        'current_price': [current_price],
        'ma_short_2days_ago': [hist_daily['ma_short_2days_ago'].iloc[-1]],
        'ma_long_2days_ago': [hist_daily['ma_long_2days_ago'].iloc[-1]],
        'ma_short_1day_ago': [hist_daily['ma_short_1day_ago'].iloc[-1]],
        'ma_long_1day_ago': [hist_daily['ma_long_1day_ago'].iloc[-1]],
        'ma_short_today': [hist_daily['ma_short'].iloc[-1]],
        'ma_long_today': [hist_daily['ma_long'].iloc[-1]]
    })

    return data_df


def should_trade(context, data_df):
    """
    判断是否应该交易
    """
    # 初始化信号
    signal = None

    # 获取当前持仓
    position = context.portfolio.positions.get(context.security)
    has_position = position is not None and position.total_amount > 0

    # 获取均线数据
    ma_short_2days_ago = data_df['ma_short_2days_ago'].iloc[0]
    ma_long_2days_ago = data_df['ma_long_2days_ago'].iloc[0]
    ma_short_1day_ago = data_df['ma_short_1day_ago'].iloc[0]
    ma_long_1day_ago = data_df['ma_long_1day_ago'].iloc[0]

    # 检查数据有效性
    if pd.isna(ma_short_2days_ago) or pd.isna(ma_long_2days_ago) or \
            pd.isna(ma_short_1day_ago) or pd.isna(ma_long_1day_ago):
        return signal

    # 买入条件：前2天的10日均线<20日均线，前一天的10日均线>=20日均线
    if not has_position:
        if ma_short_2days_ago < ma_long_2days_ago and ma_short_1day_ago >= ma_long_1day_ago:
            log_message( f"当前日期：{context.current_date} ; 股票代码：{context.security} ; 满足买入条件：前2天短均线 {ma_short_2days_ago:.2f} < 长均线 {ma_long_2days_ago:.2f} 且前一天短均线 {ma_short_1day_ago:.2f} >= 长均线 {ma_long_1day_ago:.2f}")
            signal = "BUY"

    # 卖出条件：前2天的10日均线>=20日均线，前一天的10日均线<20日均线
    else:
        if ma_short_2days_ago >= ma_long_2days_ago and ma_short_1day_ago < ma_long_1day_ago:
            log_message( f"当前日期：{context.current_date} ; 股票代码：{context.security} ; 满足卖出条件：前2天短均线 {ma_short_2days_ago:.2f} >= 长均线 {ma_long_2days_ago:.2f} 且前一天短均线 {ma_short_1day_ago:.2f} < 长均线 {ma_long_1day_ago:.2f}")
            signal = "SELL"

    return signal


def execute_trade(context, signal):
    """
    执行交易
    """
    current_price = get_current_data()[context.security].last_price

    if signal == "BUY":
        # 使用固定资金买入
        cash = 20000
        amount = int(cash * 0.98 / current_price / 100) * 100  # 确保买卖数量是100的整数倍
        qty = amount / 100

        # 买入总价
        total_amount = current_price * amount

        if amount > 0:
            # 执行买入
            buy_order = order(context.security, amount)
            log_message( f"当前日期：{context.current_date} ; 买入 {context.security} ; {qty} 手, 数量: {amount}, 买入总价 {total_amount}, , 价格 {current_price}")
            log_message(str(buy_order))
    elif signal == "SELL":
        # 卖出所有持仓
        position = context.portfolio.positions.get(context.security)
        if position and position.total_amount > 0:
            sell_order = order_target_value(context.security, 0)
            log_message( f"当前日期：{context.current_date} ; 卖出 {context.security}; 数量: {position.total_amount} , 价格: {current_price}")
            log_message(str(sell_order))

