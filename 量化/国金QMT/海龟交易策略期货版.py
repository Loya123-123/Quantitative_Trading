# coding:gbk
"""
���꽻�ײ����ڻ���
���ڹ���QMTƽ̨ʵ�ֵĺ��꽻�ײ���

�ò��Ծ��������Ĺ�����ϵ��������
����QMT ��������
����Ƶ�ʣ�����
����Ʒ�֣� �ڻ� ����������������һ�������� ��Ҫ�������е��ڻ�Ʒ�֣�ɸѡ�ܵĺõ�Ʒ�ֺ��˹�ѡ�����ص�ѡ��
��ǰ������ָ�꣺ǰ10��ATRƽ��ֵ������¼����
����1�����ࣩ�����ռ۸�>ǰ10�����̼����ߵ�ʱ������ǰ�۸�ͻ��ǰ10�ոߵ㣬��������ִ������
ֹӯ����1�������ڶ��쿪ʼ�����۸�>ǰ4�����̼����ߵ�ʱ���? Че۸�?> ���߼�-�����߼�-�����ۣ�*20% �����߼���ָ�����󵽼���ʱ�����߼ۣ�ʱ������ִ��������
ֹ������1�������ڶ��쿪ʼ�����۸� < ������-2*ATRʱ������ִ������

����2�����գ������ռ۸�<ǰ10�����̼����͵�ʱ������ǰ�۸�ͻ��10�յ͵㣬��������ִ������
ֹӯ����2�������ڶ��쿪ʼ�����۸�>ǰ4�����̼����͵�ʱ���? Че۸�?>���ͼ�+��������-���ͼۣ�*20% �����ͼ���ָ�����󵽼���ʱ�����ͼۣ�ʱ������ִ������
ֹ������2�������ڶ��쿪ʼ�����۸�>������+2*ATRʱ������ִ������

����ͷ�磺�ʽ���=100000����ֻƷ�ֵ�����������10000���������������򣬼�ÿ��Ʒ������20000������/���ո�10000
�Ӳֹ��������������������������ٽ��мӲ֣���������һ�ʣ���Ӱ�����յĿ�������֮����һ�ʣ�Ҳ��Ӱ�����࿪��
"""

import numpy as np


def init(ContextInfo):
    """
    ��ʼ������
    ���ò��Բ��������ױ��ĵ�
    """
    print("=" * 60)
    print("��ʼ��ʼ�����꽻�ײ���...")
    print("=" * 60)

    # ���ý��ױ��ģ������Ƹ��ڻ�Ϊ����ʵ��ʹ��ʱ��������Ҫ�޸ģ�
    # ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    ContextInfo.stock_code = 'rb00.SF'
    ContextInfo.set_universe([ContextInfo.stock_code])
    print(f"[��ʼ��] ���ý��ױ���: {ContextInfo.stock_code}")

    # ���Բ���
    ContextInfo.entry_window = 10  # ����ͨ�����ڣ�ͻ�����ڣ�
    ContextInfo.exit_window = 4  # ����ͨ������
    ContextInfo.atr_window = 10  # ATR��������
    ContextInfo.stop_profit_ratio = 0.2  # ֹӯ����
    ContextInfo.stop_loss_multiplier = 2  # ֹ��ATR����
    print(f"[��ʼ��] ���Բ�����������:")
    print(f"        ����ͨ������: {ContextInfo.entry_window}")
    print(f"        ����ͨ������: {ContextInfo.exit_window}")
    print(f"        ATR��������: {ContextInfo.atr_window}")
    print(f"        ֹӯ����: {ContextInfo.stop_profit_ratio}")
    print(f"        ֹ��ATR����: {ContextInfo.stop_loss_multiplier}")

    # �ʽ���������
    ContextInfo.total_capital = 100000  # ���ʽ���
    ContextInfo.single_entry_capital = 10000  # ������������
    ContextInfo.max_capital_per_symbol = 20000  # ��Ʒ�������ʽ�
    ContextInfo.long_capital = 10000  # �����ʽ�
    ContextInfo.short_capital = 10000  # �����ʽ�
    print(f"[��ʼ��] �ʽ�����������������:")
    print(f"        ���ʽ���: {ContextInfo.total_capital}")
    print(f"        ������������: {ContextInfo.single_entry_capital}")
    print(f"        ��Ʒ�������ʽ�: {ContextInfo.max_capital_per_symbol}")
    print(f"        �����ʽ�: {ContextInfo.long_capital}")
    print(f"        �����ʽ�: {ContextInfo.short_capital}")

    # �˻���Ϣ
    ContextInfo.account_id = '809213023'  # �ڻ��˻�ID
    print(f"[��ʼ��] �˻���Ϣ��������:")
    print(f"        �ڻ��˻�ID: {ContextInfo.account_id}")

    # ����״̬����
    ContextInfo.entry_price = 0  # м۸
    ContextInfo.highest_after_entry = 0  # к߼
    ContextInfo.lowest_after_entry = 0  # кͼ
    ContextInfo.N = 0  # (Nֵ/ATR)
    # ֲͣ0-޲λ1-ͷ-1-ͷ
    ContextInfo.long_position = 0  # ͷֲ״̬0-޲λ>0-ͷλΪֲ
    ContextInfo.short_position = 0  # ͷֲ״̬0-޲λ>0-ͷλΪֲ
    print(f"[��ʼ��] ����״̬������ʼ������:")
    print(f"        м۸: {ContextInfo.entry_price}")
    print(f"        к߼: {ContextInfo.highest_after_entry}")
    print(f"        кͼ: {ContextInfo.lowest_after_entry}")
    print(f"        (Nֵ): {ContextInfo.N}")
    print(f"        ͷֲ: {ContextInfo.long_position}")
    print(f"        ͷֲ: {ContextInfo.short_position}")

    print("=" * 60)
    print("���꽻�ײ��Գ�ʼ������")
    print("=" * 60)


