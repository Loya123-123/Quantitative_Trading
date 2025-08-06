from datetime import datetime

import pandas as pd
# ���뺯����
from jqdata import *

"""
���Լ�Ҫ
����Ƶ�ʣ�����/tick
����Ʒ�֣�����ҽҩ��600276.XSHG
���룺���ռ۸���ڹ�ȥ4�����̼���ߵ�ʱ������ǰ�۸�ͻ��5�ոߵ㣬��������ִ������
����ͷ�磺ȫ������
ֹӯ����������ڶ��쿪ʼ��ӯ��ʱһֱ���У����۸����߼�������ۻ���20%ʱ������ִ������
ֹ������������ڶ��쿪ʼ����������۵�95%����ִ������
"""

# ȫ�ֱ����洢����
_data_proxy = None
# log.set_level('order', 'error')

def initialize(context):
    # ���ò���
    # set_params(context)

    # ���ý���Ʒ��
    context.security = '600276.XSHG'
    # ���û�׼ ����XSHG �XSHE
    set_benchmark('600276.XSHG')

    context.buy_price = 0
    context.highest_price = 0
    context.buy_date = None

    # ���ý�����ز���
    set_option('use_real_price', True)

    # ���ý��׳ɱ��ͻ���
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), 'stock')
    set_slippage(FixedSlippage(0.02))

    # ����ÿ�տ���ǰ�ĺ���
    # run_daily(before_trading_start, time='every_bar')

    # ע�ύ�״�����
    run_daily(handle_data_wrapper, time='every_bar')


# def set_params(context):


def handle_data_wrapper(context):

    # ��ȡ�����Ʊ����
    data_df = get_data(context)

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_high = data_df['past_4_days_high'].iloc[-1]
    past_4_days_low = data_df['past_4_days_low'].iloc[-1]
    # ��ȡ��ǰ�ֲ�
    position = context.portfolio.positions.get(context.security)
    log.info(f"��ȡ��ǰ�ֲ� : {position}")
    has_position = position is not None and position.amount > 0

    # �ж��Ƿ�Ӧ�ý���
    signal = should_trade(context, current_price, past_4_days_high,past_4_days_low, has_position)

    # ִ�н���
    if signal:
        execute_trade(context, signal, current_price, past_4_days_high,past_4_days_low)


def get_data(context):
    """
    ��ȡ�����ϵ�ǰ��ȡ��������
    :param context:
    :return:
    """
    global _data_proxy
    _data_proxy = get_current_data()
    # ��ǰ����
    context.current_date = context.current_dt.date()

    # log.info(f"��ǰʱ�䣺 {context.current_date}")

    # ��ǰ����
    context.current_time = datetime.datetime.combine(context.current_date, context.current_dt.time())

    # log.info(f"��ǰʱ�䣺 {context.current_time}")

    # context.yesterday = context.current_date - datetime.timedelta(days=1)
    # log.info(f"��ǰʱ�䣺 {context.yesterday}")

    # ��ȡ��ʷ���� - ��Ҫ�㹻������������5�ոߵ�
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=5,  # ��ȥ4������ + ��������
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )
    log.info(f"��ȡ��ʷ���ݣ�\n {hist_daily}")

    past_4_days_high = hist_daily['high'].iloc[-5:-1].max()
    past_4_days_low = hist_daily['low'].iloc[-5:-1].min()
    log.info(f"��ȡ����������Сֵ���ݣ�\n {past_4_days_low}")

    # # ��ȡ����bars����
    # bars_df = get_bars(context.security,
    #                   end_dt=context.current_time,
    #                   count=1,
    #                   unit='1m',
    #                   # ���ر�ĵĿ��̼ۡ����̼ۡ���߼ۡ���ͼۣ��ɽ�������,ʱ���гɽ��Ľ���Ȩ���ӡ�ʱ����е���ͣ�ۡ�ʱ���е�ͣ�ۡ�ʱ����ƽ���ۣ��Ƿ�ͣ�ƣ�ǰһ�����̼۵�
    #                   fields=['date', 'open', 'close', 'low', 'high', 'volume', 'money'])
    # log.info(f"��ȡ��ǰbar����: \n {bars_df}")

    # context.current_time = bars_df['date']

    ticks_df = get_ticks(context.security,
                         end_dt=context.current_time,
                         count=1,
                         fields=['time', 'current', 'high', 'low', 'volume', 'money'], skip=True, df=True)

    log.info(f"��ȡ��ǰ���ݣ�\n {ticks_df}")

    # ��ȡ���¼۸�
    security_data = _data_proxy[context.security]

    # ��ȡ�۸�
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"�޷���ȡ�۸�: {e}")

    # log.info(f"��ȡ���¼۸�\n {current_price}")

    # ��������Ƿ���Ч
    if current_price is None or past_4_days_high is None:
        return

    data_df = pd.DataFrame({
        'current_time': [context.current_time]  # ��ǰʱ��
        ,'past_4_days_high': [past_4_days_high]  # ǰ������߼�
        ,'past_4_days_low':[past_4_days_low]     # ǰ������ͼ�
        ,'current_price': [ticks_df['current'].iloc[-1]]  # ��ǰ�۸�ticks_df��current�е����һ��ֵ��
        ,'current_high': [ticks_df['high'].iloc[-1]]
    })
    log.info(f"��ȡ�������ݣ�\n {data_df}")

    return data_df

