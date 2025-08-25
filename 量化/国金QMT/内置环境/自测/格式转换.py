# coding:gbk
"""
海龟交易策略期货版
基于国金QMT平台实现的海龟交易策略

该策略具有完整的规则体系，包括：
国金QMT 策略需求
计算频率：分钟
交易品种： 期货 ，代码待定，先请一个变量。 需要测试所有的期货品种，筛选跑的好的品种和人工选的做重叠选择
提前计算的指标：前10日ATR平均值，并记录下来
买入1（做多）：当日价格>前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
止盈卖出1：买入第二天开始，当价格<前4日收盘价最高点时，且价格< 最高价-（最高价-买入价）*20% （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
止损卖出1：买入第二天开始，当价格 < 买入价-2*ATR时，立刻执行卖出

买入2（做空）：当日价格<前10日收盘价最低点时，即当前价格突破10日低点，当日立刻执行做空
止盈卖出2：买入第二天开始，当价格>前4日收盘价最低点时，且价格>最低价+（买入价-最低价）*20% （最低价是指买入后到计算时的最低价）时，立刻执行卖出
止损卖出2：买入第二天开始，当价格>买入价+2*ATR时，立刻执行卖出

买入头寸：资金量=100000，单只品种单次买入金额10000，按照最大手数买，即每个品种最多20000，做多/做空各10000
加仓规则：做多或者做空买入后不再进行加仓，但是做多一笔，不影响做空的开单，反之做空一笔，也不影响做多开单
"""
# coding:gbk


import numpy as np
import pandas as pd


def log_info(message):
    """
    简单的日志记录函数，用于记录info级别日志
    """
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    import logging
    filename = f"C:\datalog\datalog-{timestamp}.log"
    # logging.basicConfig(filename=filename, level=logging.DEBUG,
    #                     format='%(asctime)s - %(levelname)s - %(message)s')
    logging.basicConfig(filename=filename, level=logging.DEBUG,
                        format='%(message)s')
    logging.info(message)

    print(f"[{timestamp}] {message}")


def log_separator(length=60, char="="):
    """
    输出分隔符

    Args:
        length (int): 分隔符长度
        char (str): 分隔符字符
    """
    log_info(char * length)


