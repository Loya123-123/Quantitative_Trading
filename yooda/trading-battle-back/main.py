# coding:utf-8
import logging
import time
import traceback
from multiprocessing import Process, Queue


# 配置日志
def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


# 初始化日志记录器
main_logger = setup_logger('main', 'logs/main.log')
buy_logger = setup_logger('buy', 'logs/buy.log')
sell_logger = setup_logger('sell', 'logs/sell.log')


class SubProcess:
    def __init__(self, buy_signal_queue, sell_signal_queue, data_queue, pos_queue):
        self.buy_strategy = BuyStrategy(data_queue, pos_queue)
        self.sell_strategy = SellStrategy(data_queue, pos_queue)
        # 设置策略的信号队列
        self.buy_signal_queue = buy_signal_queue
        self.sell_signal_queue = sell_signal_queue

    def run_buy_process(self):
        """买入进程主函数"""
        buy_logger.info("买入进程启动")
        try:
            while True:
                try:
                    # 运行买入策略
                    self.buy_strategy.run_strategy(self.buy_signal_queue)
                    time.sleep(1)
                except Exception as e:
                    buy_logger.error(f"买入进程异常: {str(e)}")
                    time.sleep(5)
        except KeyboardInterrupt:
            buy_logger.info("买入进程正常退出")

    def run_sell_process(self):
        """卖出进程主函数"""
        sell_logger.info("卖出进程启动")
        try:
            while True:
                try:
                    # 运行卖出策略
                    self.sell_strategy.run_strategy(self.sell_signal_queue)
                    time.sleep(1)
                except Exception as e:
                    sell_logger.error(f"卖出进程异常: {str(e)}")
                    time.sleep(5)
        except KeyboardInterrupt:
            sell_logger.info("卖出进程正常退出")


class MainProcess:
    def __init__(self):
        # 初始化交易接口
        self.trader = None
        # 创建资金账号为 800068 的证券账号对象 股票账号为STOCK 信用CREDIT 期货FUTURE
        self.account = StockAccount("8886650815", "stock")
        self.order_manager = None
        self.buy_strategy = None
        self.sell_strategy = None
        self.path = r'C:\国金证券QMT交易端\userdata_mini'
        # 生成session id 整数类型 同时运行的策略不能重复
        self.session_id = int(time.time())

        # 创建信号队列和数据队列
        self.buy_signal_queue = Queue()
        self.sell_signal_queue = Queue()
        self.data_queue = Queue()  # 用于向策略进程发送行情数据
        self.pos_queue = Queue()  # 用于向策略进程发送持仓数据

        # 初始化交易连接
        self.init_trading()

        # 订阅行情
        self.subscribe_market_data()

    def init_trading(self):
        """初始化交易连接"""
        try:
            self.trader = XtQuantTrader(self.path, self.session_id)
            # 创建资金账号为 800068 的证券账号对象 股票账号为STOCK 信用CREDIT 期货FUTURE
            self.account = StockAccount("8886650815", "stock")

            self.order_manager = OrderTrackingManager(self.trader, self.account)
            # 注册回调
            self.trader.register_callback(self.order_manager)
            self.trader.start()

            # 建立交易连接，返回0表示连接成功
            connect_result = self.trader.connect()
            main_logger.info(f'建立交易连接:{connect_result}')

            # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
            subscribe_result = self.trader.subscribe(self.account)
            main_logger.info(f'建立订阅连接:{subscribe_result}')

            if connect_result != 0:
                main_logger.error("交易服务器连接失败")
                raise ConnectionError("交易服务器连接失败")

            main_logger.info("交易服务器连接成功")

        except Exception as e:
            main_logger.error(f"初始化交易失败: {str(e)}")
            exit()

    def subscribe_market_data(self):
        """订阅行情数据"""
        stock_list = xtdata.get_stock_list_in_sector('T0')
        if not stock_list:
            main_logger.error("获取股票列表失败")
            return

        # 过滤无效股票代码
        valid_stocks = [s for s in stock_list if s and len(s) == 9]
        if not valid_stocks:
            main_logger.error("没有有效的股票代码")
            return

        main_logger.info(f"获取到{len(stock_list)}只股票，有效股票{len(valid_stocks)}只")
        try:
            for i in stock_list:
                # 订阅股票的行情数据(设置好所有需要的盘中数据周期)
                xtdata.subscribe_quote(i, period="5m")
                xtdata.subscribe_quote(i, period="orderflow1m")
            time.sleep(1)  # 等待订阅完成
            main_logger.info(f"已成功订阅{len(valid_stocks)}只股票行情")
        except Exception as e:
            main_logger.error(f"订阅行情失败: {str(e)}")


