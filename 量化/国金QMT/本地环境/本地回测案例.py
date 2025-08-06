

# �������ָ��xtquant��·��
import sys
import numpy as np
import pandas as pd
from xtquant import xtdata
import xtquant
print(xtquant)
print(xtdata.data_dir)
# ָ����ȡͶ�ж�����(�ɲ�ָ����Ĭ����������Ͷ��)
# xtdata.reconnect(port=58613)
# xtdata.download_sector_data()



class G():
    pass


g = G()




def init(C):
    # ------------------------�����趨-----------------------------
    g.his_st = {}

    # g.s = C.get_stock_list_in_sector("����A��")  # ��ȡ����A�ɹ�Ʊ�б�
    g.s = C.get_stock_list_in_sector("����300")  # ��ȡ����300��Ʊ�б�
    # g.s = ['000001.SZ']
    g.day = 0
    g.holdings = {i: 0 for i in g.s}
    g.weight = [0.1] * 10
    g.buypoint = {}
    g.money = 1000000  # C.capital
    g.accid = 'test'
    g.profit = 0
    # ����Ȩ��
    g.buy_num = 10  # ������ǰ5�Ĺ�Ʊ���ڹ����л��õ�
    g.per_money = g.money / g.buy_num * 0.95




def after_init(C):
    # ------------------------�������ݻ�ȡ-----------------------------
    data = xtdata.get_market_data_ex([], g.s, period='1d', dividend_type='front_ratio',
                                     fill_data=True)
    close_df = get_df_ex(data,"close")
    open_df = get_df_ex(data,"open")
    low_df = get_df_ex(data,"low")
    high_df = get_df_ex(data,"high")
    volume_df = get_df_ex(data,"volume")
    amount_df = get_df_ex(data,"amount")
    preclose_df = get_df_ex(data,"preClose")

    # ------------------------�������ݻ�ȡ-----------------------------
    # �� g.s �е�ȫ����Ʊ�� TotalVolume ����ȡ��������ϳ�һ�� DataFrame
    # ���� g.s ���� 10 ����Ʊ����ô����Ĵ���ͻ᷵��һ�� 1 �� 10 �е� DataFrame
    # �� DataFrame �� index �ǹ�Ʊ���룬columns �� TotalVolume
    # �� DataFrame ��������ÿ����Ʊ�� TotalVolume����������룺
    # C.get_instrumentdetail('600000.SH')['TotalVolume']
    # ʹ���ֵ��Ƶ�����ȡÿ����Ʊ��TotalVolume
    total_volumes = {stock: C.get_instrumentdetail(stock)['TotalVolume'] for stock in g.s}
    # ���ֵ�ת��ΪDataFrame������ת��Ϊһ��Ƕ���ֵ�
    df_total_volume = pd.DataFrame({k: v for k, v in total_volumes.items()}, index=['TotalVolume'])


    # ------------------------�������ݻ�ȡ-----------------------------

    # ------------------------����1���㼰����--------------------------------
    # 1. ��ֵ����: ����ֵ���� = ��Ʊ���̼� * ��Ʊ�ܹɱ���Ҫ���úã�Ҫ���Ӧ�������
    factor = close_df * df_total_volume.loc['TotalVolume']

    # ------------------------����2���㼰����--------------------------------
    # �ж� close_df �е� code ����ʱ�����120��
    stock_opendate_filter = filter_opendate_qmt(C, close_df, 120)

    # ------------------------�������ڹ��˴���--------------------------------
    # ��������ֵ�� DataFrame ��Ӧ��˹��˵�ÿ�����������в���120���
    factor *= stock_opendate_filter.astype(int).replace(0, np.nan)

    # ------------------------������-----------------------------------
    # �� factor ÿ����һ���ڽ�������
    factor_sorted = rank_filter(factor, 10, ascending=True, method='min', na_option='keep')


    # ------------------------������ϵõ�����ֵ�ź�--------------------------------

    # ȷ��û��δ�����ݵ�Ӱ�죬��������������ƶ�һ��
    g.factor_df = factor_sorted.shift(1)  #
    g.close_df = close_df.shift(1)  # Ϊ�˼��������ʣ������̼�����ƶ�һ��
    g.open_df = open_df
    g.stock_opendate_filter = stock_opendate_filter


