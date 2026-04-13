# -*- coding: utf-8 -*-
"""
双均线交叉策略 - 纯Python回测
策略逻辑：MA5 上穿 MA20 买入，下穿卖出
"""

import pandas as pd
import numpy as np
from xtquant import xtdata

# ================== 策略参数配置 ==================
STOCK_POOL = ['000001.SZ', '000002.SZ', '000333.SZ', '000858.SZ', '002415.SZ']
SHORT_MA = 5
LONG_MA = 20
INITIAL_CAPITAL = 1000000
MAX_HOLDINGS = 5
COUNT = 500  # 获取最近500个交易日数据
# =================================================


def get_data(stock_list, count):
    """获取历史数据 - xtquant返回格式: {code: DataFrame}"""
    print("获取历史数据...")
    data = xtdata.get_market_data_ex(
        field_list=['open', 'close'],
        stock_list=stock_list,
        period='1d',
        count=count
    )
    
    # 提取open和close数据
    open_dict = {}
    close_dict = {}
    
    for code in stock_list:
        if code in data:
            df = data[code]
            if 'open' in df.columns and 'close' in df.columns:
                open_dict[code] = df['open']
                close_dict[code] = df['close']
    
    open_df = pd.DataFrame(open_dict)
    close_df = pd.DataFrame(close_dict)
    
    return open_df, close_df


def calculate_signals(close_df, short_ma, long_ma):
    """计算买卖信号"""
    ma_short = close_df.rolling(window=short_ma).mean()
    ma_long = close_df.rolling(window=long_ma).mean()
    
    signals = pd.DataFrame(0, index=close_df.index, columns=close_df.columns)
    
    for col in close_df.columns:
        # 金叉：短期均线上穿长期均线
        golden = (ma_short[col] > ma_long[col]) & (ma_short[col].shift(1) <= ma_long[col].shift(1))
        # 死叉：短期均线下穿长期均线
        dead = (ma_short[col] < ma_long[col]) & (ma_short[col].shift(1) >= ma_long[col].shift(1))
        
        signals.loc[golden, col] = 1
        signals.loc[dead, col] = -1
    
    return signals, ma_short, ma_long


def backtest(open_df, close_df, signals, initial_capital, max_holdings):
    """执行回测"""
    cash = initial_capital
    holdings = {}  # {code: {'volume': 数量, 'cost': 成本价}}
    trades = []
    daily_values = []
    
    for date in signals.index:
        daily_signals = signals.loc[date]
        
        # 计算当日持仓市值
        holding_value = 0
        for code, pos in holdings.items():
            if code in close_df.columns:
                price = close_df.loc[date, code]
                holding_value += pos['volume'] * price
        
        total_value = cash + holding_value
        daily_values.append({'date': date, 'value': total_value, 'cash': cash})
        
        # ===== 处理卖出信号 =====
        for code in list(holdings.keys()):
            if daily_signals.get(code, 0) == -1:
                if code in close_df.columns:
                    sell_price = close_df.loc[date, code]
                    volume = holdings[code]['volume']
                    cost = holdings[code]['cost']
                    sell_amount = volume * sell_price
                    profit = (sell_price - cost) * volume
                    
                    cash += sell_amount
                    del holdings[code]
                    
                    trades.append({
                        'date': date, 'code': code, 'action': 'SELL',
                        'price': sell_price, 'volume': volume,
                        'amount': sell_amount, 'profit': profit
                    })
                    print("[%s] 卖出 %s @ %.2f, 数量 %d, 盈亏 %.2f" % (date, code, sell_price, volume, profit))
        
        # ===== 处理买入信号 =====
        can_buy = max_holdings - len(holdings)
        if can_buy > 0 and cash > 0:
            buy_candidates = []
            for code in signals.columns:
                if daily_signals.get(code, 0) == 1 and code not in holdings:
                    buy_candidates.append(code)
            
            buy_list = buy_candidates[:can_buy]
            if buy_list:
                per_stock_cash = cash / len(buy_list)
                
                for code in buy_list:
                    if code in open_df.columns:
                        buy_price = open_df.loc[date, code]
                        if buy_price > 0:
                            volume = int(per_stock_cash / buy_price / 100) * 100
                            if volume > 0:
                                buy_amount = volume * buy_price
                                cash -= buy_amount
                                holdings[code] = {'volume': volume, 'cost': buy_price}
                                
                                trades.append({
                                    'date': date, 'code': code, 'action': 'BUY',
                                    'price': buy_price, 'volume': volume,
                                    'amount': buy_amount, 'profit': 0
                                })
                                print("[%s] 买入 %s @ %.2f, 数量 %d" % (date, code, buy_price, volume))
    
    return daily_values, trades, holdings, cash


