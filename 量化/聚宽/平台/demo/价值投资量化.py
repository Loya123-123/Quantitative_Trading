# coding = udf-8
# /usr/bin/env python
# ��Ҫ�þۿ�������һ���������ײ��ԣ���Ҫ�����ײ���д�ɴ��룬���в����߼����£�
# �ò��Բ����վ�����Ϊָ�꣬����10�վ�������ͻ��20�վ���ʱ���룬ÿ��ȫ�����롣
# ������ڶ��쿪ʼ��������ӯ��״̬ʱ��һֱ���У�����10�վ�������ͻ��20�վ���ʱ��������������Ʊ����Ʒ��ѡ�����ҽҩ

# ���������Լ�ֵ/Ͷ��+�ɳ�������Ч������Ҫ��ǰ����ÿ����ҵ���������ɼ۳����������µĹ�˾��
# ��ʤ����ӯ����������ʤ����������ƣ����Կ�����Ч������ֲ��ܹ�����������ĭ���ܼ�ֳ��е��������⡣


# ����ҽҩ�������ײ���
from datetime import datetime
import logging
import pytz
import jqdata

# # ��ȡ��ǰ��UTCʱ��
# utc_now = datetime.now(pytz.utc)
# eastern = pytz.timezone('Asia/Shanghai')
# eastern_now = utc_now.astimezone(eastern)
# # ������־��¼
# log_filename = f'market_{eastern_now.strftime("%Y%m%d")}.log'
# # log_filename = f'/Users/jianzhong/ProjectCode/StartDT/PyCharm/�з/�����ĵ�/market_{eastern_now.strftime("%Y%m%d")}.log'
# logging.basicConfig(filename=log_filename, level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S %Z%z')
# logging.info("��ʼִ������Ͷ��������ݽű� ��ʼʱ�䣺  " + eastern_now.strftime("%Y-%m-%d %H:%M:%S"))


def initialize(context):
    # ���ò��Բ���
    set_params(context)
    # ���ý���Ʒ��Ϊ����ҽҩ(��Ʊ���룺600276.XSHG)
    set_universe(context)
    # ���û�׼����
    set_benchmark('600276.XSHG')
    # ���û���
    set_slippage(FixedSlippage(0))
    # ���ý���������
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    # ����ǰ����
    run_daily(before_trading_start, time='before_open')
    # ����ʱ����
    run_daily(market_open, time='open')
    # ���̺�����
    run_daily(after_trading_end, time='after_close')

    # �洢���׼�¼���ֵ�
    context.trade_records = {}


def set_params(context):
    # ���ö��ھ�������
    context.short_ma_days = 10
    # ���ó��ھ�������
    context.long_ma_days = 20
    # ������ֹ��


def set_universe(context):
    # ���ù�Ʊ��Ϊ����ҽҩ
    context.security = '600276.XSHG'


def before_trading_start(context):
    # ��ȡ��ǰ���й�Ʊ
    context.positions = context.portfolio.positions
    # ��ȡ��ʷ���ݣ���ȡ����ȷ���ܼ������
    hist_data = attribute_history(context.security,
                                  context.long_ma_days + 5,
                                  '1d',
                                  ['close'])
    # ������ھ���(10�վ���)
    context.short_ma = hist_data['close'][-context.short_ma_days:].mean()
    # ���㳤�ھ���(20�վ���)
    context.long_ma = hist_data['close'][-context.long_ma_days:].mean()
    # ����ǰһ��Ķ��ھ���
    context.last_short_ma = hist_data['close'][-(context.short_ma_days + 1):-1].mean()
    # ����ǰһ��ĳ��ھ���
    context.last_long_ma = hist_data['close'][-(context.long_ma_days + 1):-1].mean()
    # ��ȡ��ǰ�۸�
    context.current_price = hist_data['close'][-1]


def market_open(context):
    security = context.security
    # ���û�гֲ�
    if security not in context.positions:
        # ����10�վ���ͻ��20�վ���ʱ����
        if context.short_ma > context.long_ma and context.last_short_ma <= context.last_long_ma:
            # ȫ������
            order_value(security, context.portfolio.cash)
            # ��¼������Ϣ��context.trade_records
            position = context.positions[security]
            buy_price = position.avg_cost
            buy_date = context.current_dt.date()
            context.trade_records[security] = {
                'buy_price': buy_price,
                'buy_date': buy_date,
                'highest_price': buy_price
            }
            log.info(
                f"���� {security}���۸�{buy_price}����{context.portfolio.cash}��10�վ��ߣ�{context.short_ma}��20�վ��ߣ�{context.long_ma}")
    else:
        # ����гֲ֣���context.trade_records��ȡ�ֲ���Ϣ
        if security in context.trade_records:
            record = context.trade_records[security]
            buy_price = record['buy_price']
            buy_date = record['buy_date']
            current_price = context.current_price

            current_date = context.current_dt.date()

            # ������ڶ��쿪ʼ�ж���������
            if current_date > buy_date + datetime.timedelta(days=1):
                # ���㵱ǰӯ������
                profit_pct = (current_price - buy_price) / buy_price

                # ���³ֲֵ���߼۸�
                record['highest_price'] = max(record['highest_price'], current_price)

                # ����10�վ�������ͻ��20�վ���ʱ����������
                if context.short_ma < context.long_ma and context.last_short_ma >= context.last_long_ma:
                    # ֹӯ/ֹ������
                    order_target_value(security, 0)
                    # �������trade_records��ɾ����¼
                    if security in context.trade_records:
                        del context.trade_records[security]
                    log.info(
                        f"������������ {security}���۸�{current_price}��ӯ��������{profit_pct:.2%}��10�վ��ߣ�{context.short_ma}��20�վ��ߣ�{context.long_ma}")


def after_trading_end(context):
    # �����ǰ�ֲ����
    if context.security in context.positions:
        position = context.positions[context.security]
    log.info(
        f"��ǰ���� {context.security}��������{position.amount}���ɱ��ۣ�{position.avg_cost}����ǰ�ۣ�{context.current_price}��10�վ��ߣ�{context.short_ma}��20�վ��ߣ�{context.long_ma}")
    # ������׼�¼���
    log.info(f"���׼�¼: {context.trade_records}")
