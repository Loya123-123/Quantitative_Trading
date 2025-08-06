from datetime import datetime

import pandas as pd
# ���뺯����
from jqdata import *

"""
���Լ�Ҫ
����Ƶ�ʣ�����/tick
����Ʒ�֣�����ҽҩ��600276.XSHG
ҽҩ��ҵ��
����ҽҩ��600276.XSHG        �Ϻ�               
����ҽҩ��000963.XSHE        ����               
�׾ƣ�
����Һ��000858.XSHE             ����              
ɽ���ھƣ�600809.XSHG        �Ϻ�               
�����Ͻѣ�000568.XSHE         ����
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
    set_params(context)

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


def set_params(context):
    # ֹӯ����
    context.stop_profit_ratio = 0.2
    # ֹ�����
    context.stop_loss_ratio = 0.98


def handle_data_wrapper(context):
    # ��ȡ�����Ʊ����
    data_df = get_data(context)

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_high = data_df['past_4_days_high'].iloc[-1]
    past_4_days_low = data_df['past_4_days_low'].iloc[-1]

    # �ж��Ƿ�Ӧ�ý���
    signal = should_trade(context, current_price, past_4_days_high)

    # ִ�н���
    if signal:
        execute_trade(context, signal, current_price, past_4_days_high)


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

    log.info(f"��ǰʱ�䣺 {context.current_date}")

    # ��ǰ����
    context.current_time = datetime.datetime.combine(context.current_date, context.current_dt.time())

    # log.info(f"��ǰʱ�䣺 {context.current_time}")

    # ��ȡ��ʷ���� - ��Ҫ�㹻������������5�ոߵ�
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=5,  # ��ȥ4������ + ��������
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )
    # log.info(f"��ȡ��ʷ���ݣ�\n {hist_daily}")
    # ��ȡ5�ոߵ�
    past_4_days_high = hist_daily['close'].iloc[-5:-1].max()
    # ��ȡ5�յ͵�
    past_4_days_low = hist_daily['low'].iloc[-5:-1].min()
    log.info(f"��ȡ����������Сֵ���ݣ�\n {past_4_days_low}")

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
        , 'past_4_days_high': [past_4_days_high]  # ǰ������߼�
        , 'past_4_days_low': [past_4_days_low]  # ǰ������ͼ�
        , 'current_price': [ticks_df['current'].iloc[-1]]  # ��ǰ�۸�ticks_df��current�е����һ��ֵ��
        , 'current_high': [ticks_df['high'].iloc[-1]]
    })
    log.info(f"��ȡ�������ݣ�\n {data_df}")

    return data_df


def should_trade(context, current_price, past_4_days_high):
    """
    3. ���ڲ���Ҫ���жϵ�ǰ���������뻹������
    """
    # �����ź�
    signal = None

    # ��ȡ��ǰ�ֲ�
    position = context.portfolio.positions.get(context.security)
    log.info(f"��ȡ��ǰ�ֲ� : {position}")

    # ��ȡ�Ƿ�ǰ�ֲ�
    has_position = position is not None and position.total_amount > 0
    log.info(f"��ǰ�Ƿ�ֲ� : {has_position}")

    # ���һ�ν���ʱ��
    transact_time = position.transact_time
    log.info(f"��ȡ�����ʱ�� : {transact_time}")

    # �õ��������гɽ���¼
    # {1753598792: UserTrade({'trade_id': 1753598792, 'order_id': 1753599023, 'time': datetime.datetime(2025, 3, 14, 9, 46), 'amount': 1000, 'price': 45.56})}
    trades = get_trades()
    log.info(f"��ȡ���гɽ���¼ : {trades}")

    for trade_id, trade in trades.items():
        time_variable = trade.time
        log.info(f"��ȡ���гɽ���¼ʱ�� : {time_variable}")

        # if time_variable.date() == context.current_date :
        #     log.info(f"�����н��ף� ����")
        #     return

        break

    if not has_position:  # û�гֲ�ʱѰ���������
        # ��ǰ�۸���ڹ�ȥ4�����̼���ߵ�ʱ����
        if current_price >= past_4_days_high:
            log.info(f"��ǰ�۸� {current_price} ���ڵ��ڹ�ȥ4�����̼���ߵ� {past_4_days_high}��׼������")
            signal = "BUY"

    else:  # �ֲ�ʱѰ����������

        # ���һ�ν���ʱ��
        transact_time = position.transact_time
        log.info(f"��ȡ�����ʱ�� : {transact_time}")
        # ���۸����߼�(���һ������㿪ʼ�����ʷ��λ��ߵ�)������ۻ���20%ʱ������ִ������
        high_hist_daily = get_price(
            context.security,
            start_date=transact_time,
            end_date=context.current_date,
            frequency='1d',
            fields=['open', 'close', 'low', 'high', 'volume', 'money'],
            skip_paused=True
        )
        # ��߼�
        high_hist_price = high_hist_daily['high'].max()

        # �ǵ�ǰ�ֲֳɱ�
        avg_cost = position.avg_cost
        log.info(f"��ǰ�ֲֳɱ� : {avg_cost}")

        # ֹӯ��λ��߼ۻ���ֹӯ���� ֹ���  ��ߵ� - (����ߵ�-�ɱ��ۣ�* 0.2 )
        stop_profit_price = high_hist_price - ((high_hist_price - avg_cost) * context.stop_profit_ratio)

        # ֹӯ�ж�
        if current_price <= stop_profit_price and high_hist_price/avg_cost > 1.05:
            log.info(f"����ֹӯ������ ��ߵ�λ��{high_hist_price} ,ֹӯ�㣺 {stop_profit_price} ,��ǰ��Ϊ�� {current_price} , ׼������")
            context.highest_price = current_price
            signal = "SELL"

        # ֹ���������۸��������۵�95%
        stop_loss_price = avg_cost * context.stop_loss_ratio

        # ֹ���ж�
        if current_price <= stop_loss_price:
            log.info(f"����ֹ�������� �ɱ��ۣ�{avg_cost} ,ֹ��㣺 {stop_loss_price} ,��ǰ��Ϊ�� {current_price} , ׼������")
            signal = "SELL"

    return signal


def execute_trade(context, signal, current_price, past_4_days_high):
    """
    4. ִ���������������
    """
    if signal == "BUY":
        # ȫ������
        # cash = context.portfolio.cash
        cash = 50000
        amount = int(cash * 0.98 / current_price / 100) * 100  # ȷ������������100��������
        qty = amount / 100

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

        log.info(
            f"���� {context.security}: {position.total_amount} �ɣ��۸�: {current_price}�������: {context.buy_price}����߼�: {context.highest_price}")

        signal = None
