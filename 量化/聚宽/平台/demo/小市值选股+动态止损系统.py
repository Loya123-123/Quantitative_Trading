#### ��¡�Ծۿ����£�https://www.joinquant.com/post/58646
#### ���⣺ʵ��ǰ��debug�����淭��(ʮ��ز��ǧ��)
#### ���ߣ���������

#### ��¡�Ծۿ����£�https://www.joinquant.com/post/58633
#### ���⣺׼��ʵ�̣���æ�����Ƿ���ԣ�
#### ���ߣ�ͩ��

# -*- coding: utf-8 -*-
"""
�������ײ��ԣ�С��ֵѡ��+��ֹ̬��ϵͳ
�����߼���
1. ÿ�´���С��ָɸѡ��ֵ5-300�ڵĹ�Ʊ��
2. ÿ�ܵ��ֳ�����ֵ��С��4ֻ��Ʊ
3. ʵʩ���ֹ����ԣ�����ֹ��+����ֹ��
4. ���⴦����ͣ���Ʊ
5. ÿ��1�º�4�¿ղ�
"""

# �ۿ�ƽ̨API
from jqdata import *
# ���ӷ���ģ�飨δʵ��ʹ�õ�������
from jqfactor import *
import numpy as np
import pandas as pd
from datetime import time, timedelta

# ========== ȫ�ֲ������� ==========
BENCHMARK = '000001.XSHG'  # ��ָ֤����Ϊ��׼
MARKET_INDEX = '399101.XSHE'  # ��С��ָ��Ϊѡ�ɷ�Χ
EMPTY_MONTHS = [1, 4]  # 1�º�4�¿ղ�
CASH_ETF = '511880.XSHG'  # ����ETF���ڿղ�ʱ�ֽ����

# ֹ��������ͳ���
STOPLOSS_SINGLE = 1   # ������ֹ��
STOPLOSS_MARKET = 2   # ������ֹ��
STOPLOSS_COMBINED = 3 # ����ֹ����ԣ�Ĭ�ϣ�


def initialize(context):
    """���Գ�ʼ���������ɾۿ����Զ�����"""
    # ��ֹδ������
    set_option('avoid_future_data', True)
    # ���û�׼������
    set_benchmark(BENCHMARK)
    # ʹ����ʵ�۸�ز�
    set_option('use_real_price', True)
    # ���û��㣨����0.3%��
    set_slippage(FixedSlippage(3/1000))
    # ���ý��׳ɱ�����Ʊ��2.5������ӡ��˰0.1%��
    set_order_cost(
        OrderCost(
            open_tax=0,                # ����ӡ��˰
            close_tax=0.001,           # ����ӡ��˰
            open_commission=2.5/10000, # ����Ӷ��
            close_commission=2.5/10000,# ����Ӷ��
            close_today_commission=0,  # ƽ��Ӷ�𣨹�Ʊ�ޣ�
            min_commission=5           # ���Ӷ��
        ),
        type='stock'
    )

    # ������־����
    log.set_level('order', 'error')   # ������־ֻ����
    log.set_level('system', 'error')  # ϵͳ��־ֻ����
    log.set_level('strategy', 'debug') # ������־��ʾdebug��Ϣ

    # ========== ��ʼ��ȫ�ֱ��� ==========
    g.trading_signal = True       # �����Ƿ�ɽ���
    g.run_stoploss = True         # �Ƿ�����ֹ���߼�
    g.hold_list = []              # ��ǰ�ֲֹ�Ʊ�б�
    g.yesterday_HL_list = []      # ������ͣ��Ʊ�б�
    g.target_list = []            # ����Ŀ���Ʊ��
    g.pass_months = EMPTY_MONTHS  # �ղ��·�����
    g.limitup_stocks = []         # ������ͣ��Ʊ�б�
    g.target_stock_count = 4      # Ŀ��ֲ�����
    g.sell_reason = ''            # ����ԭ���¼��������־��
    g.stoploss_strategy = STOPLOSS_COMBINED  # ʹ�ø���ֹ�����
    g.stoploss_limit = 0.06       # ����ֹ����ֵ6%
    g.stoploss_market = 0.05      # ����ֹ����ֵ5%
    g.etf = CASH_ETF              # �ֽ����ETF����

    # ��ʼִ��ѡ��
    filter_monthly(context)
    # ========== ��ʱ�������� ==========
    run_monthly(filter_monthly, 1, '9:00')      # ÿ��1��9��ѡ��
    run_daily(prepare_stock_list, '9:05')       # ÿ�տ���ǰ׼��
    run_daily(trade_afternoon, '14:00')         # ���罻��ʱ��
    run_daily(sell_stocks, '10:00')             # ����ִ��ֹ��
    run_daily(close_account, '14:50')           # ����ǰ�����λ
    run_weekly(weekly_adjustment, 2, '10:00')   # ÿ�ܶ�����

