# Quantitative Trading 项目指南

> 本文档记录QMT量化交易项目的配置、连接方式和回测系统，便于新会话快速上手。

---

## 📋 项目概述

这是一个基于**QMT (迅投量化交易平台)**的本地量化交易项目，主要功能包括：

- **行情数据获取** - 通过 `xtdata` 获取股票、期货实时/历史数据
- **交易接口** - 通过 `xttrader` 连接MiniQMT执行实盘交易
- **本地回测** - 纯Python回测系统，无需依赖QMT内置回测引擎
- **策略开发** - 双均线、小市值轮动等经典策略

---

## 🔧 环境配置

### 1. QMT安装信息

| 配置项 | 路径/值 |
|--------|---------|
| QMT安装路径 | `C:\QMT001` |
| MiniQMT数据路径 | `C:\QMT001\userdata_mini` |
| Python库 | `xtquant` (已安装到系统Python) |

### 2. 关键依赖

```python
# 核心库
from xtquant import xtdata              # 行情数据接口
from xtquant.xttrader import XtQuantTrader    # 交易接口
from xtquant.xttype import StockAccount       # 账号类型
from xtquant import xtconstant          # 常量定义
from xtquant.qmttools import run_strategy_file  # QMT回测引擎
from xtquant.qmttools.functions import passorder, get_trade_detail_data
```

### 3. 资金账号

```python
ACCOUNT_ID = '8886090521'   # 股票账号
ACCOUNT_TYPE = 'STOCK'      # 账号类型: STOCK(股票) / FUTURE(期货)
```

---

## ✅ 连接测试

### 快速验证QMT连接

运行 `test_qmt_connection.py`：

```bash
cd C:\Users\loya\PycharmProjects\Quantitative_Trading
python test_qmt_connection.py
```

**预期输出：**
```
***** xtdata连接成功 *****
服务器地址: 127.0.0.1:58610
数据路径: C:\QMT001\userdata_mini/datadir
[OK] 成功获取数据!

[OK] MiniQMT连接成功!
[OK] 账号订阅成功!
  总资产: 1025.14
  可用资金: 1025.14
```

### 连接代码模板

```python
import random
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

# 配置
MINI_QMT_PATH = r'C:\QMT001\userdata_mini'
ACCOUNT_ID = '8886090521'

# 连接
session_id = int(random.randint(100000, 999999))
xt_trader = XtQuantTrader(MINI_QMT_PATH, session_id)
xt_trader.start()

if xt_trader.connect() == 0:
    print("连接成功")
    account = StockAccount(ACCOUNT_ID, 'STOCK')
    xt_trader.subscribe(account)
```

---

## 📊 数据获取

### 历史K线数据

```python
from xtquant import xtdata

# 下载数据（首次需要）
xtdata.download_history_data('000001.SZ', period='1d', start_time='20230101', end_time='20241231')

# 获取数据 - 返回格式: {code: DataFrame}
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['000001.SZ', '000002.SZ'],
    period='1d',
    count=500  # 获取最近500个交易日
)

# 提取单个股票的收盘价
df = data['000001.SZ']  # DataFrame包含open/high/low/close/volume
close_prices = df['close']
```

### 实时行情订阅

```python
# 订阅实时行情
def on_tick(data):
    print("收到tick:", data)

xtdata.subscribe_quote('000001.SZ', period='1m', callback=on_tick)
xtdata.run()  # 保持程序运行
```

---

## 🧪 回测系统

### 纯Python回测（推荐）

文件：`backtest_ma_simple.py`

**核心架构：**

```python
# 1. 数据获取
open_df, close_df = get_data(STOCK_POOL, COUNT)

# 2. 信号计算
def calculate_signals(close_df, short_ma, long_ma):
    ma_short = close_df.rolling(window=short_ma).mean()
    ma_long = close_df.rolling(window=long_ma).mean()
    
    # 金叉买入，死叉卖出
    golden = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
    dead = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
    
    signals[golden] = 1   # 买入
    signals[dead] = -1    # 卖出
    return signals

# 3. 回测引擎
def backtest(open_df, close_df, signals, initial_capital, max_holdings):
    for date in signals.index:
        # 处理卖出信号
        for code in holdings:
            if signals.loc[date, code] == -1:
                sell(...)
        
        # 处理买入信号
        for code in stock_pool:
            if signals.loc[date, code] == 1:
                buy(...)
        
        # 记录每日资产
        daily_values.append({'date': date, 'value': cash + holding_value})
    
    return daily_values, trades

# 4. 计算指标
def calculate_metrics(daily_values, initial_capital):
    total_return = (final - initial) / initial
    max_drawdown = ...
    sharpe_ratio = ...
    return metrics
```

