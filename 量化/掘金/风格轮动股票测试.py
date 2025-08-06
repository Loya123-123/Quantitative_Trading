# coding = udf-8
# /usr/bin/env python
# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *

import datetime
import numpy as np
import pandas as pd

'''
ʾ�����Խ����ο���������ֱ��ʵ��ʹ�á�

����ֶ�����
�߼�������֤50������300����֤500��Ϊ�г��������Ĵ���ÿ��ѡȡ�������õ�һ�ַ��������ɷֹ��������ֵ��Nֻ��Ʊ��ÿ���³����е��ֻ���
'''

def init(context):
    # ���ֶ��ķ��ָ��(�ֱ�Ϊ����֤50������300����֤500)
    context.index = ['SHSE.000016', 'SHSE.000300', 'SZSE.399625']
    # ����ͳ�����ݵ�����
    context.days = 20
    # �ֹ�����
    context.holding_num = 10

    # ÿ�ն�ʱ����
    schedule(schedule_func=algo, date_rule='1d', time_rule='09:30:00')


def algo(context):
    # ��������
    now_str = context.now.strftime('%Y-%m-%d')
    # ��ȡ��һ��������
    last_day = get_previous_n_trading_dates(exchange='SHSE', date=now_str, n=1)[0]
    # �ж��Ƿ�Ϊÿ���µ�һ��������
    if context.now.month!=pd.Timestamp(last_day).month:
        return_index = pd.DataFrame(columns=['return'])
        # ��ȡ������ָ��������
        for i in context.index:
            return_index_his = history_n(symbol=i, frequency='1d', count=context.days+1, fields='close,bob',
                                         fill_missing='Last', adjust=ADJUST_PREV, end_time=last_day, df=True)
            return_index_his = return_index_his['close'].values
            return_index.loc[i,'return'] = return_index_his[-1] / return_index_his[0] - 1

        # ��ȡָ�����������ʱ�����õ�ָ��
        sector = return_index.index[np.argmax(return_index)]
        print('{}:���ָ����:{}'.format(now_str,sector))

        # ��ȡ���ָ���ɷݹ�
        symbols = list(stk_get_index_constituents(index=sector, trade_date=last_day)['symbol'])

        # ����ͣ�ƵĹ�Ʊ
        stocks_info =  get_symbols(sec_type1=1010, symbols=symbols, trade_date=now_str, skip_suspended=True, skip_st=True)
        symbols = [item['symbol'] for item in stocks_info if item['listed_date']<context.now and item['delisted_date']>context.now]
        # ��ȡ���ָ���ɷݹɵ���ֵ��ѡȡ��ֵ����Nֻ��Ʊ
        fin = stk_get_daily_mktvalue_pt(symbols=symbols, fields='tot_mv', trade_date=last_day, df=True).sort_values(by='tot_mv',ascending=False)
        to_buy = list(fin.iloc[:context.holding_num]['symbol'])

        # ����Ȩ��(Ԥ����2%�ʽ𣬷�ֹʣ���ʽ𲻹������ѵֿ�)
        percent = 0.98 / len(to_buy)
        # ��ȡ��ǰ���в�λ
        positions = get_position()

        # ƽ���ڱ�ĳصĹ�Ʊ��ע�������Խ����Կ��̼�Ϊ���׼۸񣬵�������ʱ����ʱ��ʱ���������Ӧ�۸�
        for position in positions:
            symbol = position['symbol']
            if symbol not in to_buy:
                # ���̼ۣ���Ƶ���ݣ�
                new_price = history_n(symbol=symbol, frequency='1d', count=1, end_time=now_str, fields='open', adjust=ADJUST_PREV, adjust_end_time=context.backtest_end_time, df=False)[0]['open']
                # # ��ǰ�ۣ�tick���ݣ���Ѱ汾��ʱ��Ȩ�����ƣ�ʵʱģʽ�����ص�ǰ���� tick ���ݣ��ز�ģʽ�����ػز⵱ǰʱ�������һ���ӵ����̼ۣ�
                # new_price = current(symbols=symbol)[0]['price']
                order_target_percent(symbol=symbol, percent=0, order_type=OrderType_Limit,position_side=PositionSide_Long,price=new_price)

        # �����ĳ��еĹ�Ʊ��ע�������Խ����Կ��̼�Ϊ���׼۸񣬵�������ʱ����ʱ��ʱ���������Ӧ�۸�
        for symbol in to_buy:
            # ���̼ۣ���Ƶ���ݣ�
            new_price = history_n(symbol=symbol, frequency='1d', count=1, end_time=now_str, fields='open', adjust=ADJUST_PREV, adjust_end_time=context.backtest_end_time, df=False)[0]['open']
            # # ��ǰ�ۣ�tick���ݣ���Ѱ汾��ʱ��Ȩ�����ƣ�ʵʱģʽ�����ص�ǰ���� tick ���ݣ��ز�ģʽ�����ػز⵱ǰʱ�������һ���ӵ����̼ۣ�
            # new_price = current(symbols=symbol)[0]['price']
            order_target_percent(symbol=symbol, percent=percent, order_type=OrderType_Limit,position_side=PositionSide_Long,price=new_price)


