#coding:gbk
'''
�ز�ģ��ʾ������ʵ�̽��ײ��ԣ�

�����Ը��ݼ��������.��ȥ��30��bar�ľ�ֵ����0.5����׼��õ�������
�������¼۲��ϴ��Ϲ������ռ۲�,�´��¹�������۲�
���ڻع������¹�ˮƽ�ڵ�ʱ��ƽ��
'''

import numpy as np

def init(ContextInfo):
    ContextInfo.trade_pair=['rb00.SF','hc00.SF']
    ContextInfo.position_tag = {'long':False,'short':False}         #��ʼ���ֲ�״̬
    ContextInfo.set_universe(ContextInfo.trade_pair) # ���ñ���ڻ���Լ��Ӧ��Ʊ��
    ContextInfo.accid = '103427'

def handlebar(ContextInfo):
    index = ContextInfo.barpos
    bartimetag = ContextInfo.get_bar_timetag(index)
    print(timetag_to_datetime(bartimetag,'%Y-%m-%d %H:%M%S'))
    # ��ȡ����Ʒ�ֵ����̼�ʱ������
    closes=ContextInfo.get_market_data(['close'], stock_code=ContextInfo.trade_pair, period = ContextInfo.period, count=31)
    if closes.empty:
        return

    up_closes = closes[ContextInfo.trade_pair[0]]['close']
    down_closes = closes[ContextInfo.trade_pair[1]]['close']
    # ����۲�
    spread = up_closes[:-1] - down_closes[:-1]
    #spread=0
    # ���㲼�ִ����¹�
    up = np.mean(spread) + 0.5 * np.std(spread)
    down = np.mean(spread) - 0.5 * np.std(spread)
    # ����۲�
    if (up_closes[-1] is None) or (down_closes[-1] is None):
        spread_now=0
    else:
        spread_now = up_closes[-1] - down_closes[-1]

    #�޽���ʱ���۲���(��)�����ִ���(��)��������(��)�۲�
    position_up_long = ContextInfo.position_tag['long']
    position_up_short = ContextInfo.position_tag['short']
    if not position_up_long and not position_up_short:
        if spread_now > up:
            #����code1������code2
            sell_open(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            buy_open(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['short'] = True
        if spread_now < down:
            #����code1������code2
            buy_open(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            sell_open(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['long'] = True
    # �۲�ع�ʱƽ��
    elif position_up_short:
        if spread_now <= up:
            #ƽ��code1��ƽ��code2
            buy_close_tdayfirst(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            sell_close_tdayfirst(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['short'] = False
        # �����¹췴�򿪲�
        if spread_now < down:
            #����code1������code2
            buy_open(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            sell_open(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['long'] = True
    elif position_up_long:
        if spread_now >= down:
            #ƽ��code1��ƽ��code2
            sell_close_tdayfirst(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            buy_close_tdayfirst(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['long'] = False
        if spread_now > up:
            #����code1������code2
            sell_open(ContextInfo.trade_pair[0],1,ContextInfo,ContextInfo.accid)
            buy_open(ContextInfo.trade_pair[1],1,ContextInfo,ContextInfo.accid)
            ContextInfo.position_tag['short'] = True

    ContextInfo.paint('short_spread',int(spread_now > up),-1,0,'noaxis')
    ContextInfo.paint('long_spread',int(spread_now < down),-1,0,'noaxis')

























