# coding:gbk

"""
A股单边网格交易实盘策略 (布林带择入与T+1版)
针对 510100.SH (上证50等权ETF) 和 510310.SH (沪深300ETF)

核心逻辑：
1. 布林带入场：触及 20日下轨启动。
2. 1% 等比买入与卖出。
3. T+1 仓位管理：当日买入需次日“可用”后方可卖出。
4. 双重止损：10% 或 2.5*ATR。
"""

import logging
from datetime import datetime
import json
import numpy as np
import pandas as pd
import requests
import os

# 全局变量
class G():
    pass

g = G()
log_filename = None

def init(ContextInfo):
    """
    初始化
    """
    ContextInfo.account_id = account # 外部传入账户
    g.account = ContextInfo.account_id
    
    # 路径配置
    g.work_dir = 'C:\\合约选品\\'
    g.log_dir = 'C:\\datalog\\'
    g.status_file = os.path.join(g.work_dir, f'stock_grid_status_{g.account}.json')

    # 初始化日志
    global log_filename
    log_filename = get_log_filename(g.account)
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    status_msg = "初始化 A股单边等比网格策略 (T+1版)..."
    log_section(status_msg)

    # 策略参数
    g.stock_list = ['510100.SH', '510310.SH'] # 指定标的
    g.grid_ratio = 0.01          # 1% 等比
    g.grid_lot_size = 100        # A股一手
    g.stop_loss_ratio = 0.10     # 10% 止损
    g.atr_multiplier = 2.5       # 2.5 * ATR 止损
    g.bb_window = 20
    g.bb_std = 2
    g.max_lots_per_stock = 50    # 每个品种最多持有 50 手 (5000股)

    # 内部状态
    g.grid_status = load_status() # {stock_code: {"status": "WAITING/GRIDDING", "base_price": float, "pending_sells": []}}
    g.available_vol = {}          # {stock_code: int} 可用持仓
    g.total_vol = {}              # {stock_code: int} 总持仓
    g.avg_price = {}              # {stock_code: float} 均价
    g.current_atr = {}
    
    ContextInfo.set_universe(g.stock_list)
    
    log_info(f"[初始化] 交易标的: {g.stock_list}")
    log_info(f"[初始化] 止损规则: 10% 比例 / {g.atr_multiplier}*ATR 动态")
    log_section("A股策略初始化完成")

    # 3秒周期
    ContextInfo.run_time("run_time_handlebar", "3nSecond", "2026-01-01 09:30:00")

def run_time_handlebar(ContextInfo):
    """
    主执行逻辑
    """
    if not ContextInfo.is_last_bar(): return
    if not is_trading_time(datetime.now()): return

    # 1. 同步 A股 账户与可用仓位
    sync_stock_account(ContextInfo)
    
    # 2. 依次处理各股票
    for stock_code in g.stock_list:
        monitor_stock_grid(ContextInfo, stock_code)

    # 3. 状态持久化
    save_status()

def monitor_stock_grid(ContextInfo, stock_code):
    """
    单只股票监控
    """
    indicators = get_stock_indicators(ContextInfo, stock_code)
    if not indicators: return
    
    curr_price = indicators['close']
    lower_band = indicators['lower_band']
    g.current_atr[stock_code] = indicators['atr']

    state = g.grid_status.get(stock_code, {"status": "WAITING", "base_price": 0, "pending_sells": []})
    status = state["status"]

    # 止损监控 (如果总持仓 > 0)
    if g.total_vol.get(stock_code, 0) > 0:
        if perform_stock_stop_loss(ContextInfo, stock_code, curr_price):
            return

    # 状态机
    if status == "WAITING":
        # 布林带下轨触发入场
        if curr_price <= lower_band:
            msg = f"* [A股信号] {stock_code} 触轨 ({curr_price:.3f} <= {lower_band:.3f})，启动首笔买入"
            feishu_log_info(msg)
            
            # 买入 100 股
            oid = place_stock_order(ContextInfo, stock_code, 0, curr_price, g.grid_lot_size, "Init_Buy")
            if oid >= 0:
                state["status"] = "GRIDDING"
                state["base_price"] = curr_price
                g.grid_status[stock_code] = state

    elif status == "GRIDDING":
        # 监控买入补单与 T+1 卖出
        manage_active_grid(ContextInfo, stock_code, curr_price, state)

def manage_active_grid(ContextInfo, stock_code, curr_price, state):
    """
    管理运行中的网格
    """
    base_price = state["base_price"]
    
    # 逻辑 A：下跌 1% 继续补仓 (只要未达上限)
    next_buy_price = base_price * (1 - g.grid_ratio)
    if curr_price <= next_buy_price and g.total_vol.get(stock_code, 0) < g.max_lots_per_stock * 100:
        oid = place_stock_order(ContextInfo, stock_code, 0, curr_price, g.grid_lot_size, "Grid_Buy_Catch")
        if oid >= 0:
            state["base_price"] = curr_price # 更新基准价进行下一次等比计算
    
    # 逻辑 B：检测已买入层的获利卖出 (需 T+1 检查)
    # 计算当前持有且未卖出的网格位。在 A 股由于 T+1，我们通过记录 pending_sells。
    # 简化：如果价格上涨 > 均价 * 1.01，且可用持仓 > 0，则卖出。
    avg_price = g.avg_price.get(stock_code, 0)
    available = g.available_vol.get(stock_code, 0)
    
    if avg_price > 0 and curr_price >= avg_price * (1 + g.grid_ratio):
        if available >= g.grid_lot_size:
            oid = place_stock_order(ContextInfo, stock_code, 1, curr_price, g.grid_lot_size, "Grid_Sell_Profit")
            if oid >= 0:
                # 卖出后，base_price 可选择保持或重置。通常网格会重置。
                state["base_price"] = curr_price
        else:
            log_info(f"[T+1 等待] {stock_code} 达到卖点 {curr_price:.3f}，但今日无可用持仓，暂缓卖出")

