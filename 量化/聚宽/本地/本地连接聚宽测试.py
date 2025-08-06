# coding = udf-8
# /usr/bin/env python

from datetime import datetime

from jqdatasdk import *

auth('13260172312', 'Exiaozhong123')
# 查询当日剩余可调用数据条数

dk_period = 10  # DKX计算周期
madk_period = 10  # MADKX计算周期
buy_date = None  # 记录买入日期

count = get_query_count()
print(count)
security = '600276.XSHG'
start_date_str = '20240415'
start_date = datetime.strptime(start_date_str, '%Y%m%d')
end_date_str = '20250422'
end_date = datetime.strptime(end_date_str, '%Y%m%d')

# security	指定标的，获取多个标的时需传入List
# fq ： 'pre'：前复权  'none'：不复权, 返回实际价格  'post'：后复权
df = get_price(security,
               start_date=start_date, end_date=end_date,
               frequency='daily',
               # 返回标的的开盘价、收盘价、最高价、最低价，成交的数量,时段中成交的金额、复权因子、时间段中的涨停价、时段中跌停价、时段中平均价，是否停牌，前一天收盘价等
               fields=['open', 'close', 'low', 'high', 'volume', 'money', 'factor', 'high_limit', 'low_limit', 'avg',
                       'pre_close', 'paused'],
               skip_paused=False,
               fq='none', count=None, round=True)
bars_df = get_bars(security,
                   end_dt=end_date,
                   # frequency='daily',
                   count=5,
                   unit='1m',
                   # 返回标的的开盘价、收盘价、最高价、最低价，成交的数量,时段中成交的金额、复权因子、时间段中的涨停价、时段中跌停价、时段中平均价，是否停牌，前一天收盘价等
                   fields=['date', 'open', 'close', 'low', 'high', 'volume', 'money'])

# 计算DKX
# MID = (3*CLOSE + OPEN + HIGH + LOW)/6
df['MID'] = (3 * df['close'] + df['open'] + df['high'] + df['low']) / 6
# df['DKX'] = df.apply(lambda row: row['open'] if row.name.date() == context.current_date else (3 * row['close'] + 2 * row['open'] + row['high'] + row['low']) / 7, axis=1)
# (20×MID+19×昨日MID+18×2日前的MID+17×3日前的MID+16×4日前的MID+15×5日前的MID+14×6日前的MID+13×7日前的MID+12×8日前的MID+11×9日前的MID十10×10日前的MID+9×U日前的MID+8×12日前的MID+7×13日前的M1D+6×14日前的MID+5×15日前的MID+4×16日前的MID+3×17日前的MID+2×18日前的MID+20日前的MID)÷210
df['DKX'] = (20 * df['MID'] + 19 * df['MID'].shift(1) + 18 * df['MID'].shift(2) + 17 * df['MID'].shift(3)
             + 16 * df['MID'].shift(4) + 15 * df['MID'].shift(5) + 14 * df['MID'].shift(6) + 13 * df['MID'].shift(7)
             + 12 * df['MID'].shift(8) + 11 * df['MID'].shift(9) + 10 * df['MID'].shift(10) + 9 * df['MID'].shift(11)
             + 8 * df['MID'].shift(12) + 7 * df['MID'].shift(13) + 6 * df['MID'].shift(14) + 5 * df['MID'].shift(15)
             + 4 * df['MID'].shift(16) + 3 * df['MID'].shift(17) + 2 * df['MID'].shift(18) + df['MID'].shift(19)) / 210
# weights = range(20, 0, -1)
# df['DKX'] = sum(w * df['MID'].shift(i) for i, w in enumerate(weights)) / 210

# 计算MADKX - MADKX是DKX的N日简单移动平均
df['MADKX'] = df['DKX'].rolling(window=madk_period).mean()

# 计算DKX和MADKX的前一天值，用于判断金叉死叉
df['DKX_prev'] = df['DKX'].shift(1)
df['MADKX_prev'] = df['MADKX'].shift(1)

madkx_prev = df['MADKX'].iloc[-2]

df.to_csv('data.csv')
print(df)
print(madkx_prev)

print(df.loc['2024-04-19'])
