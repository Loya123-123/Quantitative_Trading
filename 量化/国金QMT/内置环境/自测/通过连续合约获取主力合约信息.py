# coding:gbk

from datetime import datetime


# 市场	市场代码	迅投市场代码
# 上期所	SHFE	SF
# 大商所	DCE	DF
# 郑商所	CZCE	ZF
# 中金所	CFFEX	IF
# 能源中心	INE	INE
# 广期所	GFEX	GF

class G(): pass


g = G()


def log_info(message):
    print(message)


def init(ContextInfo):
    pass
    # ContextInfo.stock_code = ContextInfo.stockcode + '.' + ContextInfo.market
    # ContextInfo.stock_codes = ['rb00.SF', 'fg00.ZF']  # 可以根据需要修改
    ContextInfo.stock_codes_dict = {"rb": {"code": "rb00", "market": "SF"}
        , "fg": {"code": "fg00", "market": "ZF"}
                                    }
    ContextInfo.stock_codes = [stock_info["code"] + '.' + stock_info["market"] for stock_code, stock_info in
                               ContextInfo.stock_codes_dict.items()]
    g.expire_date = {}
    g.expire_date_diff = {}


def handlebar(ContextInfo):
    # 获取历史数据 获取数据的截止时间
    bar_date = timetag_to_datetime(ContextInfo.get_bar_timetag(ContextInfo.barpos), '%Y%m%d%H%M%S')
    g.current_date = bar_date
    log_info(f"  获取截止时间: {g.current_date}")

    # 清空上一次的交易合约列表
    g.current_trading_contracts = []
    # 获取主力合约代码替代连续合约
    for stock_key, stock_info in ContextInfo.stock_codes_dict.items():
        main_stock_code = stock_info["code"] + '.' + stock_info["market"]
        # 获取主力合约代码，使用当前日期
        main_contract = ContextInfo.get_main_contract(main_stock_code, date=g.current_date[:8]) + '.' + stock_info[
            "market"]
        if main_contract:
            g.current_trading_contracts.append(main_contract)
            print(f"[初始化] 连续合约 {main_stock_code} 对应的主力合约为: {main_contract}")
        else:
            # 如果获取不到主力合约，则使用原连续合约
            g.current_trading_contracts.append(main_stock_code)
            print(f"[初始化] 无法获取 {main_stock_code} 的主力合约，继续使用原合约")
    # 为每个合约执行策略逻辑
    for stock_code in g.current_trading_contracts:
        log_info(f"[处理函数] 处理合约: {stock_code}")

        # 设置当前处理的合约为全局变量，供其他函数使用
        g.current_stock_code = stock_code

        # 获取合约基础信息
        stock_contract_info = ContextInfo.get_instrument_detail(g.current_stock_code)
        log_info(f"[数据获取] 合约基础信息: {stock_contract_info}")

        # 获合约的退市日或者到期日 ExpireDate
        g.expire_date[g.current_stock_code] = str(stock_contract_info.get('ExpireDate', 0))
        log_info(f"[数据获取] 合约的退市日或者到期日: {g.expire_date[g.current_stock_code]}")

        # 当前合约的到期日(YYYYMMDD) 和 当前日期 g.current_date[:8](YYYYMMDD) 差几天
        g.expire_date_diff[g.current_stock_code] = (datetime.strptime(g.expire_date[g.current_stock_code],
                                                                      '%Y%m%d') - datetime.strptime(
            g.current_date[:8], '%Y%m%d')).days if g.expire_date[g.current_stock_code] else 99
        log_info(f"[数据获取] 获取合约的到期日和当前日期的差: {g.expire_date_diff[g.current_stock_code]}")
