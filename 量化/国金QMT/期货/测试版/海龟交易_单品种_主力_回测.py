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
做多止盈卖出1：买入第二天开始，当价格<前4日收盘价最低点时，且价格 < 最高价-（最高价-买入价）*20% （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
做多止损卖出1：买入第二天开始，当价格 < 买入价-2*ATR时，立刻执行卖出

买入2（做空）：当日价格<前10日收盘价最低点时，即当前价格突破10日低点，当日立刻执行做空
做空止盈卖出2：买入第二天开始，当价格>前4日收盘价最高点时，且价格>最低价+（买入价-最低价）*20% （最低价是指买入后到计算时的最低价）时，立刻执行卖出
做空止损卖出2：买入第二天开始，当价格>买入价+2*ATR时，立刻执行卖出

买入头寸：资金量=100000，单只品种单次买入金额10000，按照最大手数买，即每个品种最多20000，做多/做空各10000
加仓规则：做多或者做空买入后不再进行加仓，但是做多一笔，不影响做空的开单，反之做空一笔，也不影响做多开单
"""
# coding:gbk


import numpy as np
import pandas as pd


# def clear_log_file():
#     """
#     清空日志文件内容，防止之前的脏数据影响
#     """
#     from datetime import datetime
#     timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
#     filename = f"C:\datalog\datalog-{timestamp}.log"
#     try:
#         # 清空文件内容
#         open(filename, 'w').close()
#     except Exception as e:
#         pass  # 忽略文件操作错误


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


# 自定义类 用来保存状态
class G(): pass