def on_order_status(context, order):
    # ��Ĵ���
    symbol = order['symbol']
    # ί�м۸�
    price = order['price']
    # ί������
    volume = order['volume']
    # Ŀ���λ
    target_percent = order['target_percent']
    # �鿴�µ����ί��״̬������3����ί��ȫ���ɽ�
    status = order['status']
    # ��������1Ϊ���룬2Ϊ����
    side = order['side']
    # ��ƽ�����ͣ�1Ϊ���֣�2Ϊƽ��
    effect = order['position_effect']
    # ί�����ͣ�1Ϊ�޼�ί�У�2Ϊ�м�ί��
    order_type = order['order_type']
    if status == 3:
        if effect == 1:
            if side == 1:
                side_effect = '�����'
            else:
                side_effect = '���ղ�'
        else:
            if side == 1:
                side_effect = 'ƽ�ղ�'
            else:
                side_effect = 'ƽ���'
        order_type_word = '�޼�' if order_type==1 else '�м�'
        print('{}:��ģ�{}����������{}{}��ί�м۸�{}��ί��������{}'.format(context.now,symbol,order_type_word,side_effect,price,volume))



def on_backtest_finished(context, indicator):
    print('*'*50)
    print('�ز�����ɣ���ͨ�����Ͻǡ��ز���ʷ�����ܲ�ѯ���顣')


if __name__ == '__main__':
    '''
    strategy_id����ID,��ϵͳ����
    filename�ļ���,���뱾�ļ�������һ��
    modeʵʱģʽ:MODE_LIVE�ز�ģʽ:MODE_BACKTEST
    token�󶨼������ID,����ϵͳ����-��Կ����������
    backtest_start_time�ز⿪ʼʱ��
    backtest_end_time�ز����ʱ��
    backtest_adjust��Ʊ��Ȩ��ʽ����Ȩ:ADJUST_NONEǰ��Ȩ:ADJUST_PREV��Ȩ:ADJUST_POST
    backtest_initial_cash�ز��ʼ�ʽ�
    backtest_commission_ratio�ز�Ӷ�����
    backtest_slippage_ratio�ز⻬�����
    backtest_match_mode�м۴��ģʽ������һtick/bar���̼۴��:0���Ե�ǰtick/bar���̼۴�ϣ�1
    '''
    run(strategy_id='623b4755-660f-11f0-952b-00ff59c3fc0a',
        filename='main.py',
        mode=MODE_BACKTEST,
        token='0f9176cab6b0db47c6e743efb0c1021d8b47b391',
        backtest_start_time='2019-01-01 08:00:00',
        backtest_end_time='2020-12-31 16:00:00',
        backtest_adjust=ADJUST_PREV,
        backtest_initial_cash=10000000,
        backtest_commission_ratio=0.0001,
        backtest_slippage_ratio=0.0001,
        backtest_match_mode=1)