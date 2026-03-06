# coding:gbk

"""
R_break策略示例
"""
import time
import datetime
import traceback
import sys
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import pandas as pd
import numpy as np
from random import randint


class _a():
    pass


A = _a()


def init(C):
    """
    初始化函数，设置策略相关的基本参数
    Args:
        C: 可能是上下文信息（根据代码中的使用情况推测）
    """
    A.symbol = "rb00.SF"  # 品种
    C.accID = "test"
    # C.accID = account # 实盘用这个，这里先使用测试账号
    A.period = "5m"  # 数据周期
    A.lots = 1  # 买卖手数


# 第5部分：获取市场数据函数
def get_market_data(futures_code, period, start_time, end_time):
    try:
        print(f"Fetching market data for {futures_code} from {start_time} to {end_time}.")
        xtdata.subscribe_quote(futures_code, period)
        time.sleep(5)  # 增加等待时间，确保数据更新

        market_data = xtdata.get_market_data_ex(
            ['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
            [futures_code], period, start_time=start_time, end_time=end_time
        )

        if futures_code not in market_data:
            print(f"No data returned for {futures_code}.")
            return None

        df = market_data[futures_code].copy()
        if df.empty:
            print(f"No data returned for {futures_code}")
            return None

        df['time'] = pd.to_datetime(df['time'] + 28800000, unit='ms')
        return df

    except Exception as e:
        print(f"Error fetching market data for {futures_code}: {e}")
        traceback.print_exc()
        return None


def after_init(C):
    """
    初始化后的操作函数，主要用于数据准备和计算相关指标
    Args:
        C: 可能是上下文信息（根据代码中的使用情况推测）
    """
    # 不确定有没有本地数据的话，下一次本地数据
    if 1:
        print("正在下载数据")
        # 下载指定股票的历史数据
        xtdata.supply_history_data(A.symbol, A.period, "", "")
        # download_history_data(A.symbol, A.period, "", "")  # 下载历史数据，函数未在提供的代码中实现
        print("数据下载完成，程序继续")

    # 开始获取数据
    data = C.get_market_data_ex([], [A.symbol], period="1d")  # 获取指定品种的市场数据，具体格式由函数定义决定
    close_df = get_df_ex(data, "close")  # 从数据中提取收盘价数据并转换为DataFrame格式
    open_df = get_df_ex(data, "open")  # 从数据中提取开盘价数据并转换为DataFrame格式
    low_df = get_df_ex(data, "low")  # 从数据中提取最低价数据并转换为DataFrame格式
    high_df = get_df_ex(data, "high")  # 从数据中提取最高价数据并转换为DataFrame格式

    pivot_df = (high_df + close_df + low_df) / 3  # 计算枢纽点

    A.bBreak = high_df + 2 * (pivot_df - low_df)  # 计算突破买入价
    A.sSetup = pivot_df + (high_df - low_df)  # 计算观察卖出价

    A.sEnter = 2 * pivot_df - low_df  # 计算反转卖出价
    A.bEnter = 2 * pivot_df - high_df  # 计算反转买入价
    A.bSetup = pivot_df - (high_df - low_df)  # 计算观察买入价
    A.sBreak = low_df - 2 * (high_df - pivot_df)  # 计算突破卖出价

    A.bBreak = A.bBreak.shift(1)  # 将突破买入价数据向前移动一位（可能用于计算或处理）
    A.sSetup = A.sSetup.shift(1)  # 将观察卖出价数据向前移动一位
    A.sEnter = A.sEnter.shift(1)  # 将反转卖出价数据向前移动一位
    A.bEnter = A.bEnter.shift(1)  # 将反转买入价数据向前移动一位
    A.bSetup = A.bSetup.shift(1)  # 将观察买入价数据向前移动一位
    A.sBreak = A.sBreak.shift(1)  # 将突破卖出价数据向前移动一位


def timetag_to_datetime(timetag, format_str):
    if isinstance(timetag, int):
        # 如果是时间戳，先转换为日期时间对象
        timetag = datetime.datetime.fromtimestamp(timetag)
    return timetag.strftime(format_str)


def handlebar(C):
    """
    处理每一个bar（交易时间单位）的数据和交易逻辑
    Args:
        C: 可能是上下文信息（根据代码中的使用情况推测）
    """
    backTestTime = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d%H%M%S")  # 将时间标签转换为指定格式的日期时间，函数未在提供的代码中实现

    print(backTestTime)  # 打印当前bar的时间，觉得眼花可以注释掉

    bBreak = A.bBreak.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的突破买入价
    sBreak = A.sBreak.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的突破卖出价
    sSetup = A.sSetup.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的观察卖出价
    sEnter = A.sEnter.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的反转卖出价
    bSetup = A.bSetup.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的观察买入价
    bEnter = A.bEnter.loc[backTestTime[:8], A.symbol]  # 获取当前日期对应的反转买入价

    holdings = get_Future_holdings(C.accID, symbol=A.symbol)  # 获取账户持仓信息

    position_long = holdings.get("多头数量", 0)  # 获取多头持仓数量，如果不存在则默认为0
    position_short = holdings.get("空头数量", 0)  # 获取空头持仓数量，如果不存在则默认为0

    # 获取行情
    data = C.get_market_data_ex([], [A.symbol], period=A.period, end_time=backTestTime, count=2)  # 获取指定品种的市场数据
    last_price = data[A.symbol].iloc[-1]["close"]  # 获取最新的收盘价
    high = data[A.symbol].iloc[-1]["high"]  # 获取最新的最高价
    low = data[A.symbol].iloc[-1]["low"]  # 获取最新的最低价

    # print(last_price,bBreak)

    if position_long == 0 and position_short == 0:
        if last_price > bBreak:
            # 在空仓的情况下，如果盘中价格超过突破买入价，则采取趋势策略，即在该点位开仓做多
            my_passorder(C, A.symbol, "buy_open", A.lots)  # 做多
            print("空仓,盘中价格超过突破买入价: 开仓做多")
        elif last_price < sBreak:
            my_passorder(C, A.symbol, "sell_open", A.lots)  # 做空
            print("空仓,盘中价格跌破突破卖出价: 开仓做空")
    else:

        # 反转的情况
        if position_long:

            if high > sSetup and last_price < sEnter:
                # 多头持仓,当日内最高价超过观察卖出价后，
                # 盘中价格出现回落，且进一步跌破反转卖出价构成的支撑线时，
                # 采取反转策略，即在该点位反手做空
                my_passorder(C, A.symbol, "sell_close", position_long)  # 平多
                my_passorder(C, A.symbol, "sell_open", A.lots)  # 做空
                print("盘中价格出现回落：反转做空")
        elif position_short:
            if low < bSetup and last_price > bEnter:
                # 空头持仓，当日内最低价低于观察买入价后，
                # 盘中价格出现反弹，且进一步超过反转买入价构成的阻力线时，
                # 采取反转策略，即在该点位反手做多

                my_passorder(C, A.symbol, "buy_close", position_short)  # 平空
                my_passorder(C, A.symbol, "buy_open", A.lots)  # 做多
                print("盘中价格出现反弹：反转做多")

    if backTestTime[-6:] == "144500":
        # 收盘前平掉所有仓位
        if position_long:
            my_passorder(C, A.symbol, "sell_close", position_long)  # 平多
        if position_short:
            my_passorder(C, A.symbol, "buy_close", position_short)  # 平空
        print("收盘平仓")
    return


def get_df_ex(data: dict, field: str) -> pd.DataFrame:
    """
    用于在使用get_market_data_ex的情况下，取到标准df
    Args:
        data: get_market_data_ex返回的dict
        field: ['time', 'open', 'high', 'low', 'close', 'volume','amount', 'settelementPrice', 'openInterest', 'preClose', 'suspendFlag']
    Return:
        一个以时间为index，标的为columns的df
    """
    _index = data[list(data.keys())[0]].index.tolist()  # 获取数据中第一个键对应的值的索引列表（假设数据结构合理）
    _columns = list(data.keys())  # 获取数据的键列表（即标的列表）
    df = pd.DataFrame.from_dict({col: data[col][field] for col in _columns})  # 从数据中提取指定字段并构建DataFrame
    return df


def get_Future_holdings(accid, symbol=None):
    """
    针对期货返回持仓的奇葩结构做处理
    Args:
        accid: 账户id
        symbol: 品种，不填默认返会全部持仓
    return:
        {股票名:{'手数':int,"持仓成本":float,'浮动盈亏':float,"可用余额":int}}
    """
    # 创建XtQuantTrader实例
    xttrader = XtQuantTrader()

    # 获取账户资产信息
    asset_info = xttrader.query_stock_asset(accid)

    PositionInfo_dict = {}
    Long_dict = {}
    Short_dict = {}

    # 从资产信息中提取持仓明细数据（假设资产信息中有合适的字段存储持仓明细）
    position_detail = asset_info.get('position_detail', [])

    # 按照常规顺序遍历持仓明细数据
    for i in range(len(position_detail)):
        obj = position_detail[i]
        # 防除零
        if obj.m_nVolume == 0:
            continue
        if obj.m_nDirection == 48:
            if not Long_dict.get(obj.m_strInstrumentID + "." + obj.m_strExchangeID):
                Long_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID] = {
                    "多头数量": obj.m_nVolume,
                    "多头成本": obj.m_dOpenPrice,
                    "浮动盈亏": obj.m_dFloatProfit,
                    "保证金占用": obj.m_dMargin
                }
            else:
                Long_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["多头数量"] += obj.m_nVolume
                # 算浮动盈亏
                Long_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["浮动盈亏"] += obj.m_dFloatProfit
                # 算保证金占用
                Long_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["保证金占用"] += obj.m_dMargin
                # 算多头成本
                Long_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["多头成本"] = (
                                                                                           Long_dict[
                                                                                               obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                               "多头成本"] * \
                                                                                           (Long_dict[
                                                                                                obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                                "多头数量"] - obj.m_nVolume) + \
                                                                                           (
                                                                                                       obj.m_dOpenPrice * obj.m_nVolume)
                                                                                   ) / Long_dict[
                                                                                       obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                       "多头数量"]

        elif obj.m_nDirection == 49:
            if not Short_dict.get(obj.m_strInstrumentID + "." + obj.m_strExchangeID):
                Short_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID] = {
                    "空头数量": obj.m_nVolume,
                    "空头成本": obj.m_dOpenPrice,
                    "浮动盈亏": obj.m_dFloatProfit,
                    "保证金占用": obj.m_dMargin
                }
            else:
                Short_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["空头数量"] += obj.m_nVolume
                # 算浮动盈亏
                Short_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["浮动盈亏"] += obj.m_dFloatProfit
                # 算保证金占用
                Short_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["保证金占用"] += obj.m_dMargin
                # 计算空头成本
                Short_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID]["空头成本"] = (
                                                                                            Short_dict[
                                                                                                obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                                "空头成本"] * \
                                                                                            (Short_dict[
                                                                                                 obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                                 "空头数量"] - obj.m_nVolume) + \
                                                                                            (
                                                                                                        obj.m_dOpenPrice * obj.m_nVolume)
                                                                                    ) / Short_dict[
                                                                                        obj.m_strInstrumentID + "." + obj.m_strExchangeID][
                                                                                        "空头数量"]

    for _symbol in set(list(Long_dict.keys()) + list(Short_dict.keys())):
        PositionInfo_dict[_symbol] = {
            "多头数量": Long_dict[_symbol]["多头数量"] if Long_dict.get(_symbol) else 0,
            "空头数量": Short_dict[_symbol]["空头数量"] if Short_dict.get(_symbol) else 0,
            "多头成本": Long_dict[_symbol]["多头成本"] if Long_dict.get(_symbol) else None,
            "空头成本": Short_dict[_symbol]["空头成本"] if Short_dict.get(_symbol) else None,
            "净持仓": Long_dict.get(_symbol, {}).get("多头数量", 0) - Short_dict.get(_symbol, {}).get("空头数量", 0),
            "浮动盈亏": Long_dict.get(_symbol, {}).get("浮动盈亏", 0) + Short_dict.get(_symbol, {}).get("浮动盈亏", 0),
            "保证金占用": Long_dict.get(_symbol, {}).get("保证金占用", 0) + Short_dict.get(_symbol, {}).get(
                "保证金占用", 0)
        }

    if symbol:
        return PositionInfo_dict.get(symbol, {})
    else:
        return PositionInfo_dict


