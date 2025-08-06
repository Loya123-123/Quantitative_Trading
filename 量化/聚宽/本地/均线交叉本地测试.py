# coding = udf-8

from datetime import datetime

from jqdatasdk import *

auth('13260172312', 'Exiaozhong123')

security = '601857.XSHG'

short_period = 10
long_period = 20

start_date_str = '20240415'
start_date = datetime.strptime(start_date_str, '%Y%m%d')
end_date_str = '20250425'
end_date = datetime.strptime(end_date_str, '%Y%m%d')



hist_daily = get_price(
    security,
    end_date=end_date,
    count=360,
    frequency='daily',
    fields=['open', 'close', 'low', 'high', 'volume', 'money'],
    skip_paused=True
)




hist_daily['ma_short'] = hist_daily['close'].rolling(window=short_period).mean()
hist_daily['ma_long'] = hist_daily['close'].rolling(window=long_period).mean()


hist_daily['ma_short_2days_ago'] = hist_daily['ma_short'].iloc[-3]
hist_daily['ma_long_2days_ago'] = hist_daily['ma_long'].iloc[-3]

hist_daily['ma_short_1day_ago'] = hist_daily['ma_short'].iloc[-2]
hist_daily['ma_long_1day_ago'] = hist_daily['ma_long'].iloc[-2]

hist_daily.to_csv('均线交叉data.csv')