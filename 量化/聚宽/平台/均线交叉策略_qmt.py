#coding:utf-8
from datetime import datetime
import pandas as pd
import time

# 导入QMT相关模块
from xtquant import xtdata
from xtquant import xttrader

# 全局变量
g = type('G', (), {})()
_data_proxy = None

"""
策略要求
交易频率：分钟/tick
交易品种：医药行业股票，如恒瑞医药600276.XSHG  长江水电 '600900.XSHG'  中国石油 '601857.XSHG'
策略逻辑： 
买入条件：前2天的10日均线<20日均线，前一天的10日均线>=20日均线，则买入
卖出条件：前2天的10日均线>=20日均线，前一天的10日均线<20日均线，则卖出
"""

def init(context):
    # 设置参数
    set_params(context)
    
    # 设置交易品种
    context.stocks = ['601857.SH']  # 中国石油 转换为QMT格式
    
    # 设置交易参数
    # QMT中佣金和滑点在交易端设置
    
    # 输出日志
    print("策略初始化完成")


def set_params(context):
    # 设置均线周期
    context.short_period = 10
    context.long_period = 20
    context.account = None  # 需要在实盘中设置


def log_message(message):
    """
    统一的日志处理函数
    :param message: 日志消息
    """
    # 输出到控制台
    print(message)
    
    # 写入到文件
    try:
        with open('ma_cross_log.txt', 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception as e:
        print(f"写入日志文件失败: {e}")


def handlebar(context):
    # 获取当前时间
    current_time = datetime.now()
    
    for security in context.stocks:
        # 获取交易数据
        data_df = get_data(security, context)
        
        if data_df is None:
            continue
            
        # 检查是否满足交易条件
        signal = should_trade(context, data_df, security)
        
        # 执行交易
        if signal:
            execute_trade(context, signal, security, data_df)


def get_data(security, context):
    """
    获取交易所需的数据
    :param security: 股票代码
    :param context: 上下文
    :return:
    """
    try:
        # 获取历史数据 - 需要足够数据来计算均线
        # QMT中使用xtdata获取数据，这里获取最近40个交易日的数据
        hist_data = xtdata.get_market_data(
            field_list=['open', 'close', 'high', 'low'], 
            stock_list=[security], 
            period='1d', 
            count=context.long_period + 20,  # 多获取几天数据确保计算准确
            dividend_type='front',
            fill_data=True
        )
        
        if hist_data is None or len(hist_data[security]['close']) < context.long_period + 2:
            print(f"获取{security}历史数据不足")
            return None
            
        # 转换为DataFrame
        hist_daily = pd.DataFrame({
            'open': hist_data[security]['open'],
            'close': hist_data[security]['close'],
            'high': hist_data[security]['high'],
            'low': hist_data[security]['low']
        })
        
        # 确保索引为日期格式
        hist_daily.index = pd.to_datetime(hist_daily.index)
        hist_daily.sort_index(inplace=True)
        
        if len(hist_daily) < context.long_period + 2:
            return None
            
        # 计算均线
        hist_daily['ma_short'] = hist_daily['close'].rolling(window=context.short_period).mean()
        hist_daily['ma_long'] = hist_daily['close'].rolling(window=context.long_period).mean()
        
        # 获取前2天和前一天的均线数据
        # 前2天的数据
        hist_daily['ma_short_2days_ago'] = hist_daily['ma_short'].iloc[-3]
        hist_daily['ma_long_2days_ago'] = hist_daily['ma_long'].iloc[-3]
        
        # 前一天的数据
        hist_daily['ma_short_1day_ago'] = hist_daily['ma_short'].iloc[-2]
        hist_daily['ma_long_1day_ago'] = hist_daily['ma_long'].iloc[-2]
        
        # 当前价格（最新价格）
        current_price = hist_data[security]['close'][-1]
        
        data_df = pd.DataFrame({
            'current_time': [datetime.now()],
            'current_price': [current_price],
            'ma_short_2days_ago': [hist_daily['ma_short_2days_ago'].iloc[-1]],
            'ma_long_2days_ago': [hist_daily['ma_long_2days_ago'].iloc[-1]],
            'ma_short_1day_ago': [hist_daily['ma_short_1day_ago'].iloc[-1]],
            'ma_long_1day_ago': [hist_daily['ma_long_1day_ago'].iloc[-1]],
            'ma_short_today': [hist_daily['ma_short'].iloc[-1]],
            'ma_long_today': [hist_daily['ma_long'].iloc[-1]]
        })
        
        return data_df
        
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None


def should_trade(context, data_df, security):
    """
    判断是否应该交易
    """
    # 初始化信号
    signal = None
    
    try:
        # 在QMT中获取持仓信息
        if context.account:
            # 获取持仓信息（需要在实盘中连接交易账户）
            positions = context.account.get_positions()
            has_position = any(pos.stock_code == security for pos in positions if pos.can_use_volume > 0)
        else:
            # 模拟环境中假设无持仓
            has_position = False
        
        # 获取均线数据
        ma_short_2days_ago = data_df['ma_short_2days_ago'].iloc[0]
        ma_long_2days_ago = data_df['ma_long_2days_ago'].iloc[0]
        ma_short_1day_ago = data_df['ma_short_1day_ago'].iloc[0]
        ma_long_1day_ago = data_df['ma_long_1day_ago'].iloc[0]
        
        # 检查数据有效性
        if pd.isna(ma_short_2days_ago) or pd.isna(ma_long_2days_ago) or \
                pd.isna(ma_short_1day_ago) or pd.isna(ma_long_1day_ago):
            return signal
            
        # 买入条件：前2天的10日均线<20日均线，前一天的10日均线>=20日均线
        if not has_position:
            if ma_short_2days_ago < ma_long_2days_ago and ma_short_1day_ago >= ma_long_1day_ago:
                log_message(f"满足买入条件：前2天短均线 {ma_short_2days_ago:.2f} < 长均线 {ma_long_2days_ago:.2f} 且前一天短均线 {ma_short_1day_ago:.2f} >= 长均线 {ma_long_1day_ago:.2f}")
                signal = "BUY"
                
        # 卖出条件：前2天的10日均线>=20日均线，前一天的10日均线<20日均线
        else:
            if ma_short_2days_ago >= ma_long_2days_ago and ma_short_1day_ago < ma_long_1day_ago:
                log_message(f"满足卖出条件：前2天短均线 {ma_short_2days_ago:.2f} >= 长均线 {ma_long_2days_ago:.2f} 且前一天短均线 {ma_short_1day_ago:.2f} < 长均线 {ma_long_1day_ago:.2f}")
                signal = "SELL"
                
    except Exception as e:
        print(f"判断交易信号时出错: {e}")
        
    return signal


def execute_trade(context, signal, security, data_df):
    """
    执行交易
    """
    try:
        current_price = data_df['current_price'].iloc[0]
        
        if signal == "BUY":
            # 使用固定资金买入
            cash = 20000
            amount = int(cash * 0.98 / current_price / 100) * 100  # 确保买卖数量是100的整数倍
            qty = amount / 100
            
            # 买入总价
            total_amount = current_price * amount
            
            if amount > 0 and context.account:
                # 执行买入（需要在实盘中连接交易账户）
                order = context.account.order_stock(security, xttrader.STOCK_BUY, int(current_price*10000), amount, 0)
                log_message(f"买入 {security} ; {qty} 手, 数量: {amount}, 买入总价 {total_amount}, 价格 {current_price}")
                log_message(str(order))
            elif amount > 0:
                log_message(f"模拟买入 {security} ; {qty} 手, 数量: {amount}, 买入总价 {total_amount}, 价格 {current_price}")
                
        elif signal == "SELL":
            # 卖出所有持仓（需要在实盘中连接交易账户）
            if context.account:
                # 获取持仓数量
                positions = context.account.get_positions()
                position_amount = 0
                for pos in positions:
                    if pos.stock_code == security:
                        position_amount = pos.can_use_volume
                        break
                        
                if position_amount > 0:
                    order = context.account.order_stock(security, xttrader.STOCK_SELL, int(current_price*10000), position_amount, 0)
                    log_message(f"卖出 {security}; 数量: {position_amount} , 价格: {current_price}")
                    log_message(str(order))
            else:
                log_message(f"模拟卖出 {security}; 价格: {current_price}")
                
    except Exception as e:
        print(f"执行交易时出错: {e}")