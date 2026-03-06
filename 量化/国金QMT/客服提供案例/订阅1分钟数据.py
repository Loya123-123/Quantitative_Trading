from xtquant import xtdata
import time

# 设定一个标的列表
code_list = ["SA505.ZF"]
# 设定获取数据的周期
period = "1m"


# 如果需要盘中的实时行情，需要向服务器进行订阅后才能获取
# 订阅后，get_market_data函数于get_market_data_ex函数将会自动拼接本地历史行情与服务器实时行情

# 向服务器订阅数据
for i in code_list:
    xtdata.subscribe_quote(i, period=period)  # 设置count = -1来取到当天所有实时行情

# 等待订阅完成
time.sleep(1)

# 获取订阅后的行情
kline_data = xtdata.get_market_data_ex([],code_list,period=period)
print(kline_data)

def f(data):

    # print(data)

    code_list = list(data.keys())  # 获取到本次触发的标的代码

    kline_in_callabck = xtdata.get_market_data_ex([], code_list, period=period)  # 在回调中获取klines数据
    print(kline_in_callabck)


for i in code_list:
    xtdata.subscribe_quote(i, period=period, count=-1, callback=f)  # 订阅时设定回调函数