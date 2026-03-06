
# 示例：下载指定板块对应的历史行情数据（以股票为例�?
s = "600000.SH"

# 下载1分钟线数�?
xtdata.download_history_data(s, "1m", "", "", False)
his_data = xtdata.get_market_data_ex([], [s], period="1m", start_time="", end_time="", count=-1, dividend_type="none", fill_data=False)

# 下载5分钟线数�?
xtdata.download_history_data(s, "5m", "", "", False)
his_data = xtdata.get_market_data_ex([], [s], period="5m", start_time="", end_time="", count=-1, dividend_type="none", fill_data=False)

# 下载日线数据（用于生成周线�?�月线等�?
xtdata.download_history_data(s, "1d", "", "", False)
his_data = xtdata.get_market_data_ex([], [s], period="1d", start_time="", end_time="", count=-1, dividend_type="none", fill_data=False)