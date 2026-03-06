#encoding:gbk
#int(ma_fast_period) = 3  # 蹇嚎
#int(ma_slow_period) = 10  # 鎱㈢嚎
"""
5鏃ョ嚎涓婄┛20鏃ョ嚎鏃跺紑澶氾紝涓嬬┛鏃跺紑绌?
"""


import time



def init(ContextInfo):
	#鍥炴祴鍙傛暟璁剧疆
	ContextInfo.start = "2020-02-10 00:00:00"  # 娉ㄦ剰鏍煎紡锛屼笉瑕佸啓閿?
	ContextInfo.end = time.strftime('%Y-%m-%d')+ " 00:00:00"  # 娉ㄦ剰鏍煎紡锛屼笉瑕佸啓閿?
	ContextInfo.set_commission(0, [0,0,0,0,0,0]) # 鎵嬬画璐硅缃负鍗?1
	ContextInfo.code = ContextInfo.stockcode + '.' + ContextInfo.market
	ContextInfo.account_id = 'backtest' # 鍥炴祴鏃堕殢渚垮啓涓?涓瓧绗︿覆褰撲綔璐﹀彿锛屼氦鏄撶浉鍏虫帴鍙ｉ渶瑕佺敤鍒?
	# ContextInfo.security_deposit_ratio = 0.1  # 淇濊瘉閲戞瘮渚嬶紝寮?浠撻渶瑕侊紝鑲＄エ涓嶉渶瑕佹垨璁剧疆涓?1锛屾渶濂借窡鍙充晶鐨勪繚璇侀噾姣斾緥涓?鑷?
	ContextInfo.buyed = 0
	ContextInfo.multiplier = ContextInfo.get_contract_multiplier(ContextInfo.code)
	# print(ContextInfo.code, '鍚堢害涔樻暟:', ContextInfo.multiplier)


def handlebar(ContextInfo):
	timetag = ContextInfo.get_bar_timetag(ContextInfo.barpos)
	bar_date = timetag_to_datetime(timetag, '%Y%m%d')
	price = ContextInfo.get_market_data(['close','open'],
			stock_code=[ContextInfo.code],
			end_time = bar_date,
			count = int(ma_slow_period) + 2,
			period= ContextInfo.period,
			)
	# print(bar_date, price.to_dict())
	price_dict = price.to_dict('list')
	# 鏄ㄦ棩ma璁＄畻
	fast_ma = sum(price_dict['close'][(-1 * int(ma_fast_period) - 1): -1]) / int(ma_fast_period)
	slow_ma = sum(price_dict['close'][(-1 * int(ma_slow_period) - 1): -1]) / int(ma_slow_period)
	# 鍓嶆棩ma璁＄畻
	fast_ma_last_bar = sum(price_dict['close'][(-1 * int(ma_fast_period) - 2): -2]) / int(ma_fast_period)
	slow_ma_last_bar = sum(price_dict['close'][(-1 * int(ma_slow_period) - 2): -2]) / int(ma_slow_period)
	cross_up = fast_ma_last_bar <= slow_ma_last_bar and fast_ma > slow_ma
	cross_down = fast_ma_last_bar >= slow_ma_last_bar and fast_ma < slow_ma

	bar_open = price_dict['open'][-1]
	if cross_up:
		# 寮?澶?
		passorder(0, 1123, ContextInfo.account_id, ContextInfo.code,
				11,
				bar_open,
				#int(ContextInfo.capital*0.8 / (bar_open * ContextInfo.multiplier * ContextInfo.security_deposit_ratio)),
				0.8,
				ContextInfo)  # 鐢?80%鐨勮祫閲戝紑浠?, 寮?浠撲环涓哄綋鏃ュ紑鐩樹环
		ContextInfo.draw_text(True, 0, '寮?澶?')
		# 骞崇┖
		passorder(4, 1123, ContextInfo.account_id, ContextInfo.code,
				11,
				bar_open,
				1,
					ContextInfo)
		# orders, deals, positions, accounts = query_info(ContextInfo)
	elif cross_down:

		ContextInfo.draw_text(True, 0, '骞冲')
		passorder(1, 1123, ContextInfo.account_id, ContextInfo.code,
				11,
				bar_open,
				1,
				ContextInfo)  # 鍏ㄩ儴骞充粨
		# 寮?绌?
		passorder(3, 1123, ContextInfo.account_id, ContextInfo.code,
				11,
				bar_open,
				#int(ContextInfo.capital*0.8 / (bar_open * ContextInfo.multiplier * ContextInfo.security_deposit_ratio)),
				0.8,
				ContextInfo)


def query_info(ContextInfo):
	orders = get_trade_detail_data(ContextInfo.account_id, 'future', 'order')
	orders = [to_dict(o) for o in orders]

	deals = get_trade_detail_data(ContextInfo.account_id, 'future', 'deal')
	deals = [to_dict(t) for t in deals]
	positions = get_trade_detail_data(ContextInfo.account_id, 'future', 'position')
	positions = [to_dict(p) for p in positions]

	accounts = get_trade_detail_data(ContextInfo.account_id, 'future', 'account')
	accounts = [to_dict(a) for a in accounts]
	return orders, deals, positions, accounts


def to_dict(obj):
	attr_dict = {}
	for attr in dir(obj):
		try:
			if attr[:2] == 'm_':
				attr_dict[attr] = getattr(obj, attr)
		except:
			pass
	return attr_dict
