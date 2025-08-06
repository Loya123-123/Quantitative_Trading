# 风险及免责提示：该策略由聚宽用户在聚宽社区分享，仅供学习交流使用。
# 原文一般包含策略说明，如有疑问请到原文和作者交流讨论。
# 原文网址：https://www.joinquant.com/post/44901
# 标题：首板低开策略
# 作者：wywy1995
# 原回测条件：2016-01-01 到 2023-11-11, ￥200000, 每天  Python3
# 量子象限学习平台，收集整理了很多大佬分享有代表意义的策略源码，可联系https://www.liangzxx.com平台客服分享

from jqlib.technical_analysis import *
from jqfactor import *
from jqdata import *
import datetime as dt
import pandas as pd

#####################################此处为新增加自动化实盘交易的代码###############################
import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from requests.auth import AuthBase
import math
import random

your_server_addr ="http://8.138.22.161:80/api/v1/stock/"   #更改成你部署的自动化工具的机器地址
secretId ="123"   #更改成你自己在自动化工具的config.yaml配制的ID
secretKey ="123456"  #更改成你自己在自动化工具的config.yaml配制的Key

class a():
    pass
#创建一个空的类的实例，用于保存全局变量
A=a()
#是否启用实盘的开关，如果启用，设置为1，不启用设置为0，注：回测的时候，请不要启用，因为实盘自动交易，是以当前的股票价格进行实盘下单操作
A.isShiPan=1

# 认证签名
class SignAuth(AuthBase):
    def __init__(self, secret_id:str = secretKey, secret_key:str = secretKey):
        self.secret_id = secret_id
        self.secret_key = secret_key

    def __call__(self, r):
        # 获取当前时间戳和nonce
        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())
        body = r.body or b""

        parsed_url = urlparse(r.url)
        query_params = parse_qs(parsed_url.query)  # 获取查询参数字典
        # 对查询参数进行排序
        sorted_query_params = dict(sorted(query_params.items()))
        # 将排序后的查询参数重新编码为字符串
        sorted_params_str = urlencode(sorted_query_params, doseq=True)

        # 构造待签名字符串
        sign_data = [
            r.method,
            r.path_url.split("?")[0],
            sorted_params_str,
            timestamp,
            nonce,
            body.decode('utf-8') if isinstance(body, bytes) else body
        ]

        sign_data = '\n'.join(sign_data)

        print("签名数据\n",sign_data)


        # 使用HMAC算法和SHA256哈希函数创建签名
        signature = hmac.new(self.secret_key.encode('utf-8'), sign_data.encode('utf-8'), hashlib.sha256)

        # 将签名转换为Base64编码的字符串
        signature = signature.digest().hex()

        # 添加必要的认证头
        authorization = f"hmac id=\"{self.secret_id}\", ts=\"{timestamp}\", nonce=\"{nonce}\", sig=\"{signature}\""

        print("Authorization", authorization)

        r.headers['Authorization'] = authorization


        return r




#股票买入方法
def buy_stock(stock_code,price,vol):
    start_time = time.time()
    print('开始买入:'+stock_code+' 价格：'+str(price)+' 数量：'+str(vol))
    result=requests.post(your_server_addr+"buy", json={
        "code": stock_code,
        "price": price,
        "volume": vol
    }, auth=SignAuth())
    print(result.json())
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"买入执行耗时: {elapsed_time} 秒")

#股票卖出方法
def sell_stock(stock_code,price,vol):
    start_time = time.time()
    print('开始卖出:'+stock_code+' 价格：'+str(price)+' 数量：'+str(vol))
    stock_code=stock_code[:6]
    result=requests.post(your_server_addr+"sell", json={
        "code": stock_code,
        "price": price,
        "volume": vol
    }, auth=SignAuth())
    print(result.json)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"卖出执行耗时: {elapsed_time} 秒")

#委撤撤单方法
def cancel_stock(cancelType):
    start_time = time.time()
    print('开始全部撤单')
    result=requests.post(your_server_addr+"cancel", json={
        "cancelType": cancelType
    }, auth=SignAuth())
    print(result.json)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"卖出执行耗时: {elapsed_time} 秒")

