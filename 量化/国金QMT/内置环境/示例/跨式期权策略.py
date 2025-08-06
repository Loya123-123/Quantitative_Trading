#coding:gbk
"""
跨式期权策略
回测模型示例（非实盘交易策略）

（1）认沽期权和认购期权的隐含波动率大于50etf波动率时，
以标的资产当前的价格作为行权价买入相同数量、相同标的资产和相同行权日的认购和认沽期权开仓
（2）认沽期权和认购期权的隐含波动率小于50etf波动率且有市场时，平仓
"""
import datetime
from math import (log, pow, sqrt, exp)

from scipy import stats
import numpy as np
import talib

cdf = stats.norm.cdf
STEP_CHANGE = 0.001
STEP_UP = 1 + STEP_CHANGE
STEP_DOWN = 1 - STEP_CHANGE
STEP_DIFF = STEP_CHANGE * 2
DX_TARGET = 0.00001
'''
变量说明
s：标的物股票价格
k：行权价
r：无风险利率
t：剩余到期时间（年）
v：隐含波动率
cp：期权类型，+1/-1对应call/put
price：期权价格
'''

def init(ContextInfo):
    ContextInfo.contract_unit = 10000

    #随着时间推移该对合约可能不存了，根据需求手动修改更新
    ContextInfo.optOne="10001713"
    ContextInfo.optTwo="10001714"
    #上面合约的到期年月，根据需求手动修改更新
    ContextInfo.aa= get_week_of_month(2019, 3)

    ContextInfo.holdings = {ContextInfo.optOne: 0, ContextInfo.optTwo: 0}
    ContextInfo.accountID = '8861103625'
    ContextInfo.s_volatility = []
def handlebar(ContextInfo):
    #当前K线的对应的下标从0开始
    index = ContextInfo.barpos

    #当前K线对应的时间：毫秒
    realtime = ContextInfo.get_bar_timetag(index)
    current_time = timetag_to_datetime(realtime,'%Y-%m-%d')

    #当前周期
    period = ContextInfo.period


    #取当前K线图对应的合约当前K线的当前主图复权方式下的收盘价
    price_call = ContextInfo.get_market_data(['close'],period=period, stock_code = [ContextInfo.optOne+".SHO"])
    price_put = ContextInfo.get_market_data(['close'],period=period, stock_code = [ContextInfo.optTwo+".SHO"])
    s = ContextInfo.get_market_data(["close"],stock_code = ["510050.SH"],period=period)
    #print price_call,price_put
    ContextInfo.s_volatility.append(s)
    s_volatility = np.std(np.array(ContextInfo.s_volatility))
    ContextInfo.paint("s_volatility", s_volatility*10, -1, 0)
    k = 2.55
    r = ContextInfo.get_risk_free_rate(index)/100

    t = ((datetime.datetime.strptime(ContextInfo.aa, "%Y-%m-%d") - datetime.datetime.strptime(current_time, "%Y-%m-%d")).days) / 365.0

    cp_call = 1
    cp_put = -1
    implied_volatility_call = calculateImpv(price_call, s, k, r, t, cp_call)
    implied_volatility_put = calculateImpv(price_put, s, k, r, t, cp_put)
    #print "implied_volatility_call", implied_volatility_call
    #print "implied_volatility_put", implied_volatility_put

    ContextInfo.paint("implied_volatility", (implied_volatility_put + implied_volatility_call), -1, 0)
    if (implied_volatility_put + implied_volatility_call) > s_volatility*10 :
        passorder(50,1101,ContextInfo.accountID ,ContextInfo.optOne,5,-1,1,ContextInfo)
        passorder(50,1101,ContextInfo.accountID ,ContextInfo.optTwo,5,-1,1,ContextInfo)
        ContextInfo.holdings[ContextInfo.optOne] = 1
        ContextInfo.holdings[ContextInfo.optTwo] = 1
    elif ContextInfo.holdings[ContextInfo.optOne] == 1 and ContextInfo.holdings[ContextInfo.optTwo] == 1 and (implied_volatility_put + implied_volatility_call) < s_volatility*10 :
        passorder(53,1101,ContextInfo.accountID ,ContextInfo.optOne,5,-1,1,ContextInfo)
        passorder(53,1101,ContextInfo.accountID ,ContextInfo.optTwo,5,-1,1,ContextInfo)
        ContextInfo.holdings[ContextInfo.optOne] = 0
        ContextInfo.holdings[ContextInfo.optTwo] = 0

def calculateImpv(price, s, k, r, t, cp):
    """计算隐含波动率"""
    # 检查期权价格必须为正数
    if price <= 0:
        return 0
    # 检查期权价格是否满足最小价值（即到期行权价值）
    meet = False
    if cp == 1 and (price > (s - k) * exp(-r * t)):
        meet = True
    elif cp == -1 and (price > k * exp(-r * t) - s):
        meet = True
    # 若不满足最小价值，则直接返回0
    if not meet:
        return 0
    # 采用Newton Raphson方法计算隐含波动率
    v = 0.29 # 初始波动率猜测
    for i in range(50):
        # 计算当前猜测波动率对应的期权价格和vega值
        p = calculatePrice(s, k, r, t, v, cp)
        vega = calculateOriginalVega(s, k, r, t, v, cp)

        # 如果vega过小接近0，则直接返回
        if not vega:
            break
        # 计算误差
        dx = (price - p) / vega
        # 检查误差是否满足要求，若满足则跳出循环
        if abs(dx) < DX_TARGET:
            break
        # 计算新一轮猜测的波动率
        v += dx
    # 检查波动率计算结果非负
    if v <= 0:
        return 0
    # 保留4位小数
    v = round(v, 4)
    return v


def calculateOriginalVega(s, k, r, t, v, cp):
    """计算原始vega值"""
    price1 = calculatePrice(s, k, r, t, v*STEP_UP, cp)
    price2 = calculatePrice(s, k, r, t, v*STEP_DOWN, cp)
    vega = (price1 - price2) / (v * STEP_DIFF)
    return vega

def calculatePrice(s, k, r, t, v, cp):
    """计算期权价格"""
    # 如果波动率为0，则直接返回期权空间价值
    if v <= 0:
        return max(0, cp * (s - k))
    d1 = (log(s / k) + (r + 0.5 * pow(v, 2)) * t) / (v * sqrt(t))
    d2 = d1 - v * sqrt(t)
    price = cp * (s * cdf(cp * d1) - k * cdf(cp * d2) * exp(-r * t))
    return price

def get_week_of_month(year, month):
    """
    获取指定的某天是某个月中的第几周
    周一作为一周的开始
    """
    begin = datetime.datetime(year, month, 1).weekday()
    delta = datetime.timedelta(days=21+begin)
    exercise_date = datetime.datetime(year, month, 1) + delta
    return  exercise_date.strftime('%Y-%m-%d')