### 运行回测

```bash
python backtest_ma_simple.py
```

**输出示例：**
```
============================================================
双均线交叉策略回测
============================================================
股票池: ['000001.SZ', '000002.SZ', ...]
均线: MA5 / MA20
初始资金: 1000000
============================================================
数据获取成功，共 500 个交易日 (20240318 ~ 20260410)

信号统计:
  000001.SZ: 买入信号 18 次, 卖出信号 17 次
  ...

开始回测...
------------------------------------------------------------
[20240419] 买入 000001.SZ @ 10.71, 数量 93300
[20240604] 卖出 000001.SZ @ 11.02, 数量 93300, 盈亏 28923.00
...
------------------------------------------------------------

============================================================
回测结果
============================================================
  总收益率: 5.09%
  年化收益率: 2.54%
  最大回撤: -19.03%
  夏普比率: 0.10
  交易天数: 500
  最终资产: 1050944.00

【交易记录】
  总交易次数: 81 (买入 41, 卖出 40)
  已实现盈亏: 40527.00
============================================================
```

---

## 📁 项目文件结构

```
Quantitative_Trading/
├── PROJECT_GUIDE.md          # 本指南文件
├── test_qmt_connection.py    # QMT连接测试脚本
├── backtest_ma_simple.py     # 双均线回测策略
│
├── 量化/                      # QMT相关策略和示例
│   └── 国金QMT/
│       ├── 本地环境/
│       │   └── 本地回测案例.py    # QMT官方回测示例
│       ├── 客服提供案例/          # QMT官方示例代码
│       │   ├── 查询持仓和下单.py
│       │   ├── 获取行情示例.py
│       │   └── ...
│       └── 期货/                 # 期货策略
│
└── yooda/                     # 其他项目代码
```

---

## 💡 开发指南

### 添加新策略步骤

1. **复制模板**
   ```bash
   copy backtest_ma_simple.py my_strategy.py
   ```

2. **修改信号计算**
   ```python
   def calculate_signals(df):
       # 你的策略逻辑
       # 返回: DataFrame (1=买入, -1=卖出, 0=无信号)
       return signals
   ```

3. **运行回测**
   ```bash
   python my_strategy.py
   ```

### 关键注意事项

| 问题 | 解决方案 |
|------|----------|
| 数据为空 | 确保QMT已登录并下载了历史数据 |
| 连接失败 | 检查MiniQMT是否已启动 |
| 编码错误 | 使用英文输出或GBK编码 |
| 交易时间 | 回测使用收盘价/开盘价，实盘需注意交易时间 |

---

## 🔗 常用代码片段

### 查询账户信息

```python
# 查询资金
asset = xt_trader.query_stock_asset(account)
print(f"总资产: {asset.total_asset}, 可用: {asset.cash}")

# 查询持仓
positions = xt_trader.query_stock_positions(account)
for pos in positions:
    print(f"{pos.stock_code}: {pos.volume}股, 成本{pos.avg_price}")

# 查询当日委托
orders = xt_trader.query_stock_orders(account)
for order in orders:
    print(f"{order.stock_code}: {order.order_volume}股 @ {order.price}")
```

### 下单函数

```python
from xtquant import xtconstant

# 股票买入
order_id = xt_trader.order_stock(
    account=account,
    stock_code='000001.SZ',
    order_type=xtconstant.STOCK_BUY,  # 买入
    order_volume=1000,
    price_type=xtconstant.LATEST_PRICE,  # 最新价
    price=-1  # -1表示市价
)

# 股票卖出
order_id = xt_trader.order_stock(
    account=account,
    stock_code='000001.SZ',
    order_type=xtconstant.STOCK_SELL,
    order_volume=1000,
    price_type=xtconstant.FIX_PRICE,  # 限价
    price=10.5
)
```

### 获取股票列表

```python
# 获取沪深A股所有股票
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')

# 获取指数成分股
hs300 = xtdata.get_stock_list_in_sector('沪深300')
```

---

## ⚠️ 风险提示

1. **实盘交易前务必充分回测**
2. **注意控制仓位，设置止损**
3. **API接口可能有延迟，高频交易需谨慎**
4. **策略失效风险，需定期评估策略表现**

---

## 📚 API 完整参考 (从客服案例提炼)

> 以下所有函数均已在 `test_all_api_functions.py` 中验证可用 (38/38测试通过)
> 来源: `量化/国金QMT/客服提供案例/` 目录下的19个示例文件

### 1. xtdata 模块 - 行情数据接口

```python
from xtquant import xtdata
```

