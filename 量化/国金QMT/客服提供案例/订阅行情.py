from xtquant import xtdata
from datetime import datetime
import time

def on_data (datas):
    tick_time = datas['rb2505.SF'][0]['time']
    timestamp_seconds = tick_time / 1000
    readable_time = datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%m-%d %H:%M:%S.%f')
    # 获取当前时间戳（秒级）
    current_timestamp_seconds = time.time()
    current_readable_time = datetime.fromtimestamp(current_timestamp_seconds).strftime('%Y-%m-%d %H:%M:%S.%f')
    print(readable_time)
    print(current_readable_time)
    print(datas)

seq = xtdata.subscribe_quote(stock_code='rb2505.SF', period='tick', callback=on_data)

xtdata.run()