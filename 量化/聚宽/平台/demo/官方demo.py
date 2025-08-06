# coding = udf-8

# �����һʱ���۸�߳�����ƽ����1%, ��ȫ������
# �����һʱ���۸��������ƽ����, ��ղ�����
# ����ۿ�����
import jqdata

# ��ʼ���������趨Ҫ�����Ĺ�Ʊ����׼�ȵ�
def initialize(context):
    # ����һ��ȫ�ֱ���, ����Ҫ�����Ĺ�Ʊ
    # 000001(��Ʊ:ƽ������)
    g.security = '000001.XSHE'
    # �趨����300��Ϊ��׼
    set_benchmark('000300.XSHG')
    # ������̬��Ȩģʽ(��ʵ�۸�)
    set_option('use_real_price', True)
    # ���к���
    run_daily(market_open, time='every_bar')

# ÿ����λʱ��(�������ز�,��ÿ�����һ��,���������,��ÿ���ӵ���һ��)����һ��
def market_open(context):
    security = g.security
    # ��ȡ��Ʊ�����̼�
    close_data = attribute_history(security, 5, '1d', ['close'])
    # ȡ�ù�ȥ�����ƽ���۸�
    MA5 = close_data['close'].mean()
    # ȡ����һʱ���۸�
    current_price = close_data['close'][-1]
    # ȡ�õ�ǰ���ֽ�
    cash = context.portfolio.available_cash

    # �����һʱ���۸�߳�����ƽ����1%, ��ȫ������
    if current_price > 1.01*MA5:
        # ������ cash �����Ʊ
        order_value(security, cash)
        # ��¼�������
        log.info("Buying %s" % (security))
    # �����һʱ���۸��������ƽ����, ��ղ�����
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        # �������й�Ʊ,ʹ��ֻ��Ʊ�����ճ�����Ϊ0
        order_target(security, 0)
        # ��¼�������
        log.info("Selling %s" % (security))
    # ������һʱ���۸�
    record(stock_price=current_price)