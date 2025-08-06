# coding:gbk
"""
���꽻�ײ����ڻ���
���ڹ���QMTƽ̨ʵ�ֵĺ��꽻�ײ���

�ò��Ծ��������Ĺ�����ϵ��������
����QMT ��������
����Ƶ�ʣ�����
����Ʒ�֣� �ڻ� ���������������һ�������� ��Ҫ�������е��ڻ�Ʒ�֣�ɸѡ�ܵĺõ�Ʒ�ֺ��˹�ѡ�����ص�ѡ��
��ǰ�����ָ�꣺ǰ10��ATRƽ��ֵ������¼����
����1�����ࣩ�����ռ۸�>ǰ10�����̼���ߵ�ʱ������ǰ�۸�ͻ��ǰ10�ոߵ㣬��������ִ������
ֹӯ����1������ڶ��쿪ʼ�����۸�<ǰ4�����̼���ߵ�ʱ���Ҽ۸�< ��߼�-����߼�-����ۣ�*20% ����߼���ָ����󵽼���ʱ����߼ۣ�ʱ������ִ��������
ֹ������1������ڶ��쿪ʼ�����۸� < �����-2*ATRʱ������ִ������

����2�����գ������ռ۸�<ǰ10�����̼���͵�ʱ������ǰ�۸�ͻ��10�յ͵㣬��������ִ������
ֹӯ����2������ڶ��쿪ʼ�����۸�>ǰ4�����̼���͵�ʱ���Ҽ۸�>��ͼ�+�������-��ͼۣ�*20% ����ͼ���ָ����󵽼���ʱ����ͼۣ�ʱ������ִ������
ֹ������2������ڶ��쿪ʼ�����۸�>�����+2*ATRʱ������ִ������

����ͷ�磺�ʽ���=100000����ֻƷ�ֵ���������10000��������������򣬼�ÿ��Ʒ�����20000������/���ո�10000
�Ӳֹ��������������������ٽ��мӲ֣���������һ�ʣ���Ӱ�����յĿ�������֮����һ�ʣ�Ҳ��Ӱ�����࿪��
"""

import numpy as np


def init(ContextInfo):
    """
    ��ʼ������
    ���ò��Բ��������ױ�ĵ�
    """
    print("��ʼ��ʼ�����꽻�ײ���...")

    # ���ý��ױ�ģ������Ƹ��ڻ�Ϊ����ʵ��ʹ��ʱ�������Ҫ�޸ģ�
    # ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])

    # ���Բ���
    ContextInfo.entry_window = 10  # ����ͨ�����ڣ�ͻ�����ڣ�
    ContextInfo.exit_window = 4  # ����ͨ������
    ContextInfo.atr_window = 10  # ATR��������
    ContextInfo.stop_profit_ratio = 0.2  # ֹӯ����
    ContextInfo.stop_loss_multiplier = 2  # ֹ��ATR����

    # �ʽ�������
    ContextInfo.total_capital = 100000  # ���ʽ���
    ContextInfo.single_entry_capital = 10000  # ����������
    ContextInfo.max_capital_per_symbol = 20000  # ��Ʒ������ʽ�
    ContextInfo.long_capital = 10000  # �����ʽ�
    ContextInfo.short_capital = 10000  # �����ʽ�

    # �˻���Ϣ
    ContextInfo.account_id = '809213023'  # �ڻ��˻�ID

    # ����״̬����
    ContextInfo.entry_price = 0  # ���м۸�
    ContextInfo.highest_after_entry = 0  # ���к����߼�
    ContextInfo.lowest_after_entry = 0  # ���к����ͼ�
    ContextInfo.N = 0  # ��������(Nֵ/ATR)
    ContextInfo.position_type = 0  # �ֲ����ͣ�0-�޲�λ��1-��ͷ��-1-��ͷ

    # ContextInfo.period = '1d'            # K������

    print("���꽻�ײ��Գ�ʼ�����")


def handlebar(ContextInfo):
    """
    ��Ҫ������
    ��ÿ��K�����ڶ��ᱻ����
    """
    # ��������Ƿ��㹻
    if ContextInfo.barpos < max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window):
        return

    try:
        # ��ȡ��ǰʱ��ͼ۸�����
        current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
        print(f"\n����ʱ��: {current_time}")

        # ��ȡ������Ҫ������
        price_data = get_price_data(ContextInfo)
        if price_data is None or len(price_data) < max(ContextInfo.entry_window, ContextInfo.atr_window):
            print("���ݲ��㣬�������δ���")
            return

        # ����ATR��Nֵ
        ContextInfo.N = calculate_atr(price_data, ContextInfo.atr_window)
        if ContextInfo.N <= 0:
            print("ATRֵ�����쳣���������δ���")
            return

        print(f"��ǰATR(Nֵ): {ContextInfo.N:.2f}")

        # ��ȡ��ǰ�˻���Ϣ
        account_info = get_account_info( ContextInfo.account_id)
        if account_info is None:
            print("�޷���ȡ�˻���Ϣ���������δ���")
            return

        available_cash = account_info['available']
        total_value = account_info['total_value']
        positions = account_info['positions']

        # ��ȡ��ǰ�ֲ�
        current_position = positions.get(ContextInfo.stock_code, 0) if positions else 0
        print(f"��ǰ�ֲ�: {current_position}, �����ʽ�: {available_cash:.2f}")

        # ���߷��� - �ж��Ƿ���Ҫ����
        signal = generate_signal(ContextInfo, price_data, current_position)

        # ִ����������
        if signal != 0:
            execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position)

    except Exception as e:
        print(f"��������з�������: {e}")