def handlebar(ContextInfo):
    """
    ��Ҫ��������
    ��ÿ��K�����ڶ��ᱻ����
    """
    print("=" * 60)
    print("[��������] ��ʼִ��handlebar����")
    print("=" * 60)

    # ���������Ƿ��㹻
    required_data = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window)
    print(
        f"[���ݼ���] ��ǰbarλ��: {ContextInfo.barpos}, ��������: {required_data}")
    if ContextInfo.barpos < required_data:
        print("[���ݼ���] ���ݲ��㣬�������δ���")
        print("=" * 60)
        return

    try:
        # ��ȡ��ǰʱ���ͼ۸�����
        current_time = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y-%m-%d %H:%M:%S')
        print(f"[ʱ����Ϣ] ����ʱ��: {current_time}")

        # ��ȡ������Ҫ������
        print("[���ݻ�ȡ] ��ʼ��ȡ�۸�����...")
        price_data = get_price_data(ContextInfo)
        if price_data is None or len(price_data) < max(ContextInfo.entry_window, ContextInfo.atr_window):
            print("[���ݻ�ȡ] ���ݲ��㣬�������δ���")
            print("=" * 60)
            return
        print(f"[���ݻ�ȡ] �ɹ���ȡ�۸����ݣ��� {len(price_data)} ����¼")

        # ����ATR��Nֵ
        print("[ATR����] ��ʼ����ATR��Nֵ...")
        ContextInfo.N = calculate_atr(price_data, ContextInfo.atr_window)
        if ContextInfo.N <= 0:
            print("[ATR����] ATRֵ�����쳣���������δ���")
            print("=" * 60)
            return
        print(f"[ATR����] ��ǰATR(Nֵ): {ContextInfo.N:.4f}")

        # ��ȡ��ǰ�˻���Ϣ
        print("[�˻���Ϣ] ��ʼ��ȡ�˻���Ϣ...")
        account_info = get_account_info(ContextInfo.account_id)
        if account_info is None:
            print("[�˻���Ϣ] �޷���ȡ�˻���Ϣ���������δ���")
            print("=" * 60)
            return
        print("[�˻���Ϣ] �ɹ���ȡ�˻���Ϣ")

        available_cash = account_info['available']
        total_value = account_info['total_value']
        positions = account_info['positions']

        # ��ȡ��ǰ�ֲ�
        current_position = positions.get(ContextInfo.stock_code, 0) if positions else 0
        print(
            f"[�ֲ���Ϣ] ��ǰ�ֲ�: {current_position}, �����ʽ�: {available_cash:.2f}, ���ʲ�: {total_value:.2f}")

        # ���߷��� - �ж��Ƿ���Ҫ����
        print("[�ź�����] ��ʼ���ɽ����ź�...")
        signal = generate_signal(ContextInfo, price_data, current_position)
        print(f"[�ź�����] ���ɵĽ����ź�: {signal}")

        # ִ����������
        if signal != 0:
            print("[����ִ��] ���⵽�����źţ���ʼִ�н���...")
            execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position)
        else:
            print("[����ִ��] �޽����źţ������۲��г�")

        print("=" * 60)
        print("[��������] handlebar����ִ������")
        print("=" * 60)

    except Exception as e:
        print(f"[�쳣����] ���������з�������: {e}")
        print("=" * 60)


