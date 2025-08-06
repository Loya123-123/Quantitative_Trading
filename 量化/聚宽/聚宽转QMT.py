# coding = udf-8
# /usr/bin/env python
'''
��QMT-�ۿ����ϵͳ��ʹ��˵��

ԭ�����,�̳оۿ�Ľ��׺�����
��ȡ�µ���ĺ����������ѽ������ݷ��͵�������
�������ȫ��Դ���븴�Ƶ��ۿ���ԵĿ�ͷ�Ϳ���
ʹ��ǰ��ģ���̲���һ������
�����������ȫ�����Ƶ����ԵĿ�ͷ�Ϳ���
����Ա��֤ȯ����
΢�ţ�gjtt9892
'''

import requests
import json
import pandas as pd
from jqdata import *
url='http://101.34.65.108'
port=8888
#�Զ������������
url_code='63d85b6189e42cba63feea36381da615c31ad8e36ae420ed67f60f3598efc9ad'
#�ҹ���Աע�ᣬÿ������һ���������ظ��������ִ�Сд����غ�ע��ʱһ��
password='wei_test'
class joinquant_trader:
    def __init__(self,url='http://101.34.65.108',
                 port=8888,
                 url_code='63d85b6189e42cba63feea36381da615c31ad8e36ae420ed67f60f3598efc9ad',
                 password='wei_test'):
        '''
        ��ȡ����������
        '''
        self.url=url
        self.port=port
        self.url_code=url_code
        self.password=password
    def get_user_data(self,data_type='�û���Ϣ'):
        '''
        ��ȡʹ�õ�����
        data_type='�û���Ϣ','ʵʱ����',��ʷ����','���ʵʱ����','�����ʷ����'
        '''
        url='{}:{}/_dash-update-component'.format(self.url,self.port)
        headers={'Content-Type':'application/json'}
        data={"output":"joinquant_trader_table.data@{}".format(self.url_code),
              "outputs":{"id":"joinquant_trader_table","property":"data@{}".format(self.url_code)},
              "inputs":[{"id":"joinquant_trader_password","property":"value","value":self.password},
                        {"id":"joinquant_trader_data_type","property":"value","value":data_type},
                        {"id":"joinquant_trader_text","property":"value","value":"\n               {'״̬': 'held', '�������ʱ��': 'datetime.datetime(2024, 4, 23, 9, 30)', '����': 'False', '�µ�����': '9400', '�Ѿ��ɽ�': '9400', '��Ʊ����': '001.XSHE', '����ID': '1732208241', 'ƽ���ɽ��۸�': '10.5', '�ֲֳɱ�': '10.59', '���': 'long', '���׷���': '128.31'}\n                "},
                        {"id":"joinquant_trader_run","property":"value","value":"����"},
                        {"id":"joinquant_trader_down_data","property":"value","value":"����������"}],
              "changedPropIds":["joinquant_trader_run.value"],"parsedChangedPropsIds":["joinquant_trader_run.value"]}
        res=requests.post(url=url,data=json.dumps(data),headers=headers)
        text=res.json()
        df=pd.DataFrame(text['response']['joinquant_trader_table']['data'])
        return df
    def send_order(self,result):
        '''
        ���ͽ�������
        '''
        url='{}:{}/_dash-update-component'.format(self.url,self.port)
        headers={'Content-Type':'application/json'}
        data={"output":"joinquant_trader_table.data@{}".format(self.url_code),
              "outputs":{"id":"joinquant_trader_table","property":"data@{}".format(self.url_code)},
              "inputs":[{"id":"joinquant_trader_password","property":"value","value":self.password},
                        {"id":"joinquant_trader_data_type","property":"value","value":'ʵʱ����'},
                        {"id":"joinquant_trader_text","property":"value","value":result},
                        {"id":"joinquant_trader_run","property":"value","value":"����"},
                        {"id":"joinquant_trader_down_data","property":"value","value":"����������"}],
              "changedPropIds":["joinquant_trader_run.value"],"parsedChangedPropsIds":["joinquant_trader_run.value"]}
        res=requests.post(url=url,data=json.dumps(data),headers=headers)
        text=res.json()
        df=pd.DataFrame(text['response']['joinquant_trader_table']['data'])
        return df
#�̳���
xg_data=joinquant_trader(url=url,port=port,password=password,url_code=url_code)
def send_order(result):
    '''
    ���ͺ���
    status: ״̬, һ��OrderStatusֵ
    add_time: �������ʱ��, [datetime.datetime]����
    is_buy: boolֵ, �������������ڻ�:
    ����/ƽ�� -> ��
    ����/ƽ�� -> ��
    amount: �µ�����, ������������, ��������
    filled: �Ѿ��ɽ��Ĺ�Ʊ����, ����
    security: ��Ʊ����
    order_id: ����ID
    price: ƽ���ɽ��۸�, �Ѿ��ɽ��Ĺ�Ʊ��ƽ���ɽ��۸�(һ���������ֶܷ�γɽ�)
    avg_cost: ����ʱ��ʾ������ǰ�Ĵ˹�Ʊ�ĳֲֳɱ�, ��������˴�����������. ����ʱ��ʾ�˴�����ľ���(��ͬ��price).
    side: ��/�գ�'long'/'short'
    action: ��/ƽ�� 'open'/'close'
    commission���׷��ã�Ӷ��˰�ѵȣ�
    '''
    data={}
    data['״̬']=str(result.status)
    data['�������ʱ��']=str(result.add_time)
    data['����']=str(result.is_buy)
    data['�µ�����']=str(result.amount)
    data['�Ѿ��ɽ�']=str(result.filled)
    data['��Ʊ����']=str(result.security)
    data['����ID']=str(result.order_id)
    data['ƽ���ɽ��۸�']=str(result.price)
    data['�ֲֳɱ�']=str(result.avg_cost)
    data['���']=str(result.side)
    data['���׷���']=str(result.commission)
    result=str(data)
    xg_data.send_order(result)
    return data
def xg_order(func):
    '''
    �̳�order���� ���ݽ��׺���
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return
        send_order(result)
        return result
    return wrapper
def xg_order_target(func):
    '''
    �̳�order_target���� �ٷֱ�
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return
        send_order(result)
        return result
    return wrapper

def xg_order_value(func):
    '''
    �̳�order_value���� ����
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return
        send_order(result)
        return result
    return wrapper
def xg_order_target_value(func):
    '''
    �̳�order_target_value���� ����
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return
        send_order(result)
        return result
    return wrapper
order = xg_order(order)
order_target = xg_order_target(order_target)
order_value = xg_order_value(order_value)
order_target_value = xg_order_target_value(order_target_value)