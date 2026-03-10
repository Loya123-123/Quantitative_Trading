# 选品海龟交易策略 - Prompt文档

## 策略概述

基于**海龟交易法则(Turtle Trading)**的期货量化交易策略，用于国金QMT平台实盘交易。

**核心思想**：
- 趋势跟踪策略
- 突破入场（价格突破N日高点做多，跌破N日低点做空）
- ATR动态仓位管理
- 止盈止损机制

---

## 核心参数配置

```
entry_window = 10      # 入场通道天数（突破前10日高点/低点）
exit_window = 4        # 止损通道天数（前4日高低点）
atr_window = 10        # ATR计算周期
stop_profit_ratio = 0.2  # 止盈比例（20%）
stop_loss_multiplier = 1  # 止损ATR倍数
position_limit = 4    # 最大持仓品种数
near_expiry_days = 30 # 临近到期限制天数
capital_rate = 0.1    # 资金使用率
trend_days = 30        # 选品趋势计算天数
is_trend_or_efficiency = 1  # 选品方式：1=趋势强度 2=趋势效率
order_cooldown_seconds = 10 # 订单冷却时间（秒）
```

---

## 选品逻辑

### 步骤1：读取品种池
从Excel文件读取期货品种，路径：`C:\期货选品\期货品种_{account}.xlsx`

Excel需包含字段：
- 品种代码（如：RB螺纹钢）
- 交易所代码（如：SF）
- n手数（每手合约数量）

### 步骤2：获取主连合约
- 连续合约 = 品种代码 + "00" + "." + 交易所代码
  - 例：rb00.SF
- 主连合约 = ContextInfo.get_main_contract(连续合约) + "." + 交易所代码
  - 例：RB2405.SF

### 步骤3：计算趋势指标

获取最近N日K线数据（包含OHLC），计算：

```python
# 趋势幅度（绝对值）
trend_amplitude = |昨日收盘价 - N日前收盘价|

# N日波动幅度
volatility_sum = Σ(|最高价 - 最低价|)  # i从0到N-1

# 趋势效率比
trend_efficiency = trend_amplitude / volatility_sum
```

### 步骤4：筛选TOP3品种

可选两种筛选方式：
- **方式1（趋势强度）**：按trend_amplitude降序，取前3名
- **方式2（趋势效率）**：按trend_efficiency降序，取前3名

---

## 交易信号逻辑

### 数据准备

获取最近N日OHLC数据，计算：
- **入场通道**：
  - 上轨 = 前entry_window日收盘价的最大值
  - 下轨 = 前entry_window日收盘价的最小值
- **止损通道**：
  - 止损低点 = 前exit_window日收盘价的最小值
  - 止损高点 = 前exit_window日收盘价的最大值
- **ATR值(N)**：使用atr_window周期计算

### 多头信号

**入场条件**（同时满足）：
- 当前无多头持仓
- 合约距到期日 > near_expiry_days
- 当前持仓数 < position_limit
- 当前价格 >= 前entry_window日最高价

**出场条件**（满足任一）：
1. 止盈：价格 < 前exit_window日最低价 且 价格 < 最高点-(最高点-成本价)×20%
2. 止损：价格 < 入场价 - stop_loss_multiplier × ATR

### 空头信号

**入场条件**（同时满足）：
- 当前无空头持仓
- 合约距到期日 > near_expiry_days
- 当前持仓数 < position_limit
- 当前价格 <= 前entry_window日最低价

**出场条件**（满足任一）：
1. 止盈：价格 > 前exit_window日最高价 且 价格 > 最低点+(成本价-最低点)×20%
2. 止损：价格 > 入场价 + stop_loss_multiplier × ATR

### 信号返回值格式

```python
return (signal_type, position_type)
# signal_type: 1=买入信号, -1=卖出信号, 0=无信号
# position_type: 1=多头, -1=空头
```

---

## 交易执行逻辑

### 下单函数

使用QMT的passorder函数：

