#coding:gbk

'''
�ز�ģ��ʾ������ʵ�̽��ײ��ԣ�

������ÿ��1���¶�ʱ��������1000��Դ��399381.SZ����1000���ϣ�399382.SZ����1000��ҵ��399383.SZ����
1000��ѡ��399384.SZ����1000���ѣ�399385.SZ����1000ҽҩ��399386.SZ���⼸����ҵָ����ȥ
20�������յ������ʲ�ѡȡ����������ߵ�ָ���ĳɷݹɲ���ȡ�����ǵ���ֵ����
���Ѳ�λ��������ֵ����5ֻ��Ʊ��
�ò����ڹ�Ʊָ������������
'''
import numpy as np
import math
def init(ContextInfo):
    MarketPosition ={}
    ContextInfo.MarketPosition = MarketPosition #��ʼ���ֲ�
    index_universe = ['399381.SZ','399382.SZ','399383.SZ','399384.SZ','399385.SZ','399386.SZ']
    index_stocks = []
    for index in index_universe:
        for stock in ContextInfo.get_sector(index):
            index_stocks.append(stock)
    ContextInfo.set_universe(index_universe+index_stocks)   #�趨��Ʊ��
    ContextInfo.day = 20
    ContextInfo.ratio = 0.8
    ContextInfo.holding_amount = 5
    ContextInfo.accountID='testS'

def handlebar(ContextInfo):
    buy_condition = False
    sell_condition = False
    d = ContextInfo.barpos
    lastdate = timetag_to_datetime(ContextInfo.get_bar_timetag(d - 1), '%Y%m%d')
    date = timetag_to_datetime(ContextInfo.get_bar_timetag(d), '%Y%m%d')
    print(date)
    index_list = ['399381.SZ','399382.SZ','399383.SZ','399384.SZ','399385.SZ','399386.SZ']
    return_index = []
    weight = ContextInfo.ratio/ContextInfo.holding_amount
    size_dict = {}
    if  (float(date[-4:-2]) != float(lastdate[-4:-2])):
        #print '---------------------------------------------------------------------------------'
        #print '��ǰ������',date,date[-4:-2]
        his = ContextInfo.get_history_data(21,'1d','close')
        #print "his",his,timetag_to_datetime(ContextInfo.get_bar_timetag(d),"%Y%m%d")
        for k in list(his.keys()):
            if len(his[k]) == 0:
                del his[k]
        for index in index_list:
            ratio = 0
            try:
                ratio = (his[index][-2] - his[index][0])/his[index][0]
            except KeyError:
                print('key error:' + index)
            except IndexError:
                print('list index out of range:' + index)
            return_index.append(ratio)
        # ��ȡָ�����������ʱ�����õ���ҵ
        best_index = index_list[np.argmax(return_index)]
        #print '��ǰ�����ҵ�ǣ�', ContextInfo.get_stock_name(best_index)[3:]+'��ҵ'
        # ��ȡ�����н��׵Ĺ�Ʊ
        index_stock = ContextInfo.get_sector(best_index)
        stock_available = []
        for stock in index_stock:
            if ContextInfo.is_suspended_stock(stock) == False:
                stock_available.append(stock)

        for stock in stock_available:
            if stock in list(his.keys()):
                #Ŀǰ��ʷ��ͨ�ɱ�ȡ�����������ܹɱ�
                if len(his[stock]) >= 2:
                    stocksize =his[stock][-2] * float(ContextInfo.get_financial_data(['CAPITALSTRUCTURE.total_capital'],[stock],lastdate,date).iloc[0,-1])
                    size_dict[stock] = stocksize
                elif len(his[stock]) == 1:
                    stocksize =his[stock][-1] * float(ContextInfo.get_financial_data(['CAPITALSTRUCTURE.total_capital'],[stock],lastdate,date).iloc[0,-1])
                    size_dict[stock] = stocksize
                else:
                    return
        size_sorted = sorted(list(size_dict.items()), key = lambda item:item[1])
        pre_holding = []

        for tuple in size_sorted[-ContextInfo.holding_amount:]:
            pre_holding.append(tuple[0])
        #print '���뱸ѡ',pre_holding
        #�����µ�
        if len(pre_holding) > 0:
            sellshort_list = []
            for stock in list(ContextInfo.MarketPosition.keys()):
                if stock not in pre_holding and (stock in list(his.keys())):
                    order_shares(stock,-ContextInfo.MarketPosition[stock],'lastest',his[stock][-1],ContextInfo,ContextInfo.accountID)
                    print('sell',stock)
                    sell_condition = True
                    sellshort_list.append(stock)
            if len(sellshort_list) >0:
                for stock in sellshort_list:
                    del ContextInfo.MarketPosition[stock]
            for stock in pre_holding:
                if stock not in list(ContextInfo.MarketPosition.keys()):
                    Lots = math.floor(ContextInfo.ratio * (1.0/len(pre_holding)) * ContextInfo.capital / (his[stock][-1] * 100))
                    order_shares(stock,Lots *100,'lastest',his[stock][-1],ContextInfo,ContextInfo.accountID)
                    print('buy',stock)
                    buy_condition = True
                    ContextInfo.MarketPosition[stock] = Lots *100

#ContextInfo.paint('do_buy', int(buy_condition), -1, 0)
#ContextInfo.paint('do_sell', int(sell_condition), -1, 0)




