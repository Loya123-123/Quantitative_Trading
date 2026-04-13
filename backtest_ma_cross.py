# -*- coding: utf-8 -*-
"""
双均线交叉策略 - QMT本地回测
策略逻辑：
- MA5 上穿 MA20 时买入
- MA5 下穿 MA20 时卖出
"""

import os
import numpy as np
import pandas as pd
from xtquant import xtdata
from xtquant.qmttools.functions import passorder, get_trade_detail_data
from xtquant.xtdata import timetag_to_datetime

# ================== 策略参数配置 ==================
# 股票池
STOCK_POOL = ['000001.SZ', '000002.SZ', '000333.SZ', '000858.SZ', '002415.SZ']

# 均线周期
SHORT_MA = 5   # 短期均线
LONG_MA = 20   # 长期均线

# 资金管理
INITIAL_CAPITAL = 1000000
MAX_HOLDINGS = 5

# 账号ID（回测用'test'）
ACCOUNT_ID = 'test'

# 回测时间范围
START_TIME = '2023-01-01 00:00:00'
END_TIME = '2024-01-01 00:00:00'
# =================================================


class G:
    pass


g = G()


def init(C):
    """初始化函数"""
    print("=" * 60)
    print("策略初始化...")
    print("股票池: %s" % str(STOCK_POOL))
    print("短期均线: MA%d, 长期均线: MA%d" % (SHORT_MA, LONG_MA))
    print("初始资金: %s" % INITIAL_CAPITAL)
    print("=" * 60)
    
    g.stock_pool = STOCK_POOL
    g.short_ma = SHORT_MA
    g.long_ma = LONG_MA
    g.account_id = ACCOUNT_ID
    g.max_holdings = MAX_HOLDINGS
    g.initial_capital = INITIAL_CAPITAL
    g.per_stock_capital = INITIAL_CAPITAL / MAX_HOLDINGS * 0.95


def after_init(C):
    """准备技术指标"""
    # 获取历史数据
    data = xtdata.get_market_data_ex(
        field_list=['close', 'open'],
        stock_list=g.stock_pool,
        period='1d',
        start_time='20220101',
        end_time='20241231',
        dividend_type='front_ratio'
    )
    
    # 转换为DataFrame
    close_df = get_df_ex(data, 'close')
    open_df = get_df_ex(data, 'open')
    
    # 计算双均线
    g.ma_short = close_df.rolling(window=g.short_ma).mean()
    g.ma_long = close_df.rolling(window=g.long_ma).mean()
    
    # 计算交叉信号
    g.signal = pd.DataFrame(index=close_df.index, columns=close_df.columns)
    for col in close_df.columns:
        golden_cross = (g.ma_short[col] > g.ma_long[col]) & (g.ma_short[col].shift(1) <= g.ma_long[col].shift(1))
        dead_cross = (g.ma_short[col] < g.ma_long[col]) & (g.ma_short[col].shift(1) >= g.ma_long[col].shift(1))
        
        g.signal[col] = 0
        g.signal.loc[golden_cross, col] = 1
        g.signal.loc[dead_cross, col] = -1
    
    g.open_df = open_df
    
    print("数据准备完成，共 %d 个交易日" % len(close_df))
    print("=" * 60)


def handlebar(C):
    """主策略函数"""
    current_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d")
    
    if current_time not in g.signal.index:
        return
    
    current_signal = g.signal.loc[current_time]
    
    # 获取持仓
    holdings = get_holdings(g.account_id, 'stock')
    hold_codes = list(holdings.keys())
    
    # 处理卖出
    for code in hold_codes:
        if current_signal.get(code, 0) == -1:
            price = g.open_df.loc[current_time, code]
            volume = holdings[code]['持仓数量']
            if volume > 0 and price > 0:
                print("[%s] 卖出 %s, 价格 %.2f, 数量 %d" % (current_time, code, price, volume))
                passorder(24, 1101, g.account_id, code, 11, float(price), int(volume), 
                         "双均线策略", 1, "MA死叉卖出_%s" % code, C)
    
    # 处理买入
    holdings = get_holdings(g.account_id, 'stock')
    hold_codes = list(holdings.keys())
    can_buy_num = g.max_holdings - len(hold_codes)
    
    if can_buy_num > 0:
        buy_candidates = []
        for code in g.stock_pool:
            if current_signal.get(code, 0) == 1 and code not in hold_codes:
                buy_candidates.append(code)
        
        buy_list = buy_candidates[:can_buy_num]
        
        for code in buy_list:
            price = g.open_df.loc[current_time, code]
            if price > 0:
                volume = int(g.per_stock_capital / price / 100) * 100
                if volume > 0:
                    print("[%s] 买入 %s, 价格 %.2f, 数量 %d" % (current_time, code, price, volume))
                    passorder(23, 1101, g.account_id, code, 11, float(price), volume, 
                             "双均线策略", 1, "MA金叉买入_%s" % code, C)


def get_df_ex(data: dict, field: str) -> pd.DataFrame:
    """dict转DataFrame"""
    if not data:
        return pd.DataFrame()
    _index = data[list(data.keys())[0]].index.tolist()
    _columns = list(data.keys())
    df = pd.DataFrame(index=_index, columns=_columns)
    for col in _columns:
        df[col] = data[col][field]
    return df


def get_holdings(accid, datatype):
    """获取持仓"""
    holdings = {}
    try:
        resultlist = get_trade_detail_data(accid, datatype, 'POSITION')
        for obj in resultlist:
            code = obj.m_strInstrumentID + "." + obj.m_strExchangeID
            holdings[code] = {
                '持仓数量': obj.m_nVolume,
                '持仓成本': obj.m_dOpenPrice,
                '浮动盈亏': obj.m_dFloatProfit,
                '可用数量': obj.m_nCanUseVolume
            }
    except:
        pass
    return holdings


if __name__ == '__main__':
    from xtquant.qmttools import run_strategy_file
    
    param = {
        'stock_code': '000001.SZ',  # 使用股票池中第一只作为基准
        'period': '1d',
        'start_time': START_TIME,
        'end_time': END_TIME,
        'trade_mode': 'backtest',
        'quote_mode': 'history',
        'capital': INITIAL_CAPITAL,
    }
    
    user_script = os.path.basename(__file__)
    print("\n开始回测: %s" % user_script)
    print("回测区间: %s ~ %s" % (START_TIME, END_TIME))
    print("=" * 60)
    
    result = run_strategy_file(user_script, param=param)
    
    if result:
        print("\n" + "=" * 60)
        print("回测结果")
        print("=" * 60)
        
        index_data = result.get_backtest_index()
        if index_data:
            print("\n【回测指标】")
            for key, value in index_data.items():
                print("  %s: %s" % (key, value))
        
        group_result = result.get_group_result()
        if group_result:
            print("\n【分组收益】")
            print(group_result)
    
    xtdata.run()
