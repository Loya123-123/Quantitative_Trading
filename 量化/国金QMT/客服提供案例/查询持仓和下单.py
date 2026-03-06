
import random
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
from xtquant import xtconstant

# miniQMT安装路径
mini_qmt_path = r'C:\国金QMT交易端模拟\userdata_mini'

# 创建session_id
session_id = int(random.randint(100000, 999999))
# 创建交易对象
xt_trader = XtQuantTrader(mini_qmt_path, session_id)
# 启动交易对象
xt_trader.start()
# 连接客户端
connect_result = xt_trader.connect()

if connect_result == 0:
    print('连接成功')

account_id = '130810'
# 创建账号对象
account = StockAccount(account_id,'FUTURE')
# 订阅账号
res = xt_trader.subscribe(account)
print('订阅成功')
print(res)

# 下单
order_id = xt_trader.order_stock(account, stock_code='SA504.SF', order_type=xtconstant.FUTURE_OPEN_LONG, order_volume=100, price_type=xtconstant.LATEST_PRICE, price=-1)

#order_id = trader_instance.order_stock(account_instance, futures_code, order_type, 1, xtconstant.LATEST_PRICE, price=-1)


positions2 = xt_trader.query_position_statistics(account)
print(len(positions2))
for position in positions2:
    print('账号类型:',position.account_type)
    print('资金账号:',position.account_id)
    print('证券代码:',position.stock_code)
    print('持仓数量:',position.volume)
    print('可用数量:',position.can_use_volume)
    print('开仓价:',position.open_price)
    print('市值:',position.market_value)
    print('冻结数量:',position.frozen_volume)
    print('在途股份:',position.on_road_volume)
    print('昨夜拥股:',position.yesterday_volume)
    print('成本价:',position.avg_price)



positions = xt_trader.query_stock_positions(account)
print(len(positions))

for position in positions:
    print('账号类型:',position.account_type)
    print('资金账号:',position.account_id)
    print('证券代码:',position.stock_code)
    print('持仓数量:',position.volume)
    print('可用数量:',position.can_use_volume)
    print('开仓价:',position.open_price)
    print('市值:',position.market_value)
    print('冻结数量:',position.frozen_volume)
    print('在途股份:',position.on_road_volume)
    print('昨夜拥股:',position.yesterday_volume)
    print('成本价:',position.avg_price)


trades = xt_trader.query_stock_trades(account)

for trade in trades:
    print('账号类型:',trades.account_type)
    print('资金账号:',trades.account_id)
    print('证券代码:',trades.stock_code)
    print('委托类型:',trades.order_type)
    print('成交编号:',trades.traded_id)
    print('成交时间:',trades.traded_time)
    print('成交均价:',trades.traded_price)
    print('成交数量:',trades.traded_volume)
    print('成交金额:',trades.traded_amount)
    print('订单编号:',trades.order_id)
    print('柜台合同编号:',trades.order_sysid)

orders = xt_trader.query_stock_orders(account)
for order in orders:
    print('账号类型:',order.account_type)
    print('资金账号:',order.account_id)
    print('证券代码:',order.stock_code)
    print('订单编号:',order.order_id)
    print('柜台合同编号:',order.order_sysid)
    print('报单时间:',order.order_time)
    print('委托类型:',order.order_type)
    print('委托数量:',order.order_volume)
    print('报价类型:',order.price_type)
    print('委托价格:',order.price)
    print('成交数量:',order.traded_volume)
    print('成交均价:',order.traded_price)
    print('委托状态:',order.status_msg)
    print('委托状态描述:',order.order_status)




