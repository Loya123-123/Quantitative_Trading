#coding:gbk

#���ڻ���1min��������
'''
�ز�ģ��ʾ������ʵ�̽��ײ��ԣ�

���������ȼ����˹�ȥ300���۸����ݵľ�ֵ�ͱ�׼��
�����ݾ�ֵ�Ӽ���׼��õ����������ֽ���,
���ֱ�����0.3��0.5�Ĳ�λȨ��
Ȼ����ݼ۸����ڵ����������ò�λ(+/-40Ϊ���½�,��ʵ������):
(-40,-3],(-3,-2],(-2,2],(2,3],(3,40](����۸���ھ�ֵ+���ֱ���׼��)
[0.25, 0.15, 0.0, 0.15, 0.25](�ʽ����)
'''

import numpy as np
import pandas as pd
import time
import datetime
def init(ContextInfo):
    #����ͼΪ���
    ContextInfo.tradefuture = ContextInfo.stockcode+"."+ContextInfo.market
    ContextInfo.set_universe([ContextInfo.tradefuture])
    print(ContextInfo.get_universe())
    ContextInfo.timeseries = pd.DataFrame()
    ContextInfo.band = np.zeros(5)
    #print 'ContextInfo.band',ContextInfo.band

    # ��������Ĳ�λ
    ContextInfo.weight = [0.25, 0.15, 0.0, 0.15, 0.25]
    # ��ȡ��ֲ�λ
    ContextInfo.position_long = 0
    # ��ȡ�ײֲ�λ
    ContextInfo.position_short = 0

    #ʣ���ʽ�
    ContextInfo.surpluscapital = ContextInfo.capital
    #��֤�����
    comdict = ContextInfo.get_commission()
    ContextInfo.marginratio = comdict['margin_ratio']
    #��Լ����
    ContextInfo.multiplier = ContextInfo.get_contract_multiplier(ContextInfo.tradefuture)
    #�˺�
    ContextInfo.accountid='testF'
    ContextInfo.now_timestamp = time.time()
