#coding:gbk

"""
չʾ4���������ƺ�����Ч��
accountInfo/ orderInfo / dealInfo / positonInfo ���������
��get_trade_detail_data���صĶ�Ӧ����һ�� ��� ��python���׺�������ϸ����˵�����ĵ���
"""




def init(ContextInfo):
    ContextInfo.set_account('800000235')

def handlebar(ContextInfo):
    pass
# �ʽ��˺����ƺ���
def account_callback(ContextInfo, accountInfo):
    print('accountInfo')
    # ����ʽ��˺�״̬
    print(accountInfo.m_strStatus)

# ί�����ƺ���
def order_callback(ContextInfo, orderInfo):
    print('orderInfo')
    # ���ί��֤ȯ����
    print(orderInfo.m_strInstrumentID)

# �ɽ����ƺ���
def deal_callback(ContextInfo, dealInfo):
    print('dealInfo')
    # ����ɽ�֤ȯ����
    print(dealInfo.m_strInstrumentID)

# �ֲ����ƺ���
def position_callback(ContextInfo, positonInfo):
    print('positonInfo')
    # ����ֲ�֤ȯ����
    print(positonInfo.m_strInstrumentID)

#�µ�����ص�����
def orderError_callback(ContextInfo, passOrderInfo, msg):
    print('orderError_callback')
    #����µ���Ϣ�Լ�������Ϣ
    print (passOrderInfo.orderCode)
    print (msg)


