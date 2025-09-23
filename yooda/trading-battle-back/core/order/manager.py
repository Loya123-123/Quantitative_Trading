# coding:utf-8
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from xtquant import xtconstant
from xtquant import xtdata
from xtquant.xttrader import XtQuantTraderCallback

from ..utils.query import query_stock_order_info


class OrderTracker:
    """跟踪单个订单状态"""

    def __init__(self, order_id, order_type, stockcode, vol, price, cost, manager, timeout, order_sysid, market):
        self.order_id = order_id
        self.order_sysid = order_sysid
        self.market = market
        self.order_type = order_type
        self.stockcode = stockcode
        self.vol = vol
        self.price = round(price, 3)
        self.cost = round(float(cost), 3) if self.order_type in [xtconstant.STOCK_BUY, xtconstant.STOCK_SELL] else 0
        self.manager = manager
        self.timeout = timeout
        self._is_active = True
        self._completion_event = threading.Event()

    def run(self):
        """主跟踪逻辑"""
        self.start_time = time.time()
        try:
            while not self._completion_event.wait(5):

                current_status, rest_vol = self.check_order_status()
                if current_status == "已成交":
                    break

                full_tick = xtdata.get_full_tick([self.stockcode])
                current_price = round(full_tick[self.stockcode]['lastPrice'], 3)

                if self.order_type == xtconstant.STOCK_BUY:
                    sell_p = [round(p, 3) for p in full_tick[self.stockcode]['askPrice']]
                    if sell_p[0] < self.cost - 0.003:
                        self.repeat_order("回撤", rest_vol, sell_p[0])
                        break
                elif self.order_type == xtconstant.STOCK_SELL:
                    buy_p = [round(p, 3) for p in full_tick[self.stockcode]['bidPrice']]
                    if buy_p[0] > self.cost + 0.003:
                        self.repeat_order("反弹", rest_vol, buy_p[0])
                        break

                if time.time() - self.start_time > self.timeout + 50:
                    self.repeat_order("超时", rest_vol, current_price)
                    break

        except Exception as e:
            self.manager.report_error(self.order_id, str(e))
        finally:
            self._is_active = False
            self._completion_event.set()
            self.manager.remove_order(self.order_id)

    def check_order_status(self):
        """检查订单状态"""
        order_info = query_stock_order_info(self.manager.account, self.manager.trader)
        if order_info[self.order_sysid]["volume_total"] == order_info[self.order_sysid]["order_volume"]:
            return "未成交", order_info[self.order_sysid]["volume_total"]
        elif order_info[self.order_sysid]["volume_total"] < order_info[self.order_sysid]["order_volume"]:
            return "部分成交", order_info[self.order_sysid]["volume_total"]
        return "已成交", 0

    def repeat_order(self, reason, rest_vol, reprice):
        """追单操作"""
        try:
            self.manager.cancel_order(self.order_sysid, self.market)
            time.sleep(0.1)
            remark = "T"

            if reason == '超时':
                return

            if reason == '回撤':
                remark = "S"

            if reason == '反弹':
                remark = "B"

            self.manager.place_order(
                self.stockcode,
                self.order_type,
                rest_vol,
                reprice,
                f"{remark}:{reprice}"
            )
        except Exception as e:
            raise ValueError(f"{self.order_id}_追单失败: {str(e)}")


class OrderTrackingManager(XtQuantTraderCallback):
    """订单跟踪管理"""

    def __init__(self, trader, account):
        self.trader = trader
        self.account = account
        self.active_trackers = {}
        self.lock = threading.RLock()
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=50)

    def add_order(self, order_id, order_type, stockcode, vol, price, cost, order_sysid, market):
        """添加新订单进行跟踪"""
        with self.lock:
            if order_id not in self.active_trackers:
                tracker = OrderTracker(
                    order_id, order_type, stockcode, vol, price, cost,
                    self, random.randint(1, 9), order_sysid, market
                )
                future = self.executor.submit(tracker.run)
                self.active_trackers[order_id] = (tracker, future)

    def remove_order(self, order_id):
        """移除已完成订单"""
        with self.lock:
            if order_id in self.active_trackers:
                self.active_trackers.pop(order_id)

    def query_order_info(self):
        """查询订单信息"""
        orders = self.trader.query_stock_orders(self.account)
        return {
            o.order_sysid: {
                "stock": o.stock_code,
                "order_time": o.order_time,
                "order_volume": o.order_volume,
                "volume_total": o.order_volume - o.traded_volume,
                "order_status": o.order_status,
                "order_remark": o.order_remark,
                "order_type": o.order_type,
                "limit_price": o.price,
                "order_id": o.order_id
            } for o in orders
        }

    def cancel_order(self, order_sysid, market):
        """取消订单"""
        seq = self.trader.cancel_order_stock_sysid_async(self.account, market, order_sysid)
        if seq <= 0:
            raise ValueError("撤单失败")

    def place_order(self, stockcode, order_type, vol, price, remark):
        """下单"""
        seq = self.trader.order_stock_async(
            self.account, stockcode, order_type, vol,
            xtconstant.FIX_PRICE, price, remark, str(int(time.time()))
        )
        if seq <= 0:
            raise ValueError("下单失败")

    def report_error(self, order_id, error_msg):
        """报告错误"""
        print(f"Order {order_id} error: {error_msg}")

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        with self.lock:
            for tracker, _ in self.active_trackers.values():
                tracker._completion_event.set()

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
        # 属性赋值
        account_type = order.account_type  # 账号类型
        account_id = order.account_id  # 资金账号
        stock_code = order.stock_code  # 证券代码，例如"600000.SH"
        order_id = order.order_id  # 订单编号
        order_sysid = order.order_sysid  # 柜台合同编号
        order_time = order.order_time  # 报单时间
        order_type = order.order_type  # 委托类型，参见数据字典
        order_volume = order.order_volume  # 委托数量
        price_type = order.price_type  # 报价类型，该字段在返回时为柜台返回类型，不等价于下单传入的price_type，枚举值不一样功能一样，参见数据字典
        price = order.price  # 委托价格
        traded_volume = order.traded_volume  # 成交数量
        traded_price = order.traded_price  # 成交均价
        order_status = order.order_status  # 委托状态，参见数据字典
        status_msg = order.status_msg  # 委托状态描述，如废单原因
        strategy_name = order.strategy_name  # 策略名称
        order_remark = order.order_remark  # 委托备注
        direction = order.direction  # 多空方向，股票不适用；参见数据字典
        offset_flag = order.offset_flag  # 交易操作，用此字段区分股票买卖，期货开、平仓，期权买卖等；参见数据字典

        if order.strategy_name == strategy_name:
            # 该委托是由本策略发出
            ssid = order.order_sysid
            status = order.order_status
            strategy_name = order.strategy_name
            market = order.stock_code.split(".")[1]

            # print(market, strategy_name)

            if strategy_name[:1] not in ['B', 'S']:
                # 只接受买入策略推送
                return

            if ssid and status in [50, 55]:
                ## 使用cancel_order_stock_sysid_async时，投研端market参数可以填写为0，券商端按实际情况填写
                cost = strategy_name[2:]
                self.add_order(order_id, order_type, stock_code, order_volume, price, cost, order_sysid, market)
            # _cancel_order_async(order_id)