def prepare_stock_list(context):
    """ÿ�տ���ǰ׼������"""
    # ��ȡ��ǰ�ֲ��б�
    g.hold_list = [pos.security for pos in context.portfolio.positions.values()]
    g.limitup_stocks = []  # ���õ�����ͣ�б�

    if g.hold_list:
        # ��ȡ�ֲֹ��������̼ۺ���ͣ��
        price_df = get_price(
            g.hold_list,
            end_date=context.previous_date,  # ʹ��ǰһ������
            frequency='daily',
            fields=['close', 'high_limit'], # ��Ҫ���̼ۺ���ͣ��
            count=1,
            panel=False,
            fill_paused=False
        )
        # ɸѡ�������̼۵�����ͣ�۵Ĺ�Ʊ
        g.yesterday_HL_list = price_df[price_df['close'] == price_df['high_limit']]['code'].tolist()
    else:
        g.yesterday_HL_list = []

    # ��鵱���Ƿ�ɽ��ף��ǿղ��·ݣ�
    g.trading_signal = today_is_tradable(context)

def filter_monthly(context):
    """�¶�ѡ�ɣ�����С��ָɸѡС��ֵ��Ʊ"""
    # ������ѯ��ѡ����С��ָ�ɷֹɣ���ֵ5-300�ڣ�����ֵ��������
    q = query(
        valuation.code,
    ).filter(
        valuation.code.in_(get_index_stocks(MARKET_INDEX)),
        valuation.market_cap.between(5, 300)  # ��ֵ��λ����Ԫ
    ).order_by(
        valuation.market_cap.asc()  # С��ֵ����
    )
    # ��ȡ����������
    fund_df = get_fundamentals(q)
    # ȡ��ֵ��С��N*20ֻ��Ʊ��NΪĿ��ֲ�����
    g.month_scope = fund_df['code'].head(g.target_stock_count * 20).tolist()

def get_stock_list(context):
    """���¶ȹ�Ʊ��ɸѡ���պ�ѡ��Ʊ"""
    # �Ƚ��л������ˣ��޳�ST���¹ɵȣ�
    filtered_stocks = filter_stocks(context, g.month_scope)

    # �ٴβ�ѯ��ֵ����
    q = query(
        valuation.code,
        valuation.market_cap
    ).filter(
        valuation.code.in_(filtered_stocks),
        valuation.market_cap.between(5, 300)
    ).order_by(
        valuation.market_cap.asc()  # ��Ȼ����ֵ����
    )
    fund_df = get_fundamentals(q)
    # ȡ��ֵ��С��N*3ֻ��Ϊ��ѡ��NΪĿ��ֲ�����
    candidate_stocks = fund_df['code'].head(g.target_stock_count * 3).tolist()
    return candidate_stocks