def perform_stock_stop_loss(ContextInfo, stock_code, curr_price):
    """
    A股止损逻辑
    """
    avg = g.avg_price.get(stock_code, 0)
    atr = g.current_atr.get(stock_code, 0)
    available = g.available_vol.get(stock_code, 0)
    
    # 1. 亏损 10%
    if (curr_price - avg) / avg <= -g.stop_loss_ratio:
        reason = f"比例止损 (亏损10%+)"
    # 2. 价格 < 均价 - 2.5 * ATR
    elif curr_price < avg - g.atr_multiplier * atr:
        reason = f"ATR止损 (破位 {avg - g.atr_multiplier * atr:.3f})"
    else:
        return False

    msg = f"! [A股强损] {stock_code} 触发 {reason}！"
    feishu_log_info(msg)
    
    # 撤单并以可用持仓清仓
    if available > 0:
        place_stock_order(ContextInfo, stock_code, 1, -1, available, "StopLoss_All")
    
    # 重置状态
    g.grid_status[stock_code]["status"] = "WAITING"
    return True

def sync_stock_account(ContextInfo):
    """
    同步 A 股账户信息与可用仓位 (T+1)
    """
    try:
        pos_list = ContextInfo.get_trade_detail_data(g.account, 'STOCK', 'POSITION')
        g.total_vol = {}
        g.available_vol = {}
        g.avg_price = {}
        
        if pos_list:
            for pos in pos_list:
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                if symbol not in g.stock_list: continue
                
                g.total_vol[symbol] = pos.m_nVolume
                g.available_vol[symbol] = pos.m_nCanUseVolume # 关键：可用持仓
                g.avg_price[symbol] = pos.m_dOpenPrice
                
    except Exception as e:
        log_info(f"[账户同步] 失败: {e}")

def place_stock_order(ContextInfo, stock_code, opType, price, volume, label):
    """
    股票下单 (opType 0=买, 1=卖)
    """
    # 股票通常用 1101 限价。报价类型 11 (固定价), 14 (最新价)
    # 此处默认用固定价 (11)
    prType = 11 if price > 0 else 14 # 如果传入-1则用最新价市价化
    
    oid = passorder(opType, 1101, g.account, stock_code, prType, price, volume, 1, ContextInfo)
    if oid >= 0:
        msg = f"[股票下单] {stock_code} {label} 类型:{opType} 价格:{price:.3f} 数量:{volume}"
        log_info(msg)
        return oid
    else:
        log_info(f"[股票下单] 失败 {stock_code} 错误码:{oid}")
        return -1

def get_stock_indicators(ContextInfo, stock_code):
    """
    获取指标
    """
    data = ContextInfo.get_market_data_ex(['close','high','low'], [stock_code], period='1d', count=g.bb_window + 5)
    if stock_code not in data: return None
    df = data[stock_code]
    if len(df) < g.bb_window: return None
    
    ma = df['close'].rolling(g.bb_window).mean().iloc[-1]
    std = df['close'].rolling(g.bb_window).std().iloc[-1]
    
    # ATR
    prev_close = df['close'].shift(1).values
    high, low = df['high'].values, df['low'].values
    tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - prev_close[:-1]))
    tr = np.maximum(tr, np.abs(low[1:] - prev_close[:-1]))
    atr = np.mean(tr[-10:])

    return {
        "close": df['close'].iloc[-1],
        "lower_band": ma - g.bb_std * std,
        "atr": atr
    }

# --- 通用工具 ---

def load_status():
    if os.path.exists(g.status_file):
        try:
            with open(g.status_file, 'r', encoding='gbk') as f: return json.load(f)
        except: return {}
    return {}

def save_status():
    try:
        with open(g.status_file, 'w', encoding='gbk') as f: json.dump(g.grid_status, f, indent=4)
    except: pass

def get_log_filename(account):
    return f"C:\\datalog\\stock-grid-{account}-{datetime.now().strftime('%Y%m%d')}.log"

def is_trading_time(t):
    h, m = t.hour, t.minute
    if (9 <= h < 11) or (h == 11 and m <= 30): return True
    if (13 <= h < 15): return True
    return False

def log_info(m): logging.info(m); print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")
def feishu_log_info(m): log_info(m); send_feishu_message(m)
def log_section(title): log_info(f"=== {title} ===")

def send_feishu_message(message):
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/086957a2-ddb4-4406-a720-3caaa7e3930f"
    try: requests.post(url, json={"msg_type": "text", "content": {"text": f"STK-GRID {g.account}: {message}"}}, timeout=5)
    except: pass
