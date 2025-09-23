import time
from multiprocessing import Queue
from typing import Dict

from core.strategy.base_strategy import BaseStrategy


class SellStrategy(BaseStrategy):
    """卖出策略，纯计算逻辑"""

    def __init__(self, data_queue: Queue, pos_queue: Queue):
        super().__init__(data_queue, pos_queue)
        self.last_sell_time = {}
        self.grid_size = 0.01  # 网格大小比例1%

    def generate_signal(self, stock_code: str, market_data: Dict, position: Dict) -> Dict:
        """生成卖出信号"""

        # 检查最小卖出间隔
        if stock_code in self.last_sell_time:
            if time.time() - self.last_sell_time[stock_code] < self.min_interval:
                return None

        # 计算网格卖出条件
        bid_prices = market_data.get('bidPrice', [])
        ask_prices = market_data.get('askPrice', [])
        last_price = market_data.get('lastPrice', 0)

        can_use_volume = position.get(stock_code, 0)

        if bid_prices and ask_prices and can_use_volume > 0:
            spread = ask_prices[0] - bid_prices[0]
            if spread <= last_price * self.grid_size:
                self.last_sell_time[stock_code] = time.time()
                return {
                    'stock_code': stock_code,
                    'price': bid_prices[0] + 0.001,
                    'volume': int(can_use_volume),  # 由主进程控制实际仓位
                    'action': 'sell',
                    'remark': '网格策略卖出'
                }
        return None

    @property
    def min_interval(self) -> int:
        """最小卖出间隔时间(秒)"""
        return 60 * 5  # 5分钟