def weekly_adjustment(context):
    """ÿ�ܵ����߼�"""
    if not g.trading_signal:
        # �ղ��·�ֱ���������ETF
        buy_security(context, [g.etf])
        log.info(f"�ղ��·�({g.pass_months})������{g.etf}")
        return

    # ��ȡ����Ŀ���Ʊ��
    g.target_list = get_stock_list(context)
    log.info(f"����Ŀ��ֲ֣�{g.target_list}")

    # ���������б���ͬʱ����������������
    # 1. ���ڱ���Ŀ��ǰN��
    # 2. ����δ��ͣ��������ͣ�ɶ�����л��ᣩ
    # 3. δͣ��
    current_data = get_current_data()
    sell_list = [
        stock for stock in g.hold_list
        if stock not in g.target_list[:g.target_stock_count] and
           stock not in g.yesterday_HL_list and
           not current_data[stock].paused
    ]

    # ִ������
    for stock in sell_list:
        close_position(context.portfolio.positions[stock])
    log.info(f"����������{sell_list}")
    log.info(f"�������У�{[s for s in g.hold_list if s not in sell_list]}")

    # ������Ҫ���������
    to_buy_num = g.target_stock_count - len(context.portfolio.positions)
    # ���������б���ͬʱ����������������
    # 1. ��Ŀ�����
    # 2. ��ǰδ����
    # 3. ����δ��ͣ������׷�ߣ�
    to_buy = [x for x in g.target_list
              if x not in context.portfolio.positions.keys() and
              x not in g.yesterday_HL_list][:to_buy_num]
    buy_security(context, to_buy)

def check_limit_up(context):
    """���������ͣ�ɽ����Ƿ񿪰�"""
    if not g.yesterday_HL_list:
        return

    current_data = get_current_data()
    for stock in g.yesterday_HL_list:
        current_close = current_data[stock].last_price
        high_limit = current_data[stock].high_limit

        if current_close < high_limit:
            # �����ͣ��������
            close_position(context.portfolio.positions[stock])
            g.sell_reason = 'limitup'  # ��¼����ԭ��
            g.limitup_stocks.append(stock)  # ���뵱����ͣ�б�
            log.info(f"{stock}��ͣ�򿪣�ִ������")
        else:
            log.info(f"{stock}ά����ͣ����������")

def check_remain_amount(context):
    """������ʣ���ʽ���"""
    if not g.sell_reason:  # ����������ֱ�ӷ���
        return

    g.hold_list = [pos.security for pos in context.portfolio.positions.values()]
    cash = context.portfolio.cash

    if g.sell_reason == 'limitup':
        # ��ͣ��������ʽ���Ͷ��
        need_buy_count = g.target_stock_count - len(g.hold_list)
        if need_buy_count > 0:
            # ��Ŀ����ų�����ͣ��Ʊ
            candidates = [s for s in g.target_list
                          if s not in g.limitup_stocks and
                          s not in g.hold_list]
            buy_list = candidates[:need_buy_count]
            log.info(f"��ͣ������ʣ���ʽ�{cash:.2f}Ԫ�����֣�{buy_list}")
            buy_security(context, buy_list)
    elif g.sell_reason == 'stoploss':
        # ֹ���ת����ETF
        log.info(f"ֹ���ʣ���ʽ�{cash:.2f}Ԫ������{g.etf}")
        buy_security(context, [g.etf])

    g.sell_reason = ''  # ��������ԭ��

def trade_afternoon(context):
    """���罻��ʱ�β���"""
    if g.trading_signal:
        check_limit_up(context)   # �����ͣ��
        check_remain_amount(context)  # ����ʣ���ʽ�

def sell_stocks(context):
    """ִ��ֹ�����"""
    if not g.run_stoploss:  # ֹ�𿪹ؼ��
        return

    positions = context.portfolio.positions
    if not positions:  # �޳ֲ�ֱ�ӷ���
        return

    current_data = get_current_data()

    # ����ֹ���߼������ϲ��Ի򵥶����ԣ�
    if g.stoploss_strategy in (STOPLOSS_SINGLE, STOPLOSS_COMBINED):
        for stock, pos in positions.items():
            current_price = pos.price
            avg_cost = pos.avg_cost
            if current_data[stock].paused: continue  # ����ͣ�ƹ�

            # ֹӯ�߼��������ʡ�100%��
            if current_price >= avg_cost * 2:
                order_target_value(stock, 0)
                log.debug(f"{stock}����100%��ִ��ֹӯ")
            # ֹ���߼����������ֵ��
            elif current_price < avg_cost * (1 - g.stoploss_limit):
                order_target_value(stock, 0)
                log.debug(f"{stock}������{int(g.stoploss_limit*100)}%��ִ��ֹ��")
                g.sell_reason = 'stoploss'  # ��¼ֹ��ԭ��

    # ����ֹ���߼������ϲ��Ի򵥶����ԣ�
    if g.stoploss_strategy in (STOPLOSS_MARKET, STOPLOSS_COMBINED):
        # ��ȡ��С��ָ�����ǵ���
        index_price = get_price(
            MARKET_INDEX,
            end_date=context.previous_date,
            frequency='daily',
            fields=['open', 'close'],
            count=1
        )
        if not index_price.empty:
            # ���������ǵ���������/����-1��
            market_down_ratio = (index_price['close'].iloc[0] / index_price['open'].iloc[0]) - 1
            if abs(market_down_ratio) >= g.stoploss_market:
                # �����������ǵ�������g.stoploss_market, ������з�ETF�ֲ�
                for stock in positions.keys():
                    if stock == g.etf: continue
                    order_target_value(stock, 0)
                g.sell_reason = 'stoploss'
                log.debug(f"�г�ƽ������{market_down_ratio:.2%}��ִ��ֹ��")

