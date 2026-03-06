# coding: gbk
# 期货交易示例：开仓、平仓、撤单

def init(ContextInfo):
    # 初始化全局变量
    ContextInfo.order_id = None  # 存储订单ID
    ContextInfo.position = 0     # 存储持仓数量

def handlebar(ContextInfo):
    # 期货代码（以沪深300股指期货为例）
    futures_code = "IF2406.CF"
    
    # 获取最新行情
    market_data = ContextInfo.get_market_data(["close", "openInterest"], [futures_code], 1, "1m")
    if market_data.empty:
        print(f"无法获取{futures_code}的行情数据")
        return
    
    current_price = market_data["close"].iloc[-1]
    print(f"当前价格: {current_price}")
    
    # 示例1：开仓（买入开仓```python
#coding:gbk
from datetime import datetime

# 全局变量记录订单信息
order_info = {}

def init(ContextInfo):
    pass

def handlebar(ContextInfo):
    global order_info
    account = "您的期货账号"  # 替换为实际期货账号
    
    # 1. 开仓示例 - 买入开仓1手
    if not order_info.get("opened", False):
        # 按最新价买入开仓1手
        buy_open("IF2406.CF", 1, ContextInfo, account)
        order_info["opened"] = True
        order_info["open_time"] = datetime.now()
        print(f"{datetime.now().strftime("%H:%M:%S")} 开仓委托已发送")
        return
    
    # 2. 撤单示例 - 如果开仓委托未成交，5秒后撤单
    current_time = datetime.now()
    if (current_time - order_info["open_time"]).seconds > 5 and not order_info.get("canceled", False):
        # 获取当前委托列表，找到对应的开仓委托进行撤单
        orders = ContextInfo.get_orders(account, 0)
        for order in orders:
            if order.m_strInstrumentID == "IF2406.CF" and order.m_nOrderStatus == 0:  # 0表示已报状态
                cancel(order.m_strOrderSysID, account, "future", ContextInfo)
                order_info["canceled"] = True
                print(f"{current_time.strftime("%H:%M:%S")} 撤单委托已发送")
                return
    
    # 3. 平仓示例 - 如果已有持仓，进行平仓
    if not order_info.get("closed", False) and order_info.get("opened", False):
        # 获取当前持仓
        positions = ContextInfo.get_positions(account, 0)
        for pos in positions:
            if pos.m_strInstrumentID == "IF2406.CF" and pos.m_nCanCloseVolume > 0:
                # 卖出平仓
                sell_close("IF2406.CF", pos.m_nCanCloseVolume, ContextInfo, account)
                order_info["closed"] = True
                print(f"{current_time.strftime("%H:%M:%S")} 平仓委托已发送")
                return

# 辅助函数：获取委托状态文本
def get_order_status(status):
    status_map = {
        0: "已报", 1: "正在申报", 2: "未报", 3: "废单",
        4: "部成", 5: "已成", 6: "部撤", 7: "已撤"
    }
    return status_map.get(status, "未知状态")# test
