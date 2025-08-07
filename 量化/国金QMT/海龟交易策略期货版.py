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

import numpy as np


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """
    print("=" * 60)
    print("开始初始化海龟交易策略...")
    print("=" * 60)

    # 设置交易标的（以螺纹钢期货为例，实际使用时请根据需要修改）
    # ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])
    print(f"[初始化] 设置交易标的: {ContextInfo.stock_code}")

    # 策略参数
    ContextInfo.entry_window = 10  # 入市通道周期（突破周期）
    ContextInfo.exit_window = 4  # 离市通道周期
    ContextInfo.atr_window = 10  # ATR计算周期
    ContextInfo.stop_profit_ratio = 0.2  # 止盈比例
    ContextInfo.stop_loss_multiplier = 2  # 止损ATR倍数
    print(f"[初始化] 策略参数设置完成:")
    print(f"        入市通道周期: {ContextInfo.entry_window}")
    print(f"        离市通道周期: {ContextInfo.exit_window}")
    print(f"        ATR计算周期: {ContextInfo.atr_window}")
    print(f"        止盈比例: {ContextInfo.stop_profit_ratio}")
    print(f"        止损ATR倍数: {ContextInfo.stop_loss_multiplier}")

    # 资金管理参数
    ContextInfo.total_capital = 100000  # 总资金量
    ContextInfo.single_entry_capital = 10000  # 单次买入金额
    ContextInfo.max_capital_per_symbol = 20000  # 单品种最大资金
    ContextInfo.long_capital = 10000  # 做多资金
    ContextInfo.short_capital = 10000  # 做空资金
    print(f"[初始化] 资金管理参数设置完成:")
    print(f"        总资金量: {ContextInfo.total_capital}")
    print(f"        单次买入金额: {ContextInfo.single_entry_capital}")
    print(f"        单品种最大资金: {ContextInfo.max_capital_per_symbol}")
    print(f"        做多资金: {ContextInfo.long_capital}")
    print(f"        做空资金: {ContextInfo.short_capital}")

    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID
    print(f"[初始化] 账户信息设置完成:")
    print(f"        期货账户ID: {ContextInfo.account_id}")

    # 策略状态变量
    ContextInfo.entry_price = 0  # 入市价格
    ContextInfo.highest_after_entry = 0  # 入市后的最高价
    ContextInfo.lowest_after_entry = 0  # 入市后的最低价
    ContextInfo.N = 0  # 波动幅度(N值/ATR)
    ContextInfo.position_type = 0  # 持仓类型：0-无仓位，1-多头，-1-空头
    print(f"[初始化] 策略状态变量初始化完成:")
    print(f"        入市价格: {ContextInfo.entry_price}")
    print(f"        入市后最高价: {ContextInfo.highest_after_entry}")
    print(f"        入市后最低价: {ContextInfo.lowest_after_entry}")
    print(f"        波动幅度(N值): {ContextInfo.N}")
    print(f"        持仓类型: {ContextInfo.position_type}")

    print("=" * 60)
    print("海龟交易策略初始化完成")
    print("=" * 60)


def handlebar(ContextInfo):
    """
    主要处理函数
    在每个K线周期都会被调用
    """
    print("=" * 60)
    print("[处理函数] 开始执行handlebar函数")
    print("=" * 60)

    # 检查数据是否足够
    required_data = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window)
    print(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
    if ContextInfo.barpos < required_data:
        print("[数据检查] 数据不足，跳过本次处理")
        print("=" * 60)
        return

    try:
        # 获取当前时间和价格数据
        current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
        print(f"[时间信息] 处理时间: {current_time}")

        # 获取计算需要的数据
        print("[数据获取] 开始获取价格数据...")
        price_data = get_price_data(ContextInfo)
        if price_data is None or len(price_data) < max(ContextInfo.entry_window, ContextInfo.atr_window):
            print("[数据获取] 数据不足，跳过本次处理")
            print("=" * 60)
            return
        print(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

        # 计算ATR和N值
        print("[ATR计算] 开始计算ATR和N值...")
        ContextInfo.N = calculate_atr(price_data, ContextInfo.atr_window)
        if ContextInfo.N <= 0:
            print("[ATR计算] ATR值计算异常，跳过本次处理")
            print("=" * 60)
            return
        print(f"[ATR计算] 当前ATR(N值): {ContextInfo.N:.4f}")

        # 获取当前账户信息
        print("[账户信息] 开始获取账户信息...")
        account_info = get_account_info(ContextInfo.account_id)
        if account_info is None:
            print("[账户信息] 无法获取账户信息，跳过本次处理")
            print("=" * 60)
            return
        print("[账户信息] 成功获取账户信息")

        available_cash = account_info['available']
        total_value = account_info['total_value']
        positions = account_info['positions']

        # 获取当前持仓
        current_position = positions.get(ContextInfo.stock_code, 0) if positions else 0
        print(f"[持仓信息] 当前持仓: {current_position}, 可用资金: {available_cash:.2f}, 总资产: {total_value:.2f}")

        # 决策分区 - 判断是否需要交易
        print("[信号生成] 开始生成交易信号...")
        signal = generate_signal(ContextInfo, price_data, current_position)
        print(f"[信号生成] 生成的交易信号: {signal}")

        # 执行买卖操作
        if signal != 0:
            print("[交易执行] 检测到交易信号，开始执行交易...")
            execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position)
        else:
            print("[交易执行] 无交易信号，继续观察市场")

        print("=" * 60)
        print("[处理函数] handlebar函数执行完成")
        print("=" * 60)

    except Exception as e:
        print(f"[异常处理] 处理过程中发生错误: {e}")
        print("=" * 60)


def get_price_data(ContextInfo):
    """
    获取计算需要的数据
    返回包含OHLC数据的DataFrame
    """
    try:
        print("  [价格数据] 开始获取价格数据...")

        # 计算需要的历史数据天数
        required_bars = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window) + 5
        print(f"  [价格数据] 需要获取 {required_bars} 条历史数据")

        # 获取历史数据
        bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
        print(f"  [价格数据] 获取截止时间: {bar_date}")

        # 获取行情数据
        print(f"  [价格数据] 请求市场数据...")
        print(f"  [价格数据] 请求参数 - 标的: {ContextInfo.stock_code}, 周期: {ContextInfo.period}, 数量: {required_bars}")
        market_data = ContextInfo.get_market_data_ex(
            ['open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=bar_date,
            period=ContextInfo.period,
            count=required_bars,
            subscribe=True
        )

        if not market_data or ContextInfo.stock_code not in market_data:
            print("  [价格数据] 获取市场数据为空")
            return None

        df = market_data[ContextInfo.stock_code]
        print(f"  [价格数据] 成功获取市场数据，共 {len(df)} 条记录")
        print("  [价格数据] 最近5条数据:")
        print(df.tail())
        return df

    except Exception as e:
        print(f"  [价格数据] 获取价格数据时发生错误: {e}")
        return None


def calculate_atr(data, window):
    """
    计算ATR(N值)
    ATR是真实波幅的N日平均值，用于衡量市场波动性

    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        print(f"  [ATR计算] 开始计算ATR，使用 {window} 日数据")

        # 计算真实波幅(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        print(f"  [ATR计算] 价格数据统计:")
        print(f"    最高价范围: {high[-window - 1:-1]}")
        print(f"    最低价范围: {low[-window - 1:-1]}")
        print(f"    收盘价范围: {close[-window - 1:-1]}")

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:],
                        np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        print(f"  [ATR计算] 计算得到TR值: {tr[-window:]}")

        # 计算ATR(N日均值)
        atr = np.mean(tr[-window:])
        print(f"  [ATR计算] ATR计算结果: {atr}")
        return atr

    except Exception as e:
        print(f"  [ATR计算] 计算ATR时发生错误: {e}")
        return 0