def filter_stocks(context, stock_list):
    """��Ʊ���������޳������������Ĺ�Ʊ"""
    if not stock_list:
        return []

    current_data = get_current_data()
    # ��ȡǰһ�������̼ۣ������ж��ǵ�ͣ��
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    filtered = []

    for stock in stock_list:
        data = current_data[stock]
        # ������������
        if data.paused: continue                   # �޳�ͣ�ƹ�
        if data.is_st or '��' in data.name:       # �޳�ST/*ST/���й�
            continue
        if stock.startswith(('30', '68', '8', '4')): # �޳���ҵ��/�ƴ����
            continue
            # �ǵ�ͣ���ˣ��ѳֲֹɲ����ޣ�
        if stock not in g.hold_list and last_prices[stock].iloc[-1] >= data.high_limit:
            continue  # �޳���ͣ��
        if stock not in g.hold_list and last_prices[stock].iloc[-1] <= data.low_limit:
            continue  # �޳���ͣ��
        # ���¹ɹ��ˣ����в���375�죩
        listing_date = get_security_info(stock).start_date
        if (context.previous_date - listing_date).days < 375:
            continue

        filtered.append(stock)
    return filtered

# ========== �����ǹ��ߺ��� ==========
def order_target_value_(security, value):
    """����־���µ�����"""
    if value == 0:
        log.debug(f"��� {security}")
    else:
        log.debug(f"�µ� {security}��Ŀ����ֵ {value:.2f} Ԫ")
    return order_target_value(security, value)

def open_position(security, value):
    """���ֲ���"""
    order = order_target_value_(security, value)
    return order is not None and order.filled > 0  # �����Ƿ�ɽ�

def close_position(position):
    """ƽ�ֲ���"""
    security = position.security
    order = order_target_value_(security, 0)
    if order:
        return order.status == OrderStatus.held and order.filled == order.amount
    return False

def buy_security(context, target_list):
    """���Ƚ�������Ʊ"""
    current_hold = [pos.security for pos in context.portfolio.positions.values()]
    need_buy = [stock for stock in target_list if stock not in current_hold]
    if not need_buy:
        return

    buy_count = len(need_buy)
    cash = context.portfolio.cash
    if cash <= 0 or buy_count <= 0:
        return

    # �ȷ��ֽ�����
    per_stock_value = cash / buy_count

    for stock in need_buy:
        if open_position(stock, per_stock_value):
            log.info(f"���� {stock}����� {per_stock_value:.2f} Ԫ")
            # �ﵽĿ��ֲ�����ֹͣ
            if len(context.portfolio.positions) == g.target_stock_count:
                break

def today_is_tradable(context):
    """��鵱���Ƿ����գ��ǿղ��·ݣ�"""
    return context.current_dt.month not in g.pass_months

def close_account(context):
    """����ǰ�����λ���ղ��·�ר�ã�"""
    if not g.trading_signal:
        current_data = get_current_data()
        current_hold = [pos.security for pos in context.portfolio.positions.values()]
        for stock in current_hold:
            if current_data[stock].paused: continue  # ����ͣ�ƹ�
            if stock == g.etf: continue              # ��������ETF
            close_position(context.portfolio.positions[stock])
            log.info(f"�ղ��·���֣�{stock}")