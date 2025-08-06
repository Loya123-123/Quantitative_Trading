
import pandas as pd
from datetime import datetime

# ȫ�ֱ����洢����
_data_proxy = None

# ����ҽҩ  600276.XSHG
# ����ҽҩ  000963.XSHE

def initialize(context):
    # ���ò��Բ���
    set_params(context)

    context.current_date = context.current_dt.date()

    # ���ý���Ʒ��
    context.security = '600276.XSHG'
    # ���û�׼ ����XSHG  �XSHE
    set_benchmark('600276.XSHG')
    # ���ý�����ز���
    set_option('use_real_price', True)

    # ���ý��׳ɱ��ͻ���
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), 'stock')
    set_slippage(FixedSlippage(0.02))

    # ����ÿ�����еĺ���
    run_daily(before_trading_start, time='before_open')

    # ֱ��ע��ȫ�ֺ���
    run_daily(handle_data_wrapper, time='every_bar')


def set_params(context):
    # ����DKX����
    context.dk_period = 10  # DKX��������
    context.madk_period = 10  # MADKX��������
    context.buy_date = None  # ��¼��������




def before_trading_start(context):
    # ��ȡ��ǰ����
    context.current_date = context.current_dt.date()
    log.info(f"��ȡ��ǰ����: {context.current_date}")

    # ��ȡ��ʷ��K������ - �����㹻���������ڼ���DKX
    hist_daily = get_price(
        context.security,
        end_date=context.current_date,
        count=context.dk_period * 4,  # ������������ȷ��ָ�����׼ȷ
        frequency='1d',
        # fq='pre',
        fields=['open', 'high', 'low', 'close'],  # ��Ҫ�����ֶμ���DKX
        skip_paused=True
    )

    # ����DKX��MADKX
    hist_daily = calculate_dkx(hist_daily, context.madk_period)
    log.info("��ʷ��K������:")
    for index, row in hist_daily[['open', 'high', 'low', 'close', 'DKX', 'MADKX', 'DKX_prev', 'MADKX_prev']].iterrows():
        log.info(
            f"����   {index}, ���̼�:    {row['open']}, ��߼�:    {row['high']}, ��ͼ�:    {row['low']}, ���̼�: {row['close']}, DKX:    {row['DKX']}, MADKX:  {row['MADKX']},DKX_prev: {row['DKX_prev']} , MADKX_prev :  {row['MADKX_prev']}")

    # ��������
    context.hist_daily = hist_daily


# ����DKX��MADKXָ��
def calculate_dkx(df, madk_period):
    # ����DKX
    # MID = (3*CLOSE + OPEN + HIGH + LOW)/6
    df['MID'] = (3 * df['close'] +  df['open'] + df['high'] + df['low']) / 6
    # df['DKX'] = df.apply(lambda row: row['open'] if row.name.date() == context.current_date else (3 * row['close'] + 2 * row['open'] + row['high'] + row['low']) / 7, axis=1)
    # (20��MID+19������MID+18��2��ǰ��MID+17��3��ǰ��MID+16��4��ǰ��MID+15��5��ǰ��MID+14��6��ǰ��MID+13��7��ǰ��MID+12��8��ǰ��MID+11��9��ǰ��MIDʮ10��10��ǰ��MID+9��U��ǰ��MID+8��12��ǰ��MID+7��13��ǰ��M1D+6��14��ǰ��MID+5��15��ǰ��MID+4��16��ǰ��MID+3��17��ǰ��MID+2��18��ǰ��MID+20��ǰ��MID)��210
    df['DKX'] = (20 * df['MID'] + 19 * df['MID'].shift(1) + 18 * df['MID'].shift(2) + 17 * df['MID'].shift(3)
                 + 16 * df['MID'].shift(4) + 15 * df['MID'].shift(5) + 14 * df['MID'].shift(6) + 13 * df['MID'].shift(7)
                 + 12 * df['MID'].shift(8) + 11 * df['MID'].shift(9) + 10 * df['MID'].shift(10) + 9 * df['MID'].shift(11)
                 + 8 * df['MID'].shift(12) + 7 * df['MID'].shift(13) + 6 * df['MID'].shift(14) + 5 * df['MID'].shift(15)
                 + 4 * df['MID'].shift(16) + 3 * df['MID'].shift(17) + 2 * df['MID'].shift(18) + df['MID'].shift(19)) / 210
    # ����MADKX - MADKX��DKX��N�ռ��ƶ�ƽ��
    df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

    # ����DKX��MADKX��ǰһ��ֵ�������жϽ������
    df['DKX_prev'] = df['DKX'].shift(1)
    df['MADKX_prev'] = df['MADKX'].shift(1)

    return df


# ȫ�ֺ�����װ��
def handle_data_wrapper(context):
    global _data_proxy
    _data_proxy = get_current_data()
    handle_data(context, _data_proxy)


# ���׾��ߺ���
def handle_data(context, data):
    # ��ȡ���¼۸�
    security_data = data[context.security]

    # ��ȡ�۸�
    try:
        current_price = security_data.last_price
    except AttributeError:
        current_price = security_data.price
    except Exception as e:
        log.error(f"�޷���ȡ�۸�: {e}")
        return

    # ��ȡ��ʷ����
    hist_daily = context.hist_daily

    # ȷ�����㹻�����ݼ���ָ��
    if len(hist_daily) < context.dk_period * 3:
        return

    # ��ȡ���µ�DKX��MADKXֵ
    dkx_now = hist_daily['DKX'].iloc[-2]
    madkx_now = hist_daily['MADKX'].iloc[-2]
    dkx_prev = hist_daily['DKX_prev'].iloc[-2]
    madkx_prev = hist_daily['MADKX_prev'].iloc[-2]

    # ��ȡ��ǰ�ֲ�
    position = context.portfolio.positions.get(context.security)
    has_position = position is not None and position.amount > 0

    # ���ײ����߼�
    if not has_position:  # û�гֲ�ʱ��������
        # ��������������DKX��棬��DKX���ϴ�MADKX��
        if dkx_prev <= madkx_prev and dkx_now > madkx_now:
            # ������������ - ȫ������
            cash = context.portfolio.cash
            amount = int(cash * 0.98 / current_price / 100) * 100  # ȷ�����������100��������

            if amount > 0:
                # ִ������
                order(context.security, amount)
                context.buy_date = context.current_date
                log.info(
                    f"���� {context.security}: {amount} �ɣ��۸�: {current_price}��DKX: {dkx_now:.2f}��MADKX: {madkx_now:.2f}")
    else:  # �гֲ�ʱ��������
        # �������������յڶ��쿪ʼ������DKX���棬��DKX���´�MADKX��
        if context.buy_date and context.current_date > context.buy_date:
            if dkx_prev >= madkx_prev and dkx_now < madkx_now:
                # ִ������
                order_target_value(context.security, 0)
                log.info(
                    f"���� {context.security}: {position.amount} �ɣ��۸�: {current_price}��DKX: {dkx_now:.2f}��MADKX: {madkx_now:.2f}")
                context.buy_date = None