```python
# 多头入场
passorder(0, 1101, account_id, 合约代码, 14, -1, 手数, 1, ContextInfo)
# 参数说明：0=买入, 1101=市价单, 14=开仓

# 空头入场
passorder(3, 1101, account_id, 合约代码, 14, -1, 手数, 1, ContextInfo)
# 参数说明：3=卖出, 1101=市价单, 14=开仓

# 多头平仓
passorder(7, 1101, account_id, 合约代码, 14, -1, 手数, 1, ContextInfo)
# 参数说明：7=买入平仓

# 空头平仓
passorder(9, 1101, account_id, 合约代码, 14, -1, 手数, 1, ContextInfo)
# 参数说明：9=卖出平仓
```

### 冷却机制

- 记录每次下单时间
- 同一合约在order_cooldown_seconds（10秒）内不重复下单
- 若下单后持仓未确认，持续观察

### 持仓管理

使用全局字典管理持仓状态：
```python
g.long_position = {}      # 多头持仓标志 (0/1)
g.short_position = {}    # 空头持仓标志 (0/1)
g.long_entry_price = {}  # 多头入场价
g.short_entry_price = {} # 空头入场价
g.long_volume = {}       # 多头持仓手数
g.short_volume = {}      # 空头持仓手数
g.highest_after_entry = {}  # 入场后最高价（多头）
g.lowest_after_entry = {}   # 入场后最低价（空头）
```

---

## 风控规则

1. **最大持仓限制**：同时最多持仓 position_limit 个品种
2. **合约到期过滤**：排除距到期日不足 near_expiry_days 的合约
3. **订单冷却**：10秒内不重复下单
4. **止盈止损**：详见交易信号逻辑
5. **未成交单处理**：自动撤销状态为53/54/56/57以外的挂单

---

## 执行时间

- **运行频率**：每3秒检查一次
- **交易时段限制**：
  - 夜盘：21:00-02:30
  - 日盘：09:00-11:30, 13:30-15:00
- **跳过条件**：
  - 周末不执行
  - 非交易时段不执行
  - 非最后一根K线不执行

---

## 关键函数说明

| 函数名 | 功能 |
|--------|------|
| `init` | 初始化配置、读取品种池、设置运行参数 |
| `run_time_handlebar` | 定时任务入口，主逻辑执行 |
| `select_contract` | 选品种、获取主连合约、计算趋势指标 |
| `get_price_data` | 获取OHLC价格数据（合并历史+当日） |
| `calculate_atr` | 计算ATR值（True Range均值） |
| `generate_signal` | 生成交易信号（入场/出场判断） |
| `execute_trade` | 执行下单操作 |
| `get_account_info` | 获取账户信息、持仓状态、未成交单 |
| `filter_cooling_contracts` | 过滤冷却期内合约 |
| `is_trading_time` | 判断当前是否为交易时段 |

---

## 日志与通知

- **日志路径**：`C:\datalog\datalog-{account}-{timestamp}.log`
- **飞书通知**：实时推送交易信号（需配置WebHook URL）
- **日志级别**：INFO（主要信息）、DEBUG（详细调试）

---

## 代码结构

```
├── 全局变量定义 (g对象)
├── init() - 初始化
├── run_time_handlebar() - 定时执行入口
├── select_contract() - 选品逻辑
├── get_price_data() - 获取价格数据
├── calculate_atr() - 计算ATR
├── generate_signal() - 生成信号
├── execute_trade() - 执行交易
├── get_account_info() - 账户信息
├── 辅助函数
│   ├── filter_cooling_contracts()
│   ├── is_weekend()
│   ├── is_trading_time()
│   └── send_feishu_message()
└── 工具函数
    ├── log_info()
    ├── log_debug()
    └── convert_to_stock_codes_dict()
```

---

## 注意事项

1. **编码问题**：文件使用GBK编码
2. **回测模式**：通过ContextInfo.do_back_test判断
3. **滑点风险**：使用市价单可能产生滑点
4. **未来函数**：使用当日收盘价判断，存在信号闪烁可能
5. **Excel路径**：需根据实际情况修改

---

## 修改建议

如需调整策略，可修改以下参数：
- `entry_window`：增大则信号减少，减小则信号频繁
- `stop_profit_ratio`：止盈比例，越大盈利越多但出场越晚
- `stop_loss_multiplier`：止损ATR倍数，越大抗波动越强
- `position_limit`：最大持仓数，影响分散度
- `near_expiry_days`：临近到期天数，避免交易快到期合约