def my_passorder(C, Futuer: str, opentype: str, lots: int, price=None, m_strRemark='系统备注'):
    """
    下单函数，用于发送交易指令
    Args:
        C: ContextInfo \n
        Futuer: 期货代码 \n
        opentype:
                'buy_open' 开多\n
                'sell_open' 开空\n
                'sell_close' 平多\n
                'buy_close' 平空\n
        lots: 手
        price: 下单价格，不指定时默认按市价下单
        m_strRemark = '系统备注' 用于自定义寻找orderID
    """
    Futuer_ExchangeID = Futuer.split(".")[1]
    opentype = opentype  # 买卖方向
    op = 1101  # 手数
    # 期货区分开平
    if opentype == "buy_open":
        opType = 0
    elif opentype == "sell_open":
        opType = 3
    elif opentype == "sell_close":
        opType = 7
    elif opentype == "buy_close":
        opType = 9

    volumex = lots
    price = 0 if not price else price  # price参数必须存在
    if Futuer_ExchangeID == "SF":
        prType = 14 if not price else 11  # 对于上期所，若不指定价格，则默认按对手价下单
    elif Futuer_ExchangeID == "DF" or Futuer_ExchangeID == "ZF":
        prType = 12 if not price else 11  # 对于大商所和郑商所，若不指定价格，则默认按涨跌停价下单
    else:
        prType = 14 if not price else 11  # 对于其他所，若不指定价格，则默认按对手价下单

    print(f'{Futuer} 新委托信息 方向{opentype} 价格{price} 量{volumex}')
    # print(f"opType:{opType}, op:{op}, C.accID{C.accID}, stock{stock}, prType{prType}, price{price}, volumex{volumex}")
    my_passorder (opType, op, C.accID, Futuer, prType, price, volumex, '交易注释', 1, '{}'.format(m_strRemark), C)  # 发送交易指令，函数未在提供的代码中实现
    print(f'委托发送完成')