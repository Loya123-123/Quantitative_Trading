#coding:utf-8


# 用get_market_data订阅历史和实时行情

import time


down_period={
    #需要的周期：实际应该下载/订阅的周期
    'tick':'tick',
    '1d':'1d',
    '1m':'1m',
    '5m':'5m',
    '15m':'5m',
    '10m':'5m',
    '30m':'5m',
    '1h':'5m',
    '1w':'1d',
    '1mon':'1d',

}


if __name__=='__main__':

    # 在线帮助文档：
    # http://dict.thinktrader.net/?id=I3DJ97

    from xtquant import xtdata
    period = '5m'
    code_list = ['000009.SZ']
    for s in code_list:
        if 0:
            # 下载股票行情数据
            ##### 当需要历史数据时，需要配合xtdata.download_history_data 接口使用，该接口会下载行情数据到本地，从而实现行情持久化保存
            # 实际使用时，该接口每天盘后执行一次即可
            xtdata.download_history_data(s, down_period[period],'20251210','20251226')
        if 1:
            # 调用subscribe_quote订阅接口订阅成功后可以用get_market_data_ex查询到盘中的实时行情
            # 注意客户端订阅有限制，上限是300(投研开启k线全推后就没有限制)，订阅按一个股票+周期计数，且是全局累计 即运行中的多个策略的订阅都会包含进去
            subscribe_num = xtdata.subscribe_quote(s, down_period[period], count=-1)
            print('订阅号:', subscribe_num)
            time.sleep(3) # 等待订阅成功  实际使用时可以去掉，
            # 因为本示例主线程没有阻塞，所以主线程可能会在订阅成功之前就结束，从而导致获取数据失败


    if 1: # 按照指定日期查询行情
        data = xtdata.get_market_data_ex([], code_list, period, start_time='20251216090000', end_time='20251216100000',fill_data=False)
        print('data from get_market_data:\n')

        for stock in data:
            print(f"              {stock}\n {data[stock].head()}\n")
    if 0:
        # 查询指定数量的k线
        data = xtdata.get_market_data_ex([],code_list , period, start_time='', end_time='20240610',count=10,fill_data=False)
        print('data from get_market_data:\n')
        for stock in data:
            print(f"              {stock}\n {data[stock].head()}\n")