def get_account_info(account_id):
    """
    获取账户信息
    包括可用资金、总权益、持仓等
    """
    try:
        print("  [账户信息] 开始获取账户信息...")

        # 获取账户资金信息
        print("  [账户信息] 获取账户资金详情...")
        account_details = get_trade_detail_data(account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            print("  [账户信息] 获取账户详情失败")
            return None

        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益

        print(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")

        # 获取持仓信息
        print("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(account_id, 'FUTURE', 'POSITION')
        positions = {}
        if position_details:
            print(f"  [账户信息] 获取到 {len(position_details)} 条持仓记录")
            for pos in position_details:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                positions[symbol] = pos.m_nVolume  # 持仓量
                print(f"    [账户信息] 持仓: {symbol} = {pos.m_nVolume}")
        else:
            print("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            'positions': positions
        }

    except Exception as e:
        print(f"  [账户信息] 获取账户信息时发生错误: {e}")
        return None


def generate_signal(ContextInfo, price_data, current_position):
    """
    决策分区 - 生成交易信号
    根据修改后的海龟交易法则生成买入、卖出或持有信号
    返回: 1=买入(做多), -1=卖出(做空), 0=持有
    """
    try:
        print("  [信号生成] 开始生成交易信号...")

        close_prices = price_data['close'].values
        high_prices = price_data['high'].values
        low_prices = price_data['low'].values

        current_price = close_prices[-1]
        current_high = high_prices[-1]
        current_low = low_prices[-1]

        print(f"  [信号生成] 当前价格信息:")
        print(f"    收盘价: {current_price:.4f}")
        print(f"    最高价: {current_high:.4f}")
        print(f"    最低价: {current_low:.4f}")

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

        print(f"  [信号生成] 通道信息:")
        print(f"    入市上轨: {upper_channel:.4f}")
        print(f"    入市下轨: {lower_channel:.4f}")
        print(f"    离市上轨: {exit_upper:.4f}")
        print(f"    离市下轨: {exit_lower:.4f}")

        # 更新最高价和最低价（如果已入场）
        if ContextInfo.position_type != 0:  # 已有持仓
            print(f"  [信号生成] 已有持仓，更新最高最低价:")
            print(f"    更新前最高价: {ContextInfo.highest_after_entry}")
            print(f"    更新前最低价: {ContextInfo.lowest_after_entry}")
            ContextInfo.highest_after_entry = max(ContextInfo.highest_after_entry, current_high)
            ContextInfo.lowest_after_entry = min(ContextInfo.lowest_after_entry, current_low)
            print(f"    更新后最高价: {ContextInfo.highest_after_entry}")
            print(f"    更新后最低价: {ContextInfo.lowest_after_entry}")

        print(f"  [信号生成] 当前策略状态:")
        print(f"    持仓类型: {ContextInfo.position_type}")
        print(f"    入市价格: {ContextInfo.entry_price}")
        print(f"    入市后最高价: {ContextInfo.highest_after_entry}")
        print(f"    入市后最低价: {ContextInfo.lowest_after_entry}")
        print(f"    当前ATR值: {ContextInfo.N:.4f}")

        # 海龟交易法则信号判断
        if ContextInfo.position_type == 0:  # 当前无持仓
            print("  [信号生成] 当前无持仓，判断是否开仓")
            # 入市信号
            if current_price > upper_channel:  # 突破上轨，买入信号（做多）
                print("  [信号生成] 产生买入信号：价格突破入市上轨")
                ContextInfo.highest_after_entry = current_high  # 初始化最高价
                ContextInfo.lowest_after_entry = current_low  # 初始化最低价
                print(f"  [信号生成] 设置入场后最高价: {ContextInfo.highest_after_entry}")
                print(f"  [信号生成] 设置入场后最低价: {ContextInfo.lowest_after_entry}")
                return 1
            elif current_price < lower_channel:  # 突破下轨，卖空信号（做空）
                print("  [信号生成] 产生卖空信号：价格突破入市下轨")
                ContextInfo.highest_after_entry = current_high  # 初始化最高价
                ContextInfo.lowest_after_entry = current_low  # 初始化最低价
                print(f"  [信号生成] 设置入场后最高价: {ContextInfo.highest_after_entry}")
                print(f"  [信号生成] 设置入场后最低价: {ContextInfo.lowest_after_entry}")
                return -1
            else:
                print("  [信号生成] 无开仓信号")

        elif ContextInfo.position_type == 1:  # 当前持有多头仓位
            print("  [信号生成] 当前持有多头仓位，判断是否平仓")
            # 止盈信号 - 价格跌破离市下轨且价格小于最高价回撤一定比例
            stop_profit_price = ContextInfo.highest_after_entry - (
                    ContextInfo.highest_after_entry - ContextInfo.entry_price) * ContextInfo.stop_profit_ratio
            print(f"  [信号生成] 多头止盈价格计算:")
            print(f"    公式: 最高价 - (最高价 - 入场价) * 止盈比例")
            print(
                f"    数值: {ContextInfo.highest_after_entry} - ({ContextInfo.highest_after_entry} - {ContextInfo.entry_price}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price < exit_lower and current_price < stop_profit_price:
                print("  [信号生成] 产生多头止盈信号：价格跌破离市下轨且回撤达到阈值")
                print(f"    当前价格: {current_price} < 离市下轨: {exit_lower}")
                print(f"    当前价格: {current_price} < 止盈价格: {stop_profit_price:.4f}")
                return -1
            # 止损信号 - 价格下跌超过2N
            elif current_price < ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N
                print("  [信号生成] 产生多头止损信号：价格下跌超过2N")
                print(f"    当前价格: {current_price} < 止损价格: {stop_loss_price:.4f}")
                print(f"    入场价: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return -1
            else:
                print("  [信号生成] 无平多信号")

        elif ContextInfo.position_type == -1:  # 当前持有空头仓位
            print("  [信号生成] 当前持有空头仓位，判断是否平仓")
            # 止盈信号 - 价格突破离市上轨且价格大于最低价反弹一定比例
            stop_profit_price = ContextInfo.lowest_after_entry + (
                    ContextInfo.entry_price - ContextInfo.lowest_after_entry) * ContextInfo.stop_profit_ratio
            print(f"  [信号生成] 空头止盈价格计算:")
            print(f"    公式: 最低价 + (入场价 - 最低价) * 止盈比例")
            print(
                f"    数值: {ContextInfo.lowest_after_entry} + ({ContextInfo.entry_price} - {ContextInfo.lowest_after_entry}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price > exit_upper and current_price > stop_profit_price:
                print("  [信号生成] 产生空头止盈信号：价格突破离市上轨且反弹达到阈值")
                print(f"    当前价格: {current_price} > 离市上轨: {exit_upper}")
                print(f"    当前价格: {current_price} > 止盈价格: {stop_profit_price:.4f}")
                return 1
            # 止损信号 - 价格上涨超过2N
            elif current_price > ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N
                print("  [信号生成] 产生空头止损信号：价格上涨超过2N")
                print(f"    当前价格: {current_price} > 止损价格: {stop_loss_price:.4f}")
                print(f"    入场价: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return 1
            else:
                print("  [信号生成] 无平空信号")

        return 0  # 无交易信号

    except Exception as e:
        print(f"  [信号生成] 生成交易信号时发生错误: {e}")
        return 0


def execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position):
    """
    执行买卖操作
    根据交易信号执行具体的下单操作

    策略下单规则：
    1. 单只品种单次买入金额10000元
    2. 按照最大手数买，每个品种最多20000元，做多/做空各10000元
    3. 做多和做空可以同时存在，互不影响
    """
    try:
        print("  [交易执行] 开始执行交易操作...")
        print(f"  [交易执行] 交易信号: {signal}")

        current_price = price_data['close'].iloc[-1]
        contract_multiplier = ContextInfo.get_contract_multiplier(ContextInfo.stock_code)
        print(f"  [交易执行] 合约信息:")
        print(f"    当前价格: {current_price:.4f}")
        print(f"    合约乘数: {contract_multiplier}")

        # 计算头寸规模
        # 根据资金量和合约价值计算手数
        if signal > 0:  # 做多
            position_value = ContextInfo.long_capital
            print(f"  [交易执行] 做多资金: {position_value}")
        else:  # 做空
            position_value = ContextInfo.short_capital
            print(f"  [交易执行] 做空资金: {position_value}")

        position_size = int(position_value / (current_price * contract_multiplier))
        position_size = max(1, position_size)  # 至少为1手

        print(f"  [交易执行] 头寸计算:")
        print(f"    计算公式: 资金 / (价格 * 合约乘数)")
        print(
            f"    数值计算: {position_value} / ({current_price} * {contract_multiplier}) = {position_value / (current_price * contract_multiplier):.2f}")
        print(f"    最终手数: {position_size} 手")
        print(f"    头寸价值: {position_size * current_price * contract_multiplier:.2f}元")

        if signal > 0:  # 买入信号（做多）
            if ContextInfo.position_type <= 0:  # 当前无仓位或持有空头
                # 0	开多  1101: 限价单  5: 对手价 -1: 市价  position_size: 数量
                print(f"  [交易执行] 执行买入开仓操作: {position_size} 手，价格: {current_price:.4f}")
                print(f"  [交易执行] 下单参数: 买入开仓, 限价单, 对手价, 市价, {position_size}手")
                order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size, 1,
                                       ContextInfo)
                print(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.position_type = 1
                ContextInfo.entry_price = current_price
                print(f"  [交易执行] 更新持仓状态: 多头")
                print(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")

            elif ContextInfo.position_type == 1:  # 已持有多头仓位
                print("  [交易执行] 已持有多头仓位，不重复开仓")

        elif signal < 0:  # 卖出信号（做空）
            if ContextInfo.position_type >= 0:  # 当前无仓位或持有多头
                # 3: 开空
                print(f"  [交易执行] 执行卖出开仓操作: {position_size} 手，价格: {current_price:.4f}")
                print(f"  [交易执行] 下单参数: 卖出开仓, 限价单, 对手价, 市价, {position_size}手")
                order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size, 1,
                                       ContextInfo)
                print(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.position_type = -1
                ContextInfo.entry_price = current_price
                print(f"  [交易执行] 更新持仓状态: 空头")
                print(f"  [交易执行] 记录入场价格: {ContextInfo.entry_price}")

            elif ContextInfo.position_type == -1:  # 已持有空头仓位
                print("  [交易执行] 已持有空头仓位，不重复开仓")

        else:  # 平仓操作
            if ContextInfo.position_type == 1 and signal < 0:  # 平多仓
                # 7 平多, 优先平昨
                print(f"  [交易执行] 执行买入平仓操作: {abs(current_position)} 手，价格: {current_price:.4f}")
                print(f"  [交易执行] 下单参数: 买入平仓, 限价单, 对手价, 市价, {abs(current_position)}手")
                order_info = passorder(7, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                       abs(current_position), 1, ContextInfo)
                print(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.position_type = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                print("  [交易执行] 重置持仓状态")

            elif ContextInfo.position_type == -1 and signal > 0:  # 平空仓
                print(f"  [交易执行] 执行卖出平仓操作: {current_position} 手，价格: {current_price:.4f}")
                # 9 平空, 优先平昨
                print(f"  [交易执行] 下单参数: 卖出平仓, 限价单, 对手价, 市价, {current_position}手")
                order_info = passorder(9, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, current_position,
                                       1, ContextInfo)
                print(f"  [交易执行] 下单结果: {order_info}")
                ContextInfo.position_type = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                print("  [交易执行] 重置持仓状态")

    except Exception as e:
        print(f"  [交易执行] 执行交易操作时发生错误: {e}")
