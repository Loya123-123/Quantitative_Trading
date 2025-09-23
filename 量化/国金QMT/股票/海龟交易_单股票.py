# coding:gbk
"""
海龟交易策略股票版
基于国金QMT平台实现的海龟交易策略

该策略具有完整的规则体系，包括：
计算频率：分钟
交易品种： 股票 ，代码待定，先请一个变量。
提前计算的指标：前10日ATR平均值，并记录下来
买入1（做多）：当日价格>前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
做多止盈卖出1：买入第二天开始，当价格<前4日收盘价最低点时，且价格 < 最高价-（最高价-买入价）*20% （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
做多止损卖出1：买入第二天开始，当价格 < 买入价-2*ATR时，立刻执行卖出
注： 10 、 20% 、 4 、2 为变量策略提调优确定
买入头寸：资金量=100000，单只股票单次买入金额10000，按照最大股数买

"""
# coding:gbk


import logging
from datetime import datetime

import numpy as np
import pandas as pd


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"C:\datalog\datalog-{timestamp}.log"
    logging.basicConfig(filename=filename, level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    log_info("开始初始化海龟交易策略...")

    # 设置交易标的（以螺纹钢期货为例，实际使用时请根据需要修改）
    ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market

    # ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])
    log_debug(f"[初始化] 设置交易标的: {ContextInfo.stock_code}")
    dividend_type = ContextInfo.dividend_type
    log_debug(f"[初始化] 复权方式: {dividend_type}")
    # 策略参数
    g.entry_window = 10  # 入市通道周期（突破周期）
    g.exit_window = 4  # 止盈通道周期
    g.atr_window = 10  # ATR计算周期
    g.stop_profit_ratio = 0.2  # 止盈比例
    g.position_limit = 5  # 持仓上线
    g.stop_loss_multiplier = 1  # 止损ATR倍数
    g.capital_rate = 0.1  # 资金比例 暂时无效
    g.long_capital = 10000  # 做多资金

    log_info(f"[初始化] 策略参数设置完成:")
    log_info(f"        入市通道周期: {g.entry_window}")
    log_info(f"        止盈通道周期: {g.exit_window}")
    log_info(f"        ATR计算周期: {g.atr_window}")
    log_info(f"        止盈比例: {g.stop_profit_ratio}")
    log_info(f"        止损ATR倍数: {g.stop_loss_multiplier}")
    log_info(f"        资金: {g.long_capital}")

    # 策略状态变量初始化
    g.highest_after_entry = 0  # 入市后的最高价
    g.lowest_after_entry = 0  # 入市后的最低价
    g.N = 0  # 波动幅度(N值/ATR)
    g.long_position = 0  # 持仓：0-无仓位，1-持有
    g.current_date = None  # 回测时间
    g.long_open_date = None  # 重置开仓日期
    g.long_volume = 0  # 持仓量
    g.long_use_volume = 0  # 可用持仓量
    g.long_entry_price = 0  # 持仓成本价

    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID  # 回测
    # ContextInfo.account_id = account  # 期货账户ID 实盘

    log_info(f"        期货账户ID: {ContextInfo.account_id}")

    log_info("海龟交易策略初始化完成")
    # 实盘使用
    # ContextInfo.run_time("run_time_handlebar", "60nSecond", "2025-01-01 09:30:00") # 实盘


def handlebar(ContextInfo):  # 回测
    # def run_time_handlebar(ContextInfo):  # 定时运行  # 实盘

    """
    主要处理函数
    在每个K线周期都会被调用
    """

    # 实盘使用
    # if not ContextInfo.is_last_bar():
    #     log_info("[处理函数] 当前不是最后一个K线周期，跳过本次处理")
    #     return

    log_info("=" * 60)
    log_info("[处理函数] 开始执行handlebar函数")

    # 获取历史数据 获取数据的截止时间
    g.current_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    log_info(f"  获取截止时间: {g.current_date}")
    # 时间如果是九点整时，当前分钟交易
    if g.current_date[9:12] == "0900":
        log_info(f"  当前分钟不交易{g.current_time}")
        return
    # 检查数据是否足够
    required_data = max(g.entry_window, g.exit_window, g.atr_window)
    log_debug(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
    if ContextInfo.barpos < required_data:
        log_info("[数据检查] 数据不足，跳过本次处理")
        return

    try:

        # 获取计算需要的数据
        price_data = get_price_data(ContextInfo)
        log_debug(f'[数据获取]: \n {str(price_data)}')
        if price_data is None or len(price_data) <= max(g.entry_window, g.atr_window):
            log_info("[数据获取] 数据不足，跳过本次处理")
            return
        log_debug(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

        # 计算ATR和N值
        g.N = calculate_atr(price_data, g.atr_window)

        if g.N <= 0:
            log_info("[ATR计算] ATR值计算异常，跳过本次处理")
            return
        log_debug(f"[ATR计算] 当前ATR(N值): {g.N:.4f}")

        # 获取当前账户信息
        account_info = get_account_info(ContextInfo)
        if account_info is None:
            log_info("[账户信息] 无法获取账户信息，跳过本次处理")
            return
        log_debug("[账户信息] 成功获取账户信息")

        # g.long_capital = account_info.get('available') * g.capital_rate  # 做多资金 总价 * 10%
        log_debug(f"        做多资金: {g.long_capital}")

        # 决策分区 - 判断是否需要交易
        signal_type = generate_signal(ContextInfo, price_data)
        log_debug(f"[信号生成] 生成的交易信号: {signal_type}")

        # 执行买卖操作
        if signal_type != 0:
            execute_trade(ContextInfo, signal_type, price_data)
        else:
            log_info("[交易执行] 无交易信号，继续观察市场")

    except Exception as e:
        log_info(f"[异常处理] 处理过程中发生错误: {e}")
    log_info("[处理函数] handlebar函数执行完成")
    log_info("=" * 60)


def get_price_data(ContextInfo):
    """
    获取计算需要的数据
    返回包含OHLC数据的DataFrame
    """
    try:

        # 计算需要的历史数据天数
        required_bars = max(g.entry_window, g.exit_window, g.atr_window) + 5
        log_debug(f"  [价格数据] 需要获取 {required_bars} 条历史数据")

        # 获取非当日的历史数据，使用1d周期
        history_market_data = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=g.current_date,
            period='1d',
            count=required_bars,
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )
        if not history_market_data or ContextInfo.stock_code not in history_market_data:
            log_info("  [价格数据] 获取历史市场数据为空")
            return None

        history_df = history_market_data[ContextInfo.stock_code]

        # 将时间戳转换为可读的时间格式
        history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

        log_debug(
            f"  [价格数据] 请求参数 - 标的: {ContextInfo.stock_code}, 周期: {ContextInfo.period}, 数量: 1")

        current_market_data_more = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            start_time=g.current_date[:8] + '000000',  # 当天00:00:00开始
            end_time=g.current_date,
            period=ContextInfo.period,  # 使用1分钟周期
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )

        if not current_market_data_more or ContextInfo.stock_code not in current_market_data_more:
            log_info("  [价格数据] 获取当日市场数据为空")
            return None
        current_df_more = current_market_data_more[ContextInfo.stock_code]
        current_df_more['time'] = current_df_more['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))
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
        log_debug(f"  获取当天数据: \n {current_df}")
        # 替换历史数据中的最后一条为当日最新数据
        if len(history_df) > 0 and len(current_df) > 0:
            # 删除历史数据中的最后一条（当天数据）
            history_df = history_df[:-1]
            # 将当日最新数据添加到历史数据末尾
            df = pd.concat([history_df, current_df], ignore_index=True)
        else:
            df = history_df
        return df

    except Exception as e:
        log_info(f"  [价格数据] 获取价格数据时发生错误: {e}")
        return None


def calculate_atr(data, window):
    """
    计算ATR(N值)
    ATR是真实波幅的N日平均值，用于衡量市场波动性
    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        log_debug(f"  [ATR计算] 开始计算ATR，使用 {window} 日数据")
        # 计算真实波幅(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        log_debug(f"  [ATR计算] 价格数据统计:")
        log_debug(f"    最高价范围: {high[-window - 1:-1]}")
        log_debug(f"    最低价范围: {low[-window - 1:-1]}")
        log_debug(f"    收盘价范围: {close[-window - 1:-1]}")
        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))
        log_debug(f"  [ATR计算] 计算得到TR值: {tr[-window:]}")
        # 计算ATR(N日均值)
        atr = np.mean(tr[-window:])
        log_debug(f"  [ATR计算] ATR计算结果: {atr}")
        # TR值和ATR值写到data中用于查询记录信息
        # 修复长度不匹配问题：tr数组比原始数据少一个元素（因为计算差值）
        data['tr'] = np.append([np.nan], tr)  # 在前面添加NaN以匹配长度
        data['atr'] = atr
        return atr

    except Exception as e:
        log_info(f"  [ATR计算] 计算ATR时发生错误: {e}")
        return 0


def get_account_info(ContextInfo):
    """
    获取账户信息
    包括可用资金、总权益、持仓等
    """
    try:
        log_debug("  [账户信息] 开始获取账户信息...")

        # 获取账户资金信息
        log_debug("  [账户信息] 获取账户资金详情...")
        account_details = get_trade_detail_data(ContextInfo.account_id, 'STOCK', 'ACCOUNT')
        if not account_details:
            log_debug("  [账户信息] 获取账户详情失败")
            return None

        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益
        # 回撤参数获取保证金比例 系统配置参数
        # margin_rate = account.m_dMaxMarginRate  # 保证金
        # ContextInfo.margin_rate = margin_rate  # 保证金

        log_info(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")

        # 获取未成交委托信息并撤销未成交委托
        log_debug("  [账户信息] 获取未成交委托详情...")
        order_details = get_trade_detail_data(ContextInfo.account_id, 'STOCK', 'ORDER')
        if order_details:
            log_info(f"  [账户信息] 获取到 {len(order_details)} 条委托记录")
            for order in order_details:
                # 获取委托状态，50-54表示未成交状态
                order_status = order.m_nOrderStatus
                symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID

                # 检查是否为未成交状态(状态码49-54)
                if 49 <= order_status < 54:
                    log_info(
                        f"  [账户信息] 发现未成交委托，合约: {symbol}, 状态: {order_status}, 委托编号: {order.m_strOrderSysID}")
                    # 撤销未成交委托
                    cancel_result = cancel(order.m_strOrderSysID, ContextInfo.account_id, 'STOCK', ContextInfo)
                    log_info(f"  [账户信息] 撤销委托结果: {cancel_result}")
                else:
                    log_debug(f"  [账户信息] 合约: {symbol} ,委托状态为: {order_status}，无需撤销")
        else:
            log_info("  [账户信息] 无委托记录")

        # 获取持仓信息
        log_debug("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'STOCK', 'POSITION')
        PositionInfo_dict = {}
        PositionInfo_dfs = pd.DataFrame()
        if position_details:
            log_debug(f"  [账户信息] 获取到 {len(position_details)} 条持仓记录")
            for pos in position_details:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                if symbol == ContextInfo.stock_code and pos.m_nVolume != 0:
                    position_type = pos.m_nDirection

                    g.long_position = 1
                    g.long_open_date = pos.m_strOpenDate  # 开仓日期

                    g.long_volume = pos.m_nVolume  # 持仓量
                    g.long_use_volume = pos.m_nCanUseVolume  # 可用持仓量
                    g.long_entry_price = pos.m_dOpenPrice  # 持仓成本

                    PositionInfo_dict['持仓量'] = pos.m_nVolume  # 持仓量
                    PositionInfo_dict['代码'] = symbol
                    PositionInfo_dict['持仓类型'] = position_type  # 48：多 49：空
                    PositionInfo_dict['持仓成本'] = pos.m_dOpenPrice
                    PositionInfo_dict['持仓盈亏'] = pos.m_dPositionProfit
                    PositionInfo_dict['开仓日期'] = pos.m_strOpenDate
                    PositionInfo_dict['可用持仓量'] = pos.m_nCanUseVolume
                    PositionInfo_df = pd.DataFrame([PositionInfo_dict])

                PositionInfo_dfs = pd.concat([PositionInfo_dfs, PositionInfo_df], ignore_index=True)

            log_info(f"    [账户信息] 持仓: {str(PositionInfo_dfs)} ")
            log_debug(f"  [账户信息] 更新持仓状态: ={g.long_position} ")

        else:
            log_info("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            'PositionInfo_dfs': PositionInfo_dfs,
            'PositionInfo_dict': PositionInfo_dict  # 返回更多持仓信息
        }

    except Exception as e:
        log_info(f"  [账户信息] 获取账户信息时发生错误: {e}")
        return None


def generate_signal(ContextInfo, price_data):
    """
    决策分区 - 生成交易信号
    根据修改后的海龟交易法则生成买入、卖出或持有信号
    返回: signal_type
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    """

    try:
        # 获取当前最高价
        current_price = price_data['close'].values[-1]
        current_high = price_data['high'].values[-1]
        current_low = price_data['low'].values[-1]

        # 计算入市信号 - 前N日高低点突破
        # 做多：过去entry_window天收盘价的最高价
        upper_channel = price_data['close'].iloc[-g.entry_window - 1:-1].max()

        # 做空：过去entry_window天收盘价的最低价
        lower_channel = price_data['close'].iloc[-g.entry_window - 1:-1].min()

        # 计算离市信号 - 离市通道
        # 做多止盈 过去exit_window天收盘价的最低价
        exit_lower = price_data['close'].iloc[-g.exit_window - 1:-1].min()

        # 做空止盈 过去exit_window天收盘价的最高价
        exit_upper = price_data['close'].iloc[-g.exit_window - 1:-1].max()

        log_info(f"  [信号生成] 通道信息:")
        log_info(f"    当日价格: {current_price:.4f}")
        log_info(f"    当日最高价: {current_high:.4f}")
        log_info(f"    当日最低价: {current_low:.4f}")
        log_info(f"    做多: {upper_channel:.4f}")
        log_info(f"    做空: {lower_channel:.4f}")
        log_info(f"    做多止盈: {exit_lower:.4f}")
        log_info(f"    做空止盈: {exit_upper:.4f}")
        log_info(f"    持仓: {g.long_position}")
        log_info(f"    当前ATR值: {g.N:.4f}")

        # 海龟交易法则信号判断
        # 判断信号（无持仓时可做多，有持仓时判断是否平多）
        if g.long_position == 0:  # 无持仓，判断是否做多
            # 买入1（做多）：当日价格 > 前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
            if current_price >= upper_channel:  # 突破上轨，买入信号（做多）
                log_debug("  [信号生成] 产生买入信号：价格突破入市上轨")
                log_info(f"  [信号生成] 买入1（做多）: {current_price:.4f} 大于等于 入市上轨 {upper_channel}")
                return 1
        elif g.long_position == 1 and g.current_date[:8] != g.long_open_date[:8]:  # 有持仓 且 持仓日期不是当天，判断是否卖出

            long_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [ContextInfo.stock_code],
                start_time=g.long_open_date,
                end_time=g.current_date,
                period='1d',
                dividend_type=ContextInfo.dividend_type,
                subscribe=True
            )

            long_history_market_data_max = long_history_market_data[ContextInfo.stock_code]['high'].iloc[:-1].max()
            # 历史最高价 和 当日最高价比较
            g.highest_after_entry = current_high if np.isnan(long_history_market_data_max) else max(
                long_history_market_data_max, current_high)
            log_info(f"    更新后最高价: {g.highest_after_entry}")
            log_debug(f"  [信号生成] 止盈价格计算:")
            stop_profit_price = g.highest_after_entry - (
                    g.highest_after_entry - g.long_entry_price) * g.stop_profit_ratio
            log_debug(f"    公式: 最高价 - (最高价 - 入场价) * 止盈比例")
            log_info(
                f"    止盈公式： {g.highest_after_entry} - ({g.highest_after_entry} - {g.long_entry_price}) * {g.stop_profit_ratio} = {stop_profit_price:.4f}")

            # 止损信号2 买入价 - N * ATR
            log_info(
                f" 止损公式： {g.long_entry_price} - {g.stop_loss_multiplier} * {g.N}  ")
            stop_loss_price = g.long_entry_price - g.stop_loss_multiplier * g.N
            # log_info(
            #     f" 止损公式： {g.long_entry_price} - {g.stop_loss_multiplier} * {g.N} = {stop_loss_price:.4fs} ")
            # 止盈卖出1：买入第二天开始，当价格 < 前4日收盘价最低点时，且价格 < 最高价 -（最高价 - 买入价）*20 % （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
            if current_price < exit_lower and current_price < stop_profit_price:
                log_info("  [信号生成] 产生止盈信号：价格跌破离市下轨且回撤达到阈值")
                log_info(f"    当前价格: {current_price} < 做多止盈: {exit_lower}")
                log_info(f"    当前价格: {current_price} < 止盈价格: {stop_profit_price:.4f}")
                return -1

            # 止损卖出1：买入第二天开始，当价格 < 买入价 - 2 * ATR时，立刻执行卖出
            # 止损信号 - 价格下跌超过2ATR
            elif current_price < stop_loss_price:
                log_info(f"  [信号生成] 产生止损信号：价格下跌超过 {g.N}")
                log_info(f"    当前价格: {current_price} < 止损价格: {stop_loss_price:.4f}")
                log_info(f"    入场价: {g.long_entry_price}, ATR: {g.N:.4f}")
                return -1
            else:
                log_info("  [信号生成] 无平多信号")
        return 0
    except Exception as e:
        log_info(f"  [信号生成] 生成交易信号时发生错误: {e}")
        return 0


def execute_trade(ContextInfo, signal_type, price_data):
    """
    执行买卖操作
    根据交易信号执行具体的下单操作
    策略下单规则：
    单只股票单次买入金额10000元
    参数:
    signal: signal_type
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    """
    try:
        log_debug("  [交易执行] 开始执行交易操作...")
        log_debug(f"  [交易执行] 交易信号: 信号类型={signal_type}")
        current_price = price_data['close'].iloc[-1]
        position_num = int(g.long_capital / current_price / 100) * 100  # 股数
        # 开仓操作
        if signal_type == 1 and g.long_position == 0:  # 开仓信号
            # 23 买入 1101: 限价单  14: 对手价 -1: 市价  position_num: 股
            log_info(
                f"  [交易执行] 执行买入开仓操作: 账户： {ContextInfo.account_id} , 代码：{ContextInfo.stock_code} ，价格: {current_price:.4f} , 对手价 ， {position_num} 股 ，价值: {current_price * position_num:.2f}元")
            order_info = passorder(23, 1101, ContextInfo.account_id, ContextInfo.stock_code, 14, -1, position_num, 1,
                                   ContextInfo)
            log_info(f"  [交易执行] 下单结果: {order_info}")
            g.long_position = 1  # 持仓状态
        # 清仓操作
        elif signal_type == -1 and g.long_position == 1:  # 清仓信号
            log_info(f"  [交易执行] 执行买入清仓操作: {g.long_use_volume} 股，价格: {current_price:.4f}")
            order_info = passorder(24, 1101, ContextInfo.account_id, ContextInfo.stock_code, 14, -1,
                                   g.long_use_volume, 1, ContextInfo)
            log_info(f"  [交易执行] 下单结果: {order_info}")
            g.long_position = 0  # 清仓持仓状态

    except Exception as e:
        log_info(f"  [交易执行] 执行交易操作时发生错误: {e}")


def get_log_filename():
    """
    获取当前日志文件名
    """
    global log_filename
    if log_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        log_filename = f"C:\\datalog\\datalog-{timestamp}.log"
    return log_filename


def clear_log_file():
    """
    清空日志文件内容，防止之前的脏数据影响
    """
    try:
        # 清空文件内容
        open(get_log_filename(), 'w').close()
    except Exception as e:
        pass  # 忽略文件操作错误


def log_info(message):
    """
    简单的日志记录函数，用于记录info级别日志
    """

    logging.info(message)

    print(f"[{datetime.now().strftime('%Y%m%d%H%M%S')}] {message}")


def log_debug(message):
    """
    简单的日志记录函数，用于记录debug级别日志
    """
    logging.debug(message)
    print(f"{message}")


def log_section(title):
    """
    输出带标题的分隔区块

    Args:
        title (str): 区块标题
    """
    log_info(60 * "=")
    log_info(title)


def to_dict(obj):
    attr_dict = {}
    for attr in dir(obj):
        try:
            if attr[:2] == 'm_':
                attr_dict[attr] = getattr(obj, attr)
        except:
            pass
    return attr_dict


def log_separator():
    """
    输出分隔线
    """
    log_info(60 * "-")


# 自定义类 用来保存状态
class G(): pass


g = G()
