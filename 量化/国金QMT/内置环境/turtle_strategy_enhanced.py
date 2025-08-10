# coding:gbk
"""
海龟交易策略期货版（修正版）
基于国金QMT平台实现的海龟交易策略

主要改进点：
1. 分离多空持仓状态管理
2. 增强ATR计算精度
3. 优化资金管理系统
4. 增加异常处理机制
5. 改进日志系统
"""

import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd

# 设置日志文件路径
LOG_DIR = "/Users/loay/PycharmProjects/Quantitative_Trading/量化/国金QMT/内置环境/logs"
os.makedirs(LOG_DIR, exist_ok=True)


class TurtleStrategy:
    def __init__(self):
        """初始化策略参数"""
        self.logger = self.setup_logger()
        self.strategy_params = {
            'entry_window': 10,  # 入市通道周期
            'exit_window': 4,  # 离市通道周期
            'atr_window': 10,  # ATR计算周期
            'stop_profit_ratio': 0.2,  # 止盈比例
            'stop_loss_multiplier': 2,  # 止损ATR倍数
            'total_capital': 100000,  # 总资金
            'margin_ratio': 0.1,  # 保证金比例
            'slippage': 0.001  # 滑点比例
        }
        self.position_state = {
            'long_position': 0,  # 多头持仓状态
            'short_position': 0,  # 空头持仓状态
            'entry_price': 0,  # 入市价格
            'highest_after_entry': 0,  # 入市后最高价
            'lowest_after_entry': 0,  # 入市后最低价
            'N': 0  # 波动幅度(ATR)
        }

    def setup_logger(self):
        """配置日志系统"""
        logger = logging.getLogger('TurtleStrategy')
        logger.setLevel(logging.INFO)

        # 创建文件handler
        log_file = os.path.join(LOG_DIR, f'turtle_strategy_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='gbk')
        file_handler.setLevel(logging.INFO)

        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 定义格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加handler
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def init(self, ContextInfo):
        """初始化函数"""
        self.logger.info("=" * 60)
        self.logger.info("开始初始化海龟交易策略(修正版)")
        self.logger.info("=" * 60)

        # 设置交易标的
        ContextInfo.stock_code = 'rb00.SF'
        ContextInfo.set_universe([ContextInfo.stock_code])
        self.logger.info(f"设置交易标的: {ContextInfo.stock_code}")

        # 初始化策略参数
        for param, value in self.strategy_params.items():
            setattr(ContextInfo, param, value)
            self.logger.info(f"参数设置: {param} = {value}")

        # 初始化状态变量
        for state, value in self.position_state.items():
            setattr(ContextInfo, state, value)

        self.logger.info("策略初始化完成\n")

    def handlebar(self, ContextInfo):
        """主处理函数"""
        try:
            self.logger.info("\n" + "=" * 60)
            self.logger.info(f"开始处理Bar数据 (位置: {ContextInfo.barpos})")

            # 检查数据是否足够
            required_data = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window)
            if ContextInfo.barpos < required_data:
                self.logger.warning(f"数据不足，需要{required_data}条，当前只有{ContextInfo.barpos}条")
                return

            # 获取价格数据
            price_data = self.get_price_data(ContextInfo)
            if price_data is None or len(price_data) < required_data:
                self.logger.error("获取价格数据失败")
                return

            # 计算ATR
            ContextInfo.N = self.calculate_atr(price_data, ContextInfo.atr_window)
            if ContextInfo.N <= 0:
                self.logger.error("ATR计算异常")
                return

            # 获取账户信息
            account_info = self.get_account_info(ContextInfo.account_id)
            if account_info is None:
                self.logger.error("获取账户信息失败")
                return

            # 生成交易信号
            current_position = account_info['positions'].get(ContextInfo.stock_code, 0)
            signal = self.generate_signal(ContextInfo, price_data, current_position)

            # 执行交易
            if signal != (0, 0):
                self.execute_trade(ContextInfo, signal, price_data,
                                   account_info['available'],
                                   account_info['total_value'],
                                   current_position)

            self.logger.info("处理完成\n")

        except Exception as e:
            self.logger.error(f"处理过程中发生错误: {str(e)}", exc_info=True)

    def get_price_data(self, ContextInfo):
        """获取价格数据"""
        try:
            required_bars = max(ContextInfo.entry_window, ContextInfo.exit_window, ContextInfo.atr_window) + 5
            bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')

            # 获取历史数据
            history_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close', 'volume'],
                [ContextInfo.stock_code],
                end_time=bar_date,
                period='1d',
                count=required_bars
            )

            # 获取当日数据
            current_data = ContextInfo.get_market_data_ex(
                ['time', 'open', 'high', 'low', 'close', 'volume'],
                [ContextInfo.stock_code],
                end_time=bar_date,
                period=ContextInfo.period,
                count=1
            )

            # 合并数据
            if history_data and current_data:
                history_df = history_data[ContextInfo.stock_code]
                current_df = current_data[ContextInfo.stock_code]
                return pd.concat([history_df[:-1], current_df], ignore_index=True)

            return None

        except Exception as e:
            self.logger.error(f"获取价格数据异常: {str(e)}")
            return None

    def calculate_atr(self, data, window):
        """计算ATR指标"""
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values

            # 计算真实波幅(TR)
            tr = np.maximum(high[1:] - low[1:],
                            np.abs(high[1:] - close[:-1]))
            tr = np.maximum(tr, np.abs(low[1:] - close[:-1]))

            # 计算ATR
            return np.mean(tr[-window:])

        except Exception as e:
            self.logger.error(f"ATR计算异常: {str(e)}")
            return 0

    def generate_signal(self, ContextInfo, price_data, current_position):
        """生成交易信号"""
        try:
            close = price_data['close'].values
            high = price_data['high'].values
            low = price_data['low'].values
            volume = price_data['volume'].values

            current_price = close[-1]
            current_high = high[-1]
            current_low = low[-1]

            # 计算通道
            upper_channel = np.max(high[-ContextInfo.entry_window - 1:-1])
            lower_channel = np.min(low[-ContextInfo.entry_window - 1:-1])
            exit_upper = np.max(high[-ContextInfo.exit_window - 1:-1])
            exit_lower = np.min(low[-ContextInfo.exit_window - 1:-1])

            # 更新最高最低价
            if ContextInfo.long_position == 1 or ContextInfo.short_position == 1:
                ContextInfo.highest_after_entry = max(ContextInfo.highest_after_entry, current_high)
                ContextInfo.lowest_after_entry = min(ContextInfo.lowest_after_entry, current_low)

            # 波动率过滤
            atr_ratio = ContextInfo.N / current_price
            if atr_ratio < 0.005:  # 波动率过小不交易
                return (0, 0)

            # 无持仓时判断开仓信号
            if ContextInfo.long_position == 0 and ContextInfo.short_position == 0:
                # 多头开仓信号
                if (current_price > upper_channel) and (volume[-1] > np.mean(volume[-5:])):
                    ContextInfo.highest_after_entry = current_high
                    ContextInfo.lowest_after_entry = current_low
                    return (1, 1)

                # 空头开仓信号
                elif (current_price < lower_channel) and (volume[-1] > np.mean(volume[-5:])):
                    ContextInfo.highest_after_entry = current_high
                    ContextInfo.lowest_after_entry = current_low
                    return (1, -1)

            # 多头平仓信号
            elif ContextInfo.long_position == 1:
                stop_profit_price = ContextInfo.highest_after_entry - (
                        ContextInfo.highest_after_entry - ContextInfo.entry_price) * ContextInfo.stop_profit_ratio
                stop_loss_price = ContextInfo.entry_price - ContextInfo.stop_loss_multiplier * ContextInfo.N

                if (current_price < exit_lower and current_price < stop_profit_price) or \
                        (current_price < stop_loss_price):
                    return (-1, 1)

            # 空头平仓信号
            elif ContextInfo.short_position == 1:
                stop_profit_price = ContextInfo.lowest_after_entry + (
                        ContextInfo.entry_price - ContextInfo.lowest_after_entry) * ContextInfo.stop_profit_ratio
                stop_loss_price = ContextInfo.entry_price + ContextInfo.stop_loss_multiplier * ContextInfo.N

                if (current_price > exit_upper and current_price > stop_profit_price) or \
                        (current_price > stop_loss_price):
                    return (-1, -1)

            return (0, 0)

        except Exception as e:
            self.logger.error(f"信号生成异常: {str(e)}")
            return (0, 0)

    def execute_trade(self, ContextInfo, signal, price_data, available_cash, total_value, current_position):
        """执行交易"""
        try:
            signal_type, position_type = signal
            current_price = price_data['close'].iloc[-1]
            contract_multiplier = ContextInfo.get_contract_multiplier(ContextInfo.stock_code)

            # 计算头寸规模
            capital = ContextInfo.long_capital if position_type > 0 else ContextInfo.short_capital
            position_size = int((capital * ContextInfo.margin_ratio) / (current_price * contract_multiplier))
            position_size = max(1, position_size)  # 至少1手

            # 考虑滑点
            exec_price = current_price * (1 + ContextInfo.slippage) if position_type > 0 else \
                current_price * (1 - ContextInfo.slippage)

            # 开仓操作
            if signal_type > 0:
                if position_type > 0 and ContextInfo.long_position == 0:  # 开多
                    order_info = passorder(0, 1101, ContextInfo.account_id, ContextInfo.stock_code,
                                           5, exec_price, position_size, 1, ContextInfo)
                    ContextInfo.long_position = 1
                    ContextInfo.entry_price = exec_price
                    self.logger.info(f"开多仓成功: {order_info}")

                elif position_type < 0 and ContextInfo.short_position == 0:  # 开空
                    order_info = passorder(3, 1101, ContextInfo.account_id, ContextInfo.stock_code,
                                           5, exec_price, position_size, 1, ContextInfo)
                    ContextInfo.short_position = 1
                    ContextInfo.entry_price = exec_price
                    self.logger.info(f"开空仓成功: {order_info}")

            # 平仓操作
            elif signal_type < 0:
                if position_type > 0 and ContextInfo.long_position == 1:  # 平多
                    order_info = passorder(7, 1101, ContextInfo.account_id, ContextInfo.stock_code,
                                           5, exec_price, abs(current_position), 1, ContextInfo)
                    ContextInfo.long_position = 0
                    self.logger.info(f"平多仓成功: {order_info}")

                elif position_type < 0 and ContextInfo.short_position == 1:  # 平空
                    order_info = passorder(9, 1101, ContextInfo.account_id, ContextInfo.stock_code,
                                           5, exec_price, current_position, 1, ContextInfo)
                    ContextInfo.short_position = 0
                    self.logger.info(f"平空仓成功: {order_info}")

            # 重置状态
            if signal_type < 0:
                ContextInfo.entry_price = 0
                ContextInfo.highest_after_entry = 0
                ContextInfo.lowest_after_entry = 0

        except Exception as e:
            self.logger.error(f"交易执行异常: {str(e)}")


# 策略实例化
strategy = TurtleStrategy()


# QMT标准函数
def init(ContextInfo):
    strategy.init(ContextInfo)


def handlebar(ContextInfo):
    strategy.handlebar(ContextInfo)