def get_price_data(ContextInfo):
    """
    ��ȡ������Ҫ������
    ���ذ���OHLC���ݵ�DataFrame
    """
    try:
        print("  [�۸�����] ��ʼ��ȡ�۸�����...")

        # ������Ҫ����ʷ��������
        required_bars = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window) + 5
        print(f"  [�۸�����] ��Ҫ��ȡ {required_bars} ����ʷ����")

        # ��ȡ��ʷ����
        bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
        print(f"  [�۸�����] ��ȡ��ֹʱ��: {bar_date}")

        # ��ȡ��������
        print(f"  [�۸�����] �����г�����...")
        print(
            f"  [�۸�����] �������� - ����: {ContextInfo.stock_code}, ����: {ContextInfo.period}, ����: {required_bars}")
        market_data = ContextInfo.get_market_data_ex(
            ['open', 'high', 'low', 'close'],
            [ContextInfo.stock_code],
            end_time=bar_date,
            period=ContextInfo.period,
            count=required_bars,
            subscribe=True
        )

        if not market_data or ContextInfo.stock_code not in market_data:
            print("  [�۸�����] ��ȡ�г�����Ϊ��")
            return None

        df = market_data[ContextInfo.stock_code]
        print(f"  [�۸�����] �ɹ���ȡ�г����ݣ��� {len(df)} ����¼")
        print("  [�۸�����] ����5������:")
        print(df.tail())
        return df

    except Exception as e:
        print(f"  [�۸�����] ��ȡ�۸�����ʱ��������: {e}")
        return None


def calculate_atr(data, window):
    """
    ����ATR(Nֵ)
    ATR����ʵ������N��ƽ��ֵ�����ں����г�������

    TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
    ATR = MA(TR, N)
    """
    try:
        print(f"  [ATR����] ��ʼ����ATR��ʹ�� {window} ������")

        # ������ʵ����(TR)
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values

        print(f"  [ATR����] �۸�����ͳ��:")
        print(f"    ���߼۷�Χ: {high[-window - 1:-1]}")
        print(f"    ���ͼ۷�Χ: {low[-window - 1:-1]}")
        print(f"    ���̼۷�Χ: {close[-window - 1:-1]}")

        # TR = MAX(High-Low, ABS(High-Close_prev), ABS(Low-Close_prev))
        tr = np.maximum(high[1:] - low[1:],
                        np.abs(high[1:] - close[:-1]))
        tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

        print(f"  [ATR����] �����õ�TRֵ: {tr[-window:]}")

        # ����ATR(N�վ�ֵ)
        atr = np.mean(tr[-window:])
        print(f"  [ATR����] ATR��������: {atr}")
        return atr

    except Exception as e:
        print(f"  [ATR����] ����ATRʱ��������: {e}")
        return 0


