# coding:gbk
"""
海龟交易策略期货版
基于国金QMT平台实现的海龟交易策略

该策略具有完整的规则体系，包括：
国金QMT 策略需求
计算频率：分钟
交易品种：连续合约中当前的主力期货合约加上目前有持仓的合约

提前计算的指标：前10日ATR平均值，并记录下来
买入1（做多）：当日价格>前10日收盘价最高点时，即当前价格突破前10日高点，当日立刻执行做多
做多止盈卖出1：买入第二天开始，当价格<前4日收盘价最低点时，且价格 < 最高价-（最高价-买入价）*20% （最高价是指买入后到计算时的最高价）时，立刻执行卖出。
做多止损卖出1：买入第二天开始，当价格 < 买入价-N*ATR时，立刻执行卖出

买入2（做空）：当日价格<前10日收盘价最低点时，即当前价格突破10日低点，当日立刻执行做空
做空止盈卖出2：买入第二天开始，当价格>前4日收盘价最高点时，且价格>最低价+（买入价-最低价）*20% （最低价是指买入后到计算时的最低价）时，立刻执行卖出
做空止损卖出2：买入第二天开始，当价格>买入价+N*ATR时，立刻执行卖出

买入头寸：资金量=100000，单只品种单次买入金额10000，按照最大手数买，即每个品种最多20000，做多/做空各10000
加仓规则：做多或者做空买入后不再进行加仓，但是做多一笔，不影响做空的开单，反之做空一笔，也不影响做多开单。

如果是开仓信号且持仓不满4个 或 合约距离到期小于30天 则才能开仓。

"""
# coding:gbk


import logging
from datetime import datetime
import json
import numpy as np
import pandas as pd
import requests

# 全局变量用于存储日志文件名
log_filename = None


