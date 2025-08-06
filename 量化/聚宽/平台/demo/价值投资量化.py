# coding = udf-8
# /usr/bin/env python
# 我要用聚宽量化做一个量化交易策略，需要将交易策略写成代码，其中策略逻辑如下：
# 该策略采用日均线作为指标，当日10日均线向上突破20日均线时买入，每次全仓买入。
# 从买入第二天开始，当处于盈利状态时，一直持有，当日10日均线向下突破20日均线时，触发卖出。股票交易品种选择恒瑞医药

# 这个策略针对价值/投资+成长股最有效，即需要有前景，每年有业绩增长，股价长期向上爬坡的公司，
# 从胜率与盈亏比来看，胜率起根本优势，策略可以有效避免股灾不能果断卖出，泡沫不能坚持持有的人性问题。


# 恒瑞医药量化交易策略
from datetime import datetime
import logging
import pytz
import jqdata

# # 获取当前的UTC时间
# utc_now = datetime.now(pytz.utc)
# eastern = pytz.timezone('Asia/Shanghai')
# eastern_now = utc_now.astimezone(eastern)
# # 配置日志记录
# log_filename = f'market_{eastern_now.strftime("%Y%m%d")}.log'
# # log_filename = f'/Users/jianzhong/ProjectCode/StartDT/PyCharm/螃蟹/飞书文档/market_{eastern_now.strftime("%Y%m%d")}.log'
# logging.basicConfig(filename=log_filename, level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S %Z%z')
# logging.info("开始执行渠道投入费用数据脚本 开始时间：  " + eastern_now.strftime("%Y-%m-%d %H:%M:%S"))


def initialize(context):
    # 设置策略参数
    set_params(context)
    # 设置交易品种为恒瑞医药(股票代码：600276.XSHG)
    set_universe(context)
    # 设置基准收益
    set_benchmark('600276.XSHG')
    # 设置滑点
    set_slippage(FixedSlippage(0))
    # 设置交易手续费
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    # 开盘前运行
    run_daily(before_trading_start, time='before_open')
    # 开盘时运行
    run_daily(market_open, time='open')
    # 收盘后运行
    run_daily(after_trading_end, time='after_close')

    # 存储交易记录的字典
    context.trade_records = {}


def set_params(context):
    # 设置短期均线周期
    context.short_ma_days = 10
    # 设置长期均线周期
    context.long_ma_days = 20
    # 不设置止损


def set_universe(context):
    # 设置股票池为恒瑞医药
    context.security = '600276.XSHG'


def before_trading_start(context):
    # 获取当前持有股票
    context.positions = context.portfolio.positions
    # 获取历史数据，多取几天确保能计算均线
    hist_data = attribute_history(context.security,
                                  context.long_ma_days + 5,
                                  '1d',
                                  ['close'])
    # 计算短期均线(10日均线)
    context.short_ma = hist_data['close'][-context.short_ma_days:].mean()
    # 计算长期均线(20日均线)
    context.long_ma = hist_data['close'][-context.long_ma_days:].mean()
    # 计算前一天的短期均线
    context.last_short_ma = hist_data['close'][-(context.short_ma_days + 1):-1].mean()
    # 计算前一天的长期均线
    context.last_long_ma = hist_data['close'][-(context.long_ma_days + 1):-1].mean()
    # 获取当前价格
    context.current_price = hist_data['close'][-1]


def market_open(context):
    security = context.security
    # 如果没有持仓
    if security not in context.positions:
        # 当日10日均线突破20日均线时买入
        if context.short_ma > context.long_ma and context.last_short_ma <= context.last_long_ma:
            # 全仓买入
            order_value(security, context.portfolio.cash)
            # 记录买入信息到context.trade_records
            position = context.positions[security]
            buy_price = position.avg_cost
            buy_date = context.current_dt.date()
            context.trade_records[security] = {
                'buy_price': buy_price,
                'buy_date': buy_date,
                'highest_price': buy_price
            }
            log.info(
                f"买入 {security}，价格：{buy_price}，金额：{context.portfolio.cash}，10日均线：{context.short_ma}，20日均线：{context.long_ma}")
    else:
        # 如果有持仓，从context.trade_records获取持仓信息
        if security in context.trade_records:
            record = context.trade_records[security]
            buy_price = record['buy_price']
            buy_date = record['buy_date']
            current_price = context.current_price

            current_date = context.current_dt.date()

            # 从买入第二天开始判断卖出条件
            if current_date > buy_date + datetime.timedelta(days=1):
                # 计算当前盈亏比例
                profit_pct = (current_price - buy_price) / buy_price

                # 更新持仓的最高价格
                record['highest_price'] = max(record['highest_price'], current_price)

                # 当日10日均线向下突破20日均线时，触发卖出
                if context.short_ma < context.long_ma and context.last_short_ma >= context.last_long_ma:
                    # 止盈/止损卖出
                    order_target_value(security, 0)
                    # 卖出后从trade_records中删除记录
                    if security in context.trade_records:
                        del context.trade_records[security]
                    log.info(
                        f"均线死叉卖出 {security}，价格：{current_price}，盈亏比例：{profit_pct:.2%}，10日均线：{context.short_ma}，20日均线：{context.long_ma}")


def after_trading_end(context):
    # 输出当前持仓情况
    if context.security in context.positions:
        position = context.positions[context.security]
    log.info(
        f"当前持有 {context.security}，数量：{position.amount}，成本价：{position.avg_cost}，当前价：{context.current_price}，10日均线：{context.short_ma}，20日均线：{context.long_ma}")
    # 输出交易记录情况
    log.info(f"交易记录: {context.trade_records}")
