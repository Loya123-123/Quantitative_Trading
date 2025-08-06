#coding:gbk

#���볣�ÿ�
import pandas as pd
import numpy as np
import talib
#ʾ��˵���������ԣ�ͨ���������˫���ߣ��ڽ��ʱ���룬����ʱ������ ����ز����� ��ͼѡ��Ҫ���׵Ĺ�ƱƷ��

def init(C):
    #init handlebar�����������ContextInfo���� ������дΪC
    #���ò��Ա��Ϊ��ͼƷ��
    C.stock= C.stockcode + '.' +C.market
    #line1��line2�ֱ�Ϊ������������
    C.line1=10   #���߲���
    C.line2=20   #���߲���
    #accountidΪ���Ե�ID �ز�ģʽ�ʽ��˺ſ����������ַ���
    C.accountid = "testS"

def handlebar(C):
    #��ǰk������
    bar_date = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y%m%d%H%M%S')
    #�زⲻ��Ҫ������������ʹ�ñ��������ٶȸ��� ָ��subscribe����Ϊ��. ����ز���Ʒ�� ��Ҫ�����ض�Ӧ������ʷ����
    local_data = C.get_market_data_ex(['close'], [C.stock], end_time = bar_date, period = C.period, count = max(C.line1, C.line2), subscribe = False)
    close_list = list(local_data[C.stock].iloc[:, 0])
    #����ȡ����ʷ����ת��ΪDataFrame��ʽ�������
    #���Ŀǰδ�ֲ֣�ͬʱ���ߴ������ߣ�������8�ɲ�λ
    if len(close_list) <1:
        print(bar_date, '���鲻�� ����')
    line1_mean = round(np.mean(close_list[-C.line1:]), 2)
    line2_mean = round(np.mean(close_list[-C.line2:]), 2)
    print(f"{bar_date} �̾���{line1_mean} ������{line2_mean}")
    account = get_trade_detail_data('test', 'stock', 'account')
    account = account[0]
    available_cash = int(account.m_dAvailable)
    holdings = get_trade_detail_data('test', 'stock', 'position')
    holdings = {i.m_strInstrumentID + '.' + i.m_strExchangeID : i.m_nVolume for i in holdings}
    holding_vol = holdings[C.stock] if C.stock in holdings else 0
    if holding_vol == 0 and line1_mean > line2_mean:
        vol = int(available_cash / close_list[-1] / 100) * 100
        #�µ�����
        passorder(23, 1101, C.accountid, C.stock, 5, -1, vol, C)
        print(f"{bar_date} ����")
        C.draw_text(1, 1, '��')
    #���Ŀǰ�ֲ��У�ͬʱ�����´����ߣ���ȫ��ƽ��
    elif holding_vol > 0 and line1_mean < line2_mean:
        #״̬���Ϊδ�ֲ�
        C.holding=False
        #�µ�ƽ��
        passorder(24, 1101, C.accountid, C.stock, 5, -1, holding_vol, C)
        print(f"{bar_date} ƽ��")
        C.draw_text(1, 1, 'ƽ')