g = G()


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """
    # 在初始化时清空日志文件内容
    # clear_log_file()

    log_section("开始初始化海龟交易策略...")

    # 设置交易标的（以螺纹钢期货为例，实际使用时请根据需要修改）
    ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    # ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])
    log_info(f"[初始化] 设置交易标的: {ContextInfo.stock_code}")

    dividend_type = ContextInfo.dividend_type
    log_info(f"[初始化] 复权方式: {dividend_type}")

    # 策略参数
    g.entry_window = 5  # 入市通道周期（突破周期）
    g.exit_window = 3  # 止盈通道周期
    g.atr_window = 10  # ATR计算周期
    g.stop_profit_ratio = 0.2  # 止盈比例
    g.stop_loss_multiplier = 1  # 止损ATR倍数
    g.capital_rate = 0.1  # 资金比例

    # 资金管理参数
    g.long_capital = 100000  # 做多资金
    g.short_capital = 100000  # 做空资金

    log_info(f"[初始化] 策略参数设置完成:")
    log_info(f"        入市通道周期: {g.entry_window}")
    log_info(f"        止盈通道周期: {g.exit_window}")
    log_info(f"        ATR计算周期: {g.atr_window}")
    log_info(f"        止盈比例: {g.stop_profit_ratio}")
    log_info(f"        止损ATR倍数: {g.stop_loss_multiplier}")
    log_info(f"        资金比例: {g.capital_rate}")

    # 策略状态变量
    g.highest_after_entry = 0  # 入市后的最高价
    g.lowest_after_entry = 0  # 入市后的最低价
    g.N = 0  # 波动幅度(N值/ATR)
    # 修改前：ContextInfo.position_type = 0  # 持仓类型：0-无仓位，1-多头，-1-空头
    # 修改后：使用两个独立变量分别表示多头和空头持仓状态
    g.long_position = 0  # 多头持仓：0-无仓位，1-持有多头
    g.short_position = 0  # 空头持仓：0-无仓位，1-持有空头
    log_info(f"[初始化] 策略状态变量初始化完成:")
    log_info(f"        入市后最高价: {g.highest_after_entry}")
    log_info(f"        入市后最低价: {g.lowest_after_entry}")
    log_info(f"        波动幅度(N值): {g.N}")
    log_info(f"        多头持仓: {g.long_position}")
    log_info(f"        空头持仓: {g.short_position}")

    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID
    log_info(f"[初始化] 账户信息设置完成:")
    log_info(f"        期货账户ID: {ContextInfo.account_id}")

    log_section("海龟交易策略初始化完成")


def handlebar(ContextInfo):
    """
    主要处理函数
    在每个K线周期都会被调用
    """
    log_section("[处理函数] 开始执行handlebar函数")

    # 获取历史数据 获取数据的截止时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    g.current_date = bar_date
    log_info(f"  获取截止时间: {g.current_date}")

    # 获取主合约信息
    # g.stock_main_contract = ContextInfo.get_main_contract(ContextInfo.stock_code, g.current_date[:8] )
    # log_info(f"[数据获取] 主合约信息: {g.stock_main_contract}")

    # 获取合约基础信息
    g.stock_contract_info = ContextInfo.get_instrument_detail(ContextInfo.stock_code)
    log_info(f"[数据获取] 主合约基础信息: {g.stock_contract_info}")

    # LongMarginRatio	float	多头保证金率
    # ShortMarginRatio	float	空头保证金率
    g.long_margin_ratio = g.stock_contract_info.get('LongMarginRatio', 0.0)
    g.short_margin_ratio = g.stock_contract_info.get('ShortMarginRatio', 0.0)

    # 检查数据是否足够
    required_data = max(g.entry_window, g.exit_window, g.atr_window)
    log_info(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
    if ContextInfo.barpos < required_data:
        log_info("[数据检查] 数据不足，跳过本次处理")
        log_separator()
        return

    try:
        # 获取当前时间和价格数据
        current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
        log_info(f"[时间信息] 处理时间: {current_time}")
        log_info(current_time[11:16])
        # 时间如果是九点整时，当前分钟交易
        if current_time[11:16] == "09:00":
            log_info(f"  当前分钟不交易{current_time}")
            return

        # 获取计算需要的数据
        log_info("[数据获取] 开始获取价格数据...")
        price_data = get_price_data(ContextInfo)
        log_info(f'[数据获取]: \n {str(price_data)}')
        if price_data is None or len(price_data) <= max(g.entry_window, g.atr_window):
            log_info("[数据获取] 数据不足，跳过本次处理")
            log_separator()
            return
        log_info(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

        # 计算ATR和N值
        log_info("[ATR计算] 开始计算ATR和N值...")
        g.N = calculate_atr(price_data, g.atr_window)

        if g.N <= 0:
            log_info("[ATR计算] ATR值计算异常，跳过本次处理")
            log_separator()
            return
        log_info(f"[ATR计算] 当前ATR(N值): {g.N:.4f}")

        # 获取当前账户信息
        log_info("[账户信息] 开始获取账户信息...")
        account_info = get_account_info(ContextInfo)
        if account_info is None:
            log_info("[账户信息] 无法获取账户信息，跳过本次处理")
            log_separator()
            return
        log_info("[账户信息] 成功获取账户信息")


        # g.long_capital = account_info.get('available') * g.capital_rate  # 做多资金 总价 * 10%
        # g.short_capital = account_info.get('available') * g.capital_rate  # 做空资金 总价 * 10%
        log_info(f"[初始化] 资金管理参数设置完成:")
        log_info(f"        做多资金: {g.long_capital}")
        log_info(f"        做空资金: {g.short_capital}")

        # 决策分区 - 判断是否需要交易
        log_info("[信号生成] 开始生成交易信号...")
        signal = generate_signal(ContextInfo, price_data)
        log_info(f"[信号生成] 生成的交易信号: {signal}")

        # 执行买卖操作
        if signal != (0, 0):
            log_info("[交易执行] 检测到交易信号，开始执行交易...")
            execute_trade(ContextInfo, signal, price_data)
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
        required_bars = max(g.entry_window, g.exit_window, g.atr_window) + 5
        log_info(f"  [价格数据] 需要获取 {required_bars} 条历史数据")

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

        log_info(
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

        # print(f"  获取当天数据: \n {current_df}")

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
        # 回撤参数获取保证金比例 系统配置参数
        # margin_rate = account.m_dMaxMarginRate  # 保证金
        # ContextInfo.margin_rate = margin_rate  # 保证金

        log_info(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")
        # 重置持仓状态
        g.long_position = 0  # 重置多头持仓状态
        g.short_position = 0  # 重置空头持仓状态
        # 重置开仓日期
        g.long_open_date = None  # 重置多头开仓日期
        g.short_open_date = None  # 重置空头开仓日期

        # 获取持仓信息
        log_info("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'POSITION')
        PositionInfo_dict = {}
        PositionInfo_dfs = pd.DataFrame()
        if position_details:
            log_info(f"  [账户信息] 获取到 {len(position_details)} 条持仓记录")
            for pos in position_details:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                # if symbol == ContextInfo.stock_code:
                position_type = pos.m_nDirection
                if position_type == 48:  # 多头持仓
                    g.long_position = 1
                    g.long_open_date = pos.m_strOpenDate  # 多头开仓日期
                    ContextInfo.long_volume = pos.m_nVolume  # 多头持仓量
                    ContextInfo.long_entry_price = pos.m_dOpenPrice  # 多头持仓成本

                elif position_type == 49:  # 空头持仓
                    g.short_position = 1
                    g.short_open_date = pos.m_strOpenDate  # 空头开仓日期
                    ContextInfo.short_volume = pos.m_nVolume  # 空头持仓量
                    ContextInfo.short_entry_price = pos.m_dOpenPrice  # 空头持仓成本

                PositionInfo_dict['持仓量'] = pos.m_nVolume  # 持仓量
                PositionInfo_dict['代码'] = symbol
                PositionInfo_dict['持仓类型'] = position_type  # 48：多 49：空
                PositionInfo_dict['持仓成本'] = pos.m_dOpenPrice
                PositionInfo_dict['持仓盈亏'] = pos.m_dPositionProfit
                PositionInfo_dict['开仓日期'] = pos.m_strOpenDate
                PositionInfo_df = pd.DataFrame([PositionInfo_dict])

                PositionInfo_dfs = pd.concat([PositionInfo_dfs, PositionInfo_df], ignore_index=True)

            log_info(f"    [账户信息] 持仓: {str(PositionInfo_dfs)} ")
            log_info(f"  [账户信息] 更新持仓状态: 多头={g.long_position}, 空头={g.short_position}")

        else:
            log_info("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            # 'margin_rate': margin_rate,
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
    返回: (signal_type, position_type)
    signal_type: 1=开仓信号, -1=平仓信号, 0=无信号
    position_type: 1=多头操作, -1=空头操作
    """
    try:
        log_info("  [信号生成] 开始生成交易信号...")

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
        log_info(f"    多头持仓: {g.long_position}")
        log_info(f"    空头持仓: {g.short_position}")
        log_info(f"    当前ATR值: {g.N:.4f}")

        # 修改后：检查是否持有多头或空头仓位
        if g.long_position == 1:  # 多头已有持仓
            log_info(f"  [信号生成] 已有多头持仓，更新最高:")

            long_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [ContextInfo.stock_code],
                start_time=g.long_open_date,
                end_time=g.current_date,
                period='1d',
                dividend_type=ContextInfo.dividend_type,
                subscribe=True
            )
            # log_info(f'开始时间： {g.short_open_date} 结束时间： {g.current_date}')

            long_history_market_data_max = long_history_market_data[ContextInfo.stock_code]['high'].iloc[:-1].max()
            # 历史最高价 和 当日最高价比较
            g.highest_after_entry = current_high if np.isnan(long_history_market_data_max) else max(
                long_history_market_data_max, current_high)
            # g.highest_after_entry = max(long_history_market_data[ContextInfo.stock_code]['high'].iloc[:-1].max(), current_high)

            log_info(f"    更新后最高价: {g.highest_after_entry}")

        if g.short_position == 1:  # 空头已有持仓
            log_info(f"  [信号生成] 已有空头持仓，更新最低:")
            short_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [ContextInfo.stock_code],
                start_time=g.short_open_date,
                end_time=g.current_date,
                period='1d',
                dividend_type=ContextInfo.dividend_type,
                subscribe=True
            )
            # log_info(f'开始时间： {g.short_open_date} 结束时间： {g.current_date}')

            short_history_market_data_min = short_history_market_data[ContextInfo.stock_code]['low'].iloc[:-1].min()
            # 历史最低价 和 当日最低价比较
            g.lowest_after_entry = current_low if np.isnan(short_history_market_data_min) else min(
                short_history_market_data_min, current_low)

            # g.lowest_after_entry = min(short_history_market_data_min, current_low)
            log_info(f"    更新后最低价: {g.lowest_after_entry}")

        # 海龟交易法则信号判断
        # 判断多头信号（无多头持仓时可做多，有多头持仓时判断是否平多）
        if g.long_position == 0:  # 无多头持仓，判断是否做多
            # 买入1（做多）：当日价格 > 前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
            if current_price >= upper_channel:  # 突破上轨，买入信号（做多）
                log_info("  [信号生成] 产生买入信号：价格突破入市上轨")
                log_info(f"  [信号生成] 买入1（做多）: {current_price:.4f} 大于等于 入市上轨 {upper_channel}")
                return (1, 1)  # 开仓信号，多头操作
        elif g.long_position == 1:  # 有多头持仓，判断是否平多
            log_info("  [信号生成] 当前持有多头仓位，判断是否平仓")

            log_info(f"  [信号生成] 多头止盈价格计算:")
            stop_profit_price = g.highest_after_entry - (
                    g.highest_after_entry - ContextInfo.long_entry_price) * g.stop_profit_ratio
            log_info(f"    公式: 最高价 - (最高价 - 入场价) * 止盈比例")
            log_info(
                f"    数值: {g.highest_after_entry} - ({g.highest_after_entry} - {ContextInfo.long_entry_price}) * {g.stop_profit_ratio} = {stop_profit_price:.4f}")
            # 止盈信号1 - 价格跌破止盈做多点且价格小于最高价回撤一定比例

            # 止损信号2 买入价 - 2 * ATR
            stop_loss_price = ContextInfo.long_entry_price - g.stop_loss_multiplier * g.N

            # 止盈卖出1：买入第二天开始，当价格 < 前4日收盘价最低点时，且价格 < 最高价 -（最高价 - 买入价）*20 % （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
            if current_price < exit_lower and current_price < stop_profit_price:
                log_info("  [信号生成] 产生多头止盈信号：价格跌破离市下轨且回撤达到阈值")
                log_info(f"    当前价格: {current_price} < 做多止盈: {exit_lower}")
                log_info(f"    当前价格: {current_price} < 止盈价格: {stop_profit_price:.4f}")
                return (-1, 1)  # 平仓信号，多头操作

            # 止损卖出1：买入第二天开始，当价格 < 买入价 - 2 * ATR时，立刻执行卖出
            # 止损信号 - 价格下跌超过2ATR
            elif current_price < stop_loss_price:
                log_info("  [信号生成] 产生多头止损信号：价格下跌超过2N")
                log_info(f"    当前价格: {current_price} < 止损价格: {stop_loss_price:.4f}")
                log_info(f"    入场价: {ContextInfo.long_entry_price}, ATR: {g.N:.4f}")
                return (-1, 1)  # 平仓信号，多头操作
            else:
                log_info("  [信号生成] 无平多信号")

        # 判断空头信号（无空头持仓时可做空，有空头持仓时判断是否平空）
        if g.short_position == 0:  # 无空头持仓，判断是否做空
            log_info("  [信号生成] 检测空头信号")
            # 买入2（做空）：当日价格 < 前10日收盘价最低点时，即当前价格突破10日低点，当日立刻执行做空
            if current_price < lower_channel:  # 突破下轨，卖空信号（做空）
                log_info("  [信号生成] 产生卖空信号：价格突破入市下轨")
                log_info(f"  [信号生成] 买入2（做空）: {current_price:.4f} 小于 下轨 {lower_channel}")

                return (1, -1)  # 开仓信号，空头操作
        elif g.short_position == 1:  # 有空头持仓，判断是否平空

            # 空仓止损卖出2：买入第二天开始，当价格 > 买入价 + 2 * ATR时，立刻执行卖出
            log_info("  [信号生成] 当前持有空头仓位，判断是否平仓")

            # 空仓止盈信号 - 价格突破止盈做空点且价格大于最低价反弹一定比例
            stop_profit_price = g.lowest_after_entry + (
                    ContextInfo.short_entry_price - g.lowest_after_entry) * g.stop_profit_ratio
            log_info(f"  [信号生成] 空头止盈价格计算:")
            log_info(f"    公式: 最低价 + (入场价 - 最低价) * 止盈比例")
            log_info(
                f"    数值: {g.lowest_after_entry} + ({ContextInfo.short_entry_price} - {g.lowest_after_entry}) * {g.stop_profit_ratio} = {stop_profit_price:.4f}")

            # 空仓止损信号3 卖出价 + 2 * ATR
            stop_loss_price = ContextInfo.short_entry_price + g.stop_loss_multiplier * g.N

            # 止盈卖出2：买入第二天开始，当价格 > 前4日收盘价最高点时，且价格 > 最低价 +（买入价 - 最低价）*20 % （最低价是指买入后到计算时的最低价）时，立刻执行卖出
            if current_price > exit_upper and current_price > stop_profit_price:
                log_info("  [信号生成] 产生空头止盈信号：价格突破止盈做空点且反弹达到阈值")
                log_info(f"    当前价格: {current_price} > 止盈做空点: {exit_upper}")
                log_info(f"    当前价格: {current_price} > 止盈价格: {stop_profit_price:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            # 止损信号 - 价格上涨超过2ATR
            elif current_price > ContextInfo.short_entry_price + g.stop_loss_multiplier * g.N:
                log_info("  [信号生成] 产生空头止损信号：价格上涨超过2ATR")
                log_info(f"    当前价格: {current_price} > 止损价格: {stop_loss_price:.4f}")
                log_info(f"    入场价: {ContextInfo.short_entry_price}, ATR: {g.N:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            else:
                log_info("  [信号生成] 无平空信号")

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
            position_value = g.long_capital
            log_info(f"  [交易执行] 做多资金: {position_value}")
        else:  # 做空
            position_value = g.short_capital
            log_info(f"  [交易执行] 做空资金: {position_value}")

        # 仓位保证金
        margin_size = g.long_margin_ratio * (current_price * contract_multiplier)
        log_info(
            f"  [交易执行] 多头仓位保证金: {margin_size:.2f}元 :多头仓位保证金比例: {g.long_margin_ratio:.2f} ")

        # short_margin_size = g.short_margin_ratio * (current_price * contract_multiplier)
        # log_info(
        #     f"  [交易执行] 空头仓位保证金: {short_margin_size:.2f}元 :空头仓位保证金比例: {g.short_margin_ratio:.2f} ")

        position_size = int(position_value / margin_size)
        log_info(f"  [交易执行] 头寸规模: {position_size} 手")
        position_size = max(1, position_size)  # 至少为1合约乘数
        # 股数
        position_num = position_size * contract_multiplier

        log_info(f"  [交易执行] 头寸计算:")

        log_info(f"    最终手数: {position_size} 手 , 股数： {position_num}")
        log_info(f"    头寸价值: {position_size * current_price * contract_multiplier:.2f}元")

        # 开仓操作
        if signal_type > 0:  # 开仓信号
            if position_type > 0:  # 做多
                # 检查是否当前没有多头持仓
                if g.long_position == 0:
                    # 0	开多  1101: 限价单  5: 对手价 -1: 市价  position_size: 手数
                    log_info(f"  [交易执行] 执行买入开仓操作: {position_size} 手数，价格: {current_price:.4f}")
                    log_info(f"  [交易执行] 下单参数{ContextInfo.stock_code}: 买入开仓, 限价单, 对手价, 市价, {position_size}手数")
                    order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                           position_size, 1,
                                           ContextInfo)
                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    g.long_position = 1
                    ContextInfo.entry_price = current_price
                    log_info(f"  [交易执行] 更新持仓状态: 多头")
                    log_info(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")
                else:
                    log_info("  [交易执行] 已持有多头仓位，不重复开仓")

            elif position_type < 0:  # 做空
                # 检查是否当前没有空头持仓
                if g.short_position == 0:
                    # 3: 开空
                    log_info(f"  [交易执行] 执行卖出开仓操作: {position_size} 手数，价格: {current_price:.4f}")
                    log_info(f"  [交易执行] 下单参数{ContextInfo.stock_code}: 卖出开仓, 限价单, 对手价, 市价, {position_size} 手数")
                    order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                           position_size, 1,
                                           ContextInfo)
                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    g.short_position = 1
                    ContextInfo.entry_price = current_price
                    log_info(f"  [交易执行] 更新持仓状态: 空头")
                    log_info(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")
                else:
                    log_info("  [交易执行] 已持有空头仓位，不重复开仓")

        # 平仓操作
        elif signal_type < 0:  # 平仓信号
            if position_type > 0 and g.long_position == 1:  # 平多仓
                # 7 平多, 优先平昨
                log_info(f"  [交易执行] 执行买入平仓操作: {abs(ContextInfo.long_volume)} 股，价格: {current_price:.4f}")
                log_info(f"  [交易执行] 下单参数{ContextInfo.stock_code}: 买入平仓, 限价单, 对手价, 市价, {abs(ContextInfo.long_volume)} 股")
                order_info = passorder(7, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                       abs(ContextInfo.long_volume), 1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                g.long_position = 0
                ContextInfo.entry_price = 0
                g.highest_after_entry = 0
                g.lowest_after_entry = 0
                log_info("  [交易执行] 重置持仓状态")

            elif position_type < 0 and g.short_position == 1:  # 平空仓
                log_info(f"  [交易执行] 执行卖出平仓操作: {ContextInfo.short_volume} 股，价格: {current_price:.4f}")
                # 9 平空, 优先平昨
                log_info(f"  [交易执行] 下单参数{ContextInfo.stock_code}: 卖出平仓, 限价单, 对手价, 市价, {ContextInfo.short_volume} 股")
                order_info = passorder(9, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                       ContextInfo.short_volume,
                                       1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                g.short_position = 0
                ContextInfo.entry_price = 0
                g.highest_after_entry = 0
                g.lowest_after_entry = 0
                log_info("  [交易执行] 重置持仓状态")

    except Exception as e:
        log_info(f"  [交易执行] 执行交易操作时发生错误: {e}")