def log_section(title):
    """
    输出带标题的分隔区块

    Args:
        title (str): 区块标题
    """
    log_separator()
    log_info(title)
    log_separator()


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """
    log_section("开始初始化海龟交易策略...")

    # 设置交易标的（以螺纹钢期货为例，实际使用时请根据需要修改）
    # ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])
    log_info(f"[初始化] 设置交易标的: {ContextInfo.stock_code}")

    # 策略参数
    ContextInfo.entry_window = 10  # 入市通道周期（突破周期）
    ContextInfo.exit_window = 4  # 离市通道周期
    ContextInfo.atr_window = 10  # ATR计算周期
    ContextInfo.stop_profit_ratio = 0.2  # 止盈比例
    ContextInfo.stop_loss_multiplier = 2  # 止损ATR倍数
    log_info(f"[初始化] 策略参数设置完成:")
    log_info(f"        入市通道周期: {ContextInfo.entry_window}")
    log_info(f"        离市通道周期: {ContextInfo.exit_window}")
    log_info(f"        ATR计算周期: {ContextInfo.atr_window}")
    log_info(f"        止盈比例: {ContextInfo.stop_profit_ratio}")
    log_info(f"        止损ATR倍数: {ContextInfo.stop_loss_multiplier}")

    # 资金管理参数
    ContextInfo.long_capital = 40000  # 做多资金
    ContextInfo.short_capital = 40000  # 做空资金
    log_info(f"[初始化] 资金管理参数设置完成:")
    log_info(f"        做多资金: {ContextInfo.long_capital}")
    log_info(f"        做空资金: {ContextInfo.short_capital}")

    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID
    log_info(f"[初始化] 账户信息设置完成:")
    log_info(f"        期货账户ID: {ContextInfo.account_id}")

    # 策略状态变量
    ContextInfo.entry_price = 0  # 入市价格
    ContextInfo.highest_after_entry = 0  # 入市后的最高价
    ContextInfo.lowest_after_entry = 0  # 入市后的最低价
    ContextInfo.N = 0  # 波动幅度(N值/ATR)
    # 修改前：ContextInfo.position_type = 0  # 持仓类型：0-无仓位，1-多头，-1-空头
    # 修改后：使用两个独立变量分别表示多头和空头持仓状态
    ContextInfo.long_position = 0  # 多头持仓：0-无仓位，1-持有多头
    ContextInfo.short_position = 0  # 空头持仓：0-无仓位，1-持有空头
    log_info(f"[初始化] 策略状态变量初始化完成:")
    log_info(f"        入市价格: {ContextInfo.entry_price}")
    log_info(f"        入市后最高价: {ContextInfo.highest_after_entry}")
    log_info(f"        入市后最低价: {ContextInfo.lowest_after_entry}")
    log_info(f"        波动幅度(N值): {ContextInfo.N}")
    log_info(f"        多头持仓: {ContextInfo.long_position}")
    log_info(f"        空头持仓: {ContextInfo.short_position}")

    log_section("海龟交易策略初始化完成")


def handlebar(ContextInfo):
    """
    主要处理函数
    在每个K线周期都会被调用
    """
    log_section("[处理函数] 开始执行handlebar函数")

    # 检查数据是否足够
    required_data = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window)
    log_info(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
    if ContextInfo.barpos < required_data:
        log_info("[数据检查] 数据不足，跳过本次处理")
        log_separator()
        return

    try:
        # 获取当前时间和价格数据
        current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
        log_info(f"[时间信息] 处理时间: {current_time}")

        # 获取计算需要的数据
        log_info("[数据获取] 开始获取价格数据...")
        price_data = get_price_data(ContextInfo)
        if price_data is None or len(price_data) < max(ContextInfo.entry_window, ContextInfo.atr_window):
            log_info("[数据获取] 数据不足，跳过本次处理")
            log_separator()
            return
        log_info(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

        # 计算ATR和N值
        log_info("[ATR计算] 开始计算ATR和N值...")
        ContextInfo.N = calculate_atr(price_data, ContextInfo.atr_window)

        if ContextInfo.N <= 0:
            log_info("[ATR计算] ATR值计算异常，跳过本次处理")
            log_separator()
            return
        log_info(f"[ATR计算] 当前ATR(N值): {ContextInfo.N:.4f}")

        # 获取当前账户信息
        log_info("[账户信息] 开始获取账户信息...")
        account_info = get_account_info(ContextInfo)
        if account_info is None:
            log_info("[账户信息] 无法获取账户信息，跳过本次处理")
            log_separator()
            return
        log_info("[账户信息] 成功获取账户信息")

        available_cash = account_info['available']
        total_value = account_info['total_value']
        positions = account_info['positions']

        # 获取当前持仓
        current_position = positions.get(ContextInfo.stock_code, 0) if positions else 0
        log_info(f"[持仓信息] 当前持仓: {current_position}, 可用资金: {available_cash:.2f}, 总资产: {total_value:.2f}")

        # 决策分区 - 判断是否需要交易
        log_info("[信号生成] 开始生成交易信号...")
        signal = generate_signal(ContextInfo, price_data, current_position)
        log_info(f"[信号生成] 生成的交易信号: {signal}")

        # 执行买卖操作
        if signal != (0, 0):
            log_info("[交易执行] 检测到交易信号，开始执行交易...")
            execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position)
        else:
            log_info("[交易执行] 无交易信号，继续观察市场")

        log_section("[处理函数] handlebar函数执行完成")

    except Exception as e:
        log_info(f"[异常处理] 处理过程中发生错误: {e}")
        log_separator()


def get_price_data(ContextInfo):
    """
    获取计算需要的数据
    返回包含OHLC数据的DataFrame
    """
    try:
        log_info("  [价格数据] 开始获取价格数据...")

        # 计算需要的历史数据天数
        required_bars = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window) + 5
        log_info(f"  [价格数据] 需要获取 {required_bars} 条历史数据")

        # 获取历史数据 获取数据的截止时间
        bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
        log_info(f"  [价格数据] 获取截止时间: {bar_date}")

        # 获取非当日的历史数据，使用1d周期
        # log_info(f"  [价格数据] 请求历史市场数据...")
        # log_info(f"  [价格数据] 请求参数 - 标的: {ContextInfo.stock_code}, 周期: 1d, 数量: {required_bars}")
        history_market_data = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=bar_date,
            period='1d',
            count=required_bars,
            subscribe=True
        )

        # 获取当日最新数据，使用ContextInfo.period周期
        # log_info(f"  [价格数据] 请求当日最新市场数据...")
        log_info(
            f"  [价格数据] 请求参数 - 标的: {ContextInfo.stock_code}, 周期: {ContextInfo.period}, 数量: 1")
        current_market_data = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=bar_date,
            period=ContextInfo.period,
            count=1,
            subscribe=True
        )

        if not history_market_data or ContextInfo.stock_code not in history_market_data:
            log_info("  [价格数据] 获取历史市场数据为空")
            return None

        if not current_market_data or ContextInfo.stock_code not in current_market_data:
            log_info("  [价格数据] 获取当日市场数据为空")
            return None

        # 合并历史数据和当日最新数据
        history_df = history_market_data[ContextInfo.stock_code]
        current_df = current_market_data[ContextInfo.stock_code]

        # 替换历史数据中的最后一条为当日最新数据
        if len(history_df) > 0 and len(current_df) > 0:
            # 删除历史数据中的最后一条（当天数据）
            history_df = history_df[:-1]
            # 将当日最新数据添加到历史数据末尾
            df = pd.concat([history_df, current_df], ignore_index=True)
        else:
            df = history_df

        # log_info(f"  [价格数据] 成功获取合并后市场数据，共 {len(df)} 条记录")
        log_info("  [价格数据] 所有数据:")
        log_info(f"\n {str(df)}")
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
        log_info(f"  [ATR计算] 开始计算ATR，使用 {window} 日数据")

        # 计算真实波幅(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        log_info(f"  [ATR计算] 价格数据统计:")
        log_info(f"    最高价范围: {high[-window - 1:-1]}")
        log_info(f"    最低价范围: {low[-window - 1:-1]}")
        log_info(f"    收盘价范围: {close[-window - 1:-1]}")

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        log_info(f"  [ATR计算] 计算得到TR值: {tr[-window:]}")

        # 计算ATR(N日均值)
        atr = np.mean(tr[-window:])
        log_info(f"  [ATR计算] ATR计算结果: {atr}")
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
        log_info("  [账户信息] 开始获取账户信息...")

        # 获取账户资金信息
        log_info("  [账户信息] 获取账户资金详情...")
        account_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            log_info("  [账户信息] 获取账户详情失败")
            return None

        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益

        log_info(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")

        # 获取持仓信息
        log_info("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'POSITION')
        positions = {}
        PositionInfo_dict = {}
        if position_details:
            log_info(f"  [账户信息] 获取到 {len(position_details)} 条持仓记录")
            for pos in position_details:
                log_info(pos.m_strInstrumentID)
                # 查看有哪些属性字段
                log_info(dir(pos))
                PositionInfo_dict[pos.m_strInstrumentID + "." + pos.m_strExchangeID] = {
                    # 持仓类型 48：多 49：空
                    "持仓类型": pos.m_nDirection,
                    # "持仓": pos.m_nPosition,
                    "成本": pos.m_dPositionCost,
                    "浮动盈亏": pos.m_dFloatProfit,
                    "持仓量": pos.m_nVolume
                }
                log_info(f"  [账户信息自查] 持仓信息: {PositionInfo_dict}")
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                positions[symbol] = pos.m_nVolume  # 持仓量
                log_info(f"    [账户信息] 持仓: {symbol} = {pos.m_nVolume}")
        else:
            log_info("  [账户信息] 无持仓记录")
        log_info(f"  [账户信息] 持仓信息: {positions}")
        # 更新多头和空头持仓状态
        current_position = positions.get(ContextInfo.stock_code, 0) if positions else 0
        if current_position > 0:
            ContextInfo.long_position = 1
            ContextInfo.short_position = 0
        elif current_position < 0:
            ContextInfo.long_position = 0
            ContextInfo.short_position = 1
        else:
            ContextInfo.long_position = 0
            ContextInfo.short_position = 0

        log_info(f"  [账户信息] 更新持仓状态: 多头={ContextInfo.long_position}, 空头={ContextInfo.short_position}")

        return {
            'available': available,
            'total_value': total_value,
            'positions': positions
        }

    except Exception as e:
        log_info(f"  [账户信息] 获取账户信息时发生错误: {e}")
        return None


def generate_signal(ContextInfo, price_data, current_position):
    """
    决策分区 - 生成交易信号
    根据修改后的海龟交易法则生成买入、卖出或持有信号
    返回: (signal_type, position_type)
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    position_type: 1=多头操作, -1=空头操作
    """
    try:
        log_info("  [信号生成] 开始生成交易信号...")

        close_prices = price_data['close'].values
        high_prices = price_data['high'].values
        low_prices = price_data['low'].values

        current_price = close_prices[-1]
        current_high = high_prices[-1]
        current_low = low_prices[-1]

        log_info(f"  [信号生成] 当前价格信息:")
        log_info(f"    收盘价: {current_price:.4f}")
        log_info(f"    最高价: {current_high:.4f}")
        log_info(f"    最低价: {current_low:.4f}")

        # 计算入市信号 - 前N日高低点突破
        # 上轨：过去entry_window天的最高价
        upper_channel = np.max(high_prices[-ContextInfo.entry_window - 1:-1])
        # 下轨：过去entry_window天的最低价
        lower_channel = np.min(low_prices[-ContextInfo.entry_window - 1:-1])

        # 计算离市信号 - 离市通道
        # 离市上轨
        exit_upper = np.max(high_prices[-ContextInfo.exit_window - 1:-1])
        # 离市下轨 -
        exit_lower = np.min(low_prices[-ContextInfo.exit_window - 1:-1])

        log_info(f"  [信号生成] 通道信息:")
        log_info(f"    入市上轨: {upper_channel:.4f}")
        log_info(f"    入市下轨: {lower_channel:.4f}")
        log_info(f"    离市上轨: {exit_upper:.4f}")
        log_info(f"    离市下轨: {exit_lower:.4f}")

        # 更新最高价和最低价（如果已入场）
        # 修改前：if ContextInfo.position_type != 0:  # 已有持仓
        # 修改后：检查是否持有多头或空头仓位
        if ContextInfo.long_position == 1 or ContextInfo.short_position == 1:  # 已有持仓
            log_info(f"  [信号生成] 已有持仓，更新最高最低价:")
            log_info(f"    更新前最高价: {ContextInfo.highest_after_entry}")
            log_info(f"    更新前最低价: {ContextInfo.lowest_after_entry}")
            ContextInfo.highest_after_entry = max(ContextInfo.highest_after_entry, current_high)
            ContextInfo.lowest_after_entry = min(ContextInfo.lowest_after_entry, current_low)
            log_info(f"    更新后最高价: {ContextInfo.highest_after_entry}")
            log_info(f"    更新后最低价: {ContextInfo.lowest_after_entry}")

        log_info(f"  [信号生成] 当前策略状态:")
        # 修改前：log_info(f"    持仓类型: {ContextInfo.position_type}")
        # 修改后：分别显示多头和空头持仓状态
        log_info(f"    多头持仓: {ContextInfo.long_position}")
        log_info(f"    空头持仓: {ContextInfo.short_position}")
        log_info(f"    入市价格: {ContextInfo.entry_price}")
        log_info(f"    入市后最高价: {ContextInfo.highest_after_entry}")
        log_info(f"    入市后最低价: {ContextInfo.lowest_after_entry}")
        log_info(f"    当前ATR值: {ContextInfo.N:.4f}")

        # 海龟交易法则信号判断
        # 修改前：if ContextInfo.position_type == 0:  # 当前无持仓
        # 修改后：检查是否多头和空头都没有持仓
        if ContextInfo.long_position == 0 and ContextInfo.short_position == 0:  # 当前无持仓
            log_info("  [信号生成] 当前无持仓，判断是否开仓")
            # 入市信号
            if current_price > upper_channel:  # 突破上轨，买入信号（做多）
                log_info("  [信号生成] 产生买入信号：价格突破入市上轨")
                ContextInfo.highest_after_entry = current_high  # 初始化最高价
                ContextInfo.lowest_after_entry = current_low  # 初始化最低价
                log_info(f"  [信号生成] 设置入场后最高价: {ContextInfo.highest_after_entry}")
                log_info(f"  [信号生成] 设置入场后最低价: {ContextInfo.lowest_after_entry}")
                return (1, 1)  # 开仓信号，多头操作
            elif current_price < lower_channel:  # 突破下轨，卖空信号（做空）
                log_info("  [信号生成] 产生卖空信号：价格突破入市下轨")
                ContextInfo.highest_after_entry = current_high  # 初始化最高价
                ContextInfo.lowest_after_entry = current_low  # 初始化最低价
                log_info(f"  [信号生成] 设置入场后最高价: {ContextInfo.highest_after_entry}")
                log_info(f"  [信号生成] 设置入场后最低价: {ContextInfo.lowest_after_entry}")
                return (1, -1)  # 开仓信号，空头操作
            else:
                log_info("  [信号生成] 无开仓信号")

        # 修改前：elif ContextInfo.position_type == 1:  # 当前持有多头仓位
        # 修改后：检查是否持有多头仓位
        elif ContextInfo.long_position == 1:  # 当前持有多头仓位
            log_info("  [信号生成] 当前持有多头仓位，判断是否平仓")
            # 止盈信号 - 价格跌破离市下轨且价格小于最高价回撤一定比例
            stop_profit_price = ContextInfo.highest_after_entry - (
                    ContextInfo.highest_after_entry - ContextInfo.entry_price) * ContextInfo.stop_profit_ratio
            log_info(f"  [信号生成] 多头止盈价格计算:")
            log_info(f"    公式: 最高价 - (最高价 - 入场价) * 止盈比例")
            log_info(
                f"    数值: {ContextInfo.highest_after_entry} - ({ContextInfo.highest_after_entry} - {ContextInfo.entry_price}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price < exit_lower and current_price < stop_profit_price:
                log_info("  [信号生成] 产生多头止盈信号：价格跌破离市下轨且回撤达到阈值")
                log_info(f"    当前价格: {current_price} < 离市下轨: {exit_lower}")
                log_info(f"    当前价格: {current_price} < 止盈价格: {stop_profit_price:.4f}")
                return (-1, 1)  # 平仓信号，多头操作
            # 止损信号 - 价格下跌超过2N
            elif current_price < ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N
                log_info("  [信号生成] 产生多头止损信号：价格下跌超过2N")
                log_info(f"    当前价格: {current_price} < 止损价格: {stop_loss_price:.4f}")
                log_info(f"    入场价: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return (-1, 1)  # 平仓信号，多头操作
            else:
                log_info("  [信号生成] 无平多信号")

        # 修改前：elif ContextInfo.position_type == -1:  # 当前持有空头仓位
        # 修改后：检查是否持有空头仓位
        elif ContextInfo.short_position == 1:  # 当前持有空头仓位
            log_info("  [信号生成] 当前持有空头仓位，判断是否平仓")
            # 止盈信号 - 价格突破离市上轨且价格大于最低价反弹一定比例
            stop_profit_price = ContextInfo.lowest_after_entry + (
                    ContextInfo.entry_price - ContextInfo.lowest_after_entry) * ContextInfo.stop_profit_ratio
            log_info(f"  [信号生成] 空头止盈价格计算:")
            log_info(f"    公式: 最低价 + (入场价 - 最低价) * 止盈比例")
            log_info(
                f"    数值: {ContextInfo.lowest_after_entry} + ({ContextInfo.entry_price} - {ContextInfo.lowest_after_entry}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price > exit_upper and current_price > stop_profit_price:
                log_info("  [信号生成] 产生空头止盈信号：价格突破离市上轨且反弹达到阈值")
                log_info(f"    当前价格: {current_price} > 离市上轨: {exit_upper}")
                log_info(f"    当前价格: {current_price} > 止盈价格: {stop_profit_price:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            # 止损信号 - 价格上涨超过2N
            elif current_price > ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N
                log_info("  [信号生成] 产生空头止损信号：价格上涨超过2N")
                log_info(f"    当前价格: {current_price} > 止损价格: {stop_loss_price:.4f}")
                log_info(f"    入场价: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            else:
                log_info("  [信号生成] 无平空信号")

        return (0, 0)  # 无交易信号

    except Exception as e:
        log_info(f"  [信号生成] 生成交易信号时发生错误: {e}")
        return (0, 0)


def execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position):
    """
    执行买卖操作
    根据交易信号执行具体的下单操作

    策略下单规则：
    1. 单只品种单次买入金额10000元
    2. 按照最大手数买，每个品种最多20000元，做多/做空各10000元
    3. 做多和做空可以同时存在，互不影响

    参数:
    signal: (signal_type, position_type) 元组
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    position_type: 1=多头操作, -1=空头操作
    """
    try:
        log_info("  [交易执行] 开始执行交易操作...")
        signal_type, position_type = signal
        log_info(f"  [交易执行] 交易信号: 信号类型={signal_type}, 仓位类型={position_type}")

        current_price = price_data['close'].iloc[-1]
        contract_multiplier = ContextInfo.get_contract_multiplier(ContextInfo.stock_code)
        log_info(f"  [交易执行] 合约信息:")
        log_info(f"    当前价格: {current_price:.4f}")
        log_info(f"    合约乘数: {contract_multiplier}")

        # 计算头寸规模
        # 根据资金量和合约价值计算手数
        if position_type > 0:  # 做多
            position_value = ContextInfo.long_capital
            log_info(f"  [交易执行] 做多资金: {position_value}")
        else:  # 做空
            position_value = ContextInfo.short_capital
            log_info(f"  [交易执行] 做空资金: {position_value}")

        position_size = int(position_value / (current_price * contract_multiplier))
        log_info(f"  [交易执行] 头寸规模: {position_size} 手")
        position_size = max(1, position_size)  # 至少为1手

        log_info(f"  [交易执行] 头寸计算:")
        log_info(f"    计算公式: 资金 / (价格 * 合约乘数)")
        log_info(
            f"    数值计算: {position_value} / ({current_price} * {contract_multiplier}) = {position_value / (current_price * contract_multiplier):.2f}")
        log_info(f"    最终手数: {position_size} 手")
        log_info(f"    头寸价值: {position_size * current_price * contract_multiplier:.2f}元")

        # 开仓操作
        if signal_type > 0:  # 开仓信号
            if position_type > 0:  # 做多
                # 检查是否当前没有多头持仓
                if ContextInfo.long_position == 0:
                    # 0	开多  1101: 限价单  5: 对手价 -1: 市价  position_size: 数量
                    log_info(f"  [交易执行] 执行买入开仓操作: {position_size} 手，价格: {current_price:.4f}")
                    log_info(f"  [交易执行] 下单参数: 买入开仓, 限价单, 对手价, 市价, {position_size}手")
                    order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                           position_size, 1,
                                           ContextInfo)
                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    ContextInfo.long_position = 1
                    ContextInfo.entry_price = current_price
                    log_info(f"  [交易执行] 更新持仓状态: 多头")
                    log_info(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")
                else:
                    log_info("  [交易执行] 已持有多头仓位，不重复开仓")

            elif position_type < 0:  # 做空
                # 检查是否当前没有空头持仓
                if ContextInfo.short_position == 0:
                    # 3: 开空
                    log_info(f"  [交易执行] 执行卖出开仓操作: {position_size} 手，价格: {current_price:.4f}")
                    log_info(f"  [交易执行] 下单参数: 卖出开仓, 限价单, 对手价, 市价, {position_size}手")
                    order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                           position_size, 1,
                                           ContextInfo)
                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    ContextInfo.short_position = 1
                    ContextInfo.entry_price = current_price
                    log_info(f"  [交易执行] 更新持仓状态: 空头")
                    log_info(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")
                else:
                    log_info("  [交易执行] 已持有空头仓位，不重复开仓")

        # 平仓操作
        elif signal_type < 0:  # 平仓信号
            if position_type > 0 and ContextInfo.long_position == 1:  # 平多仓
                # 7 平多, 优先平昨
                log_info(f"  [交易执行] 执行买入平仓操作: {abs(current_position)} 手，价格: {current_price:.4f}")
                log_info(f"  [交易执行] 下单参数: 买入平仓, 限价单, 对手价, 市价, {abs(current_position)}手")
                order_info = passorder(7, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                       abs(current_position), 1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.long_position = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                log_info("  [交易执行] 重置持仓状态")

            elif position_type < 0 and ContextInfo.short_position == 1:  # 平空仓
                log_info(f"  [交易执行] 执行卖出平仓操作: {current_position} 手，价格: {current_price:.4f}")
                # 9 平空, 优先平昨
                log_info(f"  [交易执行] 下单参数: 卖出平仓, 限价单, 对手价, 市价, {current_position}手")
                order_info = passorder(9, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, current_position,
                                       1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.short_position = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                log_info("  [交易执行] 重置持仓状态")

    except Exception as e:
        log_info(f"  [交易执行] 执行交易操作时发生错误: {e}")