| 函数 | 用途 | 示例 |
|------|------|------|
| `get_stock_list_in_sector(sector)` | 获取板块股票列表 | `xtdata.get_stock_list_in_sector('沪深A股')` |
| `download_history_data(code, period, start, end)` | 下载历史数据 | `xtdata.download_history_data('000001.SZ', '1d', '20240101', '20241231')` |
| `get_market_data_ex(fields, stocks, period, count)` | 获取行情数据 | `xtdata.get_market_data_ex(['close'], ['000001.SZ'], '1d', count=100)` |
| `subscribe_quote(code, period, callback)` | 订阅实时行情 | `xtdata.subscribe_quote('000001.SZ', '1m', callback=on_tick)` |
| `get_local_data(stocks, period, count)` | 获取本地数据 | `xtdata.get_local_data(['000001.SZ'], '1d', count=5)` |
| `run()` | 启动订阅循环 | `xtdata.run()` |

**完整示例 - 获取历史K线:**
```python
from xtquant import xtdata

# 下载数据（首次需要）
xtdata.download_history_data('000001.SZ', period='1d', start_time='20230101', end_time='20241231')

# 获取数据 - 返回格式: {code: DataFrame}
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['000001.SZ'],
    period='1d',
    count=500
)

df = data['000001.SZ']  # DataFrame包含OHLCV数据
close_prices = df['close']
```

**完整示例 - 订阅实时行情:**
```python
from xtquant import xtdata

def on_tick(datas):
    """实时tick数据回调"""
    for code, data in datas.items():
        print(f"{code}: 最新价 {data[0]['lastPrice']}")

# 订阅tick行情
xtdata.subscribe_quote('000001.SZ', period='tick', callback=on_tick)
xtdata.run()  # 保持程序运行
```

---

### 2. xtconstant 模块 - 交易常量

```python
from xtquant import xtconstant
```

| 常量 | 值 | 用途 |
|------|-----|------|
| `STOCK_BUY` | 23 | 股票买入 |
| `STOCK_SELL` | 24 | 股票卖出 |
| `LATEST_PRICE` | 5 | 最新价(市价) |
| `FIX_PRICE` | 11 | 限价 |
| `FUTURE_OPEN_LONG` | 0 | 期货开多 |
| `FUTURE_OPEN_SHORT` | 3 | 期货开空 |
| `FUTURE_CLOSE_LONG_TODAY_FIRST` | 6 | 期货平多(平今优先) |
| `FUTURE_CLOSE_SHORT_TODAY_FIRST` | 8 | 期货平空(平今优先) |
| `FUTURE_CLOSE_LONG_HISTORY_FIRST` | 7 | 期货平多(平昨优先) |
| `FUTURE_CLOSE_SHORT_HISTORY_FIRST` | 9 | 期货平空(平昨优先) |

---

### 3. xttrader 模块 - 交易接口

```python
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
```

#### 3.1 初始化与连接

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `XtQuantTrader(path, session_id)` | 创建交易对象 | 交易对象实例 |
| `xt_trader.start()` | 启动交易线程 | None |
| `xt_trader.connect()` | 连接MiniQMT | 0=成功 |
| `xt_trader.subscribe(account)` | 订阅账号 | 0=成功 |
| `xt_trader.register_callback(callback)` | 注册回调 | None |

**连接示例:**
```python
import random
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

MINI_QMT_PATH = r'C:\QMT001\userdata_mini'
ACCOUNT_ID = '8886090521'

# 创建并连接
session_id = random.randint(100000, 999999)
xt_trader = XtQuantTrader(MINI_QMT_PATH, session_id)
xt_trader.start()

if xt_trader.connect() == 0:
    account = StockAccount(ACCOUNT_ID, 'STOCK')
    xt_trader.subscribe(account)
    print("连接成功")
```

#### 3.2 查询接口

| 方法 | 用途 | 返回值属性 |
|------|------|------------|
| `query_stock_asset(account)` | 查询资金 | `total_asset`, `cash`, `market_value` |
| `query_stock_positions(account)` | 查询持仓 | `stock_code`, `volume`, `avg_price`, `can_use_volume` |
| `query_position_statistics(account)` | 持仓统计 | `open_price`, `market_value`, `yesterday_volume` |
| `query_stock_orders(account)` | 查询委托 | `order_id`, `stock_code`, `order_volume`, `price`, `status_msg` |
| `query_stock_trades(account)` | 查询成交 | `traded_id`, `traded_price`, `traded_volume`, `traded_time` |

