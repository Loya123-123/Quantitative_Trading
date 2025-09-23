# coding:utf-8
import time
from abc import ABC, abstractmethod
from multiprocessing import Queue
from typing import Dict


class BaseStrategy(ABC):
    """纯计算策略基类，完全独立于交易系统"""

    def __init__(self, data_queue: Queue, pos_queue: Queue):
        """初始化策略"""
        self.data_queue = data_queue
        self.pos_queue = pos_queue

    @abstractmethod
    def generate_signal(self, stock_code: str, market_data: Dict, pos_data: Dict) -> Dict:
        """生成交易信号
        Returns:
            Dict: 交易信号，格式为 {
                'stock_code': str,
                'price': float,
                'volume': int,
                'action': 'buy'/'sell',
                'remark': str
            }
        """
        pass

    def run_strategy(self, signal_queue: Queue):
        """运行策略主循环"""
        while True:
            try:
                if not self.data_queue.empty() and not self.pos_queue.empty():
                    data = self.data_queue.get()
                    pos = self.pos_queue.get()
                    if isinstance(data, dict) and isinstance(pos, dict):
                        for stock_code, tick_data in data.items():
                            signal = self.generate_signal(stock_code, tick_data, pos)
                            if signal:
                                signal_queue.put(signal)
                time.sleep(0.1)
            except Exception as e:
                print(f"策略运行异常: {str(e)}")
                time.sleep(1)

    @property
    def min_interval(self) -> int:
        """默认交易间隔时间"""
        return 10
