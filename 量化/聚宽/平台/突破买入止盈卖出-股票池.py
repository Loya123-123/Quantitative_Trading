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
����ͷ�磺��ֻ��������20000���������������

���룺���ռ۸���ڹ�ȥ4�����̼���ߵ�ʱ������ǰ�۸�ͻ��5�ոߵ㣬��������ִ������
ֹӯ����1������ڶ��쿪ʼ������߼�/�����>1.2ʱ���Ҽ۸�<��߼�-����߼�-����ۣ�*20%ʱ������ִ������
ֹӯ����2������ڶ��쿪ʼ�����۸�<ǰһ����ͼۣ��Ҽ۸�<��߼�-����߼�-����ۣ�*30%ʱ������ִ������
ֹ������������ڶ��쿪ʼ����������۵�95%����ִ������


����k��dkx>masksʱ���Ž������룬��k��dkx<masksʱ����������
���룺����k��dkx>masksʱ ,���ռ۸���ڹ�ȥ10�����̼���ߵ�ʱ������ǰ�۸�ͻ��10�ոߵ㣬��������ִ������
ֹӯ����1������ڶ��쿪ʼ�����۸�<ǰ4�����̼�ʱ���Ҽ۸�<��߼�-����߼�-����ۣ�*20%ʱ������ִ������
ֹӯ����2������ڶ��쿪ʼ�����۸�<ǰһ����ͼۣ��Ҽ۸�<��߼�-����߼�-����ۣ�*50%ʱ������ִ������
ֹ������������ڶ��쿪ʼ����������۵�95%����ִ������
"""

# ȫ�ֱ����洢����
_data_proxy = None


# log.set_level('order', 'error')

def initialize(context):
    # ���ò���
    set_params(context)

    # g.stocks = ['600276.XSHG','000963.XSHE','000858.XSHE','600809.XSHG','000568.XSHE']
    g.stocks = ['600276.XSHG']

    # ���û�׼ ����XSHG �XSHE
    set_benchmark('600276.XSHG')

    context.highest_price = 0

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
    # ֹӯ1����
    context.stop_profit_ratio1 = 0.2
    # ֹӯ2����
    context.stop_profit_ratio2 = 0.5
    # ֹ�����
    context.stop_loss_ratio = 0.95
    # ֹӯ�Ƿ�����
    context.stop_profit_ratio_change = 1.2
    # MADKX��DKX��N�ռ��ƶ�ƽ��
    context.madk_period = 10


def handle_data_wrapper(context):
    for security in g.stocks:
        # ���ý���Ʒ��
        context.security = security
        # ��ȡ�����Ʊ����
        data_df = get_data(context)

        # �ж��Ƿ�Ӧ�ý���
        signal = should_trade(context, data_df)

        # ִ�н���
        if signal:
            execute_trade(context, signal, data_df)


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

    # ��ȡ��ʷ���� - ��Ҫ�㹻������������5�ոߵ�
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=365,  # ��ȥ4������ + ��������
        frequency='1d',
        fields=['open', 'close', 'low', 'high', 'volume', 'money'],
        skip_paused=True
    )
    ticks_df = get_ticks(context.security,
                         end_dt=context.current_time,
                         count=1,
                         fields=['time', 'current', 'high', 'low', 'volume', 'money'], skip=True, df=True)

    # log.info(f"��Ʊ���룺 {context.security} �� ��ȡ��ʷ���ݣ�\n {hist_daily}")

    # ��ȡ���һ�������
    last_day_index = hist_daily.index[-1]

    hist_daily.loc[last_day_index, 'close'] = ticks_df['current'].iloc[-1]
    hist_daily.loc[last_day_index, 'low'] = ticks_df['low'].iloc[-1]
    hist_daily.loc[last_day_index, 'high'] = ticks_df['high'].iloc[-1]

    weekly_df = hist_daily.resample('W').agg({
        'open': 'first',  # �ܿ��̼� = ��һ�Ŀ��̼�
        'high': 'max',  # ����߼� = һ���ڵ���߼�
        'low': 'min',  # ����ͼ� = һ���ڵ���ͼ�
        'close': 'last',  # �����̼� = ��������̼�
    })
    # log.info(f"��K���ݣ�\n {weekly_df}")


    # ɾ������NaN��
    weekly_df = weekly_df.dropna()

    weekly_dkx_df = calculate_dkx(weekly_df, context.madk_period)

    # ��ȡ���µ�DKX��MADKXֵ
    dkx_now = weekly_dkx_df['DKX'].iloc[-1]
    madkx_now = weekly_dkx_df['MADKX'].iloc[-1]
    dkx_prev = weekly_dkx_df['DKX_prev'].iloc[-1]
    madkx_prev = weekly_dkx_df['MADKX_prev'].iloc[-1]

    # ��ȡǰ4�����̼���ߵ�
    past_4_days_close_max = hist_daily['close'].iloc[-5:-1].max()
    # ��ȡǰ4�����̼���͵�
    past_4_days_close_min = hist_daily['close'].iloc[-5:-1].min()
    # ��ȡ5�յ͵�
    past_4_days_low_min = hist_daily['low'].iloc[-5:-1].min()
    # ��ȡ10��������ߵ�
    past_10_days_high = hist_daily['close'].iloc[-11:-1].max()
    # log.info(f"��ȡ����������Сֵ���ݣ�\n {past_4_days_low_min}")

    # ǰһ����ͼ�
    past_yest_days_low = hist_daily['low'].iloc[-2]

    # log.info(f"ǰһ����ͼ� : {past_yest_days_low}")

    # log.info(f"��ȡ��ǰ���ݣ�\n {ticks_df}")

    # ��ȡ���¼۸�
    security_data = _data_proxy[context.security]

    # ��ȡ�۸�
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"�޷���ȡ�۸�: {e}")

    # log.info(f"��Ʊ���룺 {context.security} ����ȡ���¼۸�\n {current_price}")

    # ��������Ƿ���Ч
    if current_price is None or past_4_days_close_max is None:
        return

    data_df = pd.DataFrame({
        'current_time': [context.current_time]  # ��ǰʱ��
        , 'past_4_days_close_max': [past_4_days_close_max]  # ǰ������߼�
        , 'past_4_days_close_min': [past_4_days_close_min]  # ǰ������ͼ�
        , 'past_4_days_low_min': [past_4_days_low_min]  # ǰ������ͼ�
        , 'past_10_days_high': [past_10_days_high] # ǰʮ�����̼���߼�
        , 'current_price': [ticks_df['current'].iloc[-1]]  # ��ǰ�۸�ticks_df��current�е����һ��ֵ��
        , 'current_high': [ticks_df['high'].iloc[-1]]
        , 'past_yest_days_low': [past_yest_days_low]
        , 'dkx_now': [dkx_now]
        , 'madkx_now': [madkx_now]
        , 'dkx_prev': [dkx_prev]
        , 'madkx_prev': [madkx_prev]
    })

    # log.info(f"��Ʊ���룺 {context.security} \n ; ��ȡ�������ݣ�\n {data_df}")

    return data_df


def calculate_dkx(df, madk_period):
    # ����DKX
    # MID = (3*CLOSE + OPEN + HIGH + LOW)/6
    df['MID'] = (3 * df['close'] + df['open'] + df['high'] + df['low']) / 6
    # df['DKX'] = df.apply(lambda row: row['open'] if row.name.date() == context.current_date else (3 * row['close'] + 2 * row['open'] + row['high'] + row['low']) / 7, axis=1)
    # (20��MID+19������MID+18��2��ǰ��MID+17��3��ǰ��MID+16��4��ǰ��MID+15��5��ǰ��MID+14��6��ǰ��MID+13��7��ǰ��MID+12��8��ǰ��MID+11��9��ǰ��MIDʮ10��10��ǰ��MID+9��U��ǰ��MID+8��12��ǰ��MID+7��13��ǰ��M1D+6��14��ǰ��MID+5��15��ǰ��MID+4��16��ǰ��MID+3��17��ǰ��MID+2��18��ǰ��MID+20��ǰ��MID)��210
    df['DKX'] = (20 * df['MID'] + 19 * df['MID'].shift(1) + 18 * df['MID'].shift(2) + 17 * df['MID'].shift(3)
                 + 16 * df['MID'].shift(4) + 15 * df['MID'].shift(5) + 14 * df['MID'].shift(6) + 13 * df['MID'].shift(7)
                 + 12 * df['MID'].shift(8) + 11 * df['MID'].shift(9) + 10 * df['MID'].shift(10) + 9 * df['MID'].shift(
                11)
                 + 8 * df['MID'].shift(12) + 7 * df['MID'].shift(13) + 6 * df['MID'].shift(14) + 5 * df['MID'].shift(15)
                 + 4 * df['MID'].shift(16) + 3 * df['MID'].shift(17) + 2 * df['MID'].shift(18) + df['MID'].shift(
                19)) / 210
    # ����MADKX - MADKX��DKX��N�ռ��ƶ�ƽ��
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # ����DKX��MADKX��ǰһ��ֵ�������жϽ������
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df


def should_trade(context, data_df):
    """
    3. ���ڲ���Ҫ���жϵ�ǰ���������뻹������
    """
    # �����ź�
    signal = None

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_close_max = data_df['past_4_days_close_max'].iloc[-1]
    past_4_days_close_min = data_df['past_4_days_close_min'].iloc[-1]
    current_high = data_df['current_high'].iloc[-1]
    past_yest_days_low = data_df['past_yest_days_low'].iloc[-1]
    past_10_days_high = data_df['past_10_days_high'].iloc[-1]
    dkx_now = data_df['dkx_now'].iloc[-1]
    madkx_now = data_df['madkx_now'].iloc[-1]


    # ��ȡ��ǰ�ֲ�
    position = context.portfolio.positions.get(context.security)
    # log.info(f"��Ʊ���룺 {context.security} ; ��ȡ��ǰ�ֲ� : {position}")

    # ��ȡ�Ƿ�ǰ�ֲ�
    has_position = position is not None and position.total_amount > 0
    # log.info(f"��Ʊ���룺 {context.security} ; ��ǰ�Ƿ�ֲ� : {has_position}")

    # �õ��������гɽ���¼
    # {1753598792: UserTrade({'trade_id': 1753598792, 'order_id': 1753599023, 'time': datetime.datetime(2025, 3, 14, 9, 46), 'amount': 1000, 'price': 45.56})}
    # trades = get_trades()
    # log.info(f"��Ʊ���룺 {context.security} ; ��ȡ���гɽ���¼ : {trades}")
    # for trade_id, trade in trades.items():
    #     time_variable = trade.time
    # log.info(f"��Ʊ���룺 {context.security} ; ��ȡ���гɽ���¼ʱ�� : {time_variable}")
    # if time_variable.date() == context.current_date :
    #     log.info(f"�����н��ף� ����")
    #     return

    # ���һ�ν���ʱ��
    transact_time = position.transact_time
    # log.info(f"��Ʊ���룺 {context.security} ; ��ȡ�����ʱ�� : {transact_time}")

    if not has_position:  # û�гֲ�ʱѰ���������
        # # ����k��dkx>masksʱ ,���ռ۸���ڹ�ȥ10�����̼���ߵ�
        # if current_price >= past_10_days_high and dkx_now >= madkx_now:
        # ���ռ۸���ڹ�ȥ10�����̼���ߵ�
        if current_price >= past_10_days_high :
            log_info = f"��ǰ���ڣ� {context.current_date} ; ��Ʊ���룺 {context.security} ; ��ǰ�۸� {current_price} ; 10�����̼���ߵ� {past_10_days_high} , ����DKX�� {dkx_now}����MADKX�� {madkx_now} ��׼������ \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)
            signal = "BUY"

    elif not transact_time.date() == context.current_date:  # �ֲ�ʱѰ���������� ���������룬�Ͳ���������

        # ���۸����߼�(���һ������㿪ʼ�����ʷ��λ��ߵ�)������ۻ���20%ʱ������ִ������
        high_hist_daily = get_price(
            context.security,
            start_date=transact_time,
            end_date=context.current_date,
            frequency='1d',
            fields=['open', 'close', 'low', 'high', 'volume', 'money'],
            skip_paused=True
        )
        # ��ʷ��߼�
        high_hist_price_tmp = high_hist_daily['high'].iloc[:-1].max()
        # ��ʷ��߼� �� ������߼۱Ƚ�
        high_hist_price = high_hist_price_tmp if high_hist_price_tmp > current_high else current_high

        context.highest_price = high_hist_price

        # �ǵ�ǰ�ֲֳɱ�
        avg_cost = position.avg_cost
        # log.info(f"��Ʊ���룺 {context.security} ; ��ǰ�ֲֳɱ� : {avg_cost}")

        # ֹӯ��1λ��߼ۻ���ֹӯ����   ��ߵ� - (����ߵ�-�ɱ��ۣ�* 0.2 )
        stop_profit_price1 = high_hist_price - ((high_hist_price - avg_cost) * context.stop_profit_ratio1)

        # ֹӯ��2λ��߼ۻ���ֹӯ����   ��ߵ� - (����ߵ�-�ɱ��ۣ�* 0.3 )
        stop_profit_price2 = high_hist_price - ((high_hist_price - avg_cost) * context.stop_profit_ratio2)

        # ֹӯ����1�� ֹ����ڶ��쿪ʼ�����۸�<��С��ǰ4�����̼�ʱ���Ҽ۸�<��߼�-����߼�-����ۣ�*20%������ִ������
        if current_price <= past_4_days_close_min and current_price <= stop_profit_price1:
            log_info = f"��ǰ���ڣ� {context.current_date} ; ��Ʊ���룺 {context.security} ; ����ֹӯ����1�� ǰ4�����̼���͵�λ��{past_4_days_close_min} ,ֹӯ�㣺 {stop_profit_price1} ,��ǰ��Ϊ�� {current_price} , ׼������ \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)
            signal = "SELL"

        # # ֹӯ����2������ڶ��쿪ʼ�����۸�<ǰһ����ͼۣ��Ҽ۸�<��߼�-����߼�-�ɱ��ۣ�*50%ʱ������ִ������
        # if current_price <= past_yest_days_low and current_price <= stop_profit_price2:
        #     log_info = f"��ǰ���ڣ� {context.current_date} ; ��Ʊ���룺 {context.security} ; ����ֹӯ����2�� ��ߵ�λ��{high_hist_price} ,�ɱ��ۣ�{avg_cost} ,ֹӯ��: {stop_profit_price2} ,��ǰ��Ϊ�� {current_price},������ͼۣ�{past_yest_days_low}  , ׼������ \n "
        #     log.info(log_info)
        #     write_file('log.txt', str((log_info)), append=True)
        #     signal = "SELL"

        # ֹ���������۸��������۵�95%
        stop_loss_price = avg_cost * context.stop_loss_ratio

        # ֹ���ж� ����ڶ��쿪ʼ����������۵�95%����ִ������
        if current_price <= stop_loss_price:
            log_info = f"��ǰ���ڣ� {context.current_date} ; ��Ʊ���룺 {context.security} ; ����ֹ�������� �ɱ��ۣ�{avg_cost} ,ֹ��㣺 {stop_loss_price} ,��ǰ��Ϊ�� {current_price} , ׼������ \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)

            signal = "SELL"

    return signal


def execute_trade(context, signal, data_df):
    """
    4. ִ���������������
    """

    current_price = data_df['current_price'].iloc[-1]
    past_4_days_close_max = data_df['past_4_days_close_max'].iloc[-1]

    if signal == "BUY":
        # ȫ������
        # cash = context.portfolio.cash
        cash = 20000
        amount = int(cash * 0.98 / current_price / 100) * 100  # ȷ������������100��������
        # ��
        qty = amount / 100
        # �����ܼ�
        total_amount = current_price * amount

        if amount > 0:
            # ִ������
            order(context.security, amount)
            log_info = f"��ǰ���ڣ� {context.current_date} ;  ���� {context.security} ; {qty} �֣�����: {amount} , �����ܼ� {total_amount}, ����� {current_price}����ȥ4��������̼�: {past_4_days_close_max} \n "
            log.info(log_info)
            write_file('log.txt', str((log_info)), append=True)

            signal = None

    elif signal == "SELL":
        # ִ������
        position = context.portfolio.positions.get(context.security)

        order_target_value(context.security, 0)

        log_info = f"��ǰ���ڣ� {context.current_date} ; ���� {context.security};  {position.total_amount} �ɣ��۸�: {current_price} ����߼�: {context.highest_price} \n "
        log.info(log_info)
        write_file('log.txt', str((log_info)), append=True)
        signal = None
