from xtquant import xtdata

xtdata.download_history_data2(stock_list=['rb2505.SF'], period='1d', start_time='20240922', end_time='20241021')

res = xtdata.get_local_data(stock_list=['rb2505.SF'], period='1d', start_time='20240922', end_time='20241021')




print(res)

print(res['rb2501.SF'])