def main():
    try:
        # 创建主进程实例
        main_process = MainProcess()
        sub_process = SubProcess(main_process.buy_signal_queue, main_process.sell_signal_queue, main_process.data_queue,
                                 main_process.pos_queue)

        # 创建并启动买入进程(设置为守护进程)
        buy_process = Process(
            target=sub_process.run_buy_process,
            name="BuyProcess",
            daemon=True
        )
        buy_process.start()
        main_logger.info(f"买入进程已启动 PID: {buy_process.pid}")

        # 创建并启动卖出进程(设置为守护进程)
        sell_process = Process(
            target=sub_process.run_sell_process,
            name="SellProcess",
            daemon=True
        )
        sell_process.start()
        main_logger.info(f"卖出进程已启动 PID: {sell_process.pid}")

        # 主进程循环
        while True:
            # 获取并发送行情数据(tick更新是间为3秒，其他k线数据按照周期更新，周期时间要大于数据更新时间)
            time.sleep(5)
            etf_list = xtdata.get_stock_list_in_sector('T0')
            full_ticks = xtdata.get_full_tick(etf_list)
            main_process.data_queue.put(full_ticks)

            # 更新最新的仓位发送给策略(柜台仓位有延迟，需要本地准确计算)
            hist_postions = query_stock_holding(main_process.account, main_process.trader)
            latest_orders = query_stock_order_info(main_process.account, main_process.trader)
            orders = []
            for o, i in latest_orders.items():
                orders.append(i)
            latest_postions = calculate_available_position(orders, hist_postions)
            main_process.pos_queue.put(latest_postions)

            # 处理买入信号
            if not main_process.buy_signal_queue.empty():
                signal = main_process.buy_signal_queue.get()
                buy_logger.info(f"执行买入: {signal}")
                # 添加账户信息到信号
                signal['account'] = main_process.account
                seq = main_process.trader.order_stock_async(
                    signal['account'], signal['stock_code'], xtconstant.STOCK_BUY,
                    signal['volume'], xtconstant.FIX_PRICE, signal['price'],
                    signal['remark'], signal['timestamp']
                )

            # 处理卖出信号
            if not main_process.sell_signal_queue.empty():
                signal = main_process.sell_signal_queue.get()
                sell_logger.info(f"执行卖出: {signal}")
                # 添加账户信息到信号
                signal['account'] = main_process.account
                seq = main_process.trader.order_stock_async(
                    signal['account'], signal['stock_code'], xtconstant.STOCK_SELL,
                    signal['volume'], xtconstant.FIX_PRICE, signal['price'],
                    signal['remark'], f"S_{signal['stock_code']}_{int(time.time())}"
                )

            time.sleep(0.1)

    except KeyboardInterrupt:
        main_logger.info("主进程收到中断信号，准备退出...")
    except Exception as e:
        main_logger.error(f"主进程异常: {str(e)}")
        traceback.print_exc()
    finally:
        main_logger.info("程序退出")


if __name__ == '__main__':
    # 导入MiniQMT模块(不能序列化)
    from xtquant.xttrader import XtQuantTrader
    from xtquant import xtconstant
    from xtquant import xtdata
    from xtquant.xttype import StockAccount

    # 导入行情委托模块(不能序列化)
    from core.order.manager import OrderTrackingManager
    from core.utils.query import calculate_available_position, query_stock_holding, query_stock_order_info

    # 导入策略模块(可以序列化)
    from core.strategy.buy_strategy import BuyStrategy
    from core.strategy.sell_strategy import SellStrategy

    main()
