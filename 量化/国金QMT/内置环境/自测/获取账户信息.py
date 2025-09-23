# coding:gbk
import pandas as pd
import logging
from datetime import datetime
import numpy as np

# 市场	市场代码	迅投市场代码
# 上期所	SHFE	SF
# 大商所	DCE	DF
# 郑商所	CZCE	ZF
# 中金所	CFFEX	IF
# 能源中心	INE	INE
# 广期所	GFEX	GF

class G():
    pass


g = G()


def init(ContextInfo):
    g.long_position = {}  # 多头持仓：0-无仓位，1-持有多头，为每个合约保存
    g.short_position = {}  # 空头持仓：0-无仓位，1-持有空头，为每个合约保存
    g.highest_after_entry = {}  # 入市后的最高价，为每个合约保存
    g.lowest_after_entry = {}  # 入市后的最低价，为每个合约保存
    g.long_open_date = {}  # 多头开仓日期，为每个合约保存
    g.short_open_date = {}  # 空头开仓日期，为每个合约保存
    g.long_volume = {}  # 多头持仓量，为每个合约保存
    g.long_entry_price = {}  # 多头持仓价，为每个合约保存
    g.short_volume = {}  # 空头持仓量，为每个合约保存
    g.short_entry_price = {}  # 空头持仓价，为每个合约保存
    # ContextInfo.account_id = 'test1'
    ContextInfo.account_id = account  # 期货账户ID
    get_account_info(ContextInfo)

def get_account_info(ContextInfo):
    """
    获取账户信息
    包括可用资金、总权益、持仓等
    """
    try:
        print("  [账户信息] 开始获取账户信息...")

        # 获取账户资金信息
        print("  [账户信息] 获取账户资金详情...")
        account_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ACCOUNT')
        if not account_details:
            print("  [账户信息] 获取账户详情失败")
            return None
        g.position_code = []  # 仓位代码
        account = account_details[0]
        available = account.m_dAvailable  # 可用资金
        total_value = account.m_dBalance  # 总权益


        print(f"  [账户信息] 账户资金信息: 可用资金={available:.2f}, 总资产={total_value:.2f}")


        # 获取未成交委托信息并撤销未成交委托
        print("  [账户信息] 获取未成交委托详情...")
        order_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'ORDER')
        if order_details:
            order_len = 0
            for order in order_details:
                # print(f"  [账户信息] 获取到委托记录：\n {to_dict(order)}")
                # 获取委托状态，50-54表示未成交状态
                order_status = order.m_nOrderStatus
                symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID

                # 检查是否为未成交状态(状态码49-53)
                if 49 <= order_status < 54:
                    print(
                        f"  [账户信息] 发现未成交委托，合约: {symbol}, 状态: {order_status}, 委托编号: {order.m_strOrderSysID}")
                    # 撤销未成交委托
                    # cancel_result = cancel(order.m_strOrderSysID, ContextInfo.account_id, 'FUTURE', ContextInfo)
                    # print(f"  [账户信息] 撤销委托结果: {cancel_result}")
                    order_len += 1
                else:
                    print(f"  [账户信息] 合约: {symbol} ,委托状态为: {order_status}，无需撤销")
            print(f"  [账户信息] 处理  {order_len} 条委托记录")
        else:
            print("  [账户信息] 无委托记录")

        # 获取持仓信息
        print("  [账户信息] 获取持仓详情...")
        position_details = get_trade_detail_data(ContextInfo.account_id, 'FUTURE', 'POSITION')
        PositionInfo_dict = {}
        PositionInfo_dfs = pd.DataFrame()

        if position_details:
            position_data_list = []
            for pos in position_details:
                if pos.m_nVolume != 0:  # 忽略持仓量为0的合约
                    # 获取 pos 对象转json信息
                    # print(f"  [账户信息] 获取持仓属性信息: {dir(pos)}")
                    symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID

                    position_type = pos.m_nDirection

                    # 构建持仓数据列表用于后续聚合
                    position_record = {
                        '持仓量': pos.m_nVolume,
                        '代码': symbol,
                        '持仓类型': position_type,
                        '持仓成本': pos.m_dOpenPrice,
                        '持仓盈亏': pos.m_dPositionProfit,
                        '开仓日期': pos.m_strOpenDate
                    }
                    position_data_list.append(position_record)

            # 创建DataFrame并按代码和持仓类型聚合持仓数据
            if position_data_list:
                PositionInfo_dfs = pd.DataFrame(position_data_list)

                # 按代码和持仓类型聚合持仓数据
                aggregated_positions = PositionInfo_dfs.groupby(['代码', '持仓类型']).agg({
                    '持仓量': 'sum',
                    '持仓成本': lambda x: np.average(x, weights=PositionInfo_dfs.loc[x.index, '持仓量']),  # 加权平均成本
                    '持仓盈亏': 'sum',
                    '开仓日期': 'first'
                }).reset_index()

                # 从聚合后的数据中获取持仓信息
                for _, row in aggregated_positions.iterrows():
                    symbol = row['代码']
                    position_type = row['持仓类型']
                    volume = row['持仓量']
                    entry_price = row['持仓成本']
                    open_date = row['开仓日期']

                    # 检查持仓是否属于当前策略的合约
                    if position_type == 48:  # 多头持仓
                        g.long_position[symbol] = 1  # 多头持仓状态
                        g.long_open_date[symbol] = open_date  # 多头开仓日期
                        g.long_volume[symbol] = volume  # 多头持仓量
                        g.long_entry_price[symbol] = entry_price  # 多头持仓成本

                    elif position_type == 49:  # 空头持仓
                        g.short_position[symbol] = 1  # 空头持仓状态
                        g.short_open_date[symbol] = open_date  # 空头开仓日期
                        g.short_volume[symbol] = volume  # 空头持仓量
                        g.short_entry_price[symbol] = entry_price  # 空头持仓成本

                print(f"    [账户信息] 持仓明细:\n {str(PositionInfo_dfs)} ")
                print(f"    [账户信息] 聚合后持仓:\n {str(aggregated_positions)} ")

                # 持仓数量通过aggregated_positions有几行数据来决定
                g.position_count = aggregated_positions.shape[0]
                print(f"  [账户信息] 更新持仓状态，当前持仓合约数: {g.position_count}")

                g.position_code = aggregated_positions['代码'].tolist()
                print(f"  [账户信息] 持仓合约列表: {g.position_code}")
            else:
                print("  [账户信息] 无持仓记录")

        else:
            print("  [账户信息] 无持仓记录")

        return {
            'available': available,
            'total_value': total_value,
            'PositionInfo_dfs': PositionInfo_dfs,
            'PositionInfo_dict': PositionInfo_dict,  # 返回更多持仓信息
        }

    except Exception as e:
        print(f"  [账户信息] 获取账户信息时发生错误: {e}")
        return None


def handlebar(ContextInfo):
    pass
