
import time, datetime

# 获取沪深A股全市场股票列表
stock_list = get_stock_list_in_sector("沪深A�?")

# 订阅全市场tick行情（全推）
subscribe_whole_quote(stock_list)

print(f"已订�? {len(stock_list)} 只股票的全市场tick行情")

# 等待几秒确保行情初始�?
time.sleep(3)

# 获取部分股票的tick数据验证
sample_stocks = stock_list[:5]  # 取前5只测�?
full_tick = get_full_tick(sample_stocks)

for code in sample_stocks:
    if code in full_tick:
        last_price = full_tick[code].get("lastPrice")
        print(f"{code} �?新价: {last_price}")
    else:
        print(f"{code} 无tick数据")