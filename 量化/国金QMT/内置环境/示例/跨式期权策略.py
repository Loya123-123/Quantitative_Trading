#coding:gbk
"""
��ʽ��Ȩ����
�ز�ģ��ʾ������ʵ�̽��ײ��ԣ�

��1���Ϲ���Ȩ���Ϲ���Ȩ�����������ʴ���50etf������ʱ��
�Ա���ʲ���ǰ�ļ۸���Ϊ��Ȩ��������ͬ��������ͬ����ʲ�����ͬ��Ȩ�յ��Ϲ����Ϲ���Ȩ����
��2���Ϲ���Ȩ���Ϲ���Ȩ������������С��50etf�����������г�ʱ��ƽ��
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
����˵��
s��������Ʊ�۸�
k����Ȩ��
r���޷�������
t��ʣ�ൽ��ʱ�䣨�꣩
v������������
cp����Ȩ���ͣ�+1/-1��Ӧcall/put
price����Ȩ�۸�
'''

def init(ContextInfo):
    ContextInfo.contract_unit = 10000

    #����ʱ�����ƸöԺ�Լ���ܲ����ˣ����������ֶ��޸ĸ���
    ContextInfo.optOne="10001713"
    ContextInfo.optTwo="10001714"
    #�����Լ�ĵ������£����������ֶ��޸ĸ���
    ContextInfo.aa= get_week_of_month(2019, 3)

    ContextInfo.holdings = {ContextInfo.optOne: 0, ContextInfo.optTwo: 0}
    ContextInfo.accountID = '8861103625'
    ContextInfo.s_volatility = []
def handlebar(ContextInfo):
    #��ǰK�ߵĶ�Ӧ���±��0��ʼ
    index = ContextInfo.barpos

    #��ǰK�߶�Ӧ��ʱ�䣺����
    realtime = ContextInfo.get_bar_timetag(index)
    current_time = timetag_to_datetime(realtime,'%Y-%m-%d')

    #��ǰ����
    period = ContextInfo.period


    #ȡ��ǰK��ͼ��Ӧ�ĺ�Լ��ǰK�ߵĵ�ǰ��ͼ��Ȩ��ʽ�µ����̼�
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
    """��������������"""
    # �����Ȩ�۸����Ϊ����
    if price <= 0:
        return 0
    # �����Ȩ�۸��Ƿ�������С��ֵ����������Ȩ��ֵ��
    meet = False
    if cp == 1 and (price > (s - k) * exp(-r * t)):
        meet = True
    elif cp == -1 and (price > k * exp(-r * t) - s):
        meet = True
    # ����������С��ֵ����ֱ�ӷ���0
    if not meet:
        return 0
    # ����Newton Raphson������������������
    v = 0.29 # ��ʼ�����ʲ²�
    for i in range(50):
        # ���㵱ǰ�²Ⲩ���ʶ�Ӧ����Ȩ�۸��vegaֵ
        p = calculatePrice(s, k, r, t, v, cp)
        vega = calculateOriginalVega(s, k, r, t, v, cp)

        # ���vega��С�ӽ�0����ֱ�ӷ���
        if not vega:
            break
        # �������
        dx = (price - p) / vega
        # �������Ƿ�����Ҫ��������������ѭ��
        if abs(dx) < DX_TARGET:
            break
        # ������һ�ֲ²�Ĳ�����
        v += dx
    # ��鲨���ʼ������Ǹ�
    if v <= 0:
        return 0
    # ����4λС��
    v = round(v, 4)
    return v


def calculateOriginalVega(s, k, r, t, v, cp):
    """����ԭʼvegaֵ"""
    price1 = calculatePrice(s, k, r, t, v*STEP_UP, cp)
    price2 = calculatePrice(s, k, r, t, v*STEP_DOWN, cp)
    vega = (price1 - price2) / (v * STEP_DIFF)
    return vega

def calculatePrice(s, k, r, t, v, cp):
    """������Ȩ�۸�"""
    # ���������Ϊ0����ֱ�ӷ�����Ȩ�ռ��ֵ
    if v <= 0:
        return max(0, cp * (s - k))
    d1 = (log(s / k) + (r + 0.5 * pow(v, 2)) * t) / (v * sqrt(t))
    d2 = d1 - v * sqrt(t)
    price = cp * (s * cdf(cp * d1) - k * cdf(cp * d2) * exp(-r * t))
    return price

def get_week_of_month(year, month):
    """
    ��ȡָ����ĳ����ĳ�����еĵڼ���
    ��һ��Ϊһ�ܵĿ�ʼ
    """
    begin = datetime.datetime(year, month, 1).weekday()
    delta = datetime.timedelta(days=21+begin)
    exercise_date = datetime.datetime(year, month, 1) + delta
    return  exercise_date.strftime('%Y-%m-%d')