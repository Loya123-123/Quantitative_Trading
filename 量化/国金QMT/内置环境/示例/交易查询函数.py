# coding:gbk

account = '800174'  # 在策略交易界面运行时，account的值会被赋值为策略配置中的账号，编辑器界面运行时，需要手动赋值；编译器环境里执行的下单函数不会产生实际委托


def init(ContextInfo):
    pass


def handlebar(ContextInfo):
    if not ContextInfo.is_last_bar():
        return

    orders = get_trade_detail_data(account, 'stock', 'order')
    print('查询委托结果：')
    for o in orders:
        print(
            f'股票代码: {o.m_strInstrumentID}, 市场类型: {o.m_strExchangeID}, 证券名称: {o.m_strInstrumentName}, 买卖方向: {o.m_nOffsetFlag}',
            f'委托数量: {o.m_nVolumeTotalOriginal}, 成交均价: {o.m_dTradedPrice}, 成交数量: {o.m_nVolumeTraded}, 成交金额:{o.m_dTradeAmount}')

    deals = get_trade_detail_data(account, 'stock', 'deal')
    print('查询成交结果：')
    for dt in deals:
        print(
            f'股票代码: {dt.m_strInstrumentID}, 市场类型: {dt.m_strExchangeID}, 证券名称: {dt.m_strInstrumentName}, 买卖方向: {dt.m_nOffsetFlag}',
            f'成交价格: {dt.m_dPrice}, 成交数量: {dt.m_nVolume}, 成交金额: {dt.m_dTradeAmount}')

    positions = get_trade_detail_data(account, 'stock', 'position')
    print('查询持仓结果：')
    for dt in positions:
        print(
            f'股票代码: {dt.m_strInstrumentID}, 市场类型: {dt.m_strExchangeID}, 证券名称: {dt.m_strInstrumentName}, 持仓量: {dt.m_nVolume}, 可用数量: {dt.m_nCanUseVolume}',
            f'成本价: {dt.m_dOpenPrice:.2f}, 市值: {dt.m_dInstrumentValue:.2f}, 持仓成本: {dt.m_dPositionCost:.2f}, 盈亏: {dt.m_dPositionProfit:.2f}')

    accounts = get_trade_detail_data(account, 'stock', 'account')
    print('查询账号结果：')
    for dt in accounts:
        print(f'总资产: {dt.m_dBalance:.2f}, 净资产: {dt.m_dAssureAsset:.2f}, 总市值: {dt.m_dInstrumentValue:.2f}',
              f'总负债: {dt.m_dTotalDebit:.2f}, 可用金额: {dt.m_dAvailable:.2f}, 盈亏: {dt.m_dPositionProfit:.2f}')

    position_statistics = get_trade_detail_data(account, "FUTURE", 'POSITION_STATISTICS')
    for obj in position_statistics:
        if obj.m_nDirection == 49:
            continue
        PositionInfo_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID] = {
            "持仓": obj.m_nPosition,
            "成本": obj.m_dPositionCost,
            "浮动盈亏": obj.m_dFloatProfit,
            "保证金占用": obj.m_dUsedMargin
        }
        print(PositionInfo_dict)

# 返回值
# 8000000213
# 【2023-10-31 13:35:41.063】  [quote]start simulation mode
# 【2023-10-31 13:35:41.125】  查询委托结果：
# 股票代码: 000001, 市场类型: SZ, 证券名称: 平安银行, 买卖方向: 48 委托数量: 5000, 成交均价: 10.43, 成交数量: 2500, 成交金额:26075.0
# 查询成交结果：
# 股票代码: 000001, 市场类型: SZ, 证券名称: 平安银行, 买卖方向: 48 成交价格: 10.43, 成交数量: 2500, 成交金额: 26075.0
# 查询持仓结果：
# 股票代码: 110055, 市场类型: SH, 证券名称: 伊力转债, 持仓量: 10, 可用数量: 10 成本价: 174.66, 市值: 1767.50, 持仓成本: 1746.57, 盈亏: 20.93
# 股票代码: 000001, 市场类型: SZ, 证券名称: 平安银行, 持仓量: 2500, 可用数量: 0 成本价: 10.43, 市值: 26150.00, 持仓成本: 26075.00, 盈亏: 75.00
# 股票代码: 123018, 市场类型: SZ, 证券名称: 溢利转债, 持仓量: 10, 可用数量: 10 成本价: 353.02, 市值: 3117.42, 持仓成本: 3530.23, 盈亏: -412.81
# 股票代码: 128136, 市场类型: SZ, 证券名称: 立讯转债, 持仓量: 60, 可用数量: 60 成本价: 109.30, 市值: 6715.56, 持仓成本: 6558.03, 盈亏: 157.53
# 查询账号结果：总资产: 999999839.30, 净资产: 999999839.30, 总市值: 37750.48 总负债: 0.00, 可用金额: 999962089.17, 盈亏: -159.35
# {'持仓': 22, '成本': 1726450.0, '浮动盈亏': 0.0, '保证金占用': 207174.0}
