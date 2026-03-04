# 选品海龟交易策略 Prompt

## 策略概述
基于国金QMT平台的选品+海龟交易策略，策略包含两部分：
1. **选品模块**：每日自动筛选10日趋势TOP3和趋势效率TOP3的期货合约
2. **交易模块**：基于海龟交易法则执行买卖操作

## 策略文件
- 路径：`/Users/exiaozhong/CodeProjects/Quantitative_Trading/量化/国金QMT/期货/选品海龟交易策略/选品海龟交易_回测版.py`

## 策略结构

### 1. init(ContextInfo) - 初始化函数
初始化策略参数、读取品种池等。

**主要功能：**
- 设置账户ID：`ContextInfo.account_id = '809213023'`
- 读取品种池Excel文件
- 设置策略参数（入市通道周期、止盈通道周期、ATR周期等）
- 初始化日志

### 2. select_pools(ContextInfo) - 选品函数
每个handlebar调用时检查是否执行选品逻辑。

**触发时间：**
- 日盘开始：09:00
- 夜盘开始：21:00
- 时间获取方式：
  ```python
  bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
  current_date = int(bar_date[:8])
  current_hour = int(bar_date[8:10])
  ```
- 时段判断：
  ```python
  session = 1 if current_hour in (9, 0) else (2 if current_hour == 21 else 0)
  ```
- 执行控制：通过 `g.last_execute_date` 避免同一时段重复执行

**品种池：**
- 文件路径：`C:\合约选品\期货品种池.xlsx`
- 读取字段：`代码`、`交易所代码`、`n手（取整）`

**选品流程：**
1. 遍历品种池，构造连续合约代码（品种代码 + "00" + "." + 交易所代码）
2. 使用 `ContextInfo.get_main_contract()` 获取主力合约
3. 获取近10日历史K线数据（count=13）
4. 计算指标

**指标计算：**
1. **10日趋势** = |昨日收盘价 - 10日前收盘价| / 10日前收盘价
2. **10日趋势幅度** = |昨日收盘价 - 10日前收盘价|
3. **10日波动** = Σ(|最高价 - 最低价|)，近10天
4. **趋势效率** = 10日趋势幅度 / 10日波动

**历史数据处理：**
```python
# 转换时间戳
history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))

# 删除当天数据（根据时段）
history_df = history_df[:-1] if current_hour < 21 else history_df

# 按时间倒序排列
history_df = history_df.sort_values(by='time', ascending=False).reset_index(drop=True)
```

**输出结果：**
- 10日趋势TOP3
- 趋势效率TOP3

**stock_codes_dict格式：**
```python
{
    "品种代码": {"code": "连续合约代码", "market": "交易所代码", "size": n手}
}
```

### 3. handlebar(ContextInfo) - 主处理函数
每个K线周期都会被调用。

**执行流程：**
1. 调用 `select_pools(ContextInfo)` 执行选品
2. 设置交易标的：
   ```python
   ContextInfo.stock_codes = [stock_info["code"] + '.' + stock_info["market"]
                             for stock_code, stock_info in ContextInfo.stock_codes_dict.items()]
   ContextInfo.set_universe(ContextInfo.stock_codes)
   ```
3. 判断是否执行交易（回测模式跳过/实盘模式判断时间和周末）
4. 执行海龟交易策略逻辑

**回测/实盘区分：**
- `g.is_backtest = True`：回测模式
- `g.is_backtest = False`：实盘模式

## 海龟交易策略规则

### 买入/卖出信号
1. **做多买入**：当日价格 > 前10日收盘价最高点（突破前10日高点）
2. **做空买入**：当日价格 < 前10日收盘价最低点（突破10日低点）

### 止盈/止损规则
1. **做多止盈**：买入第二天开始，价格 < 前4日收盘价最低点，且价格 < 最高价 - (最高价 - 买入价) × 20%
2. **做多止损**：买入第二天开始，价格 < 买入价 - N × ATR
3. **做空止盈**：买入第二天开始，价格 > 前4日收盘价最高点，且价格 > 最低价 + (买入价 - 最低价) × 20%
4. **做空止损**：买入第二天开始，价格 > 买入价 + N × ATR

### 仓位管理
- 单只品种单次买入金额：10000
- 每个品种最多20000（做多/做空各10000）
- 不加仓：做多或做空买入后不再加仓

### 开仓条件
- 开仓信号触发
- 持仓不满4个
- 合约距离到期大于30天

## 策略参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| entry_window | 10 | 入市通道周期（突破周期） |
| exit_window | 4 | 止盈通道周期 |
| atr_window | 14 | ATR计算周期 |
| atr_multiplier | 2 | ATR倍数（用于止损） |
| max_position | 4 | 最大持仓品种数 |

## 注意事项
1. 选品模块在每个handlebar中都会检查是否执行（09:00和21:00）
2. 回测模式下，交易逻辑会被跳过，仅执行选品
3. 实盘模式下，需要判断交易时间和周末
4. 选品结果通过 `ContextInfo.stock_codes_dict` 传递给交易模块
5. 历史数据获取需要至少12条有效数据才能计算指标