def handlebar(C):
    # ��ȡ��ǰ K ��λ��
    d = C.barpos
    # ��ȡ��ǰ K ��ʱ��
    backtest_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d")
    factor_series = g.factor_df.loc[backtest_time]
    buy_list = daily_filter(factor_series, backtest_time)
    print(backtest_time, buy_list)

    # ��ȡ�ֲ�
    hold = get_holdings(g.accid, 'stock')
    need_sell = [s for s in hold if s not in buy_list]
    print('\t\t\t\t\t\t\t', backtest_time, 'sell list', need_sell)

    # ����
    for s in need_sell:
        price = g.open_df.loc[backtest_time, s]
        vol = hold[s]['�ֲ�����']
        passorder(24, 1101, g.accid, s, 11, price, vol, 1,"backtest","С��ֵ",C)

    # ��ȡ�ֲ�
    hold = get_holdings(g.accid, 'stock')
    asset = get_trade_detail_data(g.accid, 'stock', 'account')
    cash = asset[0].m_dAvailable
    buy_num = g.buy_num - len(hold)
    buy_list = [s for s in buy_list if s not in hold]

    # ����
    if buy_num > 0 and buy_list:
        buy_list = buy_list[:buy_num]
        # money = cash/buy_num
        print(backtest_time, 'buy list', buy_list)
        for s in buy_list:
            price = g.open_df.loc[backtest_time, s]
            if price > 0:
                passorder(23, 1102, g.accid, s, 11, float(price), g.per_money,1,"backtest","С��ֵ",C)


def daily_filter(factor_series, backtest_time):
    # �� factor_series ��ֵ True ��index��ת�����б�
    print(len(factor_series))
    sl = factor_series[factor_series].index.tolist()
    print(len(sl))
    # exit()
    # st����
    sl = [s for s in sl if not is_st(s, backtest_time)]
    sl = sorted(sl, key=lambda k: factor_series.loc[k])
    return sl[:g.buy_num]


def is_st(s, date):
    # �ж�ĳ������ʷ���ǲ���st *st
    st_dict = g.his_st.get(s, {})
    if not st_dict:
        return False
    else:
        st = st_dict.get('ST', []) + st_dict.get('*ST', [])
        for start, end in st:
            if start <= date <= end:
                return True


def get_df(dt: dict, df: pd.DataFrame, values_name: str) -> pd.DataFrame:
    '''
    ѭ�����ֵ��︳ֵ����
    values_name��ѡ�ֶ�: ['time', 'stime', 'open', 'high', 'low', 'close', 'volume','amount', 'settelementPrice', 'openInterest', 'preClose', 'suspendFlag']
    '''
    df1 = df.copy()
    df1 = df1.apply(lambda x: dt[x.name][values_name])

    return df1

def get_df_ex(data:dict,field:str) -> pd.DataFrame:

    '''
    ToDo:������ʹ��get_market_data_ex������£�ȡ����׼df

    Args:
        data: get_market_data_ex���ص�dict
        field: ['time', 'open', 'high', 'low', 'close', 'volume','amount', 'settelementPrice', 'openInterest', 'preClose', 'suspendFlag']

    Return:
        һ����ʱ��Ϊindex�����Ϊcolumns��df
    '''

    _index = data[list(data.keys())[0]].index.tolist()
    _columns = list(data.keys())
    df = pd.DataFrame(index=_index,columns=_columns)
    for i in _columns:
        df[i] = data[i][field]
    return df


def rank_filter(df: pd.DataFrame, N: int, axis=1, ascending=False, method="max", na_option="keep") -> pd.DataFrame:
    """
    Args:
        df: ��׼���ݵ�df
        N: �ж��Ƿ���ǰN��
        axis: Ĭ���Ǻ�������
        ascending : Ĭ���ǽ�������
        na_option : Ĭ�ϱ���nanֵ,������������
    Return:
        pd.DataFrame:һ��ȫ��boolֵ��df
    """
    _df = df.copy()

    _df = _df.rank(axis=axis, ascending=ascending, method=method, na_option=na_option)

    return _df <= N


