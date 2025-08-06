# coding=utf-8
from __future__ import print_function, absolute_import
from gm.api import *

import numpy as np
import pandas as pd

def init(context):
    """
    策略初始化
    :param context:
    :return:
    """
    print('开始加载')
    # 订阅恒瑞医药的股票行情，这里以600276.SH为例，频率为日线 获取30个交易日数据（用于计算10日均线）

    subscribe(symbols='SHSE.600276', frequency='1d', count=30)

    # 设置交易品种
    context.symbol = 'SHSE.600276'

    # 记录是否持仓的标志
    context.hold = False

    # 每日定时任务
    schedule(schedule_func=algo, date_rule='1d', time_rule='09:30:00')


# 定时任务回调函数：用于执行交易逻辑
def algo(context):
    """
    每日交易逻辑
    :param context:
    :return:
    """
    # 当前时间
    now_str = context.now.strftime('%Y-%m-%d')

    # 获取最新行情数据
    bar = current(symbols=context.symbol)[0]

    # 获取历史数据用于计算指标. 获取11日历史数据（含当日）
    history_data = history_n(
        symbol=context.symbol,
        frequency='1d',
        count=11,  # 获取11天数据，因为需要10日均线
        fields='close,high,low,open',
        fill_missing='Last',
        adjust=ADJUST_PREV,
        end_time=now_str,
        df=True
    )

    # 计算DKX指标
    def calculate_dkx(data):
        # DKX计算公式：(收盘价*3 + 开票价*2 + 最低价 + 最高价)/7
        return (data['close'] * 3 + data['open'] * 2 + data['low'] + data['high']) / 7

    # 计算DKX和10日MADKX
    history_data['dkx'] = calculate_dkx(history_data)
    # 计算移动平均
    history_data['madkx'] = history_data['dkx'].rolling(window=10).mean()

    # 获取当前和前一天的DKX和MADKX值
    current_dkx = history_data.iloc[-1]['dkx']
    current_madkx = history_data.iloc[-1]['madkx']
    prev_dkx = history_data.iloc[-2]['dkx']
    prev_madkx = history_data.iloc[-2]['madkx']

    # 判断是否形成金叉（DKX上穿MADKX） 昨日DKX < 均线 且 今日DKX > 均线
    golden_cross = (prev_dkx < prev_madkx) and (current_dkx > current_madkx)

    # 判断是否形成死叉（DKX下穿MADKX） 昨日DKX > 均线 且 今日DKX < 均线
    dead_cross = (prev_dkx > prev_madkx) and (current_dkx < current_madkx)

    # 获取当前持仓
    position = context.account().position(symbol=context.symbol, side=PositionSide_Long)

    # 交易逻辑 金叉+无持仓 → 全仓买入
    if not context.hold and golden_cross:
        # 全仓买入
        cash = context.account().cash['available']
        price = bar['price']
        volume = int(cash / price / 100) * 100  # 按手数取整

        if volume > 0:
            order_volume(symbol=context.symbol, volume=volume, side=OrderSide_Buy,
                         order_type=OrderType_Market, position_effect=PositionEffect_Open)
            context.hold = True
            print(f'买入 {context.symbol} {volume}股，价格 {price}')
    # 死叉+有持仓
    elif context.hold and dead_cross:
        # 卖出全部持仓
        position = context.account().position(symbol=context.symbol, side=PositionSide_Long)
        if position:
            order_volume(symbol=context.symbol, volume=position['volume'], side=OrderSide_Sell,
                         order_type=OrderType_Market, position_effect=PositionEffect_Close)
            context.hold = False
            print(f'卖出 {context.symbol} {position["volume"]}股，价格 {bar["price"]}')


def on_order_status(context, order):
    """
    订单状态回调
    :param context:
    :param order:
    :return:
    """
    # 标的代码
    symbol = order['symbol']
    # 委托价格
    price = order['price']
    # 委托数量
    volume = order['volume']
    # 目标仓位
    target_percent = order['target_percent']
    # 查看下单后的委托状态，等于3代表委托全部成交
    status = order['status']
    # 买卖方向，1为买入，2为卖出
    side = order['side']
    # 开平仓类型，1为开仓，2为平仓
    effect = order['position_effect']
    # 委托类型，1为限价委托，2为市价委托
    order_type = order['order_type']
    if status == 3: # 完全成交
        if effect == 1:
            if side == 1:
                side_effect = '开多仓'
            else:
                side_effect = '开空仓'
        else:
            if side == 1:
                side_effect = '平空仓'
            else:
                side_effect = '平多仓'
        order_type_word = '限价' if order_type==1 else '市价'
        print('{}:标的：{}，操作：以{}{}，委托价格：{}，委托数量：{}'.format(context.now,symbol,order_type_word,side_effect,price,volume))


def on_backtest_finished(context, indicator):
    """
    回测结束回调
    :param context:
    :param indicator:
    :return:
    """
    print('*'*50)
    print('回测已完成，请通过右上角“回测历史”功能查询详情。')


if __name__ == '__main__':
    '''
        strategy_id策略ID, 由系统生成
        filename文件名, 请与本文件名保持一致
        mode运行模式, 实时模式:MODE_LIVE回测模式:MODE_BACKTEST
        token绑定计算机的ID, 可在系统设置-密钥管理中生成
        backtest_start_time回测开始时间
        backtest_end_time回测结束时间
        backtest_adjust股票复权方式, 不复权:ADJUST_NONE前复权:ADJUST_PREV后复权:ADJUST_POST
        backtest_initial_cash回测初始资金
        backtest_commission_ratio回测佣金比例
        backtest_slippage_ratio回测滑点比例
        backtest_match_mode市价撮合模式，以下一tick/bar开盘价撮合:0，以当前tick/bar收盘价撮合：1
        '''
    run(strategy_id='bb053e65-661a-11f0-952b-00ff59c3fc0a',
        filename='main.py',
        mode=MODE_BACKTEST,
        token='0f9176cab6b0db47c6e743efb0c1021d8b47b391',
        backtest_start_time='2020-11-01 08:00:00',
        backtest_end_time='2023-11-10 16:00:00',
        backtest_adjust=ADJUST_PREV,
        backtest_initial_cash=10000,
        backtest_commission_ratio=0.0001,
        backtest_slippage_ratio=0.0001,
        backtest_match_mode=1)