def get_price_data(ContextInfo):
    """
    ��ȡ������Ҫ������
    ���ذ���OHLC���ݵ�DataFrame
    """
    try:
        # ������Ҫ����ʷ��������
        required_bars = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window) + 5

        # ��ȡ��ʷ����
        bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')

        # ��ȡ��������
        market_data = ContextInfo.get_market_data_ex(
            ['open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=bar_date,
            period=ContextInfo.period,
            count=required_bars,
            subscribe=True
        )

        if not market_data or ContextInfo.stock_code not in market_data:
            print("��ȡ�г�����Ϊ��")
            return None

        df = market_data[ContextInfo.stock_code]
        return df

    except Exception as e:
        print(f"��ȡ�۸�����ʱ��������: {e}")
        return None


def calculate_atr(data, window):
    """
    ����ATR(Nֵ)
    ATR����ʵ������N��ƽ��ֵ�����ں����г�������

    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        # ������ʵ����(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:],
                        np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        # ����ATR(N�վ�ֵ)
        atr = np.mean(tr[-window:])
        return atr

    except Exception as e:
        print(f"����ATRʱ��������: {e}")
        return 0


def get_account_info( account_id):
    """
    ��ȡ�˻���Ϣ
    ���������ʽ���Ȩ�桢�ֲֵ�
    """
    try:
        # ��ȡ�˻��ʽ���Ϣ
        account_details = get_trade_detail_data(account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            return None

        account = account_details[0]
        available = account.m_dAvailable  # �����ʽ�
        total_value = account.m_dBalance  # ��Ȩ��

        # ��ȡ�ֲ���Ϣ
        position_details = get_trade_detail_data(account_id, 'FUTURE', 'POSITION')
        positions = {}
        if position_details:
            for pos in position_details:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                positions[symbol] = pos.m_nVolume  # �ֲ���

        return {
            'available': available,
            'total_value': total_value,
            'positions': positions
        }

    except Exception as e:
        print(f"��ȡ�˻���Ϣʱ��������: {e}")
        return None


def generate_signal(ContextInfo, price_data, current_position):
    """
    ���߷��� - ���ɽ����ź�
    �����޸ĺ�ĺ��꽻�׷����������롢����������ź�
    ����: 1=����(����), -1=����(����), 0=����
    """
    try:
        close_prices = price_data['close'].values
        high_prices = price_data['high'].values
        low_prices = price_data['low'].values

        current_price = close_prices[-1]
        current_high = high_prices[-1]
        current_low = low_prices[-1]

        # ���������ź� - ǰN�ոߵ͵�ͻ��
        # �Ϲ죺��ȥentry_window�����߼�
        upper_channel = np.max(high_prices[-ContextInfo.entry_window - 1:-1])
        # �¹죺��ȥentry_window�����ͼ�
        lower_channel = np.min(low_prices[-ContextInfo.entry_window - 1:-1])

        # ���������ź� - ����ͨ��
        # �����Ϲ�
        exit_upper = np.max(high_prices[-ContextInfo.exit_window - 1:-1])
        # �����¹�
        exit_lower = np.min(low_prices[-ContextInfo.exit_window - 1:-1])

        print(f"��ǰ�۸�: {current_price:.2f}")
        print(f"�����Ϲ�: {upper_channel:.2f}, �����¹�: {lower_channel:.2f}")
        print(f"�����Ϲ�: {exit_upper:.2f}, �����¹�: {exit_lower:.2f}")

        # ������߼ۺ���ͼۣ�������볡��
        if ContextInfo.position_type != 0:  # ���гֲ�
            ContextInfo.highest_after_entry = max(ContextInfo.highest_after_entry, current_high)
            ContextInfo.lowest_after_entry = min(ContextInfo.lowest_after_entry, current_low)

        # ���꽻�׷����ź��ж�
        if ContextInfo.position_type == 0:  # ��ǰ�޳ֲ�
            # �����ź�
            if current_price > upper_channel:  # ͻ���Ϲ죬�����źţ����ࣩ
                print("���������źţ��۸�ͻ�������Ϲ�")
                ContextInfo.highest_after_entry = current_high  # ��ʼ����߼�
                ContextInfo.lowest_after_entry = current_low  # ��ʼ����ͼ�
                return 1
            elif current_price < lower_channel:  # ͻ���¹죬�����źţ����գ�
                print("���������źţ��۸�ͻ�������¹�")
                ContextInfo.highest_after_entry = current_high  # ��ʼ����߼�
                ContextInfo.lowest_after_entry = current_low  # ��ʼ����ͼ�
                return -1

        elif ContextInfo.position_type == 1:  # ��ǰ���ж�ͷ��λ
            # ֹӯ�ź� - �۸���������¹��Ҽ۸�С����߼ۻس�һ������
            stop_profit_price = ContextInfo.highest_after_entry - (
                    ContextInfo.highest_after_entry - ContextInfo.entry_price) * ContextInfo.stop_profit_ratio
            if current_price < exit_lower and current_price < stop_profit_price:
                print("������ͷֹӯ�źţ��۸���������¹��һس��ﵽ��ֵ")
                return -1
            # ֹ���ź� - �۸��µ�����2N
            elif current_price < ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N:
                print("������ͷֹ���źţ��۸��µ�����2N")
                return -1

        elif ContextInfo.position_type == -1:  # ��ǰ���п�ͷ��λ
            # ֹӯ�ź� - �۸�ͻ�������Ϲ��Ҽ۸������ͼ۷���һ������
            stop_profit_price = ContextInfo.lowest_after_entry + (
                    ContextInfo.entry_price - ContextInfo.lowest_after_entry) * ContextInfo.stop_profit_ratio
            if current_price > exit_upper and current_price > stop_profit_price:
                print("������ͷֹӯ�źţ��۸�ͻ�������Ϲ��ҷ����ﵽ��ֵ")
                return 1
            # ֹ���ź� - �۸����ǳ���2N
            elif current_price > ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N:
                print("������ͷֹ���źţ��۸����ǳ���2N")
                return 1

        return 0  # �޽����ź�

    except Exception as e:
        print(f"���ɽ����ź�ʱ��������: {e}")
        return 0


def execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position):
    """
    ִ����������
    ���ݽ����ź�ִ�о�����µ�����

    �����µ�����
    1. ��ֻƷ�ֵ���������10000Ԫ
    2. �������������ÿ��Ʒ�����20000Ԫ������/���ո�10000Ԫ
    3. ��������տ���ͬʱ���ڣ�����Ӱ��
    """
    try:
        current_price = price_data['close'].iloc[-1]
        contract_multiplier = ContextInfo.get_contract_multiplier(ContextInfo.stock_code)

        # ����ͷ���ģ
        # �����ʽ����ͺ�Լ��ֵ��������
        if signal > 0:  # ����
            position_value = ContextInfo.long_capital
        else:  # ����
            position_value = ContextInfo.short_capital

        position_size = int(position_value / (current_price * contract_multiplier))
        position_size = max(1, position_size)  # ����Ϊ1��

        print(f"����ͷ���ģ: {position_size} �֣���ֵԼ: {position_size * current_price * contract_multiplier:.2f}Ԫ")

        if signal > 0:  # �����źţ����ࣩ
            if ContextInfo.position_type <= 0:  # ��ǰ�޲�λ����п�ͷ
                # 23: ���뿪��  1101: �޼۵�  5: ���ּ� -1: �м�  position_size: ����
                print(f"ִ�����뿪�ֲ���: {position_size} �֣��۸�: {current_price:.2f}")
                order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size)
                print(order_info)
                ContextInfo.position_type = 1
                ContextInfo.entry_price = current_price

            elif ContextInfo.position_type == 1:  # �ѳ��ж�ͷ��λ
                print("�ѳ��ж�ͷ��λ�����ظ�����")

        elif signal < 0:  # �����źţ����գ�
            if ContextInfo.position_type >= 0:  # ��ǰ�޲�λ����ж�ͷ
                # 37: ��������
                print(f"ִ���������ֲ���: {position_size} �֣��۸�: {current_price:.2f}")
                order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size)
                print(order_info)
                ContextInfo.position_type = -1
                ContextInfo.entry_price = current_price

            elif ContextInfo.position_type == -1:  # �ѳ��п�ͷ��λ
                print("�ѳ��п�ͷ��λ�����ظ�����")
        else:  # ƽ�ֲ���
            if ContextInfo.position_type == 1 and signal < 0:  # ƽ���
                # 24: ����ƽ��
                print(f"ִ������ƽ�ֲ���: {abs(current_position)} �֣��۸�: {current_price:.2f}")
                order_info = passorder(2, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, abs(current_position))
                print(order_info)
                ContextInfo.position_type = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0

            elif ContextInfo.position_type == -1 and signal > 0:  # ƽ�ղ�
                print(f"ִ������ƽ�ֲ���: {current_position} �֣��۸�: {current_price:.2f}")
                # 38: ����ƽ��
                order_info = passorder(5, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, current_position)
                print(order_info)
                ContextInfo.position_type = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0

    except Exception as e:
        print(f"ִ�н��ײ���ʱ��������: {e}")
