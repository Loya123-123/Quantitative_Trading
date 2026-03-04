# 期货选品策略 Prompt

## 策略目标
每天日盘开始时和夜盘开始时，从品种池中筛选出10日趋势TOP3和趋势效率TOP3的期货主力合约。

## 触发时间
- 日盘开始：09:00（每个交易日的09:00执行）
- 夜盘开始：21:00（每个交易日的21:00执行）
- 时间获取方式：
  ```python
  bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
  current_date = int(bar_date[:8])  # 日期部分 20250228
  current_hour = int(bar_date[8:10])  # 小时分钟
  ```
- 执行控制：每天每个时段只执行一次（通过 `g.last_execute_date` 记录）
- 时段判断逻辑：
  ```python
  session = 1 if current_hour in (9, 0) else (2 if current_hour == 21 else 0)
  # 9代表日盘09:00，0代表日盘00:00（夜盘结束后的凌晨），21代表夜盘21:00
  ```

## 品种池
- 文件路径：`C:\合约选品\期货品种池.xlsx`（Windows路径）
- 需读取字段：
  - `代码`：品种代码（如 rb, hc, ao 等）
  - `交易所代码`：SF（上海期货）、ZF（郑州商品）、DF（大连商品）
  - `n手（取整）`：交易手数（整数）

## 主力合约获取
1. 根据品种池的代码和交易所代码，构造连续合约代码：品种代码 + "00" + "." + 交易所代码
   - 例如：rb + "00" + "." + "SF" = "rb00.SF"
2. 使用 `ContextInfo.get_main_contract(连续合约代码)` 获取主力合约代码
3. 主力合约 = 主力合约代码 + "." + 交易所代码
   - 例如：get_main_contract("rb00.SF") = "RB2405"，则主力合约为 "RB2405.SF"

## 回测/实盘区分
- 通过 `g.is_backtest` 变量控制：
  - `g.is_backtest = True`：回测模式，使用连续合约获取K线数据
  - `g.is_backtest = False`：实盘模式，使用主力合约获取K线数据
- 代码逻辑：
  ```python
  current_contract = continuous_contract if g.is_backtest else main_contract
  ```

## 指标计算
获取近10日历史日K线数据，使用 `ContextInfo.get_market_data_ex` 函数：
```python
history_data = ContextInfo.get_market_data_ex(
    ['time', 'open', 'high', 'low', 'close'],
    [current_contract],  # 回测用连续合约，实盘用主力合约
    end_time=bar_date,
    period='1d',
    count=13,  # 需要11天前的数据
    dividend_type=ContextInfo.dividend_type
)
```

### 历史数据处理
1. 转换时间戳：`df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))`
2. 日盘和夜盘的0-2点（后半段）删除历史数据中的最后一条（当天数据），夜盘21点-24点保留
   ```python
   history_df = history_df[:-1] if current_hour < 21 else history_df
   ```
3. 按时间倒序排列（重要！排序后索引0是最新的数据）
   ```python
   history_df = history_df.sort_values(by='time', ascending=False).reset_index(drop=True)
   ```

### 计算公式
1. **10日趋势** = |昨日收盘价 - 10日前收盘价| / 10日前收盘价
   - 昨日收盘价：`history_df['close'].iloc[0]`（排序后第0根K线，最近一天）
   - 10日前收盘价：`history_df['close'].iloc[9]`（排序后第9根K线，10天前）
2. **10日趋势的幅度** = |昨日收盘价 - 10日前收盘价|
3. **10日波动** = 近10天 Σ |最高价 - 最低价|
   - 即：Σ(第0根到第9根K线的 |high - low|)
   - 代码：`for i in range(0, 10)`
4. **趋势效率** = 10日趋势幅度 / 10日总波动
   - 趋势效率越高，说明波动越有方向

## 输出结果
需要输出两个榜单：
1. **10日趋势TOP3**：按10日趋势降序排列前3名
2. **趋势效率TOP3**：按趋势效率降序排列前3名

每个榜单需包含：
- 连续合约代码（如 rb00.SF）- 用于回测
- 主力合约代码（如 RB2405.SF）- 用于实盘
- 交易所代码（SF/ZF/DF）
- n手（取整）
- 对应的指标值

### stock_codes_dict 格式封装
为方便与海龟交易策略对接，需要将选品结果封装为 `stock_codes_dict` 格式：
```python
# 目标格式
{
    "品种代码": {"code": "连续合约代码", "market": "交易所代码", "size": n手}
}

# 示例
{
    "RB": {"code": "rb00", "market": "SF", "size": 10},
    "JM": {"code": "jm00", "market": "DF", "size": 4}
}
```

输出变量：
- `g.stock_codes_dict_top3_trend` - 10日趋势TOP3的stock_codes_dict
- `g.stock_codes_dict_top3_efficiency` - 趋势效率TOP3的stock_codes_dict

## 注意事项
1. 读取Excel文件使用 `pd.read_excel()`，需在代码中导入 pandas
2. 如果某品种无法获取主力合约，跳过该品种
3. 需要处理数据为空或不足的情况（需要至少10条数据）
4. 计算时注意使用绝对值
5. 趋势效率可能出现inf（除零）情况，需处理
6. 通过 `g.last_execute_date` 避免同一时段重复执行
7. 历史数据获取后必须进行排序（按时间倒序），确保索引0是最新的数据