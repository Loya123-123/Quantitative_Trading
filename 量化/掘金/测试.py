# coding = udf-8
# /usr/bin/env python
# 我要用聚宽量化做一个量化交易策略，需要将交易策略写成代码，其中策略逻辑如下：
# 交易品种：
# 恒瑞医药：600276.XSHG
# 华东医药：000963.XSHE
# 五粮液：000858.XSHE
# 山西汾酒：600809.XSHG
# 泸州老窖：000568.XSHE
# 科沃斯：603486.XSHG
# 买入：当日dkx金叉时买入，即dkx线上穿10日madkx线时买入
# 买入头寸：每一个品种在不超过98%的资金份额下，尽可能多买
# 卖出：买日第二天开始，当日dkx死叉时卖出，即dkx线向下穿10日madkx线时买入

# 掘金量化AI代码

import pandas as pd
import numpy as np
from gm.api import *

# 全局变量存储数据
_data_proxy = None

def init(context):
    # 设置策略参数
    set_params(context)
    # 设置交易品种
    set_security(context)
    # 设置基准
    set_benchmark('SHSE.000300')

    # 设置交易相关参数
    context.account = context.account_list[0]  # 获取默认账户

    # 设置交易成本和滑点
    # 掘金量化的交易成本设置可能与聚宽不同，这里仅作示例
    # context.set_commission(stock_tax=0.001, stock_commission=0.0003)

    # 定义每日运行的函数
    schedule(schedule_func=before_trading_start, date_rule='1d', time_rule='09:00:00')
    schedule(schedule_func=handle_data, date_rule='1d', time_rule='09:30:00')

def set_params(context):
    # 定义DKX参数
    context.dk_period = 10  # DKX计算周期
    context.madk_period = 10  # MADKX计算周期
    context.max_position_ratio = 0.20  # 单个品种最大资金占比
    context.buy_dates = {}  # 记录每只股票的买入日期

def set_security(context):
    # 定义多只交易品种 - 转换为掘金量化的代码格式
    context.security_list = [
        'SHSE.600276',  # 恒瑞医药
        'SZSE.000963',  # 华东医药
        'SZSE.000858',  # 五粮液
        'SHSE.600809',  # 山西汾酒
        'SZSE.000568',  # 泸州老窖
        'SHSE.603486',  # 科沃斯
    ]

def before_trading_start(context):
    # 获取当前日期
    context.current_date = context.now.date()

    # 为每只股票获取历史数据并计算指标
    hist_data = {}
    for security in context.security_list:
        # 获取历史日K线数据 - 转换为掘金量化API
        hist_daily = history_n(symbol=security, frequency='1d', count=context.dk_period * 3,
                               fields='open,high,low,close', fill_missing='Last', adjust=ADJUST_PREV,
                               df=True)

        # 计算DKX和MADKX
        if not hist_daily.empty:  # 确保数据不为空
            hist_daily = calculate_dkx(hist_daily, context.dk_period, context.madk_period)
            hist_data[security] = hist_daily

    # 保存数据
    context.hist_data = hist_data

# 计算DKX和MADKX指标
def calculate_dkx(df, dk_period=10, madk_period=10):
    # 计算DKX
    # DKX = (3*CLOSE + 2*OPEN + HIGH + LOW)/7
    df['DKX'] = (3 * df['close'] + 2 * df['open'] + df['high'] + df['low']) / 7

    # 计算MADKX - MADKX是DKX的N日简单移动平均
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # 计算DKX和MADKX的前一天值，用于判断金叉死叉
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df

# 交易决策函数
def handle_data(context):
    # 获取当前数据 - 转换为掘金量化API
    global _data_proxy
    current_data = {}
    for security in context.security_list:
        tick = current(symbols=security, df=True)
        if not tick.empty:
            current_data[security] = tick.iloc[0]
    _data_proxy = current_data

    # 遍历每只股票进行交易决策
    for security in context.security_list:
        try:
            # 获取最新价格
            security_data = _data_proxy.get(security)

            if security_data is None:
                continue

            # 获取价格
            current_price = security_data['last_price']

            # 获取历史数据
            hist_daily = context.hist_data.get(security)

            # 确保有足够的数据计算指标
            if hist_daily is None or len(hist_daily) < context.dk_period * 3:
                continue

            # 获取最新的DKX和MADKX值
            dkx_now = hist_daily['DKX'].iloc[-1]
            madkx_now = hist_daily['MADKX'].iloc[-1]
            dkx_prev = hist_daily['DKX_prev'].iloc[-1]
            madkx_prev = hist_daily['MADKX_prev'].iloc[-1]

            # 获取当前持仓 - 转换为掘金量化API
            positions = context.account().position(symbol=security, side=PositionSide_Long)
            has_position = len(positions) > 0

            # 交易策略逻辑
            if not has_position:  # 没有持仓时考虑买入
                # 买入条件：当日DKX金叉，即DKX线上穿MADKX线
                if dkx_prev <= madkx_prev and dkx_now > madkx_now:
                    # 计算买入数量 - 单个品种不超过20%的资产份额
                    account_info = context.account().info()
                    total_value = account_info['nav']  # 总资产
                    max_position_value = total_value * context.max_position_ratio

                    # 考虑已有持仓占用的资金
                    current_position_value = 0
                    for pos in context.account().positions():
                        if pos['symbol'] in context.security_list:
                            current_position_value += pos['position_value']

                    # 可用资金 = 总资产 * 最大比例 - 已有持仓价值
                    available_cash = max_position_value - current_position_value
                    available_cash = max(available_cash, 0)  # 确保可用资金非负

                    # 计算可买入数量
                    amount = int(available_cash * 0.98 / current_price / 100) * 100  # 确保买入股数是100的整数倍

                    if amount > 0:
                        # 执行买入 - 转换为掘金量化API
                        order_volume(symbol=security, volume=amount, side=OrderSide_Buy,
                                     order_type=OrderType_Market, position_effect=PositionEffect_Open)
                        context.buy_dates[security] = context.current_date
                        print(f"买入 {security}: {amount} 股，价格: {current_price}，DKX: {dkx_now:.2f}，MADKX: {madkx_now:.2f}")
            else:  # 有持仓时考虑卖出
                # 卖出条件：买日第二天开始，当日DKX死叉，即DKX线下穿MADKX线
                buy_date = context.buy_dates.get(security)
                if buy_date and context.current_date > buy_date:
                    if dkx_prev >= madkx_prev and dkx_now < madkx_now:
                        # 获取持仓数量
                        position = positions[0]
                        amount = position['volume']

                        # 执行卖出 - 转换为掘金量化API
                        order_volume(symbol=security, volume=amount, side=OrderSide_Sell,
                                     order_type=OrderType_Market, position_effect=PositionEffect_Close)
                        if security in context.buy_dates:
                            del context.buy_dates[security]
                        print(f"卖出 {security}: {amount} 股，价格: {current_price}，DKX: {dkx_now:.2f}，MADKX: {madkx_now:.2f}")
        except Exception as e:
            print(f"处理 {security} 时出错: {e}")
            continue