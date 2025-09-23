# coding:gbk
"""
海龟交易策略期货版
基于国金QMT平台实现的海龟交易策略

该策略具有完整的规则体系，包括：
国金QMT 策略需求
计算频率：分钟
交易品种：连续股票中当前的主力期货股票加上目前有持仓的股票

提前计算的指标：前10日ATR平均值，并记录下来
买入1（做多）：当日价格>前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
做多止盈卖出1：买入第二天开始，当价格<前4日收盘价最低点时，且价格 < 最高价-（最高价-买入价）*20% （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
做多止损卖出1：买入第二天开始，当价格 < 买入价-N*ATR时，立刻执行卖出

买入头寸：资金量=100000，单只品种单次买入金额10000，按照最大手数买，即每个品种最多20000，做多 10000

如果是开仓信号且持仓不满4个

"""
# coding:gbk


import logging
from datetime import datetime

import numpy as np
import pandas as pd

# 全局变量用于存储日志文件名
log_filename = None


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """
    # 在初始化时清空日志文件内容
    global log_filename
    log_filename = None  # 重置日志文件名
    # clear_log_file()

    filename = get_log_filename()

    logging.basicConfig(filename=filename, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    log_section("开始初始化海龟交易策略...")

    ContextInfo.stock_codes = ['002230.SZ', '600276.SH']

    ContextInfo.set_universe(ContextInfo.stock_codes)
    log_info(f"[初始化] 设置交易标的: {ContextInfo.stock_codes}")

    dividend_type = ContextInfo.dividend_type
    log_info(f"[初始化] 复权方式: {dividend_type}")

    # 策略参数
    g.entry_window = 10  # 入市通道周期（突破周期）
    g.exit_window = 4  # 止盈通道周期
    g.atr_window = 10  # ATR计算周期
    g.stop_profit_ratio = 0.2  # 止盈比例
    g.stop_loss_multiplier = 1  # 止损ATR倍数
    g.position_limit = 5  # 持仓上线
    g.capital_rate = 0.1  # 资金比例 资金固定值，参数失效

    # # 资金管理参数
    g.long_capital = 10000  # 做多资金

    log_info(f"[初始化] 策略参数设置完成:")
    log_info(f"        入市通道周期: {g.entry_window}")
    log_info(f"        止盈通道周期: {g.exit_window}")
    log_info(f"        ATR计算周期: {g.atr_window}")
    log_info(f"        止盈比例: {g.stop_profit_ratio}")
    log_info(f"        止损ATR倍数: {g.stop_loss_multiplier}")
    log_info(f"        资金比例: {g.capital_rate}")

    # 策略状态变量
    g.N = {}  # 波动幅度(N值/ATR)，为每个股票保存
    g.long_position = {}  # 多头持仓：0-无仓位，1-持有多头，为每个股票保存
    g.highest_after_entry = {}  # 入市后的最高价，为每个股票保存
    g.lowest_after_entry = {}  # 入市后的最低价，为每个股票保存
    g.long_open_date = {}  # 多头开仓日期，为每个股票保存
    g.long_volume = {}  # 多头持仓量，为每个股票保存
    g.long_use_volume = {}  # 可用持仓量
    g.long_entry_price = {}  # 多头持仓价，为每个股票保存

    g.expire_date = {}  # 当前需要交易的股票的到期日，为每个股票保存
    g.current_trading_contracts = []  # 当前需要交易的股票，为每个股票保存
    g.position_count = 0  # 当前持仓数量

    g.position_code = []  # 当前持仓的股票
    g.position_size = {}  # 交易股票对应的手数，为每个股票保存
    log_info(f"[初始化] 策略状态变量初始化完成")

    # 账户信息
    ContextInfo.account_id = '8886090521'  # 期货账户ID
    # ContextInfo.account_id = account  # 期货账户ID
    log_info(f"[初始化] 账户信息设置完成:")
    log_info(f"        期货账户ID: {ContextInfo.account_id}")

    log_section("海龟交易策略初始化完成")
    # ContextInfo.run_time("run_time_handlebar", "60nSecond", "2025-01-01 09:30:00")


def handlebar(ContextInfo):  # 策略处理函数
    # def run_time_handlebar(ContextInfo):  # 定时运行
    """
    主要处理函数
    在每个K线周期都会被调用
    """

    # if not ContextInfo.is_last_bar():
    #     log_info("[处理函数] 当前不是最后一个K线周期，跳过本次处理")
    #     return

    log_section("[处理函数] 开始执行handlebar函数")

    # 获取历史数据 获取数据的截止时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    g.current_date = bar_date
    log_info(f"  获取截止时间: {g.current_date}")

    # 清空上一次的交易股票列表
    g.current_trading_contracts = ContextInfo.stock_codes

    log_info(f"[初始化] 当前在交易的股票: {g.current_trading_contracts}")

    # 获取当前账户信息（只需要获取一次）
    log_info("[账户信息] 开始获取账户信息...")
    account_info = get_account_info(ContextInfo)
    if account_info is None:
        log_info("[账户信息] 无法获取账户信息，跳过本次处理")
        log_separator()
        return
    log_info("[账户信息] 成功获取账户信息")

    # 需要交易的股票g.current_trading_contracts 和持仓代码 position_code 两个list 合并去重得到要执行的股票代码
    g.current_trading_contracts = list(set(g.current_trading_contracts + g.position_code))
    log_info(f"[初始化]  需要处理的股票: {g.current_trading_contracts}")

    # 为每个股票执行策略逻辑
    for stock_code in g.current_trading_contracts:
        log_info(f"{60 * '-'} \n [处理函数] 处理股票: {stock_code}")

        # 设置当前处理的股票为全局变量，供其他函数使用
        g.current_stock_code = stock_code

        # 检查数据是否足够
        required_data = max(g.entry_window, g.exit_window, g.atr_window)
        log_debug(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
        if ContextInfo.barpos < required_data:
            log_info("[数据检查] 数据不足，跳过本次处理")
            log_separator()
            continue

        try:
            # 获取当前时间和价格数据
            current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
            log_info(f"[时间信息] 处理时间: {current_time}")
            log_info(current_time[11:16])
            # 时间如果是九点整时，当前分钟交易 9点整的1分钟k线是当日的数据没有办法使用
            if current_time[11:16] == "09:00":
                log_info(f"  当前分钟不交易{current_time}")
                continue

            # 获取计算需要的数据
            log_debug("[数据获取] 开始获取价格数据...")
            price_data = get_price_data(ContextInfo)
            log_debug(f'[数据获取]: \n {str(price_data)}')
            if price_data is None or len(price_data) <= max(g.entry_window, g.atr_window):
                log_info("[数据获取] 数据不足，跳过本次处理")
                log_separator()
                continue
            log_debug(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

            # 计算ATR和N值
            log_debug("[ATR计算] 开始计算ATR和N值...")
            g.N[stock_code] = calculate_atr(stock_code, price_data, g.atr_window)

            if g.N[stock_code] <= 0:
                log_info("[ATR计算] ATR值计算异常，跳过本次处理")
                log_separator()
                continue
            log_debug(f"[ATR计算] 当前ATR(N值): {g.N[stock_code]:.4f}")

            if g.position_count >= g.position_limit:
                log_info(f"[交易执行] 当前持仓{g.position_count}个， 已满足{g.position_limit}个，不执行新的开仓操作")
            else:
                log_info(f"[交易执行] 当前持仓{g.position_count}个，不满{g.position_limit}个，可以执行新的开仓操作")

            # 决策分区 - 判断是否需要交易
            log_debug("[信号生成] 开始生成交易信号...")
            signal = generate_signal(ContextInfo, price_data)
            log_info(f"[信号生成] 生成的交易信号: {signal}")

            # 执行买卖操作
            if signal != (0, 0):
                log_debug("[交易执行] 检测到交易信号，开始执行交易...")
                execute_trade(ContextInfo, signal, price_data)
            else:
                log_info("[交易执行] 无交易信号，继续观察市场")

        except Exception as e:
            log_info(f"[异常处理] 处理过程中发生错误: {e}")
            log_separator()
            continue

    log_section("[处理函数] handlebar函数执行完成")


def get_price_data(ContextInfo):
    """
    获取计算需要的数据
    返回包含OHLC数据的DataFrame
    """
    try:
        log_debug("  [价格数据] 开始获取价格数据...")

        # 计算需要的历史数据天数
        required_bars = max(g.entry_window, g.exit_window, g.atr_window) + 5
        log_debug(f"  [价格数据] 需要获取 {required_bars} 条历史数据")

        # 获取非当日的历史数据，使用1d周期
        history_market_data = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [g.current_stock_code],
            end_time=g.current_date,
            period='1d',
            count=required_bars,
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )
        if not history_market_data or g.current_stock_code not in history_market_data:
            log_info("  [价格数据] 获取历史市场数据为空")
            return None

        history_df = history_market_data[g.current_stock_code]

        # 将时间戳转换为可读的时间格式
        history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

        log_debug(f"  [价格数据] 请求参数 - 标的: {g.current_stock_code}, 周期: {ContextInfo.period}, 数量: 1")

        current_market_data_more = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [g.current_stock_code],
            start_time=g.current_date[:8] + '000000',  # 当天00:00:00开始
            end_time=g.current_date,
            period=ContextInfo.period,  # 使用1分钟周期
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )

        if not current_market_data_more or g.current_stock_code not in current_market_data_more:
            log_info("  [价格数据] 获取当日市场数据为空")
            return None

        current_df_more = current_market_data_more[g.current_stock_code]

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
        log_info(f"  获取当天数据: \n {current_df}")

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


def calculate_atr(stock_code, data, window):
    """
    计算ATR(N值)，支持多股票独立计算
    ATR是真实波幅的N日平均值，用于衡量市场波动性
    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        log_debug(f"  [ATR计算] 开始计算ATR，使用 {window} 日数据 (股票: {stock_code})")
        # 计算真实波幅(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        log_debug(f"  [ATR计算] 价格数据统计 (股票: {stock_code}):")
        log_debug(f"    最高价范围: {high[-window - 1:-1]}")
        log_debug(f"    最低价范围: {low[-window - 1:-1]}")
        log_debug(f"    收盘价范围: {close[-window - 1:-1]}")

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        log_debug(f"  [ATR计算] 计算得到TR值: {tr[-window:]}")

        # 计算ATR(N日均值)
        atr = np.mean(tr[-window:])
        log_info(f"  [ATR计算] ATR计算结果: {atr} (股票: {stock_code})")

        # TR值和ATR值写到data中用于查询记录信息
        # 修复长度不匹配问题：tr数组比原始数据少一个元素（因为计算差值）
        data['tr'] = np.append([np.nan], tr)  # 在前面添加NaN以匹配长度
        data['atr'] = atr

        # 保存到全局变量中，每个股票独立存储
        g.N[stock_code] = atr

        return atr

    except Exception as e:
        log_info(f"  [ATR计算] 计算ATR时发生错误: {e} (股票: {stock_code})")
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
            log_info("  [账户信息] 获取账户详情失败")
            return None
        g.position_code = []  # 仓位代码
        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益

        log_info(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")

        # 重置所有股票的持仓状态
        for stock_code in g.current_trading_contracts:
            g.long_position[stock_code] = 0  # 重置多头持仓状态
            g.long_open_date[stock_code] = None  # 重置多头开仓日期
        g.position_count = 0

        # 获取未成交委托信息并撤销未成交委托
        log_debug("  [账户信息] 获取未成交委托详情...")
        order_details = get_trade_detail_data(ContextInfo.account_id, 'STOCK', 'ORDER')
        if order_details:
            order_len = 0
            for order in order_details:
                # log_info(f"  [账户信息] 获取到委托记录：\n {to_dict(order)}")
                # 获取委托状态，50-54表示未成交状态
                order_status = order.m_nOrderStatus
                symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID

                # 检查是否为未成交状态(状态码49-53)
                if 49 <= order_status < 54:
                    log_info(
                        f"  [账户信息] 发现未成交委托，股票: {symbol}, 状态: {order_status}, 委托编号: {order.m_strOrderSysID}")
                    # 撤销未成交委托
                    cancel_result = cancel(order.m_strOrderSysID, ContextInfo.account_id, 'STOCK', ContextInfo)
                    log_info(f"  [账户信息] 撤销委托结果: {cancel_result}")
                    order_len += 1
                else:
                    log_debug(f"  [账户信息] 股票: {symbol} ,委托状态为: {order_status}，无需撤销")
            log_info(f"  [账户信息] 处理  {order_len} 条委托记录")
        else:
            log_info("  [账户信息] 无委托记录")

        # 获取持仓信息
        log_debug("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'STOCK', 'POSITION')
        PositionInfo_dict = {}
        PositionInfo_dfs = pd.DataFrame()

        if position_details:
            for pos in position_details:
                if pos.m_nVolume != 0:  # 忽略持仓量为0的股票
                    # 获取 pos 对象转json信息
                    # log_info(f"  [账户信息] 获取持仓属性信息: {dir(pos)}")
                    symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID

                    position_type = pos.m_nDirection
                    # 检查持仓是否属于当前策略的股票
                    if position_type == 48:  # 多头持仓
                        g.long_position[symbol] = 1  # 多头持仓状态
                        g.long_open_date[symbol] = pos.m_strOpenDate  # 多头开仓日期
                        g.long_volume[symbol] = pos.m_nVolume  # 多头持仓量

                        g.long_use_volume[symbol] = pos.m_nCanUseVolume  # 可用持仓量

                        g.long_entry_price[symbol] = pos.m_dOpenPrice  # 多头持仓成本

                    PositionInfo_dict['持仓量'] = pos.m_nVolume  # 持仓量
                    PositionInfo_dict['代码'] = symbol  # 持仓代码
                    PositionInfo_dict['持仓类型'] = position_type  # 48：多 49：空
                    PositionInfo_dict['持仓成本'] = pos.m_dOpenPrice  # 持仓成本
                    PositionInfo_dict['持仓盈亏'] = pos.m_dPositionProfit  # 持仓盈亏
                    PositionInfo_dict['开仓日期'] = pos.m_strOpenDate  # 开仓日期
                    PositionInfo_df = pd.DataFrame([PositionInfo_dict])

                    PositionInfo_dfs = pd.concat([PositionInfo_dfs, PositionInfo_df], ignore_index=True)

            log_info(f"    [账户信息] 持仓:\n {str(PositionInfo_dfs)} ")
            # 持仓数量通过PositionInfo_dfs有几行数据来决定
            g.position_count = PositionInfo_dfs.shape[0]
            log_debug(f"  [账户信息] 更新持仓状态，当前持仓股票数: {g.position_count}")

            g.position_code = PositionInfo_dfs['代码'].tolist()
            log_debug(f"  [账户信息] 持仓股票列表: {g.position_code}")


        else:
            log_info("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            'PositionInfo_dfs': PositionInfo_dfs,
            'PositionInfo_dict': PositionInfo_dict,  # 返回更多持仓信息
        }

    except Exception as e:
        log_info(f"  [账户信息] 获取账户信息时发生错误: {e}")
        return None


def generate_signal(ContextInfo, price_data):
    """
    决策分区 - 生成交易信号
    根据修改后的海龟交易法则生成买入、卖出或持有信号
    返回: (signal_type, position_type)
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    position_type: 1=多头操作, -1=空头操作
    """
    try:

        log_debug("  [信号生成] 开始生成交易信号...")

        # 获取当前最高价
        current_price = price_data['close'].values[-1]
        current_high = price_data['high'].values[-1]
        current_low = price_data['low'].values[-1]

        # 计算入市信号 - 前N日高低点突破
        # 做多：过去entry_window天收盘价的最高价
        upper_channel = price_data['close'].iloc[-g.entry_window - 1:-1].max()

        # 计算离市信号 - 离市通道
        # 做多止盈 过去exit_window天收盘价的最低价
        exit_lower = price_data['close'].iloc[-g.exit_window - 1:-1].min()

        log_info(f"  [信号生成] 通道信息: 股票代码: {g.current_stock_code}")
        log_info(f"    当日价格: {current_price:.4f}")
        log_info(f"    当日最高价: {current_high:.4f}")
        log_info(f"    当日最低价: {current_low:.4f}")
        log_info(f"    做多: {upper_channel:.4f}")
        log_info(f"    做多止盈: {exit_lower:.4f}")
        log_info(f"    多头持仓: {g.long_position[g.current_stock_code]}")
        log_info(f"    当前ATR值: {g.N[g.current_stock_code]:.4f}")

        # 修改后：检查是否持有多头或空头仓位
        if g.long_position[g.current_stock_code] == 1:  # 多头已有持仓
            log_debug(f"  [信号生成] 已有多头持仓，更新最高:")

            long_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [g.current_stock_code],
                start_time=g.long_open_date[g.current_stock_code],
                end_time=g.current_date,
                period='1d',
                dividend_type=ContextInfo.dividend_type,
                subscribe=True
            )

            long_history_market_data_max = long_history_market_data[g.current_stock_code]['high'].iloc[:-1].max()
            # 历史最高价 和 当日最高价比较
            g.highest_after_entry[g.current_stock_code] = current_high if np.isnan(
                long_history_market_data_max) else max(
                long_history_market_data_max, current_high)

            log_info(f"    更新后最高价: {g.highest_after_entry[g.current_stock_code]}   ")

        # 海龟交易法则信号判断
        # 判断多头信号（无多头持仓时可做多，有多头持仓时判断是否平多）
        if g.long_position[g.current_stock_code] == 0 and g.position_count < g.position_limit:  # 无多头持仓，判断是否做多 持仓小于4个
            # 买入1（做多）：当日价格 > 前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
            if current_price >= upper_channel:  # 突破上轨，买入信号（做多）
                log_debug("  [信号生成] 产生买入信号：价格突破入市上轨")
                log_info(f"  [信号生成] 买入1（做多）: {current_price:.4f} 大于等于 入市上轨 {upper_channel}")
                return (1, 1)  # 开仓信号，多头操作
        elif g.long_position[g.current_stock_code] == 1:  # 有多头持仓，判断是否平多
            log_debug("  [信号生成] 当前持有多头仓位，判断是否平仓")

            log_debug(f"  [信号生成] 多头止盈价格计算:")
            stop_profit_price = g.highest_after_entry[g.current_stock_code] - (
                    g.highest_after_entry[g.current_stock_code] - g.long_entry_price[
                g.current_stock_code]) * g.stop_profit_ratio
            log_info(f"    公式: 最高价 - (最高价 - 入场价) * 止盈比例")
            log_info(
                f"    止盈公式计算数值: {g.highest_after_entry[g.current_stock_code]} - ({g.highest_after_entry[g.current_stock_code]} - {g.long_entry_price[g.current_stock_code]}) * {g.stop_profit_ratio} = {stop_profit_price:.4f}")
            # 止盈信号1 - 价格跌破止盈做多点且价格小于最高价回撤一定比例

            # 止损信号2 买入价 - N * ATR
            stop_loss_price = g.long_entry_price[g.current_stock_code] - g.stop_loss_multiplier * g.N[
                g.current_stock_code]
            log_info(
                f" 止损价格计算: {g.long_entry_price[g.current_stock_code]} - {g.stop_loss_multiplier} * {g.N[g.current_stock_code]} = {stop_loss_price:.4f}")
            # 止盈卖出1：买入第二天开始，当价格 < 前4日收盘价最低点时，且价格 < 最高价 -（最高价 - 买入价）*20 % （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
            if current_price < exit_lower and current_price < stop_profit_price:
                log_info("  [信号生成] 产生多头止盈信号：价格跌破离市下轨且回撤达到阈值")
                log_info(f"    当前价格: {current_price} < 做多止盈: {exit_lower}")
                log_info(f"    当前价格: {current_price} < 止盈价格: {stop_profit_price:.4f}")
                return (-1, 1)  # 平仓信号，多头操作

            # 止损卖出1：买入第二天开始，当价格 < 买入价 - N * ATR时，立刻执行卖出
            # 止损信号 - 价格下跌超过NATR
            elif current_price < stop_loss_price:
                log_info("  [信号生成] 产生多头止损信号：价格下跌超过NATR")
                log_info(f"    当前价格: {current_price} < 止损价格: {stop_loss_price:.4f}")
                log_info(
                    f"    入场价: {g.long_entry_price[g.current_stock_code]}, ATR: {g.N[g.current_stock_code]:.4f}")
                return (-1, 1)  # 平仓信号，多头操作
            else:
                log_info("  [信号生成] 无平多信号")

        return (0, 0)  # 无交易信号

    except Exception as e:
        log_info(f"  [信号生成] 生成交易信号时发生错误: {e}")
        return (0, 0)


def execute_trade(ContextInfo, signal, price_data):
    """
    执行买卖操作
    根据交易信号执行具体的下单操作

    策略下单规则：
    1. 单只品种单次买入金额10000元
    2. 按照最大手数买，每个品种最多20000元，做多10000元

    参数:
    signal: (signal_type, position_type) 元组
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    position_type: 1=多头操作, -1=空头操作
    """
    try:

        log_debug("  [交易执行] 开始执行交易操作...")
        signal_type, position_type = signal
        log_info(f"  [交易执行] 交易信号: 信号类型={signal_type}, 仓位类型={position_type}")

        current_price = price_data['close'].iloc[-1]
        position_num = int(g.long_capital / current_price / 100) * 100  # 股数

        log_info(
            f"    最终手数: {position_num} 手 ,头寸价值: {position_num * current_price:.2f}元")

        # 开仓操作
        if signal_type > 0:  # 开仓信号
            if position_type > 0:  # 做多
                # 检查是否当前没有多头持仓
                if g.long_position[g.current_stock_code] == 0:
                    # 0	开多  1101: 限价单  5: 对手价 -1: 市价
                    log_info(
                        f"  [交易执行] 执行买入开仓操作 下单参数: 买入开仓,  对手价, 价格: {current_price:.4f}, {position_num}股数")
                    # passorder( opType, orderType, accountid , orderCode, prType, price, volume , strategyName, quickTrade, userOrderId , ContextInfo)
                    #        #  操作号    组合方式     资金账号    品种代码     报价类型  价格    下单量    策略名称        快速下单标记  投资备注        策略上下文
                    order_info = passorder(23, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                           position_num, 1,
                                           ContextInfo)

                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    g.long_position[g.current_stock_code] = 1
                    g.long_open_date[g.current_stock_code] = g.current_date

                    g.position_count = g.position_count + 1
                    log_info(f"  [交易执行] 持仓计数器: {g.position_count}")
                else:
                    log_info("  [交易执行] 已持有多头仓位，不重复开仓")

        # 平仓操作
        elif signal_type < 0:  # 平仓信号
            if position_type > 0 and g.long_position[g.current_stock_code] == 1:  # 平多仓

                log_info(
                    f"  [交易执行] 执行买入清仓操作: {g.long_use_volume[g.current_stock_code]} 股，价格: {current_price:.4f}")

                order_info = passorder(24, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                       g.long_use_volume[g.current_stock_code], 1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                g.long_position[g.current_stock_code] = 0

                g.position_count = g.position_count - 1
                log_info(f"  [交易执行] 持仓计数器: {g.position_count}")


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
