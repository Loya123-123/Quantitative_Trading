def query_stock_holding(account, xt_trader):
    """查询股票持仓

    Args:
        account (_type_): 股票账户类

    Returns:
    stock:{
        "volume":obj.volume,
        "can_use_volume":obj.can_use_volume,
        "open_price":obj.open_price,
        "market_value":obj.market_value,
        "yesterday_volume":obj.yesterday_volume,
        "avg_price":obj.avg_price
        
    """
    positions = xt_trader.query_stock_positions(account)
    Position_info = {}
    for obj in positions:
        Position_info[obj.stock_code] = {
            "volume": obj.volume,
            "can_use_volume": obj.can_use_volume,
            "open_price": obj.open_price,
            "market_value": obj.market_value,
            "yesterday_volume": obj.yesterday_volume,
            "avg_price": obj.avg_price
        }
    return Position_info


def query_stock_order_info(account, xt_trader) -> dict:
    """
    返回的结构是{stock:{order_sysID:{order_info...}}}
    """
    order = xt_trader.query_stock_orders(account)
    Order_info = {}
    for obj in order:
        stock = obj.stock_code
        # Order_info.setdefault(stock, {})
        order_time = obj.order_time  # 委托时间
        order_type = obj.order_type  # 委托方向判断
        order_remark = obj.order_remark  # 投资备注
        order_volume = obj.order_volume  # 委托量
        volume_total = order_volume - obj.traded_volume  # 剩余委托量
        order_status = obj.order_status  # 委托状态
        limit_price = obj.price  # 委托价格
        order_id = obj.order_id  # 订单编号
        order_sysID = obj.order_sysid  # 委托编号
        Order_info[order_sysID] = {
            "stock": stock,  # a股代码
            "order_time": order_time,  # 委托时间
            "order_volume": order_volume,  # 委托量
            "volume_total": volume_total,  # 剩余委托量
            "order_status": order_status,  # 委托状态
            "order_remark": order_remark,  # 投资备注
            "order_type": order_type,  # 成交方向判断
            "limit_price": limit_price,  # 委托价格
            "order_id": order_id  # 订单编号
        }
    return Order_info


def calculate_available_position(orders, last_position):
    """
    计算当前可用持仓（完整处理所有订单状态）
    
    参数:
        orders: 订单列表，每个订单包含:
            - 'stock': 标的代码
            - 'order_type': 委托方向 (23:买入, 24:卖出)
            - 'order_status': 订单状态 (48-57, 255)
            - 'order_volume': 委托数量
            - 'volume_total': 剩余未成交数量
    
    返回:
        {标的代码: 可用持仓量}，仅包含持仓量 > 0 的标的
    """
    # print(last_position)
    # 初始化统计项
    position = {}  # 净持仓（买入增加，卖出减少）
    buy_frozen = {}  # 买入方向冻结量
    sell_frozen = {}  # 卖出方向冻结量
    yesterday_position = {}  # 昨日持仓量
    try:
        for order in orders:
            stock = order['stock']
            order_type = order['order_type']
            order_status = order['order_status']
            order_volume = order['order_volume']
            volume_total = order['volume_total']
            traded_volume = order_volume - volume_total  # 已成交量

            # 初始化标的的统计项
            if stock not in position:
                position[stock] = 0
                buy_frozen[stock] = 0
                sell_frozen[stock] = 0
                yesterday_position[stock] = int(
                    last_position[stock]['yesterday_volume']) if stock in last_position else 0

            # 买入方向处理
            if order_type == 23:
                if order_status == 56:  # 已成
                    position[stock] += order_volume
                elif order_status in [52, 55]:  # 部成待撤/部成
                    position[stock] += traded_volume
                    buy_frozen[stock] += volume_total
                elif order_status == 53:  # 部撤
                    position[stock] += traded_volume
                    # 剩余量自动释放（不冻结）
                elif order_status in [50, 51]:  # 已报/已报待撤
                    buy_frozen[stock] += volume_total
            # 卖出方向处理
            elif order_type == 24:
                if order_status == 56:  # 已成
                    position[stock] -= order_volume
                elif order_status in [52, 55]:  # 部成待撤/部成
                    position[stock] -= traded_volume
                    sell_frozen[stock] += volume_total
                elif order_status == 53:  # 部撤
                    position[stock] -= traded_volume
                    # 剩余量自动释放（不冻结）
                elif order_status in [50, 51]:  # 已报/已报待撤
                    sell_frozen[stock] += volume_total
            # if stock=='159302.SZ':
            # print('159302.SZ',position[stock],sell_frozen[stock])
        # 计算可用持仓 =昨日持仓 + 净持仓 - 卖出冻结（且 >= 0）
        # 订单统计只统计今日的，因此需要将昨日持仓初始化
        available_position = {
            stock: max(yesterday_position[stock] + position[stock] - sell_frozen[stock], 0)
            for stock in position
        }

        # 仅返回可用持仓 > 0 的标的
        return {stock: pos for stock, pos in available_position.items() if pos > 0}
    except Exception as e:
        return {}
