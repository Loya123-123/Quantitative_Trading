# coding:gbk
import pandas as pd


# 市场	市场代码	迅投市场代码
# 上期所	SHFE	SF
# 大商所	DCE	DF
# 郑商所	CZCE	ZF
# 中金所	CFFEX	IF
# 能源中心	INE	INE
# 广期所	GFEX	GF

class G(): pass


g = G()


def init(ContextInfo):
    ContextInfo.account_id = 'test1'
    g.current_stock_code = 'FG601.ZF'
    # passorder( opType, orderType, accountid , orderCode, prType, price, volume , strategyName, quickTrade, userOrderId , ContextInfo)
    #             操作号    组合方式     资金账号    品种代码     报价类型  价格    下单量    策略名称        快速下单标记  投资备注        策略上下文
    order_info = passorder(opType=0, orderType=1101, accountID=ContextInfo.account_id, orderCode=g.current_stock_code,
                           prType=5, price=-1, volume=2, strategyName='策略测试', ContextInfo=ContextInfo)
    print(order_info)
    # 获取持仓信息
    print("  [账户信息] 获取持仓详情...")
    position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'POSITION')
    PositionInfo_dict = {}
    PositionInfo_dfs = pd.DataFrame()

    if position_details:
        print(f"  [账户信息] 获取到 {len(position_details)} 条持仓记录")
        for pos in position_details:
            # 获取 pos 对象转json信息
            # print(f"  [账户信息] 获取持仓属性信息: {dir(pos)}")
            symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID

            position_type = pos.m_nDirection
            # 检查持仓是否属于当前策略的合约
            if position_type == 48:  # 多头持仓
                g.long_position[symbol] = 1
                g.long_open_date[symbol] = pos.m_strOpenDate  # 多头开仓日期
                g.long_volume[symbol] = pos.m_nVolume  # 多头持仓量
                g.long_entry_price[symbol] = pos.m_dOpenPrice  # 多头持仓成本

            elif position_type == 49:  # 空头持仓
                g.short_position[symbol] = 1
                g.short_open_date[symbol] = pos.m_strOpenDate  # 空头开仓日期
                g.short_volume[symbol] = pos.m_nVolume  # 空头持仓量
                g.short_entry_price[symbol] = pos.m_dOpenPrice  # 空头持仓成本

            PositionInfo_dict['持仓量'] = pos.m_nVolume  # 持仓量
            PositionInfo_dict['代码'] = symbol
            PositionInfo_dict['持仓类型'] = position_type  # 48：多 49：空
            PositionInfo_dict['持仓成本'] = pos.m_dOpenPrice
            PositionInfo_dict['持仓盈亏'] = pos.m_dPositionProfit
            PositionInfo_dict['开仓日期'] = pos.m_strOpenDate
            PositionInfo_df = pd.DataFrame([PositionInfo_dict])

            PositionInfo_dfs = pd.concat([PositionInfo_dfs, PositionInfo_df], ignore_index=True)

        print(f"    [账户信息] 持仓:\n {str(PositionInfo_dfs)} ")
        # 持仓数量通过PositionInfo_dfs有几行数据来决定
        g.position_count = PositionInfo_dfs.shape[0]
        print(f"  [账户信息] 更新持仓状态，当前持仓合约数: {g.position_count}")

        g.position_code = PositionInfo_dfs['代码'].tolist()
        print(f"  [账户信息] 持仓合约列表: {g.position_code}")


def handlebar(ContextInfo):
    pass