def calculate_metrics(daily_values, initial_capital):
    """计算回测指标"""
    df = pd.DataFrame(daily_values)
    df.set_index('date', inplace=True)
    
    total_return = (df['value'].iloc[-1] - initial_capital) / initial_capital * 100
    days = len(df)
    annual_return = ((df['value'].iloc[-1] / initial_capital) ** (252 / days) - 1) * 100
    
    df['cummax'] = df['value'].cummax()
    df['drawdown'] = (df['value'] - df['cummax']) / df['cummax'] * 100
    max_drawdown = df['drawdown'].min()
    
    df['daily_return'] = df['value'].pct_change()
    sharpe = (df['daily_return'].mean() * 252 - 0.03) / (df['daily_return'].std() * np.sqrt(252))
    
    return {
        '总收益率': '%.2f%%' % total_return,
        '年化收益率': '%.2f%%' % annual_return,
        '最大回撤': '%.2f%%' % max_drawdown,
        '夏普比率': '%.2f' % sharpe,
        '交易天数': days,
        '最终资产': '%.2f' % df['value'].iloc[-1]
    }


def main():
    print("=" * 60)
    print("双均线交叉策略回测")
    print("=" * 60)
    print("股票池: %s" % str(STOCK_POOL))
    print("均线: MA%d / MA%d" % (SHORT_MA, LONG_MA))
    print("初始资金: %s" % INITIAL_CAPITAL)
    print("=" * 60)
    
    # 获取数据
    open_df, close_df = get_data(STOCK_POOL, COUNT)
    
    if open_df.empty or close_df.empty:
        print("获取数据失败！")
        return
    
    print("数据获取成功，共 %d 个交易日 (%s ~ %s)" % (len(open_df), open_df.index[0], open_df.index[-1]))
    
    # 计算信号
    signals, ma_short, ma_long = calculate_signals(close_df, SHORT_MA, LONG_MA)
    
    print("\n信号统计:")
    for code in signals.columns:
        buy_count = (signals[code] == 1).sum()
        sell_count = (signals[code] == -1).sum()
        print("  %s: 买入信号 %d 次, 卖出信号 %d 次" % (code, buy_count, sell_count))
    
    # 执行回测
    print("\n开始回测...")
    print("-" * 60)
    daily_values, trades, final_holdings, final_cash = backtest(
        open_df, close_df, signals, INITIAL_CAPITAL, MAX_HOLDINGS
    )
    print("-" * 60)
    
    # 计算最终资产
    final_value = final_cash
    final_date = close_df.index[-1]
    for code, pos in final_holdings.items():
        price = close_df.loc[final_date, code]
        final_value += pos['volume'] * price
    
    daily_values[-1]['value'] = final_value
    
    # 计算指标
    metrics = calculate_metrics(daily_values, INITIAL_CAPITAL)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    for key, value in metrics.items():
        print("  %s: %s" % (key, value))
    
    print("\n【交易记录】")
    buy_count = len([t for t in trades if t['action'] == 'BUY'])
    sell_count = len([t for t in trades if t['action'] == 'SELL'])
    print("  总交易次数: %d (买入 %d, 卖出 %d)" % (len(trades), buy_count, sell_count))
    
    sell_trades = [t for t in trades if t['action'] == 'SELL']
    if sell_trades:
        total_profit = sum(t['profit'] for t in sell_trades)
        print("  已实现盈亏: %.2f" % total_profit)
    
    print("\n【最终持仓】")
    if final_holdings:
        for code, pos in final_holdings.items():
            price = close_df.loc[final_date, code]
            value = pos['volume'] * price
            profit = (price - pos['cost']) * pos['volume']
            print("  %s: %d 股, 成本 %.2f, 现价 %.2f, 市值 %.2f, 盈亏 %.2f" % 
                  (code, pos['volume'], pos['cost'], price, value, profit))
    else:
        print("  无持仓")
    
    print("  现金: %.2f" % final_cash)
    print("=" * 60)


if __name__ == '__main__':
    main()