**查询示例:**
```python
# 查询资金
asset = xt_trader.query_stock_asset(account)
print(f"总资产: {asset.total_asset}, 可用: {asset.cash}")

# 查询持仓
positions = xt_trader.query_stock_positions(account)
for pos in positions:
    print(f"{pos.stock_code}: {pos.volume}股, 成本{pos.avg_price}, 可用{pos.can_use_volume}")

# 查询当日委托
orders = xt_trader.query_stock_orders(account)
for order in orders:
    print(f"{order.stock_code}: {order.order_volume}股 @ {order.price}, 状态: {order.status_msg}")

# 查询当日成交
trades = xt_trader.query_stock_trades(account)
for trade in trades:
    print(f"成交: {trade.traded_volume}股 @ {trade.traded_price}")
```

#### 3.3 下单接口

| 方法 | 用途 | 参数说明 |
|------|------|----------|
| `order_stock(account, code, order_type, volume, price_type, price)` | 同步下单 | account, code, order_type(买/卖), volume, price_type, price |
| `order_stock_async(account, code, order_type, volume, price_type, price, order_remark)` | 异步下单 | 同上 + order_remark(备注) |
| `cancel_order_stock(account, order_id)` | 撤单 | account, order_id |

**下单示例:**
```python
from xtquant import xtconstant

# 股票买入 - 市价单
order_id = xt_trader.order_stock(
    account=account,
    stock_code='000001.SZ',
    order_type=xtconstant.STOCK_BUY,      # 买入
    order_volume=1000,
    price_type=xtconstant.LATEST_PRICE,   # 最新价
    price=-1                              # -1表示市价
)

# 股票卖出 - 限价单
order_id = xt_trader.order_stock(
    account=account,
    stock_code='000001.SZ',
    order_type=xtconstant.STOCK_SELL,     # 卖出
    order_volume=1000,
    price_type=xtconstant.FIX_PRICE,      # 限价
    price=10.5
)

# 期货开多(异步)
xt_trader.order_stock_async(
    account, 
    'rb2505.SF', 
    xtconstant.FUTURE_OPEN_LONG, 
    1, 
    xtconstant.LATEST_PRICE, 
    0,
    order_remark='策略A开多'
)
```

#### 3.4 交易回调 (XtQuantTraderCallback)

```python
from xtquant.xttrader import XtQuantTraderCallback

class MyCallback(XtQuantTraderCallback):
    def on_stock_order(self, order):
        """委托回报"""
        print(f"委托: {order.stock_code}, 数量{order.order_volume}, 备注:{order.order_remark}")
    
    def on_stock_trade(self, trade):
        """成交回报"""
        print(f"成交: {trade.stock_code}, 价格{trade.traded_price}, 数量{trade.traded_volume}")
    
    def on_order_error(self, order_error):
        """委托失败"""
        print(f"委托失败: {order_error.error_msg}")
    
    def on_disconnected(self):
        """连接断开"""
        print("连接断开")

# 注册回调
callback = MyCallback()
xt_trader.register_callback(callback)
```

---

### 4. qmttools 模块 - 大QMT工具 (回测专用)

> 注意: 以下函数仅在QMT内置回测引擎中可用

```python
from xtquant.qmttools.functions import passorder, get_trade_detail_data
```

| 函数 | 用途 | 示例 |
|------|------|------|
| `passorder(optype, op, account, code, pricetype, price, volume, strategy, remark, ContextInfo)` | 下单(回测) | `passorder(0, 1101, account, '000001.SZ', 5, -1, 100, 1, '备注', ContextInfo)` |
| `get_trade_detail_data(account, type, datatype)` | 获取交易详情 | `get_trade_detail_data(account, 'FUTURE', 'position')` |

**数据类型参数:**
- `datatype='order'` - 委托数据
- `datatype='deal'` - 成交数据  
- `datatype='position'` - 持仓数据
- `datatype='account'` - 账户数据

---

### 5. 快速参考卡片

#### 常用股票代码格式
| 市场 | 代码格式 | 示例 |
|------|----------|------|
| 上海 | XXXXXX.SH | 600000.SH, rb2505.SF |
| 深圳 | XXXXXX.SZ | 000001.SZ, 159915.SZ |

#### 常用周期
| 周期 | 代码 | 说明 |
|------|------|------|
| 1分钟 | 1m | 分钟线 |
| 5分钟 | 5m | 分钟线 |
| 日线 | 1d | 日K线 |
| tick | tick | 逐笔数据 |

---

## 📞 联系信息

- **项目路径**: `C:\Users\loya\PycharmProjects\Quantitative_Trading`
- **QMT安装**: `C:\QMT001`
- **账号**: 8886090521 (国金QMT)

---

*最后更新: 2026-04-12 (添加了从客服案例提炼的完整API参考)*