# updated_df = pd.concat([existing_df, new_row], ignore_index=True)


def should_trade(context, current_price, past_4_days_high,past_4_days_low, has_position):
    """
    3. ���ڲ���Ҫ���жϵ�ǰ���������뻹������
    """
    # �����ź�
    signal = None

    if not has_position:  # û�гֲ�ʱѰ���������
        # ��ǰ�۸���ڹ�ȥ4�����̼���ߵ�ʱ����
        if current_price >= past_4_days_high:
            log.info(f"��ǰ�۸� {current_price} ���ڵ��ڹ�ȥ4�����̼���ߵ� {past_4_days_high}��׼������")
            signal = "BUY"

    else :  # �ֲ�ʱѰ����������
        # ��ǰ�۸���ڹ�ȥ4�����̼���ߵ�ʱ����
        if current_price <= past_4_days_low:
            log.info(f"��ǰ�۸� {current_price} С�ڵ��ڹ�ȥ4�����̼���͵� {past_4_days_low}��׼������")
            signal = "SELL"

    # else:  # �гֲ�ʱ����ֹӯֹ��
    #     # ������߼�
    #     if current_price > context.highest_price:
    #         context.highest_price = current_price
    #
    #     # ����ڶ��쿪ʼ����ֹӯֹ��
    #     if context.buy_date and context.current_date > context.buy_date:
    #         # ֹӯ�������۸����߼ۻ���20%
    #         stop_profit_price = context.highest_price * 0.8
    #
    #         # ֹ���������۸��������۵�95%
    #         stop_loss_price = context.buy_price * 0.95
    #
    #         # ����Ƿ񴥷�ֹӯ��ֹ��
    #         if current_price <= stop_profit_price or current_price <= stop_loss_price:
    #             log.info(f"��ǰ�۸� {current_price} ,�۸��ѵ���ֹӯ��ֹ��������׼������")
    #             signal = "SELL"

    return signal


def execute_trade(context, signal, current_price, past_4_days_high,past_4_days_low):
    """
    4. ִ���������������
    """
    if signal == "BUY":
        # ȫ������
        cash = context.portfolio.cash
        amount = int(cash * 0.98 / current_price / 100) * 100  # ȷ������������100��������
        qty = amount/100

        if amount > 0:
            # ִ������
            order(context.security, amount)
            context.buy_price = current_price
            context.highest_price = current_price
            context.buy_date = context.current_date
            log.info(f"���� {context.security}: {qty} �ɣ��۸�: {amount} , ����� {current_price}����ȥ4��������̼�: {past_4_days_high}")
            signal = None
    elif signal == "SELL":
        # ִ������
        position = context.portfolio.positions.get(context.security)
        order_target_value(context.security, 0)

        log.info(f"���� {context.security}: {position.amount} �ɣ��۸�: {current_price}�������: {context.buy_price}����߼�: {context.highest_price}")
        # ����״̬
        context.buy_price = 0
        context.highest_price = 0
        context.buy_date = None
        signal = None