def get_account_info(account_id):
    """
    ��ȡ�˻���Ϣ
    ���������ʽ�����Ȩ�桢�ֲֵ�
    """
    try:
        print("  [�˻���Ϣ] ��ʼ��ȡ�˻���Ϣ...")

        # ��ȡ�˻��ʽ���Ϣ
        print("  [�˻���Ϣ] ��ȡ�˻��ʽ�����...")
        account_details = get_trade_detail_data(account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            print("  [�˻���Ϣ] ��ȡ�˻�����ʧ��")
            return None

        account = account_details[0]
        available = account.m_dAvailable  # �����ʽ�
        total_value = account.m_dBalance  # ��Ȩ��

        print(
            f"  [�˻���Ϣ] �˻��ʽ���Ϣ: �����ʽ�={available:.2f}, ���ʲ�={total_value:.2f}")

        # ��ȡ�ֲ���Ϣ
        print("  [�˻���Ϣ] ��ȡ�ֲ�����...")
        position_details = get_trade_detail_data(account_id, 'FUTURE', 'POSITION')
        positions = {}
        if position_details:
            print(f"  [�˻���Ϣ] ��ȡ�� {len(position_details)} ���ֲּ�¼")
            for pos in position_details:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                positions[symbol] = pos.m_nVolume  # �ֲ���
                print(f"    [�˻���Ϣ] �ֲ�: {symbol} = {pos.m_nVolume}")
        else:
            print("  [�˻���Ϣ] �޳ֲּ�¼")

        return {
            'available': available,
            'total_value': total_value,
            'positions': positions
        }

    except Exception as e:
        print(f"  [�˻���Ϣ] ��ȡ�˻���Ϣʱ��������: {e}")
        return None


def generate_signal(ContextInfo, price_data, current_position):
    """
    ���߷��� - ���ɽ����ź�
    �����޸ĺ��ĺ��꽻�׷����������롢�����������ź�
    ����: 1=����(����), -1=����(����), 0=����
    """
    try:
        print("  [�ź�����] ��ʼ���ɽ����ź�...")

        close_prices = price_data['close'].values
        high_prices = price_data['high'].values
        low_prices = price_data['low'].values

        current_price = close_prices[-1]
        current_high = high_prices[-1]
        current_low = low_prices[-1]

        print(f"  [�ź�����] ��ǰ�۸���Ϣ:")
        print(f"    ���̼�: {current_price:.4f}")
        print(f"    ���߼�: {current_high:.4f}")
        print(f"    ���ͼ�: {current_low:.4f}")

        # ���������ź� - ǰN�ոߵ͵�ͻ��
        # �Ϲ죺��ȥentry_window�������߼�
        upper_channel = np.max(high_prices[-ContextInfo.entry_window - 1:-1])
        # �¹죺��ȥentry_window�������ͼ�
        lower_channel = np.min(low_prices[-ContextInfo.entry_window - 1:-1])

        # ���������ź� - ����ͨ��
        # �����Ϲ�
        exit_upper = np.max(high_prices[-ContextInfo.exit_window - 1:-1])
        # �����¹� -
        exit_lower = np.min(low_prices[-ContextInfo.exit_window - 1:-1])

        print(f"  [�ź�����] ͨ����Ϣ:")
        print(f"    �����Ϲ�: {upper_channel:.4f}")
        print(f"    �����¹�: {lower_channel:.4f}")
        print(f"    �����Ϲ�: {exit_upper:.4f}")
        print(f"    �����¹�: {exit_lower:.4f}")

        # �������߼ۺ����ͼۣ��������볡��
        if ContextInfo.long_position > 0 or ContextInfo.short_position > 0:  # гֲ
            print(f"  [ź] гֲ֣ͼ:")
            print(f"    ǰ߼: {ContextInfo.highest_after_entry}")
            print(f"    ǰͼ: {ContextInfo.lowest_after_entry}")
            ContextInfo.highest_after_entry = max(ContextInfo.highest_after_entry, current_high)
            ContextInfo.lowest_after_entry = min(ContextInfo.lowest_after_entry, current_low)
            print(f"    º߼: {ContextInfo.highest_after_entry}")
            print(f"    ºͼ: {ContextInfo.lowest_after_entry}")

        print(f"  [ź] ǰ״̬:")
        # 수정日志输出
        print(f"    ͷֲ: {ContextInfo.long_position}")
        print(f"    ͷֲ: {ContextInfo.short_position}")
        print(f"    м۸: {ContextInfo.entry_price}")
        print(f"    к߼: {ContextInfo.highest_after_entry}")
        print(f"    кͼ: {ContextInfo.lowest_after_entry}")
        print(f"    ǰATRֵ: {ContextInfo.N:.4f}")

        # 꽻׷ź�?
        # 수정持仓判断逻辑
        if ContextInfo.long_position == 0 and ContextInfo.short_position == 0:  # ǰ޳ֲ
            print("  [ź] ǰ޳ֲ֣жǷ񿪲")
            # ź
            if current_price > upper_channel:  # ͻϹ죬źţࣩ
                print("  [ź] źţ۸ͻϹ")
                ContextInfo.highest_after_entry = current_high  # ʼ߼
                ContextInfo.lowest_after_entry = current_low  # ʼͼ
                print(f"  [ź] 볡�?: {ContextInfo.highest_after_entry}")
                print(f"  [ź] 볡�?: {ContextInfo.lowest_after_entry}")
                return 1
            elif current_price < lower_channel:  # ͻ¹죬źţ�?
                print("  [ź] źţ۸ͻ¹")
                ContextInfo.highest_after_entry = current_high  # ʼ߼
                ContextInfo.lowest_after_entry = current_low  # ʼͼ
                print(f"  [ź] 볡�?: {ContextInfo.highest_after_entry}")
                print(f"  [ź] 볡�?: {ContextInfo.lowest_after_entry}")
                return -1
            else:
                print("  [ź] ޿ź")

        elif ContextInfo.long_position > 0:  # ǰжͷλ
            print("  [ź] ǰжͷλжǷƽ")
            # ֹӯź - ۸¹Ҽ۸С߼ۻسһ
            stop_profit_price = ContextInfo.highest_after_entry - (
                    ContextInfo.highest_after_entry - ContextInfo.entry_price) * ContextInfo.stop_profit_ratio
            print(f"  [ź] ͷֹӯ۸:")
            print(f"    ʽ: ߼ - (߼ - �?) * ֹӯ")
            print(
                f"    ֵ: {ContextInfo.highest_after_entry} - ({ContextInfo.highest_after_entry} - {ContextInfo.entry_price}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price < exit_lower and current_price < stop_profit_price:
                print("  [ź] ͷֹӯźţ۸¹һסﵽ�?")
                print(f"    ǰ۸: {current_price} < ¹: {exit_lower}")
                print(f"    ǰ۸: {current_price} < ֹӯ۸: {stop_profit_price:.4f}")
                return -1
            # ֹź - ۸µ2N
            elif current_price < ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N
                print("  [ź] ͷֹźţ۸µ2N")
                print(f"    ǰ۸: {current_price} < ֹ۸: {stop_loss_price:.4f}")
                print(f"    �?: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return -1
            else:
                print("  [ź] ƽź")

        elif ContextInfo.short_position > 0:  # ǰпͷλ
            print("  [ź] ǰпͷλжǷƽ")
            # ֹӯź - ۸ͻϹ Че۸ͼ۷һ
            stop_profit_price = ContextInfo.lowest_after_entry + (
                    ContextInfo.entry_price - ContextInfo.lowest_after_entry) * ContextInfo.stop_profit_ratio
            print(f"  [ź] ͷֹӯ۸:")
            print(f"    ʽ: ͼ + (�? - ͼ) * ֹӯ")
            print(
                f"    ֵ: {ContextInfo.lowest_after_entry} + ({ContextInfo.entry_price} - {ContextInfo.lowest_after_entry}) * {ContextInfo.stop_profit_ratio} = {stop_profit_price:.4f}")

            if current_price > exit_upper and current_price > stop_profit_price:
                print("  [ź] ͷֹӯźţ۸ͻϹҷﵽ�?")
                print(f"    ǰ۸: {current_price} > Ϲ: {exit_upper}")
                print(f"    ǰ۸: {current_price} > ֹӯ۸: {stop_profit_price:.4f}")
                return 1
            # ֹź - ۸ǳ2N
            elif current_price > ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N:
                stop_loss_price = ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N
                print("  [ź] ͷֹźţ۸ǳ2N")
                print(f"    ǰ۸: {current_price} > ֹ۸: {stop_loss_price:.4f}")
                print(f"    �?: {ContextInfo.entry_price}, ATR: {ContextInfo.N:.4f}")
                return 1
            else:
                print("  [ź] ƽź")

        return 0  # ޽ź

    except Exception as e:
        print(f"  [�ź�����] ���ɽ����ź�ʱ��������: {e}")
        return 0


def execute_trade(ContextInfo, signal, price_data, available_cash, total_value, current_position):
    """
    ִ����������
    ���ݽ����ź�ִ�о������µ�����

    �����µ�������
    1. ��ֻƷ�ֵ�����������10000Ԫ
    2. ����������������ÿ��Ʒ������20000Ԫ������/���ո�10000Ԫ
    3. ���������տ���ͬʱ���ڣ�����Ӱ��
    """
    try:
        print("  [����ִ��] ��ʼִ�н��ײ���...")
        print(f"  [����ִ��] �����ź�: {signal}")

        current_price = price_data['close'].iloc[-1]
        contract_multiplier = ContextInfo.get_contract_multiplier(ContextInfo.stock_code)
        print(f"  [����ִ��] ��Լ��Ϣ:")
        print(f"    ��ǰ�۸�: {current_price:.4f}")
        print(f"    ��Լ����: {contract_multiplier}")

        # ����ͷ����ģ
        # �����ʽ����ͺ�Լ��ֵ��������
        if signal > 0:  # ����
            position_value = ContextInfo.long_capital
            print(f"  [����ִ��] �����ʽ�: {position_value}")
        else:  # ����
            position_value = ContextInfo.short_capital
            print(f"  [����ִ��] �����ʽ�: {position_value}")

        position_size = int(position_value / (current_price * contract_multiplier))
        print(f"  [����ִ��] ͷ����ģ: {position_size} ��")
        position_size = max(1, position_size)  # ����Ϊ1��

        print(f"  [����ִ��] ͷ������:")
        print(f"    ���㹫ʽ: �ʽ� / (�۸� * ��Լ����)")
        print(
            f"    ��ֵ����: {position_value} / ({current_price} * {contract_multiplier}) = {position_value / (current_price * contract_multiplier):.2f}")
        print(f"    ��������: {position_size} ��")
        print(f"    ͷ����ֵ: {position_size * current_price * contract_multiplier:.2f}Ԫ")

        if signal > 0:  # źţ�?
            # 수정持仓判断逻辑
            if ContextInfo.short_position > 0:  # ǰпͷλƽ
                # 7 ƽ, ƽ
                print(f"  [ִ] ִƽֲ: {abs(current_position)} ֣۸: {current_price:.4f}")
                print(f"  [ִ] µ: ƽ, ޼۵, ּ, м, {abs(current_position)}")
                order_info = passorder(7, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1,
                                       abs(current_position), 1, ContextInfo)
                print(f"  [ִ] µ: {order_info}")
                ContextInfo.short_position = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                print("  [ִ] óֲ״̬")

            # ƽ¿
            if ContextInfo.short_position == 0 and ContextInfo.long_position == 0:  # ǰ޲λ
                # 0	  1101: ޼۵  5: ּ -1: м  position_size: 
                print(f"  [ִ] ִ뿪�?: {position_size} ֣۸: {current_price:.4f}")
                print(f"  [ִ] µ: �?, ޼۵, ּ, м, {position_size}")
                order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size, 1,
                                       ContextInfo)
                print(f"  [ִ] µ: {order_info}")
                ContextInfo.long_position = position_size  # ¼ͷλ
                ContextInfo.entry_price = current_price
                print(f"  [ִ] ³ֲ״̬: ͷ")
                print(f"  [ִ] ¼볡�?: {ContextInfo.entry_price}")

            elif ContextInfo.long_position > 0:  # ѳжͷλ
                print("  [ִ] ѳжͷλظ")

        elif signal < 0:  # źţգ
            # 수정持仓判断 로직
            if ContextInfo.long_position > 0:  # ǰжͷλƽ
                print(f"  [ִ] ִƽֲ: {current_position} ֣۸: {current_price:.4f}")
                # 9 ƽ, ƽ
                print(f"  [ִ] µ: ƽ, ޼۵, ּ, м, {current_position}")
                order_info = passorder(9, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, current_position,
                                       1, ContextInfo)
                print(f"  [ִ] µ: {order_info}")
                ContextInfo.long_position = 0
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0
                print("  [ִ] óֲ״̬")

            # ƽղ¿
            if ContextInfo.long_position == 0 and ContextInfo.short_position == 0:  # ǰ޲λ
                # 3: 
                print(f"  [ִ] ֲִ: {position_size} ֣۸: {current_price:.4f}")
                print(f"  [ִ] µ: , ޼۵, ּ, м, {position_size}")
                order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code, 5, -1, position_size, 1,
                                       ContextInfo)
                print(f"  [ִ] µ: {order_info}")
                ContextInfo.short_position = position_size  # ¼ͷλ
                ContextInfo.entry_price = current_price
                print(f"  [ִ] ³ֲ״̬: ͷ")
                print(f"  [ִ] ¼볡�?: {ContextInfo.entry_price}")

            elif ContextInfo.short_position > 0:  # ѳпͷλ
                print("  [ִ] ѳпͷλظ")

        else:  # ƽֲ
            # 삭제原来的平仓�?�辑，因为已经在上面处理�?
            pass

    except Exception as e:
        print(f"  [ִ] ִнײʱ: {e}")
