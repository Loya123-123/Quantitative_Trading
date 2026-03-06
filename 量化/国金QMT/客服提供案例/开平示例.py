import time
from datetime import datetime
import sys
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print(datetime.now(), '连接断开回调')

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print(datetime.now(), '委托回调 投资备注', order.order_remark)

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print(datetime.now(), '成交回调', trade.order_remark,
              f"委托方向(48买 49卖) {trade.offset_flag} 成交价格 {trade.traded_price} 成交数量 {trade.traded_volume}")

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        # print("on order_error callback")
        # print(order_error.order_id, order_error.error_id, order_error.error_msg)
        print(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print(datetime.now(), sys._getframe().f_code.co_name)

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print(f"异步委托回调 投资备注: {response.order_remark}")

    def on_cancel_order_stock_async_response(self, response):
        """
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        print(datetime.now(), sys._getframe().f_code.co_name)

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        print(datetime.now(), sys._getframe().f_code.co_name)


# 1. 初始化
path = r'E:\迅投极速交易终端睿智融科版\userdata'
session_id = int(time.time())
xt_trader = XtQuantTrader(path, session_id)
acc = StockAccount('1043955', 'FUTURE')


def open_long(code, info="strategy_name"):
    """多开"""
    xt_trader.order_stock_async(acc, code, xtconstant.FUTURE_OPEN_LONG, 1, xtconstant.LATEST_PRICE, price=0, order_remark=info)


# 连接交易
callback = MyXtQuantTraderCallback()
xt_trader.register_callback(callback)
xt_trader.start()  # 启动交易线程

# 连接交易主推
connect_result = xt_trader.connect()
subscribe_result = xt_trader.subscribe(acc)  # 获取交易主推

# 开始下单
code = 'i2512.DF'
xt_trader.order_stock_async(acc, code, xtconstant.FUTURE_OPEN_LONG, 1, xtconstant.LATEST_PRICE, 0, )  # 多开
xt_trader.order_stock_async(acc, code, xtconstant.FUTURE_OPEN_SHORT, 1, xtconstant.LATEST_PRICE, 0, )  # 空开
xt_trader.order_stock_async(acc, code, xtconstant.FUTURE_CLOSE_LONG_HISTORY_FIRST, 1, xtconstant.LATEST_PRICE, 0)  # 平多
xt_trader.order_stock_async(acc, code, xtconstant.FUTURE_CLOSE_SHORT_HISTORY_FIRST, 1, xtconstant.LATEST_PRICE, 0, )  # 平空
# https://dict.thinktrader.net/nativeApi/xttrader.html?id=S7b19l#%E8%82%A1%E7%A5%A8%E5%90%8C%E6%AD%A5%E6%92%A4%E5%8D%95-1