def filter_opendate_qmt(C, df: pd.DataFrame, n: int) -> pd.DataFrame:
    '''

    ToDo: �жϴ����df.columns�У����������Ƿ����N�գ����ص�ֵ��һ��ȫ��boolֵ��df

    Args:
        C:contextinfo��
        df:indexΪʱ�䣬columnsΪstock_code��df,Ŀ����Ϊ�˺Ͳ����е�����df����
        n:�����ж����������Ĳ�������Ҫ�ж��Ƿ�����120��,����д
    Return:pd.DataFrame

    '''
    local_df = pd.DataFrame(index=df.index, columns=df.columns)
    stock_list = df.columns
    stock_opendate = {i: C.get_instrument_detail(i)["OpenDate"] for i in stock_list}
    # print(type(stock_opendate["000001.SZ"]), stock_opendate["000001.SZ"])
    for stock, date in stock_opendate.items():
        local_df.at[date, stock] = 1
    df_fill = local_df.fillna(method="ffill")

    result = df_fill.expanding().sum() >= n

    return result


def filter_opendate_xt(df: pd.DataFrame, n: int) -> pd.DataFrame:
    '''

    ToDo: �жϴ����df.columns�У����������Ƿ����N�գ����ص�ֵ��һ��ȫ��boolֵ��df

    Args:
        C:contextinfo��
        df:indexΪʱ�䣬columnsΪstock_code��df,Ŀ����Ϊ�˺Ͳ����е�����df����
        n:�����ж����������Ĳ�������Ҫ�ж��Ƿ�����120��,����д
    Return:pd.DataFrame

    '''
    local_df = pd.DataFrame(index=df.index, columns=df.columns)
    stock_list = df.columns
    stock_opendate = {i: xtdata.get_instrument_detail(i)["OpenDate"] for i in stock_list}
    for stock, date in stock_opendate.items():
        local_df.at[date, stock] = 1
    df_fill = local_df.fillna(method="ffill")

    result = df_fill.expanding().sum() >= n

    return result


def get_holdings(accid, datatype):
    '''
    Arg:
        accondid:�˻�id
        datatype:
            'FUTURE'���ڻ�
            'STOCK'����Ʊ
            ......
    return:
        {��Ʊ��:{'����':int,"�ֲֳɱ�":float,'����ӯ��':float,"�������":int}}
    '''
    PositionInfo_dict = {}
    resultlist = get_trade_detail_data(accid, datatype, 'POSITION')
    for obj in resultlist:
        PositionInfo_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID] = {
            "�ֲ�����": obj.m_nVolume,
            "�ֲֳɱ�": obj.m_dOpenPrice,
            "����ӯ��": obj.m_dFloatProfit,
            "�������": obj.m_nCanUseVolume
        }
    return PositionInfo_dict



if __name__ == '__main__':
    import sys
    from xtquant.qmttools import run_strategy_file

    # �������巽��һ�����ʹ�÷��������������run_strategy_file��param�����ɲ���
    param = {
        'stock_code': '000300.SH',  # ����handlebar�Ĵ���,
        'period': '1d',  # ����ִ������ ����ͼ����
        'start_time': '2022-01-01 00:00:00',  # ע���ʽ����Ҫд��
        'end_time': '2024-03-01 00:00:00',  # ע���ʽ����Ҫд��
        'trade_mode': 'backtest',  # 'backtest':�ز�
        'quote_mode': 'history',
        # handlebarģʽ��'realtime':��ʵʱ���飨��������ʷ�����handlebar��,'history':����ʷ����, 'all'�����У���history+realtime
    }
    # user_script = os.path.basename(__file__)  # ��ǰ�ű�·�������·��������·������,�˴�Ϊ���·���ķ���
    user_script = sys.argv[0]  # ��ǰ�ű�·�������·��������·�����ɣ��˴�Ϊ����·���ķ���

    print(user_script)
    result = run_strategy_file(user_script, param=param)
    if result:
        print(result.get_backtest_index())
        print(result.get_group_result())

    xtdata.run()
