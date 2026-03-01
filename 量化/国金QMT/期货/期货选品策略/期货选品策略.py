# coding:gbk

"""
期货选品策略
基于国金QMT平台的期货品种选择策略

策略目标：
每天日盘开始时（09:00）和夜盘开始时（21:00），从品种池中筛选出：
1. 10日趋势TOP3的期货合约
2. 趋势效率TOP3的期货合约

指标计算：
1. 10日趋势 = |昨日收盘价 - 11日前收盘价| / 11日前收盘价
2. 10日趋势幅度 = |昨日收盘价 - 11日前收盘价|
3. 10日波动 = Σ(|最高价 - 最低价|)，近10天
4. 趋势效率 = 10日趋势幅度 / 10日波动

输出：
- 连续合约代码（用于回测）
- 主力合约代码（用于实盘）
- 交易所代码
- n手（取整）
- 对应的指标值
"""
# coding:gbk
import logging
from datetime import datetime
import json
import numpy as np
import pandas as pd

# 全局变量用于存储日志文件名
log_filename = None

# work_dir = '/Users/exiaozhong/CodeProjects/Quantitative_Trading/量化/国金QMT/期货/期货选品策略/'
work_dir = 'C:\\合约选品\\'

def init(ContextInfo):
    """
    初始化函数
    设置策略参数、交易标的等
    """
    # 账户信息
    ContextInfo.account_id = '809213023'  # 期货账户ID
    g.account = ContextInfo.account_id

    # 初始化日志文件
    global log_filename
    log_filename = None

    filename = get_log_filename(ContextInfo.account_id)
    # INFO 简要信息  DEBUG 详细日志
    logging.basicConfig(filename=filename, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    log_section("开始初始化期货选品策略...")

    # 品种池文件路径
    g.excel_file = '期货品种池.xlsx'

    g.excel_path = f'{work_dir}期货品种池.xlsx'

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

    g.is_backtest = True  # 获取是否为回测模式

    # 设置定时任务：日盘09:00和夜盘21:00执行
    # 注意：QMT的定时任务格式需要根据实际情况调整
    # 这里设置为每分钟检查一次，在handlebar中判断时间是否到达
    log_info("[初始化] 设置定时任务检查机制")

    # 记录上次执行时间，避免重复执行
    g.last_execute_date = None

    log_section("期货选品策略初始化完成")


def handlebar(ContextInfo):
    """
    主要处理函数
    在每个K线周期都会被调用
    """


    # ========== 获取当前时间 ==========
    # 使用timetag_to_datetime获取当前时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    log_info(f"[处理函数] 获取当前时间: {bar_date}")
    # bar_timetag = ContextInfo.get_bar_timetag(ContextInfo.barpos)
    # current_time_str = timetag_to_datetime(bar_timetag, '%Y-%m-%d %H:%M:%S')
    current_date = int(bar_date[:8])  # 日期部分 20250228
    current_hour = int(bar_date[8:10])  # 小时分钟

    log_info(f"[处理函数] 当前时间: {bar_date}")
    log_info(f"[处理函数] 当前日期: {current_date}, 当前小时: {current_hour}")

    # ========== 判断是否执行选品逻辑 ==========
    # 日盘开始时间：09:00
    # 夜盘开始时间：21:00
    # 只有在09:00或21:00时才执行，且每天每个时段只执行一次

    # 构造执行标记：日期_时段（1=日盘，2=夜盘）
    session = 1 if current_hour in (9,0) else (2 if current_hour == 21 else 0)
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
        if pools_df.empty:
            log_info("[处理函数] 品种池为空，无法执行选品")
            return

        log_info(f"[处理函数] 品种池共 {len(pools_df)} 个品种")

        # 步骤2：遍历品种池，获取主力合约和计算指标
        log_section("步骤2：获取主力合约和计算指标")

        results = []  # 存储所有品种的计算结果

        for idx, row in pools_df.iterrows():
            # 获取品种信息
            code = row['代码']  # 品种代码，如 rb
            exchange_code = row['交易所代码']  # 交易所代码，如 SF
            n_lots = row['n手（取整）']  # n手（取整）

            log_info(f"\n{'='*60}")
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
                # 11天前收盘价 = history_df['close'].iloc[9]
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
                for i in range(0, 9):  # 第1根到第10根K线
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

                log_info(f"[处理函数] 品种 {code} 计算完成，10日趋势={ten_day_trend:.4%}, 趋势效率={trend_efficiency:.4f}")

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
        log_info(f"\n{top3_efficiency[['连续合约', '主力合约', '代码', '交易所代码', 'n手（取整）', '趋势效率']].to_string()}")

        # 步骤4：输出完整结果（可用于后续合约交易所）
        log_section("完整计算结果（用于后续交易所）")
        log_info(f"\n{results_df.to_string()}")

        # 步骤5：封装成stock_codes_dict格式，供海龟交易策略使用
        log_section("步骤5：封装stock_codes_dict格式")
        g.stock_codes_dict_top3_trend = convert_to_stock_codes_dict(top3_trend)
        g.stock_codes_dict_top3_efficiency = convert_to_stock_codes_dict(top3_efficiency)

        log_info(f"[处理函数] 10日趋势TOP3 stock_codes_dict: {g.stock_codes_dict_top3_trend}")
        log_info(f"[处理函数] 趋势效率TOP3 stock_codes_dict: {g.stock_codes_dict_top3_efficiency}")

        # 保存结果到全局变量，供后续使用
        g.top3_trend = top3_trend
        g.top3_efficiency = top3_efficiency
        g.all_results = results_df

        log_info("[处理函数] 选品策略执行完成")

    except Exception as e:
        log_info(f"[处理函数] 执行选品逻辑异常: {str(e)}")
        import traceback
        log_info(traceback.format_exc())


# ==================== 辅助函数 ====================

def log_info(message):
    """
    日志记录函数
    记录info级别日志，同时打印到控制台
    """
    logging.info(message)
    print(f"[{datetime.now().strftime('%Y%m%d%H%M%S')}] {message}")


def log_section(title):
    """
    输出带标题的分隔区块
    用于日志中区分不同阶段
    """
    log_info(60 * "=")
    log_info(title)
    log_info(60 * "=")


def convert_to_stock_codes_dict(df):
    """
    将选品结果DataFrame转换为stock_codes_dict格式

    目标格式（与海龟交易策略一致）：
    {
        "品种代码": {"code": "连续合约代码", "market": "交易所代码", "size": n手}
    }

    例如：
    {
        "RB": {"code": "rb00", "market": "SF", "size": 10},
        "JM": {"code": "jm00", "market": "DF", "size": 4}
    }

    Args:
        df: 选品结果DataFrame，需包含 '代码', '连续合约', '交易所代码', 'n手（取整）' 字段

    Returns:
        dict: stock_codes_dict格式的字典
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

        stock_codes_dict[code.upper()] = {
            "code": contract_code,  # 连续合约代码，如 rb00
            "market": exchange_code,  # 交易所代码，如 SF
            "size": int(n_lots)  # n手（取整）
        }

    return stock_codes_dict



def get_log_filename(account_id=None):
    """
    获取日志文件名

    Args:
        account_id: 账户ID

    Returns:
        日志文件路径
    """
    global log_filename
    if log_filename is None:
        # 日志文件保存在策略同目录下
        import os
        
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        log_filename = os.path.join(work_dir, '选品策略日志.log')

    return log_filename


# 自定义类 用来保存全局状态
class G():
    pass


g = G()