#获取账户资金方法
def get_account():
    result=requests.get(your_server_addr+"funding", auth=SignAuth()).text
    data_dict=json.loads(result)
    return data_dict['data']

#获取委托信息方法
def get_order():
    result=requests.get(your_server_addr+"order", auth=SignAuth()).text
    data_dict=json.loads(result)
    if 'data' in data_dict.keys():
        return data_dict['data']
    else:
        return

#获取持仓方法
def get_position():
    result=requests.get(your_server_addr+"position", auth=SignAuth()).text
    data_dict=json.loads(result)
    return data_dict['data']

#####################################此处为新增加自动化实盘交易的代码###############################

def initialize(context):
    # 系统设置
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    log.set_level('system', 'error')
    # 每日运行
    run_daily(buy, '09:30') #9:25分知道开盘价后可以提前下单
    run_daily(sell, '11:28')
    run_daily(sell, '14:50')



# 选股
def buy(context):
    #####################################此处为新增加自动化实盘交易的代码###############################
    #获取账户总资金
    try:
        if A.isShiPan==1:
            print('开始获取账户信息')
            account1=get_account()
            print(account1)
            account_total1=float(account1['total'])
            print("账号总资金："+str(account_total1))
    except Exception as e:
        account_total1=0
        print(f"获取账号资金发生异常:{e}")
    #####################################此处为新增加自动化实盘交易的代码###############################
    
    # 基础信息
    date = transform_date(context.previous_date, 'str')
    current_data = get_current_data()
    
    # 昨日涨停列表
    initial_list = prepare_stock_list(date)
    hl_list = get_hl_stock(initial_list, date)
    
    if len(hl_list) != 0:    
        # 获取非连板涨停的股票
        ccd = get_continue_count_df(hl_list, date, 10)
        lb_list = list(ccd.index)
        stock_list = [s for s in hl_list if s not in lb_list]
        
        # 计算相对位置
        rpd = get_relative_position_df(stock_list, date, 60)
        rpd = rpd[rpd['rp'] <= 0.5]
        stock_list = list(rpd.index)
        
        # 低开
        df =  get_price(stock_list, end_date=date, frequency='daily', fields=['close'], count=1, panel=False, fill_paused=False, skip_paused=True).set_index('code') if len(stock_list) != 0 else pd.DataFrame()
        df['open_pct'] = [current_data[s].day_open/df.loc[s, 'close'] for s in stock_list]
        df = df[(0.96 <= df['open_pct']) & (df['open_pct'] <= 0.97)] #低开越多风险越大，选择3个多点即可
        stock_list = list(df.index)
        
        # 买入
        if len(context.portfolio.positions) == 0:
            for s in stock_list:
                #####################################此处为新增加自动化实盘交易的代码###############################
                #调用实盘买入方法，参考原策略中的order_target_value买入仓位进行设置
                try:
                    if A.isShiPan==1:
                        #获取股票当前最新价格
                        current_data = get_current_data()
                        current_price = current_data[s].last_price
                        #获取股票买入数量，需要为100的整数倍
                        vol = int(account_total1/len(stock_list)/current_price/100)*100
                        #执行买入，以当前价格上浮1%进行挂价
                        buy_stock(s[:6],round(current_price*1.01,2),vol)
                except Exception as e:
                    print(f"实盘买入执行报错:{e}")
                #####################################此处为新增加自动化实盘交易的代码###############################
                order_target_value(s, context.portfolio.total_value/len(stock_list))
                print( '买入', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')



def sell(context):
    #####################################此处为新增加自动化实盘交易的代码###############################
    #获取账户持仓信息
    try:
        if A.isShiPan==1:
            print('开始获取持仓信息')
            holdings_dict={}
            holdings = get_position()
            if holdings and len(holdings)>0:
                for i in holdings:
                    if int(i['可用余额'])>0:
                        stock_code=i['证券代码']
                        holdings_dict[stock_code]=int(i['可用余额'])
            print('账号持仓')
            print(holdings_dict)
    except Exception as e:
        holdings_dict={}
        print(f"实盘买入执行报错:{e}")
    #####################################此处为新增加自动化实盘交易的代码###############################
    
    # 基础信息
    date = transform_date(context.previous_date, 'str')
    current_data = get_current_data()
    
    # 根据时间执行不同的卖出策略
    if str(context.current_dt)[-8:] == '11:28:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and (current_data[s].last_price < current_data[s].high_limit) and (current_data[s].last_price > context.portfolio.positions[s].avg_cost)):
                #####################################此处为新增加自动化实盘交易的代码###############################
                #调用实盘卖出方法，参考原策略中的order_target_value卖出仓位进行设置
                try:
                    if A.isShiPan==1:
                        #获取股票当前最新价格
                        current_data = get_current_data()
                        current_price = current_data[s].last_price
                        #获取股票代码
                        instrument=s[:6]
                        #执行卖出，以当前价格下幅1%进行挂价，卖出可卖的所有股票
                        sell_stock(instrument,round(current_price*0.99,2),holdings_dict[instrument])
                except Exception as e:
                    print(f"实盘买入执行报错:{e}")
                #####################################此处为新增加自动化实盘交易的代码###############################
                order_target_value(s, 0)
                print( '止盈卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')
    
    if str(context.current_dt)[-8:] == '14:50:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and (current_data[s].last_price < current_data[s].high_limit)):
                #####################################此处为新增加自动化实盘交易的代码###############################
                #调用实盘卖出方法，参考原策略中的order_target_value卖出仓位进行设置
                try:
                    if A.isShiPan==1:
                        #获取股票当前最新价格
                        current_data = get_current_data()
                        current_price = current_data[s].last_price
                        #获取股票代码
                        instrument=s[:6]
                        #执行卖出，以当前价格下幅1%进行挂价，卖出可卖的所有股票
                        sell_stock(instrument,round(current_price*0.99,2),holdings_dict[instrument])
                except Exception as e:
                    print(f"实盘买入执行报错:{e}")
                #####################################此处为新增加自动化实盘交易的代码###############################
                order_target_value(s, 0)
                print( '止损卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')


############################################################################################################################################################################

# 处理日期相关函数
def transform_date(date, date_type):
    if type(date) == str:
        str_date = date
        dt_date = dt.datetime.strptime(date, '%Y-%m-%d')
        d_date = dt_date.date()
    elif type(date) == dt.datetime:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = date
        d_date = dt_date.date()
    elif type(date) == dt.date:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = dt.datetime.strptime(str_date, '%Y-%m-%d')
        d_date = date
    dct = {'str':str_date, 'dt':dt_date, 'd':d_date}
    return dct[date_type]

def get_shifted_date(date, days, days_type='T'):
    #获取上一个自然日
    d_date = transform_date(date, 'd')
    yesterday = d_date + dt.timedelta(-1)
    #移动days个自然日
    if days_type == 'N':
        shifted_date = yesterday + dt.timedelta(days+1)
    #移动days个交易日
    if days_type == 'T':
        all_trade_days = [i.strftime('%Y-%m-%d') for i in list(get_all_trade_days())]
        #如果上一个自然日是交易日，根据其在交易日列表中的index计算平移后的交易日        
        if str(yesterday) in all_trade_days:
            shifted_date = all_trade_days[all_trade_days.index(str(yesterday)) + days + 1]
        #否则，从上一个自然日向前数，先找到最近一个交易日，再开始平移
        else: #否则，从上一个自然日向前数，先找到最近一个交易日，再开始平移
            for i in range(100):
                last_trade_date = yesterday - dt.timedelta(i)
                if str(last_trade_date) in all_trade_days:
                    shifted_date = all_trade_days[all_trade_days.index(str(last_trade_date)) + days + 1]
                    break
    return str(shifted_date)



# 过滤函数
def filter_new_stock(initial_list, date, days=250):
    d_date = transform_date(date, 'd')
    return [stock for stock in initial_list if d_date - get_security_info(stock).start_date > dt.timedelta(days=days)]

def filter_st_stock(initial_list, date):
    str_date = transform_date(date, 'str')
    if get_shifted_date(str_date, 0, 'N') != get_shifted_date(str_date, 0, 'T'):
        str_date = get_shifted_date(str_date, -1, 'T')
    df = get_extras('is_st', initial_list, start_date=str_date, end_date=str_date, df=True)
    df = df.T
    df.columns = ['is_st']
    df = df[df['is_st'] == False]
    filter_list = list(df.index)
    return filter_list

def filter_kcbj_stock(initial_list):
    return [stock for stock in initial_list if stock[0] != '4' and stock[0] != '8' and stock[:2] != '68']

def filter_paused_stock(initial_list, date):
    df = get_price(initial_list, end_date=date, frequency='daily', fields=['paused'], count=1, panel=False, fill_paused=True)
    df = df[df['paused'] == 0]
    paused_list = list(df.code)
    return paused_list



# 每日初始股票池
def prepare_stock_list(date): 
    initial_list = get_all_securities('stock', date).index.tolist()
    initial_list = filter_kcbj_stock(initial_list)
    initial_list = filter_new_stock(initial_list, date)
    initial_list = filter_st_stock(initial_list, date)
    initial_list = filter_paused_stock(initial_list, date)
    return initial_list

# 筛选出某一日涨停的股票
def get_hl_stock(initial_list, date):
    df = get_price(initial_list, end_date=date, frequency='daily', fields=['close','high','high_limit'], count=1, panel=False, fill_paused=False, skip_paused=False)
    df = df.dropna() #去除停牌
    df = df[df['close'] == df['high_limit']]
    hl_list = list(df.code)
    return hl_list

# 计算涨停数
def get_hl_count_df(hl_list, date, watch_days):
    # 获取watch_days的数据
    df = get_price(hl_list, end_date=date, frequency='daily', fields=['low','close','high_limit'], count=watch_days, panel=False, fill_paused=False, skip_paused=False)
    df.index = df.code
    #计算涨停与一字涨停数，一字涨停定义为最低价等于涨停价
    hl_count_list = []
    extreme_hl_count_list = []
    for stock in hl_list:
        df_sub = df.loc[stock]
        hl_days = df_sub[df_sub.close==df_sub.high_limit].high_limit.count()
        extreme_hl_days = df_sub[df_sub.low==df_sub.high_limit].high_limit.count()
        hl_count_list.append(hl_days)
        extreme_hl_count_list.append(extreme_hl_days)
    #创建df记录
    df = pd.DataFrame(index=hl_list, data={'count':hl_count_list, 'extreme_count':extreme_hl_count_list})
    return df

# 计算连板数
def get_continue_count_df(hl_list, date, watch_days):
    df = pd.DataFrame()
    for d in range(2, watch_days+1):
        HLC = get_hl_count_df(hl_list, date, d)
        CHLC = HLC[HLC['count'] == d]
        df = df.append(CHLC)
    stock_list = list(set(df.index))
    ccd = pd.DataFrame()
    for s in stock_list:
        tmp = df.loc[[s]]
        if len(tmp) > 1:
            M = tmp['count'].max()
            tmp = tmp[tmp['count'] == M]
        ccd = ccd.append(tmp)
    if len(ccd) != 0:
        ccd = ccd.sort_values(by='count', ascending=False)    
    return ccd

# 计算股票处于一段时间内相对位置
def get_relative_position_df(stock_list, date, watch_days):
    if len(stock_list) != 0:
        df = get_price(stock_list, end_date=date, fields=['high', 'low', 'close'], count=watch_days, fill_paused=False, skip_paused=False, panel=False).dropna()
        close = df.groupby('code').apply(lambda df: df.iloc[-1,-1])
        high = df.groupby('code').apply(lambda df: df['high'].max())
        low = df.groupby('code').apply(lambda df: df['low'].min())
        result = pd.DataFrame()
        result['rp'] = (close-low) / (high-low)
        return result
    else:
        return pd.DataFrame(columns=['rp'])
