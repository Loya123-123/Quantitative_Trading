# coding = udf-8
# /usr/bin/env python



## ���̺����к���
def after_market_close(context):
    log.info(str('��������ʱ��(after_market_close):'+str(context.current_dt.time())))
    #�õ��������гɽ���¼
    trades = get_trades()
    for _trade in trades.values():
        log.info('�ɽ���¼��'+str(_trade))
    df = context.portfolio.positions
    write_file('json_test.josn', str(dict(df)))
    log.info('һ�����')
    log.info('##############################################################')

## ���̻�ȡ����
import cPickle as pickle
df = get_price('600507.XSHG')
content = pickle.dumps(df)  #���������л���pkl��ʽ���ַ���
write_file('test.pkl',content)  #��������

df = pickle.loads(read_file('test.pkl')) #��ȡ�ַ�����ʽ��pkl�ļ�
print df



# д���о�������ز�
import pandas as pd
from six import StringIO
from six import BytesIO  #python3
"""
���ز���д���о��У�csv�ļ�
"""
def excel_to_research(dataframe,file_name) :
    """��dataframe��excel��ʽ���浽�о� ,
      �������͵�����Ҳ���Բο����ַ���"""
    tmp_name = "temp."+ file_name.split(".")[-1]
    dataframe.to_excel(tmp_name)
    with open(tmp_name , 'rb') as f :
        data = f.read()
    write_file(file_name ,data)

# ��ʼ���������趨��׼�ȵ�
def initialize(context):
    # д��
    df = get_price('000001.XSHE')
    excel_to_research(dataframe,'test_df.xlsx',)

    # ����
    df2 = pd.read_excel(StringIO(read_file('test_df.xlsx')))
    #df2 = pd.read_excel(BytesIO(read_file('test_df.xlsx')))#python3
    print(type(df2))
    print(df2)