# coding = udf-8
# /usr/bin/env python



## 收盘后运行函数
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    df = context.portfolio.positions
    write_file('json_test.josn', str(dict(df)))
    log.info('一天结束')
    log.info('##############################################################')

## 开盘获取数据
import cPickle as pickle
df = get_price('600507.XSHG')
content = pickle.dumps(df)  #将数据序列化成pkl格式的字符串
write_file('test.pkl',content)  #储存数据

df = pickle.loads(read_file('test.pkl')) #读取字符串形式的pkl文件
print df



# 写入研究及读入回测
import pandas as pd
from six import StringIO
from six import BytesIO  #python3
"""
将回测结果写入研究中，csv文件
"""
def excel_to_research(dataframe,file_name) :
    """将dataframe以excel方式保存到研究 ,
      其他类型的数据也可以参考这种方法"""
    tmp_name = "temp."+ file_name.split(".")[-1]
    dataframe.to_excel(tmp_name)
    with open(tmp_name , 'rb') as f :
        data = f.read()
    write_file(file_name ,data)

# 初始化函数，设定基准等等
def initialize(context):
    # 写入
    df = get_price('000001.XSHE')
    excel_to_research(dataframe,'test_df.xlsx',)

    # 读入
    df2 = pd.read_excel(StringIO(read_file('test_df.xlsx')))
    #df2 = pd.read_excel(BytesIO(read_file('test_df.xlsx')))#python3
    print(type(df2))
    print(df2)