def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """

    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID
    # ContextInfo.account_id = account  # 期货账户ID
    g.account = ContextInfo.account_id
    # 在初始化时清空日志文件内容
    global log_filename
    log_filename = None  # 重置日志文件名

    filename = get_log_filename(ContextInfo.account_id)
    # INFO 简要信息  DEBUG 详细日志
    logging.basicConfig(filename=filename, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    log_section("开始初始化海龟交易策略...")

    # 选品
    g.work_dir = 'C:\\合约选品\\'
    # 品种池文件路径
    g.excel_file = '期货品种池.xlsx'
    g.excel_path = f'{g.work_dir}期货品种池.xlsx'
    log_info(f"[初始化] 品种池文件路径: {g.excel_path}")
    # 读取品种池数据
    try:
        g.pools_df = pd.read_excel(g.excel_path)
        log_info(f"[初始化] 品种池读取成功，共 {len(g.pools_df)} 个品种")
        log_info(f"[初始化] 品种池字段: {g.pools_df.columns.tolist()}")
    except Exception as e:
        log_info(f"[初始化] 品种池读取失败: {str(e)}")
        g.pools_df = pd.DataFrame()

    # 显示品种池内容（用于调试）
    log_info(f"[初始化] 品种池内容预览:")
    log_info(f"{g.pools_df[['代码', '交易所代码', 'n手（取整）']].to_string()}")

    if g.pools_df.empty:
        log_info("[处理函数] 品种池为空，无法执行选品")
        return

    # 记录上次选品执行时间，避免重复执行
    g.last_execute_date = None

    ContextInfo.stock_codes_dict = None

    # ContextInfo.stock_codes = [stock_info["code"] + '.' + stock_info["market"] for stock_code, stock_info in
    #                            ContextInfo.stock_codes_dict.items()]
    #
    # ContextInfo.set_universe(ContextInfo.stock_codes)
    # log_info(f"[初始化] 设置交易标的: {ContextInfo.stock_codes}")

    dividend_type = ContextInfo.dividend_type
    log_info(f"[初始化] 复权方式: {dividend_type}")

    # 策略参数
    g.entry_window = 10  # 入市通道周期（突破周期）
    g.exit_window = 4  # 止盈通道周期
    g.atr_window = 10  # ATR计算周期
    g.stop_profit_ratio = 0.2  # 止盈比例
    g.stop_loss_multiplier = 1  # 止损ATR倍数
    g.position_limit = 5  # 持仓上线
    g.near_expiry_days = 30  # 临近到期日天数上线
    g.capital_rate = 0.1  # 资金比例 资金固定值，参数失效
    g.is_trend_or_efficiency = 1  # 1：趋势幅度； 2:效率策略

    # # 资金管理参数
    # g.long_capital = 10000  # 做多资金
    # g.short_capital = 10000  # 做空资金

    log_info(f"[初始化] 策略参数设置完成:")
    log_info(f"        入市通道周期: {g.entry_window}")
    log_info(f"        止盈通道周期: {g.exit_window}")
    log_info(f"        ATR计算周期: {g.atr_window}")
    log_info(f"        止盈比例: {g.stop_profit_ratio}")
    log_info(f"        止损ATR倍数: {g.stop_loss_multiplier}")
    log_info(f"        资金比例: {g.capital_rate}")

    # 策略状态变量
    g.N = {}  # 波动幅度(N值/ATR)，为每个合约保存
    g.long_position = {}  # 多头持仓：0-无仓位，1-持有多头，为每个合约保存
    g.short_position = {}  # 空头持仓：0-无仓位，1-持有空头，为每个合约保存
    g.highest_after_entry = {}  # 入市后的最高价，为每个合约保存
    g.lowest_after_entry = {}  # 入市后的最低价，为每个合约保存
    g.long_open_date = {}  # 多头开仓日期，为每个合约保存
    g.short_open_date = {}  # 空头开仓日期，为每个合约保存
    g.long_volume = {}  # 多头持仓量，为每个合约保存
    g.long_entry_price = {}  # 多头持仓价，为每个合约保存
    g.short_volume = {}  # 空头持仓量，为每个合约保存
    g.short_entry_price = {}  # 空头持仓价，为每个合约保存

    g.expire_date = {}  # 当前需要交易的合约的到期日，为每个合约保存
    g.current_trading_contracts = []  # 当前需要交易的合约，为每个合约保存
    g.expire_date_diff = {}  # 到期日与当前日期的差值，为每个合约保存
    g.position_count = 0  # 当前持仓数量
    g.position_code = []  # 当前持仓的合约
    g.position_size = {}  # 交易合约对应的手数，为每个合约保存
    g.pending_cancel_contracts = []  # 需要撤销委托的合约列表

    g.is_backtest = True  # 获取是否为回测模式

    log_info(f"[初始化] 策略状态变量初始化完成")

    log_info(f"[初始化] 账户信息设置完成:")
    log_info(f"        期货账户ID: {ContextInfo.account_id}")

    log_section("海龟交易策略初始化完成")

    # ContextInfo.run_time("run_time_handlebar", "3nSecond", "2025-01-01 09:30:00")

# 选品方法
def select_pools(ContextInfo):

    # ========== 获取当前时间 ==========
    # 使用timetag_to_datetime获取当前时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    log_info(f"[处理函数] 获取当前时间: {bar_date}")
    current_date = int(bar_date[:8])  # 日期部分 20250228
    current_hour = int(bar_date[8:10])  # 小时分钟
    log_info(f"[处理函数] 当前时间: {bar_date}")
    log_info(f"[处理函数] 当前日期: {current_date}, 当前小时: {current_hour}")

    # ========== 判断是否执行选品逻辑 ==========
    # 日盘开始时间：09:00
    # 夜盘开始时间：21:00
    # 只有在09:00或21:00时才执行，且每天每个时段只执行一次

    # 构造执行标记：日期_时段（1=日盘，2=夜盘）
    session = 1 if current_hour in (9, 0) else (2 if current_hour == 21 else 0)
    execute_key = f"{current_date}_{session}"

    if session == 0:
        log_info("[处理函数] 当前不是日盘或夜盘开始时间，跳过")
        return

    if g.last_execute_date == execute_key:
        log_info(f"[处理函数] 本时段已经执行过选品，跳过 (execute_key={execute_key})")
        return

    # 更新执行标记
    g.last_execute_date = execute_key
    log_info(f"[处理函数] 开始执行选品逻辑，执行时段: {'日盘' if session == 1 else '夜盘'}")
    # ========== 执行选品逻辑 ==========
    try:
        # 步骤1：读取品种池
        log_section("步骤1：读取品种池")
        pools_df = g.pools_df

        log_info(f"[处理函数] 品种池共 {len(pools_df)} 个品种")
        # 步骤2：遍历品种池，获取主力合约和计算指标
        log_section("步骤2：获取主力合约和计算指标")
        results = []  # 存储所有品种的计算结果
        for idx, row in pools_df.iterrows():
            # 获取品种信息
            code = row['代码']  # 品种代码，如 rb
            exchange_code = row['交易所代码']  # 交易所代码，如 SF
            n_lots = row['n手（取整）']  # n手（取整）
            log_info(f"\n{'=' * 60}")
            log_info(f"[处理函数] 正在处理品种: {code}, 交易所: {exchange_code}, n手: {n_lots}")
            # 步骤2.1：构造连续合约代码
            # 连续合约 = 品种代码 + "00" + "." + 交易所代码
            # 例如：rb + "00" + "." + "SF" = "rb00.SF"
            continuous_contract = code + "00" + "." + exchange_code
            log_info(f"[处理函数] 连续合约代码: {continuous_contract}")

            # 步骤2.2：获取主力合约代码
            # 使用 ContextInfo.get_main_contract() 获取主力合约
            try:
                main_contract_code = ContextInfo.get_main_contract(continuous_contract)
                if not main_contract_code:
                    log_info(f"[处理函数] 无法获取 {continuous_contract} 的主力合约，跳过")
                    continue

                # 主力合约 = 主力合约代码 + "." + 交易所代码
                # 例如：RB2405 + "." + "SF" = "RB2405.SF"
                main_contract = main_contract_code + "." + exchange_code
                log_info(f"[处理函数] 主力合约代码: {main_contract}")
            except Exception as e:
                log_info(f"[处理函数] 获取主力合约失败: {str(e)}，跳过")
                continue

            # 步骤2.3：获取近10日历史K线数据
            current_contract = continuous_contract if g.is_backtest else main_contract  # 回测用continuous_contract，实盘使用main_contract

            # 需要获取15条数据（取11天前的数据用于计算10日趋势）
            try:
                log_info(f"[处理函数] 正在获取 {current_contract} 的历史K线数据...")
                history_data = ContextInfo.get_market_data_ex(
                    ['time', 'open', 'high', 'low', 'close'],
                    [current_contract],
                    end_time=bar_date,
                    period='1d',
                    count=13,  # 需要11天前的数据
                    dividend_type=ContextInfo.dividend_type,
                    subscribe=True
                )
                if not history_data or current_contract not in history_data:
                    log_info(f"[处理函数] 无法获取 {current_contract} 的历史数据，跳过")
                    continue
                history_df = history_data[current_contract]
                log_info(f"[处理函数] 获取到 {len(history_df)} 条历史数据")
                # 转换时间戳为可读格式
                history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))
                # 日盘和夜盘的0-2点（后半段）删除历史数据中的最后一条（当天数据）。 夜盘21点-24点 最后一条是当天白天的记录不删除
                history_df = history_df[:-1] if current_hour < 21 else history_df
                # 根据时间倒序排列
                history_df = history_df.sort_values(by='time', ascending=False).reset_index(drop=True)
                log_info(f"[处理函数] 历史数据:\n{history_df.to_string()}")
            except Exception as e:
                log_info(f"[处理函数] 获取历史数据失败: {str(e)}，跳过")
                continue

            # 步骤2.4：计算指标
            # 需要至少12条数据（第0条到第11条）
            if len(history_df) < 12:
                log_info(f"[处理函数] 数据不足12条，无法计算指标，跳过（当前{len(history_df)}条）")
                continue

            try:
                # 10日趋势 = |昨日收盘价 - 11日前收盘价| / 11日前收盘价

                # 昨天收盘价 = history_df['close'].iloc[0]
                # 11天前收盘价 = history_df['close'].iloc[11]
                close_yesterday = history_df['close'].iloc[0]  # 昨天收盘价
                close_11days_ago = history_df['close'].iloc[9]  # 11天前收盘价

                # 计算10日趋势的幅度（绝对值）
                trend_amplitude = abs(close_yesterday - close_11days_ago)

                # 计算10日趋势（百分比）
                if close_11days_ago != 0:
                    ten_day_trend = trend_amplitude / close_11days_ago
                else:
                    ten_day_trend = 0

                log_info(f"[处理函数] 昨日收盘价: {close_yesterday}, 11日前收盘价: {close_11days_ago}")
                log_info(f"[处理函数] 10日趋势幅度: {trend_amplitude}, 10日趋势: {ten_day_trend:.4%}")

                # 10日波动 = Σ(|最高价 - 最低价|)，近10天
                # 即：Σ(第1根到第10根K线的 |high - low|)
                volatility_sum = 0
                for i in range(0, 10):  # 第1根到第10根K线
                    high = history_df['high'].iloc[i]
                    low = history_df['low'].iloc[i]
                    daily_range = abs(high - low)
                    volatility_sum += daily_range

                log_info(f"[处理函数] 10日波动: {volatility_sum}")

                # 趋势效率 = 10日趋势幅度 / 10日波动
                # 趋势效率越高，说明波动越有方向
                if volatility_sum != 0:
                    trend_efficiency = trend_amplitude / volatility_sum
                else:
                    trend_efficiency = 0  # 避免除零

                log_info(f"[处理函数] 趋势效率: {trend_efficiency:.4f}")

                # 保存结果
                result = {
                    '连续合约': continuous_contract,
                    '主力合约': main_contract,
                    '代码': code,
                    '交易所代码': exchange_code,
                    'n手（取整）': n_lots,
                    '10日趋势': ten_day_trend,
                    '10日趋势幅度': trend_amplitude,
                    '10日波动': volatility_sum,
                    '趋势效率': trend_efficiency
                }
                results.append(result)

                log_info(
                    f"[处理函数] 品种 {code} 计算完成，10日趋势={ten_day_trend:.4%}, 趋势效率={trend_efficiency:.4f}")

            except Exception as e:
                log_info(f"[处理函数] 计算指标失败: {str(e)}，跳过")
                continue

        # 步骤3：排序并输出TOP3
        log_section("步骤3：排序并输出TOP3")

        if not results:
            log_info("[处理函数] 没有有效的计算结果")
            return

        # 转换为DataFrame便于排序
        results_df = pd.DataFrame(results)
        log_info(f"[处理函数] 有效品种数量: {len(results_df)}")

        # 3.1 10日趋势TOP3（按10日趋势降序排列）
        log_section("10日趋势TOP3")
        top3_trend = results_df.nlargest(3, '10日趋势')
        log_info(f"\n{top3_trend[['连续合约', '主力合约', '代码', '交易所代码', 'n手（取整）', '10日趋势']].to_string()}")

        # 3.2 趋势效率TOP3（按趋势效率降序排列）
        log_section("趋势效率TOP3")
        top3_efficiency = results_df.nlargest(3, '趋势效率')
        log_info(
            f"\n{top3_efficiency[['连续合约', '主力合约', '代码', '交易所代码', 'n手（取整）', '趋势效率']].to_string()}")

        # 步骤4：输出完整结果（可用于后续合约交易所）
        log_section("完整计算结果（用于后续交易所）")
        log_info(f"\n{results_df.to_string()}")

        # 步骤5：封装成stock_codes_dict格式，供海龟交易策略使用
        log_section("步骤5：封装stock_codes_dict格式")
        g.stock_codes_dict_top3_trend = convert_to_stock_codes_dict(top3_trend)
        g.stock_codes_dict_top3_efficiency = convert_to_stock_codes_dict(top3_efficiency)

        log_info(f"[处理函数] 10日趋势TOP3 stock_codes_dict: {g.stock_codes_dict_top3_trend}")
        log_info(f"[处理函数] 趋势效率TOP3 stock_codes_dict: {g.stock_codes_dict_top3_efficiency}")
        if g.is_trend_or_efficiency == 1:
            ContextInfo.stock_codes_dict = g.stock_codes_dict_top3_trend
        elif g.is_trend_or_efficiency == 2:
            ContextInfo.stock_codes_dict = g.stock_codes_dict_top3_efficiency

        # 保存结果到全局变量，供后续使用
        # g.top3_trend = top3_trend
        # g.top3_efficiency = top3_efficiency
        # g.all_results = results_df

        log_info("[处理函数] 选品策略执行完成")

    except Exception as e:
        log_info(f"[处理函数] 执行选品逻辑异常: {str(e)}")
        import traceback
        log_info(traceback.format_exc())



def handlebar(ContextInfo):  # 策略处理函数
# def run_time_handlebar(ContextInfo):  # 定时运行
    """
    主要处理函数
    在每个K线周期都会被调用
    """

    select_pools(ContextInfo)

    ContextInfo.stock_codes = [stock_info["code"] + '.' + stock_info["market"] for stock_code, stock_info in
                               ContextInfo.stock_codes_dict.items()]

    ContextInfo.set_universe(ContextInfo.stock_codes)
    log_info(f"[初始化] 设置交易标的: {ContextInfo.stock_codes}")
    # 获取是否为回测模式
    if g.is_backtest == True:
        log_info("[处理函数] 当前为回测任务，跳过本次处理")
    else:
        if not ContextInfo.is_last_bar():
            log_info("[处理函数] 当前不是最后一个K线周期，跳过本次处理")
            return

        # 判断当前是否为周末
        if is_weekend():
            return

        # 根据当前时间计算如果如果时间不在开盘时间内就直接退出，已知的开盘时间段有：0:00-2:30，9:00-11:30，13:30-15:00，21:00-24:00

        if not is_trading_time(datetime.now()):
            log_info(f"[处理函数] 当前时间不在交易时间段内，跳过本次处理")
            return

    log_section("[处理函数] 开始执行handlebar函数")

    # 获取历史数据 获取数据的截止时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    g.current_date_bar = bar_date
    g.current_date_bar_hour = int(bar_date[8:10])
    log_info(f"  获取截止时间: {g.current_date_bar}")


    # 清空上一次的交易合约列表
    g.current_trading_contracts = []
    # 获取主力合约代码替代连续合约
    for stock_key, stock_info in ContextInfo.stock_codes_dict.items():
        main_stock_code = stock_info["code"] + '.' + stock_info["market"]
        # 获取主力合约代码，使用当前日期
        main_contract = ContextInfo.get_main_contract(main_stock_code) + '.' + stock_info["market"]
        if main_contract and g.is_backtest == False:
            g.position_size[main_contract] = stock_info["size"]
            g.current_trading_contracts.append(main_contract)
            log_info(f"[初始化] 连续合约 {main_stock_code} 对应的主力合约为: {main_contract}")
        else:
            # 如果获取不到主力合约，则使用原连续合约
            g.position_size[main_stock_code] = stock_info["size"]

            g.current_trading_contracts.append(main_stock_code)
            log_info(f"[初始化] 无法获取 {main_stock_code} 的主力合约，继续使用原合约")

    log_info(f"[初始化] 当前在交易的合约: {g.current_trading_contracts}")

    # 获取当前账户信息（只需要获取一次）
    log_info("[账户信息] 开始获取账户信息...")
    account_info = get_account_info(ContextInfo)
    if account_info is None:
        log_info("[账户信息] 无法获取账户信息，跳过本次处理")
        log_separator()
        return
    log_info("[账户信息] 成功获取账户信息")

    # 需要交易的合约g.current_trading_contracts 和持仓代码 position_code 两个list 合并去重得到要执行的合约代码
    g.current_trading_contracts = list(set(g.current_trading_contracts + g.position_code))

    # 从需要交易的合约中剔除需要撤销委托的合约
    if hasattr(g, 'pending_cancel_contracts') and g.pending_cancel_contracts:
        g.current_trading_contracts = [contract for contract in g.current_trading_contracts if
                                       contract not in g.pending_cancel_contracts]
        log_info(f"[初始化] 剔除需要撤销委托的合约后，需要处理的合约: {g.current_trading_contracts}")
    log_info(f"[初始化]  需要处理的合约: {g.current_trading_contracts}")

    # 为每个合约执行策略逻辑
    for stock_code in g.current_trading_contracts:
        log_info(f"{60 * '-'} \n [处理函数] 处理合约: {stock_code}")

        # 设置当前处理的合约为全局变量，供其他函数使用
        g.current_stock_code = stock_code

        # 获取合约基础信息
        stock_contract_info = ContextInfo.get_instrument_detail(g.current_stock_code)
        if stock_contract_info is None:
            message = f"[异常处理] 合约基础信息获取失败: {g.current_stock_code}"
            log_info(message)
            # send_feishu_message(message)

            continue
        log_debug(f"[数据获取] 合约基础信息: {stock_contract_info}")

        # 获合约的退市日或者到期日 ExpireDate
        g.expire_date[g.current_stock_code] = '99991231' if g.is_backtest else str(stock_contract_info.get('ExpireDate', 99991231))
        log_info(f"[数据获取] 合约的退市日或者到期日: {g.expire_date[g.current_stock_code]}")

        # 当前合约的到期日(YYYYMMDD) 和 当前日期 g.current_date_bar[:8](YYYYMMDD) 差几天
        g.expire_date_diff[g.current_stock_code] = (datetime.strptime(g.expire_date[g.current_stock_code],
                                                                      '%Y%m%d') - datetime.strptime(
            g.current_date_bar[:8], '%Y%m%d')).days if g.expire_date[g.current_stock_code] else 999
        log_info(f"[数据获取] 获取合约的到期日和当前日期的差: {g.expire_date_diff[g.current_stock_code]}")

        if g.expire_date_diff[g.current_stock_code] < g.near_expiry_days:
            log_info(f"[数据获取] {g.current_stock_code} 的到期日小于{g.near_expiry_days}天，不执行新的开仓操作")
        else:
            log_info(f"[数据获取] {g.current_stock_code} 的到期日大于{g.near_expiry_days}天，可以执行新的开仓操作")

        # 检查数据是否足够
        required_data = max(g.entry_window, g.exit_window, g.atr_window)
        log_debug(f"[数据检查] 当前bar位置: {ContextInfo.barpos}, 所需数据: {required_data}")
        if ContextInfo.barpos < required_data:
            message = "[异常处理] 数据不足，跳过本次处理"
            log_info(message)
            # send_feishu_message(message)
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
                message = "[异常处理] 数据不足，跳过本次处理"
                log_info(message)
                # send_feishu_message(message)
                log_separator()
                continue
            log_debug(f"[数据获取] 成功获取价格数据，共 {len(price_data)} 条记录")

            # 计算ATR和N值
            log_debug("[ATR计算] 开始计算ATR和N值...")
            g.N[stock_code] = calculate_atr(stock_code, price_data, g.atr_window)

            if g.N[stock_code] <= 0:
                log_info("[异常处理] ATR值计算异常，跳过本次处理")

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
            end_time=g.current_date_bar,
            period='1d',
            count=required_bars,
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )
        if not history_market_data or g.current_stock_code not in history_market_data:
            message = "  [异常处理] 获取历史市场数据为空"
            log_info(message)
            # send_feishu_message(message)
            return None

        history_df = history_market_data[g.current_stock_code]

        # 将时间戳转换为可读的时间格式
        history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))
        log_debug(f"\n{history_df}")
        log_debug(f"  [价格数据] 请求参数 - 标的: {g.current_stock_code}, 周期: {ContextInfo.period}, 数量: 1")

        # 当日K线集合
        current_market_data_more = ContextInfo.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close'],
            [g.current_stock_code],
            start_time=get_futures_start_time(g.current_date_bar),  # 根据期货交易时间规则确定开始时间
            end_time=g.current_date_bar,
            period=ContextInfo.period,  # 使用1分钟周期
            dividend_type=ContextInfo.dividend_type,
            subscribe=True
        )

        if not current_market_data_more or g.current_stock_code not in current_market_data_more:
            message = "  [异常处理] 获取当日市场数据为空"
            log_info(message)
            # send_feishu_message(message)
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

            # 日盘和夜盘的0-2点（后半段）删除历史数据中的最后一条（当天数据）。 夜盘21点-24点 最后一条是当天白天的记录不删除
            history_df = history_df[:-1] if g.current_date_bar_hour < 21 else history_df
            # 将当日最新数据添加到历史数据末尾
            df = pd.concat([history_df, current_df], ignore_index=True)
        else:
            df = history_df

        return df

    except Exception as e:
        message = f"  [异常处理] 获取价格数据时发生错误: {e}"
        log_info(message)
        send_feishu_message(message)
        return None


def calculate_atr(stock_code, data, window):
    """
    计算ATR(N值)，支持多合约独立计算
    ATR是真实波幅的N日平均值，用于衡量市场波动性
    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        log_debug(f"  [ATR计算] 开始计算ATR，使用 {window} 日数据 (合约: {stock_code})")
        # 计算真实波幅(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        log_debug(f"  [ATR计算] 价格数据统计 (合约: {stock_code}):")
        log_debug(f"    最高价范围: {high[-window - 1:-1]}")
        log_debug(f"    最低价范围: {low[-window - 1:-1]}")
        log_debug(f"    收盘价范围: {close[-window - 1:-1]}")

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        log_debug(f"  [ATR计算] 计算得到TR值: {tr[-window:]}")

        # 计算ATR(N日均值)
        atr = np.mean(tr[-window:])
        log_info(f"  [ATR计算] ATR计算结果: {atr} (合约: {stock_code})")

        # TR值和ATR值写到data中用于查询记录信息
        # 修复长度不匹配问题：tr数组比原始数据少一个元素（因为计算差值）
        data['tr'] = np.append([np.nan], tr)  # 在前面添加NaN以匹配长度
        data['atr'] = atr

        # 保存到全局变量中，每个合约独立存储
        g.N[stock_code] = atr

        return atr

    except Exception as e:
        message = f"  [异常处理] 计算ATR时发生错误: {e} (合约: {stock_code})"
        log_info(message)
        # send_feishu_message(message)
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
        account_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            message = "  [异常处理] 获取账户详情失败"
            log_info(message)
            # send_feishu_message(message)
            return None
        g.position_code = []  # 仓位代码
        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益

        log_info(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")

        # 重置主力合约的持仓状态
        for stock_code in g.current_trading_contracts:
            g.long_position[stock_code] = 0  # 重置多头持仓状态
            g.short_position[stock_code] = 0  # 重置空头持仓状态
            g.long_open_date[stock_code] = None  # 重置多头开仓日期
            g.short_open_date[stock_code] = None  # 重置空头开仓日期
            log_info(f"重置所有主力合约的持仓状态 {stock_code} 仓位状态 重置成功 {g.long_position[stock_code]} ")

        g.position_count = 0

        # 获取未成交委托信息并撤销未成交委托
        log_debug("  [账户信息] 获取未成交委托详情...")
        order_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ORDER')
        # 清空需要撤销委托的合约列表
        g.pending_cancel_contracts = []
        if order_details:
            order_len = 0
            for order in order_details:
                # log_info(f"  [账户信息] 获取到委托记录：\n {to_dict(order)}")
                # 获取委托状态
                order_status = order.m_nOrderStatus
                symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID
                log_info(f"  [账户信息] 获取委托记录: {symbol} 委托状态为： {order_status}")

                # 检查是否为未成交状态 53 部撤 54 已撤、 56 已成、57 废单
                if order_status not in (53, 54, 56, 57):
                    log_info(
                        f"  [账户信息] 发现未完成委托，合约: {symbol}, 状态: {order_status}, 委托编号: {order.m_strOrderSysID}")
                    # 将需要撤销委托的合约添加到列表中
                    if symbol not in g.pending_cancel_contracts:
                        g.pending_cancel_contracts.append(symbol)
                        message = f"  [账户信息] 将需要撤销的合约添加到列表中: {symbol}"
                        log_info(message)
                        # send_feishu_message(message)
                    # 撤销未成交委托
                    cancel_result = cancel(order.m_strOrderSysID, ContextInfo.account_id, 'FUTURE', ContextInfo)
                    log_info(f"  [账户信息] 撤销委托结果: {cancel_result}")
                    order_len += 1
                else:
                    log_info(f"  [账户信息] 合约: {symbol} ,委托状态为: {order_status}，无需撤销")
            message = f"  [账户信息] 处理  {order_len} 条委托记录，需要撤销委托的合约: {g.pending_cancel_contracts}"
            log_info(message)

        else:
            log_info("  [账户信息] 无委托记录")

        # 获取持仓信息
        log_debug("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'POSITION')
        log_debug(f"  [账户信息] 获取持仓详情成功，共有 {len(position_details)} 条数据")
        PositionInfo_dict = {}
        PositionInfo_dfs = pd.DataFrame()

        aggregated_positions = pd.DataFrame()  # 初始化为空DataFrame

        if position_details:
            position_data_list = []
            for pos in position_details:
                if pos.m_nVolume != 0:  # 忽略持仓量为0的合约
                    # 获取 pos 对象转json信息
                    log_debug(f"  [账户信息] 获取持仓属性信息: {dir(pos)}")
                    symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID

                    position_type = pos.m_nDirection
                    # 构建持仓数据列表用于后续聚合
                    position_record = {
                        '持仓量': pos.m_nVolume,
                        '代码': symbol,
                        '持仓类型': position_type,
                        '持仓成本': pos.m_dOpenPrice,
                        '持仓盈亏': pos.m_dPositionProfit,
                        '开仓日期': pos.m_strOpenDate
                    }
                    position_data_list.append(position_record)
            # 创建DataFrame并按代码和持仓类型聚合持仓数据
            if position_data_list:
                PositionInfo_dfs = pd.DataFrame(position_data_list)

                # 按代码和持仓类型聚合持仓数据
                aggregated_positions = PositionInfo_dfs.groupby(['代码', '持仓类型']).agg({
                    '持仓量': 'sum',
                    '持仓成本': lambda x: np.average(x, weights=PositionInfo_dfs.loc[x.index, '持仓量']),
                    # 加权平均成本
                    '持仓盈亏': 'sum',
                    '开仓日期': 'first'
                }).reset_index()
            if not aggregated_positions.empty:
                # 从聚合后的数据中获取持仓信息
                for _, row in aggregated_positions.iterrows():

                    symbol = row['代码']
                    position_type = row['持仓类型']
                    volume = row['持仓量']
                    entry_price = row['持仓成本']
                    open_date = row['开仓日期']
                    log_info(
                        f"  [账户信息] 获取持仓信息: {symbol} ，持仓类型:{position_type}，持仓量: {volume}，持仓成本: {entry_price}，开仓日期: {open_date}")

                    g.long_position[symbol] = 0  # 重置多头持仓状态
                    g.short_position[symbol] = 0  # 重置空头持仓状态

                    # 检查持仓是否属于当前策略的合约
                    if position_type == 48:  # 多头持仓
                        g.long_position[symbol] = 1  # 多头持仓状态
                        g.long_open_date[symbol] = open_date  # 多头开仓日期
                        g.long_volume[symbol] = volume  # 多头持仓量
                        g.long_entry_price[symbol] = entry_price  # 多头持仓成本

                    elif position_type == 49:  # 空头持仓
                        g.short_position[symbol] = 1  # 空头持仓状态
                        g.short_open_date[symbol] = open_date  # 空头开仓日期
                        g.short_volume[symbol] = volume  # 空头持仓量
                        g.short_entry_price[symbol] = entry_price  # 空头持仓成本
            log_debug(f"    [账户信息] 持仓明细:\n {str(PositionInfo_dfs)} ")
            log_debug(f"    [账户信息] 聚合后持仓:\n {str(aggregated_positions)} ")

            # 持仓数量通过PositionInfo_dfs有几行数据来决定
            g.position_count = aggregated_positions.shape[0]
            log_debug(f"  [账户信息] 更新持仓状态，当前持仓合约数: {g.position_count}")

            g.position_code = aggregated_positions['代码'].tolist() if g.position_count != 0 else []
            log_debug(f"  [账户信息] 持仓合约列表: {g.position_code}")


        else:
            log_info("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            'PositionInfo_dfs': PositionInfo_dfs,
            'PositionInfo_dict': PositionInfo_dict,  # 返回更多持仓信息
        }

    except Exception as e:
        message = f"  [异常处理] 获取账户信息时发生错误: {e}"
        log_info(message)
        # send_feishu_message(message)
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

        # 做空：过去entry_window天收盘价的最低价
        lower_channel = price_data['close'].iloc[-g.entry_window - 1:-1].min()

        # 计算离市信号 - 离市通道
        # 做多止盈 过去exit_window天收盘价的最低价
        exit_lower = price_data['close'].iloc[-g.exit_window - 1:-1].min()

        # 做空止盈 过去exit_window天收盘价的最高价
        exit_upper = price_data['close'].iloc[-g.exit_window - 1:-1].max()

        log_info(f"  [信号生成] 通道信息: 合约代码: {g.current_stock_code}")
        log_info(f"    当日价格: {current_price:.4f}")
        log_info(f"    当日最高价: {current_high:.4f}")
        log_info(f"    当日最低价: {current_low:.4f}")
        log_info(f"    做多: {upper_channel:.4f}")
        log_info(f"    做空: {lower_channel:.4f}")
        log_info(f"    做多止盈: {exit_lower:.4f}")
        log_info(f"    做空止盈: {exit_upper:.4f}")
        log_info(f"    多头持仓: {g.long_position[g.current_stock_code]}")
        log_info(f"    空头持仓: {g.short_position[g.current_stock_code]}")
        log_info(f"    当前ATR值: {g.N[g.current_stock_code]:.4f}")

        # 修改后：检查是否持有多头或空头仓位
        if g.long_position[g.current_stock_code] == 1:  # 多头已有持仓
            log_debug(f"  [信号生成] 已有多头持仓，更新最高:")

            long_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [g.current_stock_code],
                start_time=g.long_open_date[g.current_stock_code],
                end_time=g.current_date_bar,
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

        if g.short_position[g.current_stock_code] == 1:  # 空头已有持仓
            log_debug(f"  [信号生成] 已有空头持仓，更新最低:")
            short_history_market_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close'],
                [g.current_stock_code],
                start_time=g.short_open_date[g.current_stock_code],
                end_time=g.current_date_bar,
                period='1d',
                dividend_type=ContextInfo.dividend_type,
                subscribe=True
            )

            short_history_market_data_min = short_history_market_data[g.current_stock_code]['low'].iloc[:-1].min()
            # 历史最低价 和 当日最低价比较
            g.lowest_after_entry[g.current_stock_code] = current_low if np.isnan(
                short_history_market_data_min) else min(
                short_history_market_data_min, current_low)

            log_info(f"    更新后最低价: {g.lowest_after_entry[g.current_stock_code]}")

        # 海龟交易法则信号判断
        # 判断多头信号（无多头持仓时可做多，有多头持仓时判断是否平多）
        if g.long_position[g.current_stock_code] == 0 and g.expire_date_diff[
            g.current_stock_code] > g.near_expiry_days and g.position_count < g.position_limit:  # 无多头持仓，判断是否做多 距离到期日大于30天 持仓小于4个
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

        # 判断空头信号（无空头持仓时可做空，有空头持仓时判断是否平空）
        if g.short_position[g.current_stock_code] == 0 and g.expire_date_diff[
            g.current_stock_code] > g.near_expiry_days and g.position_count < g.position_limit:  # 无空头持仓，判断是否做空 且 距离到期日大于30天 持仓小于4个
            log_info("  [信号生成] 检测空头信号")
            # 买入2（做空）：当日价格 < 前10日收盘价最低点时，即当前价格突破10日低点，当日立刻执行做空
            if current_price < lower_channel:  # 突破下轨，卖空信号（做空）
                log_info("  [信号生成] 产生卖空信号：价格突破入市下轨")
                log_info(f"  [信号生成] 买入2（做空）: {current_price:.4f} 小于 下轨 {lower_channel}")

                return (1, -1)  # 开仓信号，空头操作
        elif g.short_position[g.current_stock_code] == 1:  # 有空头持仓，判断是否平空

            # 空仓止损卖出2：买入第二天开始，当价格 > 买入价 + N * ATR时，立刻执行卖出
            log_info("  [信号生成] 当前持有空头仓位，判断是否平仓")

            # 空仓止盈信号 - 价格突破止盈做空点且价格大于最低价反弹一定比例
            stop_profit_price = g.lowest_after_entry[g.current_stock_code] + (
                    g.short_entry_price[g.current_stock_code] - g.lowest_after_entry[
                g.current_stock_code]) * g.stop_profit_ratio
            log_info(f"  [信号生成] 空头止盈价格计算:")
            log_info(f"    公式: 最低价 + (入场价 - 最低价) * 止盈比例")
            log_info(
                f"    数值: {g.lowest_after_entry[g.current_stock_code]} + ({g.short_entry_price[g.current_stock_code]} - {g.lowest_after_entry[g.current_stock_code]}) * {g.stop_profit_ratio} = {stop_profit_price:.4f}")

            # 空仓止损信号3 卖出价 + N * ATR
            stop_loss_price = g.short_entry_price[g.current_stock_code] + g.stop_loss_multiplier * g.N[
                g.current_stock_code]

            # 止盈卖出2：买入第二天开始，当价格 > 前4日收盘价最高点时，且价格 > 最低价 +（买入价 - 最低价）*20 % （最低价是指买入后到计算时的最低价）时，立刻执行卖出
            if current_price > exit_upper and current_price > stop_profit_price:
                log_info("  [信号生成] 产生空头止盈信号：价格突破止盈做空点且反弹达到阈值")
                log_info(f"    当前价格: {current_price} > 止盈做空点: {exit_upper}")
                log_info(f"    当前价格: {current_price} > 止盈价格: {stop_profit_price:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            # 止损信号 - 价格上涨超过NATR
            elif current_price > g.short_entry_price[g.current_stock_code] + g.stop_loss_multiplier * g.N[
                g.current_stock_code]:
                log_info("  [信号生成] 产生空头止损信号：价格上涨超过NATR")
                log_info(f"    当前价格: {current_price} > 止损价格: {stop_loss_price:.4f}")
                log_info(
                    f"    入场价: {g.short_entry_price[g.current_stock_code]}, ATR: {g.N[g.current_stock_code]:.4f}")
                return (-1, -1)  # 平仓信号，空头操作
            else:
                log_info("  [信号生成] 无平空信号")

        return (0, 0)  # 无交易信号

    except Exception as e:
        message = f"  [异常处理] 生成交易信号时发生错误: {e}"
        log_info(message)
        # send_feishu_message(message)
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

        log_debug("  [交易执行] 开始执行交易操作...")
        signal_type, position_type = signal
        log_info(f"  [交易执行] 交易信号: 信号类型={signal_type}, 仓位类型={position_type}")

        current_price = price_data['close'].iloc[-1]
        log_info(f"  [交易执行] 合约信息:当前价格: {current_price:.4f}")

        # 开仓操作
        if signal_type > 0:  # 开仓信号
            if position_type > 0:  # 做多
                # 检查是否当前没有多头持仓
                if g.long_position[g.current_stock_code] == 0:

                    # 0	开多  1101: 限价单  5: 对手价 -1: 市价  position_size: 手数
                    # passorder( opType, orderType, accountid , orderCode, prType, price, volume , strategyName, quickTrade, userOrderId , ContextInfo)
                    #        #  操作号    组合方式     资金账号    品种代码     报价类型  价格    下单量    策略名称        快速下单标记  投资备注        策略上下文
                    order_info = passorder(0, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                           g.position_size[g.current_stock_code], 1,
                                           ContextInfo)

                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    if order_info == 0:
                        message = f"  [交易执行] 执行买入开仓操作 下单参数: 合约代码： {g.current_stock_code},买入开仓,  对手价, 价格: {current_price:.4f}, {g.position_size[g.current_stock_code]}手数"
                        log_info(message)
                        # send_feishu_message(message)
                    else:
                        message = f"  [交易执行] 合约代码： {g.current_stock_code} 执行买入开仓操作 下单失败: {order_info}"
                        log_info(message)
                        # send_feishu_message(message)
                    g.long_position[g.current_stock_code] = 1
                    g.long_open_date[g.current_stock_code] = g.current_date_bar

                    g.position_count = g.position_count + 1
                    log_info(f"  [交易执行] 持仓计数器: {g.position_count}")
                else:
                    log_info("  [交易执行] 已持有多头仓位，不重复开仓")

            elif position_type < 0:  # 做空
                # 检查是否当前没有空头持仓

                if g.short_position[g.current_stock_code] == 0:
                    # 3: 开空
                    order_info = passorder(3, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                           g.position_size[g.current_stock_code], 1,
                                           ContextInfo)
                    log_info(f"  [交易执行] 下单结果: {order_info}")
                    if order_info == 0:
                        message = f"  [交易执行] 执行卖出开仓操作下单参数: 合约代码： {g.current_stock_code},卖出开仓, 限价单, 对手价, 市价, {g.position_size[g.current_stock_code]} 手数，价格: {current_price:.4f}"
                        log_info(message)
                        # send_feishu_message(message)
                    else:
                        message = f"  [交易执行] 合约代码： {g.current_stock_code} 执行卖出开仓操作下单失败: 错误信息: {order_info}"
                        log_info(message)
                        # send_feishu_message(message)
                    g.short_position[g.current_stock_code] = 1
                    g.short_open_date[g.current_stock_code] = g.current_date_bar

                    g.position_count = g.position_count + 1
                    log_info(f"  [交易执行] 持仓计数器: {g.position_count}")
                else:
                    log_info("  [交易执行] 已持有空头仓位，不重复开仓")

        # 平仓操作
        elif signal_type < 0:  # 平仓信号
            if position_type > 0 and g.long_position[g.current_stock_code] == 1:  # 平多仓
                # 7 平多, 优先平昨
                # 修正：使用手数而不是股数进行平仓

                order_info = passorder(7, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                       g.long_volume[g.current_stock_code], 1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                if order_info == 0:
                    message = f"  [交易执行] 执行买入平仓操作：下单参数: 合约代码： {g.current_stock_code},买入平仓, 对手价,  {g.long_volume[g.current_stock_code]} 手持仓，价格: {current_price:.4f} "
                    log_info(message)
                    # send_feishu_message(message)

                else:
                    message = "  [交易执行]  合约代码： {g.current_stock_code} ,平多仓失败"
                    log_info(message)
                    # send_feishu_message(message)

                g.long_position[g.current_stock_code] = 0
                g.highest_after_entry[g.current_stock_code] = 0
                g.lowest_after_entry[g.current_stock_code] = 0
                g.long_open_date[g.current_stock_code] = None
                g.position_count = g.position_count - 1
                log_info(f"  [交易执行] 持仓计数器: {g.position_count}")

            elif position_type < 0 and g.short_position[g.current_stock_code] == 1:  # 平空仓
                # 9 平空, 优先平昨
                # 修正：使用手数而不是股数进行平仓

                order_info = passorder(9, 1101, ContextInfo.account_id, g.current_stock_code, 14, -1,
                                       g.short_volume[g.current_stock_code],
                                       1, ContextInfo)
                log_info(f"  [交易执行] 下单结果: {order_info}")
                if order_info == 0:
                    message = f"  [交易执行] 执行卖出平仓操作:下单参数: 合约代码： {g.current_stock_code},卖出平仓, 对手价, {g.short_volume[g.current_stock_code]} 手持仓 ，价格: {current_price:.4f}"
                    log_info(message)
                    # send_feishu_message(message)
                else:
                    message = f"  [交易执行] 合约代码： {g.current_stock_code} ,平空仓失败"
                    log_info(message)
                    # send_feishu_message(message)
                g.short_position[g.current_stock_code] = 0
                g.highest_after_entry[g.current_stock_code] = 0
                g.lowest_after_entry[g.current_stock_code] = 0
                g.short_open_date[g.current_stock_code] = None
                g.position_count = g.position_count - 1
                log_info(f"  [交易执行] 持仓计数器: {g.position_count}")

    except Exception as e:
        message = f"  [异常处理] 执行交易操作时发生错误: {e}"
        log_info(message)
        # send_feishu_message(message)


def is_weekend():
    """
    判断当前是否为周末
    周六返回 True，周日返回 True，其他返回 False
    """
    current_date = datetime.now()
    # weekday(): Monday=0, Sunday=6，所以周六=5，周日=6
    if current_date.weekday() >= 5:
        log_info("[时间判断] 当前是周末，退出程序")
        return True
    return False


def is_trading_time(current_time):
    """
    判断当前时间是否为交易时间
    交易时间段：0:00-2:30，9:00-11:30，13:30-15:00，21:00-24:00
    """
    hour = current_time.hour
    minute = current_time.minute

    # 0:00-2:30
    if 0 <= hour <= 2:
        if hour == 2 and minute > 30:
            return False
        return True

    # 9:00-11:30
    if 9 <= hour <= 11:
        if hour == 11 and minute > 30:
            return False
        return True

    # 13:30-15:00
    if 13 <= hour <= 15:
        if hour == 13 and minute < 30:
            return False
        if hour == 15 and minute > 0:
            return False
        return True

    # 21:00-24:00 (即21:00-23:59)
    if 21 <= hour <= 23:
        return True

    return False


def get_log_filename(account_id=None):
    """
    获取当前日志文件名
    """
    global log_filename
    if log_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if account_id:
            log_filename = f"C:\\datalog\\datalog-{account_id}-{timestamp}.log"
        else:
            log_filename = f"C:\\datalog\\datalog-{timestamp}.log"
    return log_filename


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
    # print(f"{message}")


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
class G():
    pass


g = G()



def convert_to_stock_codes_dict(df):
    """
    工具方法
    将选品结果DataFrame转换为stock_codes_dict格式
    目标格式（与海龟交易策略一致）：
    {"品种代码": {"code": "连续合约代码", "market": "交易所代码", "size": n手}}
    例如：
        {"RB": {"code": "rb00", "market": "SF", "size": 10},
        "JM": {"code": "jm00", "market": "DF", "size": 4}}
    Args:  df: 选品结果DataFrame，需包含 '代码', '连续合约', '交易所代码', 'n手（取整）' 字段
    Returns:  dict: stock_codes_dict格式的字典
    """
    stock_codes_dict = {}
    for idx, row in df.iterrows():
        code = row['代码']  # 品种代码，如 rb
        continuous_contract = row['连续合约']  # 连续合约，如 rb00.SF
        exchange_code = row['交易所代码']  # 交易所代码，如 SF
        n_lots = row['n手（取整）']  # n手
        # 提取连续合约代码部分（去掉.SF等后缀）
        # 如 rb00.SF -> rb00
        contract_code = continuous_contract.split('.')[0] if '.' in continuous_contract else continuous_contract
        stock_codes_dict[code] = {
            "code": contract_code,  # 连续合约代码，如 rb00
            "market": exchange_code,  # 交易所代码，如 SF
            "size": int(n_lots)  # n手（取整）
        }

    return stock_codes_dict

def get_futures_start_time(current_date):
    """
    根据当前时间确定期货交易起始时间
    如果current_date的小时在21点之后，那么期货的交易时间从今天晚上九点开始
    否则期货交易时间从昨天晚上9点开始
    """

    current_time = datetime.strptime(current_date, '%Y%m%d%H%M%S')
    current_hour = current_time.hour

    # 期货交易日从晚上9点开始
    start_time = current_time.replace(hour=21, minute=0, second=0)

    # 如果当前时间在21点之前，说明是当天的日盘交易，需要从前一晚的夜盘开始
    if current_hour < 21:
        # 往前推一天
        start_time = start_time - pd.Timedelta(days=1)

    return start_time.strftime('%Y%m%d%H%M%S')


def send_feishu_message(message):
    if g.is_backtest == True:
        pass
    else:
        """发送飞书消息"""
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/086957a2-ddb4-4406-a720-3caaa7e3930f"

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        message = g.account + " : " + message
        # 飞书API要求content字段是JSON字符串，如 '{"text":"test content"}'
        content_str = json.dumps({"text": message}, ensure_ascii=False)
        body = {
            "msg_type": "text",
            "content": content_str  # content字段必须是JSON字符串格式
        }
        try:
            response = requests.post(url=url, headers=headers, json=body)  # 使用json参数自动处理序列化
            response_json = response.json()
            if response_json.get("code") == 0:
                print("消息发送成功")
                return True
            else:
                print(f"消息发送失败: {response_json}")
                return False
        except Exception as e:
            print(f"发送消息时出错: {e}")
            return False
