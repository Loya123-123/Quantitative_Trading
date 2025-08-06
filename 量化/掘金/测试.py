# coding = udf-8
# /usr/bin/env python
# ��Ҫ�þۿ�������һ���������ײ��ԣ���Ҫ�����ײ���д�ɴ��룬���в����߼����£�
# ����Ʒ�֣�
# ����ҽҩ��600276.XSHG
# ����ҽҩ��000963.XSHE
# ����Һ��000858.XSHE
# ɽ���ھƣ�600809.XSHG
# �����Ͻѣ�000568.XSHE
# ����˹��603486.XSHG
# ���룺����dkx���ʱ���룬��dkx���ϴ�10��madkx��ʱ����
# ����ͷ�磺ÿһ��Ʒ���ڲ�����98%���ʽ�ݶ��£������ܶ���
# ���������յڶ��쿪ʼ������dkx����ʱ��������dkx�����´�10��madkx��ʱ����

# �������AI����

import pandas as pd
import numpy as np
from gm.api import *

# ȫ�ֱ����洢����
_data_proxy = None

def init(context):
    # ���ò��Բ���
    set_params(context)
    # ���ý���Ʒ��
    set_security(context)
    # ���û�׼
    set_benchmark('SHSE.000300')

    # ���ý�����ز���
    context.account = context.account_list[0]  # ��ȡĬ���˻�

    # ���ý��׳ɱ��ͻ���
    # ��������Ľ��׳ɱ����ÿ�����ۿ�ͬ���������ʾ��
    # context.set_commission(stock_tax=0.001, stock_commission=0.0003)

    # ����ÿ�����еĺ���
    schedule(schedule_func=before_trading_start, date_rule='1d', time_rule='09:00:00')
    schedule(schedule_func=handle_data, date_rule='1d', time_rule='09:30:00')

def set_params(context):
    # ����DKX����
    context.dk_period = 10  # DKX��������
    context.madk_period = 10  # MADKX��������
    context.max_position_ratio = 0.20  # ����Ʒ������ʽ�ռ��
    context.buy_dates = {}  # ��¼ÿֻ��Ʊ����������

def set_security(context):
    # �����ֻ����Ʒ�� - ת��Ϊ��������Ĵ����ʽ
    context.security_list = [
        'SHSE.600276',  # ����ҽҩ
        'SZSE.000963',  # ����ҽҩ
        'SZSE.000858',  # ����Һ
        'SHSE.600809',  # ɽ���ھ�
        'SZSE.000568',  # �����Ͻ�
        'SHSE.603486',  # ����˹
    ]

def before_trading_start(context):
    # ��ȡ��ǰ����
    context.current_date = context.now.date()

    # Ϊÿֻ��Ʊ��ȡ��ʷ���ݲ�����ָ��
    hist_data = {}
    for security in context.security_list:
        # ��ȡ��ʷ��K������ - ת��Ϊ�������API
        hist_daily = history_n(symbol=security, frequency='1d', count=context.dk_period * 3,
                               fields='open,high,low,close', fill_missing='Last', adjust=ADJUST_PREV,
                               df=True)

        # ����DKX��MADKX
        if not hist_daily.empty:  # ȷ�����ݲ�Ϊ��
            hist_daily = calculate_dkx(hist_daily, context.dk_period, context.madk_period)
            hist_data[security] = hist_daily

    # ��������
    context.hist_data = hist_data

# ����DKX��MADKXָ��
def calculate_dkx(df, dk_period=10, madk_period=10):
    # ����DKX
    # DKX = (3*CLOSE + 2*OPEN + HIGH + LOW)/7
    df['DKX'] = (3 * df['close'] + 2 * df['open'] + df['high'] + df['low']) / 7

    # ����MADKX - MADKX��DKX��N�ռ��ƶ�ƽ��
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # ����DKX��MADKX��ǰһ��ֵ�������жϽ������
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df

# ���׾��ߺ���
def handle_data(context):
    # ��ȡ��ǰ���� - ת��Ϊ�������API
    global _data_proxy
    current_data = {}
    for security in context.security_list:
        tick = current(symbols=security, df=True)
        if not tick.empty:
            current_data[security] = tick.iloc[0]
    _data_proxy = current_data

    # ����ÿֻ��Ʊ���н��׾���
    for security in context.security_list:
        try:
            # ��ȡ���¼۸�
            security_data = _data_proxy.get(security)

            if security_data is None:
                continue

            # ��ȡ�۸�
            current_price = security_data['last_price']

            # ��ȡ��ʷ����
            hist_daily = context.hist_data.get(security)

            # ȷ�����㹻�����ݼ���ָ��
            if hist_daily is None or len(hist_daily) < context.dk_period * 3:
                continue

            # ��ȡ���µ�DKX��MADKXֵ
            dkx_now = hist_daily['DKX'].iloc[-1]
            madkx_now = hist_daily['MADKX'].iloc[-1]
            dkx_prev = hist_daily['DKX_prev'].iloc[-1]
            madkx_prev = hist_daily['MADKX_prev'].iloc[-1]

            # ��ȡ��ǰ�ֲ� - ת��Ϊ�������API
            positions = context.account().position(symbol=security, side=PositionSide_Long)
            has_position = len(positions) > 0

            # ���ײ����߼�
            if not has_position:  # û�гֲ�ʱ��������
                # ��������������DKX��棬��DKX���ϴ�MADKX��
                if dkx_prev <= madkx_prev and dkx_now > madkx_now:
                    # ������������ - ����Ʒ�ֲ�����20%���ʲ��ݶ�
                    account_info = context.account().info()
                    total_value = account_info['nav']  # ���ʲ�
                    max_position_value = total_value * context.max_position_ratio

                    # �������гֲ�ռ�õ��ʽ�
                    current_position_value = 0
                    for pos in context.account().positions():
                        if pos['symbol'] in context.security_list:
                            current_position_value += pos['position_value']

                    # �����ʽ� = ���ʲ� * ������ - ���гֲּ�ֵ
                    available_cash = max_position_value - current_position_value
                    available_cash = max(available_cash, 0)  # ȷ�������ʽ�Ǹ�

                    # �������������
                    amount = int(available_cash * 0.98 / current_price / 100) * 100  # ȷ�����������100��������

                    if amount > 0:
                        # ִ������ - ת��Ϊ�������API
                        order_volume(symbol=security, volume=amount, side=OrderSide_Buy,
                                     order_type=OrderType_Market, position_effect=PositionEffect_Open)
                        context.buy_dates[security] = context.current_date
                        print(f"���� {security}: {amount} �ɣ��۸�: {current_price}��DKX: {dkx_now:.2f}��MADKX: {madkx_now:.2f}")
            else:  # �гֲ�ʱ��������
                # �������������յڶ��쿪ʼ������DKX���棬��DKX���´�MADKX��
                buy_date = context.buy_dates.get(security)
                if buy_date and context.current_date > buy_date:
                    if dkx_prev >= madkx_prev and dkx_now < madkx_now:
                        # ��ȡ�ֲ�����
                        position = positions[0]
                        amount = position['volume']

                        # ִ������ - ת��Ϊ�������API
                        order_volume(symbol=security, volume=amount, side=OrderSide_Sell,
                                     order_type=OrderType_Market, position_effect=PositionEffect_Close)
                        if security in context.buy_dates:
                            del context.buy_dates[security]
                        print(f"���� {security}: {amount} �ɣ��۸�: {current_price}��DKX: {dkx_now:.2f}��MADKX: {madkx_now:.2f}")
        except Exception as e:
            print(f"���� {security} ʱ����: {e}")
            continue