def handlebar(ContextInfo):
    index = ContextInfo.barpos
    realtimetag  = ContextInfo.get_bar_timetag(index)
    lasttimetag = ContextInfo.get_bar_timetag(index - 1)
    print(timetag_to_datetime(realtimetag, '%Y-%m-%d %H:%M:%S'))
    if ContextInfo.period in ['1m','3m','5m','15m','30m'] and not ContextInfo.do_back_test:
        if (datetime.datetime.fromtimestamp(ContextInfo.now_timestamp) - datetime.datetime.fromtimestamp(realtimetag / 1000)).days > 7:
            return
    starttime = timetag_to_datetime(realtimetag-86400000 * 10, '%Y%m%d%H%M%S')
    endtime = timetag_to_datetime(realtimetag-86400000, '%Y%m%d%H%M%S')
    #print 'starttime,endtime',starttime,endtime
    Result=ContextInfo.get_market_data(['close'],stock_code=[ContextInfo.tradefuture],start_time=starttime,end_time=endtime,skip_paused=False,period=ContextInfo.period,dividend_type='front')
    close_sort = Result['close'].sort_index(axis = 0,ascending = True)
    #print close_sort,starttime,endtime
    #��ȥ300���۸����ݵľ�ֵ�ͱ�׼��
    Result_mean = close_sort.tail(300).mean()
    Result_std = close_sort.tail(300).std()
    ContextInfo.band = Result_mean + np.array([-40, -3, -2, 2, 3, 40]) * Result_std
    #print 'ContextInfo.band',ContextInfo.band
    if np.isnan(ContextInfo.band).any() or Result_std==0:
        return
    if index > 0:
        lasttimetag = ContextInfo.get_bar_timetag(index - 1)
        #ǰһ��bar���̼�
        close_lastbar = ContextInfo.get_market_data (['close'],stock_code=[ContextInfo.tradefuture],period=ContextInfo.period,dividend_type='front')
        #��ǰ���̼�
        open_currentbar = ContextInfo.get_market_data (['open'],stock_code=[ContextInfo.tradefuture],period=ContextInfo.period,dividend_type='front')
        #��������
        #print close_lastbar,ContextInfo.band
        grid = pd.cut([close_lastbar], ContextInfo.band, labels=[0, 1, 2, 3, 4])[0]
        #print 'grid ',grid
        if not ContextInfo.do_back_test:
            ContextInfo.paint('grid',float(grid),-1,0)
        # ���޲�λ�Ҽ۸�ͻ���������úõ����俪��
        if ContextInfo.position_long == 0 and ContextInfo.position_short == 0 and grid != 2:
            # ����3Ϊ���м�������Ϸ�,����
            if grid >= 3 and ContextInfo.surpluscapital > 0 :
                long_num = int(ContextInfo.weight[grid]*ContextInfo.surpluscapital/(ContextInfo.marginratio*close_lastbar*ContextInfo.multiplier))
                ContextInfo.position_long = long_num
                buy_open(ContextInfo.tradefuture,long_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital -= long_num * ContextInfo.marginratio * close_lastbar * ContextInfo.multiplier
            #print '����'
            elif grid <= 1 and ContextInfo.surpluscapital > 0 :
                short_num = int(ContextInfo.weight[grid]*ContextInfo.surpluscapital/(ContextInfo.marginratio*close_lastbar*ContextInfo.multiplier))
                ContextInfo.position_short = short_num
                sell_open(ContextInfo.tradefuture,short_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital -= short_num * ContextInfo.marginratio * close_lastbar * ContextInfo.multiplier
            #print '����'
        # ���ж�ֵĴ���
        elif ContextInfo.position_long > 0 :
            if grid >= 3 and ContextInfo.surpluscapital > 0 :
                targetlong_num = int(ContextInfo.weight[grid] * (ContextInfo.surpluscapital + ContextInfo.multiplier * close_lastbar * ContextInfo.position_long*ContextInfo.marginratio)/ (ContextInfo.marginratio*close_lastbar * ContextInfo.multiplier))
                if targetlong_num > ContextInfo.position_long :
                    trade_num = targetlong_num - ContextInfo.position_long
                    ContextInfo.position_long = targetlong_num
                    buy_open(ContextInfo.tradefuture,trade_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital -= trade_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                elif targetlong_num < ContextInfo.position_long:
                    trade_num = ContextInfo.position_long - targetlong_num
                    ContextInfo.position_long = targetlong_num
                    sell_close_tdayfirst(ContextInfo.tradefuture,trade_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital += trade_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
            #print '����ֵ���λ'
            # ����2Ϊ���м�����,ƽ��
            elif grid == 2:
                sell_close_tdayfirst(ContextInfo.tradefuture,ContextInfo.position_long,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital += ContextInfo.position_long * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                ContextInfo.position_long = 0
            #print 'ƽ��'
            # С��1Ϊ���м�������·�,����
            elif grid <= 1:
                sell_close_tdayfirst(ContextInfo.tradefuture,ContextInfo.position_long,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital += ContextInfo.position_long * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                ContextInfo.position_long = 0
                #print 'ȫƽ���'
                if ContextInfo.surpluscapital > 0 :
                    short_num = int(ContextInfo.weight[grid]*ContextInfo.surpluscapital/(ContextInfo.multiplier * ContextInfo.marginratio * close_lastbar))
                    ContextInfo.position_short = short_num
                    sell_open(ContextInfo.tradefuture,short_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital -= short_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                #print '���ղֵ���λ'

        # ���пղֵĴ���
        elif ContextInfo.position_short> 0 :
            # С��1Ϊ���м�������·�,����
            if grid <= 1:
                targetlshort_num = int(ContextInfo.weight[grid]*(ContextInfo.surpluscapital + ContextInfo.multiplier*close_lastbar*ContextInfo.position_short*ContextInfo.marginratio)/(ContextInfo.multiplier * ContextInfo.marginratio * close_lastbar))
                if targetlshort_num > ContextInfo.position_short:
                    trade_num = targetlshort_num - ContextInfo.position_short
                    ContextInfo.position_short = targetlshort_num
                    sell_open(ContextInfo.tradefuture,trade_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital -= trade_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                #print '���ղֵ���λ' ,targetlshort_num
                elif targetlshort_num < ContextInfo.position_short:
                    trade_num = ContextInfo.position_short -  targetlshort_num
                    ContextInfo.position_short = targetlshort_num
                    buy_close_tdayfirst(ContextInfo.tradefuture,trade_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital += trade_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                #print  'ƽ�ղֵ���λ' ,targetlshort_num
            # ����2Ϊ���м�����,ƽ��
            elif grid == 2:
                buy_close_tdayfirst(ContextInfo.tradefuture,ContextInfo.position_short,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital += ContextInfo.position_short * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                ContextInfo.position_short = 0
            #print 'ȫƽ�ղ�'
            # ����3Ϊ���м�������Ϸ�,����
            elif grid >= 3:
                buy_close_tdayfirst(ContextInfo.tradefuture,ContextInfo.position_short,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                ContextInfo.surpluscapital += ContextInfo.position_short * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                ContextInfo.position_short = 0
                #print  'ȫƽ�ղ�'
                if ContextInfo.surpluscapital > 0 :
                    trade_num = int(ContextInfo.weight[grid]*ContextInfo.surpluscapital / (ContextInfo.marginratio * close_lastbar * ContextInfo.multiplier))
                    ContextInfo.position_long = trade_num
                    buy_open(ContextInfo.tradefuture,trade_num,'fix',close_lastbar,ContextInfo,ContextInfo.accountid)
                    ContextInfo.surpluscapital -= trade_num * close_lastbar * ContextInfo.marginratio * ContextInfo.multiplier
                #print ' ����ֵ���λ'
# ��ȡ��ֲ�λ
#print 'ContextInfo.position_long',ContextInfo.position_long
# ��ȡ�ղֲ�λ
#print 'ContextInfo.position_short',ContextInfo.position_short
# ��ȡʣ���ʽ�
#print 'ContextInfo.surpluscapital',ContextInfo.surpluscapital

