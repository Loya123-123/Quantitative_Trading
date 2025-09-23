import time
from multiprocessing import Queue
from typing import Dict

from core.strategy.base_strategy import BaseStrategy


class BuyStrategy(BaseStrategy):
    """买入策略，纯计算逻辑"""

    def __init__(self, data_queue: Queue, pos_queue: Queue):
        super().__init__(data_queue, pos_queue)
        self.last_buy_time = {}
        self.grid_size = 0.01  # 网格大小比例1%

    def generate_signal(self, stock_code: str, market_data: Dict, position: Dict) -> Dict:
        """生成买入信号"""
        # 检查最小买入间隔
        if stock_code in self.last_buy_time:
            if time.time() - self.last_buy_time[stock_code] < self.min_interval:
                return None

        # 计算网格买入条件
        bid_prices = market_data.get('bidPrice', [])
        ask_prices = market_data.get('askPrice', [])
        last_price = market_data.get('lastPrice', 0)

        timestamp = str(int(time.time()))
        tp = round(ask_prices[0] - 0.001, 3)
        aribtrage = f"B:{round(tp, 3)}"
        if bid_prices and ask_prices:
            spread = ask_prices[0] - bid_prices[0]
            if spread <= last_price * self.grid_size:
                self.last_buy_time[stock_code] = time.time()
                return {
                    'stock_code': stock_code,
                    'price': tp,
                    'volume': 100,  # 固定数量，由主进程控制实际仓位
                    'action': 'buy',
                    'remark': aribtrage,
                    'timestamp': timestamp,
                }
        return None

    @property
    def min_interval(self) -> int:
        """最小买入间隔时间(秒)"""
        return 60 * 5  # 5分钟
