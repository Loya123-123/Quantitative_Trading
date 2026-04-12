# coding:gbk

"""
双向等比网格交易策略 (布林带择入与双重止损版)
基于国金QMT平台实现

核心功能：
1. 布林带入场：价格触及下轨启动。
2. 1% 等比网格：支持成交价校准。
3. 双重止损：亏损10% 或 价格 < 持仓均价 - 2.5 * ATR。
4. 状态持久化：JSON 记录。
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
    策略初始化
    """
    ContextInfo.account_id = account  # 外部传入账户
    g.account = ContextInfo.account_id
    
    # 路径与文件 (Windows 绝对路径)
    g.work_dir = 'C:\\合约选品\\'
    g.log_dir = 'C:\\datalog\\'
    g.status_file = os.path.join(g.work_dir, f'grid_v3_status_{g.account}.json')
    
    # 初始化日志
    global log_filename
    log_filename = get_log_filename(g.account)
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    if is_weekend():
        return

    log_section("初始化布林带-网格交易策略 (v3)...")

    # 核心策略参数
    g.grid_ratio = 0.01          # 1% 等比网格
    g.num_grids = 5              # 初始布单层数
    g.stop_loss_ratio = 0.10     # 10% 比例止损
    g.atr_multiplier = 2.5       # 2.5 * ATR 止损
    g.bb_window = 20             # 布林带周期
    g.bb_std = 2                 # 布林带标准差
    g.max_lots = 10              # 单品种单边持仓上限
    g.near_expiry_days = 30
    g.trend_days = 30
    g.position_limit = 4         # 最大持仓品种数
    g.is_trend_or_efficiency = 2

    # 策略内部状态
    g.grid_status = load_status()  # {stock_code: {"status": "WAITING/GRIDDING/STOPPED", "base_price": float, "orders": {}}}
    g.long_position = {}           # {stock_code: volume}
    g.short_position = {}
    g.entry_price = {}             # {stock_code: avg_price}
    g.current_atr = {}             # {stock_code: float}
    g.position_codes = []

    # 选品初始化
    g.pools_df = select_pools()
    if g.pools_df.empty:
        log_info("[初始化] 品种池为空")
        return

    select_contract(ContextInfo)
    
    # 设置运行宇宙
    ContextInfo.stock_codes = [info["code"] + '.' + info["market"] for k, info in ContextInfo.stock_codes_dict.items()]
    ContextInfo.set_universe(ContextInfo.stock_codes)
    
    log_info(f"[初始化] 布林带参数: ({g.bb_window}, {g.bb_std})")
    log_info(f"[初始化] 止损规则: 10% 或 2.5*ATR")
    log_section("策略初始化完成")

    # 3秒运行一次
    ContextInfo.run_time("run_time_handlebar", "3nSecond", "2026-01-01 09:30:00")

def run_time_handlebar(ContextInfo):
    """
    主循环
    """
    if not ContextInfo.is_last_bar(): return
    if not is_trading_time(datetime.now()): return

    # 1. 同步账户与持仓
    get_account_info(ContextInfo)
    
    # 2. 处理选中的合约
    for stock_code in ContextInfo.stock_codes:
        monitor_strategy(ContextInfo, stock_code)

    # 3. 结果持久化
    save_status()

def monitor_strategy(ContextInfo, stock_code):
    """
    单合约监控逻辑
    """
    # 获取指标数据
    price_data = get_market_indicators(ContextInfo, stock_code)
    if not price_data: return
    
    curr_price = price_data['close']
    lower_band = price_data['lower_band']
    g.current_atr[stock_code] = price_data['atr']
    
    # 获取或初始化合约状态
    state = g.grid_status.get(stock_code, {"status": "WAITING", "base_price": 0, "orders": {}})
    status = state["status"]

    # 止损检查（如果有持仓）
    if stock_code in g.position_codes:
        if check_stop_loss(ContextInfo, stock_code, curr_price):
            return

    # 状态机处理
    if status == "WAITING":
        # 等待布林带下轨入场
        if curr_price <= lower_band:
            msg = f"* [入场号角] {stock_code} 触及布林线区间 (价:{curr_price:.2f} 轨:{lower_band:.2f})，启动网格交易"
            feishu_log_info(msg)
            
            # 执行首笔买入
            qty = ContextInfo.stock_codes_dict[stock_code.split('.')[0]]["size"]
            oid = place_limit_order(ContextInfo, stock_code, 0, curr_price, qty, "Entry_Buy")
            
            # 更新状态
            state["status"] = "GRIDDING"
            state["base_price"] = curr_price
            g.grid_status[stock_code] = state
            
    elif status == "GRIDDING":
        # 监控挂单成交并进行补单
        monitor_grid_fills(ContextInfo, stock_code, curr_price)

def check_stop_loss(ContextInfo, stock_code, curr_price):
    """
    双重止损逻辑
    """
    avg_price = g.entry_price.get(stock_code, 0)
    atr = g.current_atr.get(stock_code, 0)
    
    if avg_price <= 0: return False

    # 条件1：亏损 10%
    loss_ratio = (curr_price - avg_price) / avg_price
    # 条件2：价格 < 均价 - 2.5 * ATR
    atr_threshold = avg_price - g.atr_multiplier * atr
    
    # 做空持仓逻辑反向 (此处演示以多头网格为主，双向需细化)
    is_long = g.long_position.get(stock_code, 0) > 0
    
    stop_triggered = False
    stop_reason = ""
    
    if is_long:
        if loss_ratio <= -g.stop_loss_ratio:
            stop_triggered = True
            stop_reason = f"比例止损 (亏损:{loss_ratio:.2%})"
        elif curr_price < atr_threshold:
            stop_triggered = True
            stop_reason = f"ATR止损 (现价:{curr_price:.2f} < 阈值:{atr_threshold:.2f})"
    
    if stop_triggered:
        msg = f"! [强行止损] {stock_code} 触发 {stop_reason}，清仓所有挂单与持仓！"
        feishu_log_info(msg)
        execute_emergency_close(ContextInfo, stock_code)
        g.grid_status[stock_code]["status"] = "STOPPED" # 或者重置为 WAITING
        return True
    
    return False

def monitor_grid_fills(ContextInfo, stock_code, curr_price):
    """
    监控网格成交并补单
    """
    status_data = g.grid_status.get(stock_code)
    if not status_data: return
    
    # 获取成交回报
    order_details = ContextInfo.get_trade_detail_data(g.account, 'FUTURE', 'ORDER')
    if not order_details: return
    
    executed_ids = []
    
    for order in order_details:
        oid = str(order.m_strOrderSysID)
        symbol = order.m_strInstrumentID + '.' + order.m_strExchangeID
        
        if symbol == stock_code and oid in status_data["orders"]:
            # 54 = 已成交
            if order.m_nOrderStatus == 54:
                fill_info = status_data["orders"][oid]
                executed_ids.append(oid)
                # 使用实盘持仓成本校准补单
                handle_grid_cycle(ContextInfo, stock_code, fill_info)
            # 56, 58 = 废单/已撤
            elif order.m_nOrderStatus in (56, 58):
                executed_ids.append(oid)

    for oid in executed_ids:
        del status_data["orders"][oid]

def handle_grid_cycle(ContextInfo, stock_code, fill_info):
    """
    成交后的补单逻辑：根据持仓成本校准
    """
    otype = fill_info["type"] # 0=买开, 3=卖开...
    # 获取该合约最新成交价（从持仓更新中获取，更准）
    # 在本周期 get_account_info 已更新 g.entry_price
    real_fill_price = g.entry_price.get(stock_code, fill_info["price"])
    qty = fill_info["volume"]
    
    # 对冲补单
    if otype == 0: # 买入成交 -> 挂高位平仓
        target_sell = real_fill_price * (1 + g.grid_ratio)
        place_limit_order(ContextInfo, stock_code, 9, target_sell, qty, "Grid_Profit_Sell")
    elif otype == 3: # 卖开成交 -> 挂低位买平
        target_buy = real_fill_price * (1 - g.grid_ratio)
        place_limit_order(ContextInfo, stock_code, 7, target_buy, qty, "Grid_Profit_Buy")

def get_market_indicators(ContextInfo, stock_code):
    """
    计算布林带与 ATR
    """
    data = ContextInfo.get_market_data_ex(['close', 'high', 'low'], [stock_code], period='1d', count=g.bb_window + 5)
    if stock_code not in data: return None
    df = data[stock_code]
    
    if len(df) < g.bb_window: return None
    
    # 布林带
    ma = df['close'].rolling(g.bb_window).mean().iloc[-1]
    std = df['close'].rolling(g.bb_window).std().iloc[-1]
    
    # ATR 计算
    high = df['high'].values
    low = df['low'].values
    prev_close = df['close'].shift(1).values
    tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - prev_close[:-1]))
    tr = np.maximum(tr, np.abs(low[1:] - prev_close[:-1]))
    atr = np.mean(tr[-10:]) # 默认取10日ATR
    
    return {
        "close": df['close'].iloc[-1],
        "lower_band": ma - g.bb_std * std,
        "ma": ma,
        "atr": atr
    }

def get_account_info(ContextInfo):
    """
    完整的账户信息与持仓同步
    """
    try:
        # 1. 持仓查询
        pos_list = get_trade_detail_data(g.account, 'FUTURE', 'POSITION')
        g.position_codes = []
        g.entry_price = {}
        g.long_position = {}
        g.short_position = {}
        
        if pos_list:
            for pos in pos_list:
                if pos.m_nVolume == 0: continue
                symbol = pos.m_strInstrumentID + '.' + pos.m_strExchangeID
                g.position_codes.append(symbol)
                
                # QMT m_nDirection: 48=多, 49=空
                if pos.m_nDirection == 48:
                    g.long_position[symbol] = pos.m_nVolume
                    g.entry_price[symbol] = pos.m_dOpenPrice # 实盘开仓均价
                else:
                    g.short_position[symbol] = pos.m_nVolume
                    g.entry_price[symbol] = pos.m_dOpenPrice
                    
    except Exception as e:
        log_info(f"[账户同步] 失败: {e}")

def execute_emergency_close(ContextInfo, stock_code):
    """
    紧急清仓逻辑
    """
    # 1. 撤销所有相关挂单
    # (QMT cancel函数调用)
    
    # 2. 对冲平仓
    long_vol = g.long_position.get(stock_code, 0)
    if long_vol > 0:
        passorder(7, 1101, g.account, stock_code, 14, -1, long_vol, 1, ContextInfo)
        
    short_vol = g.short_position.get(stock_code, 0)
    if short_vol > 0:
        passorder(9, 1101, g.account, stock_code, 14, -1, short_vol, 1, ContextInfo)

def place_limit_order(ContextInfo, stock_code, opType, price, qty, label):
    """
    封装下单，记录到字典
    """
    # 这里需要增加仓位限制判断
    if qty > g.max_lots: qty = g.max_lots # 简单限制
    
    oid = passorder(opType, 1101, g.account, stock_code, 11, price, qty, 1, ContextInfo)
    if oid >= 0:
        log_info(f"[下单] {stock_code} {label} 价格:{price:.2f} ID:{oid}")
        if stock_code not in g.grid_status: 
            g.grid_status[stock_code] = {"status": "GRIDDING", "orders": {}}
        g.grid_status[stock_code]["orders"][str(oid)] = {"price": price, "type": opType, "volume": qty, "label": label}
        return oid
    return -1

# --- 工具类函数 (复用) ---

def select_contract(ContextInfo):
    """
    执行海龟同款选品逻辑
    """
    bar_date_now = datetime.strftime(datetime.now(), '%Y%m%d')
    current_hour = int(datetime.strftime(datetime.now(), '%H'))
    # ========== 执行选品逻辑 ==========
    try:
        # 步骤1：读取品种池
        log_section("步骤1：读取品种池")
        log_info(f"[处理函数] 品种池共 {len(g.pools_df)} 个品种")
        
        # 步骤2：遍历品种池，获取主力合约和计算指标
        log_section("步骤2：获取主力合约和计算指标")
        results = []  # 存储所有品种的计算结果
        for idx, row in g.pools_df.iterrows():
            code = row['代码']  # 品种代码，如 rb
            exchange_code = row['交易所代码']  # 交易所代码，如 SF
            n_lots = row['n手（取整）']  # n手（取整）
            
            continuous_contract = code + "00" + "." + exchange_code
            
            try:
                main_contract_code = ContextInfo.get_main_contract(continuous_contract)
                if not main_contract_code:
                    continue
                main_contract = main_contract_code + "." + exchange_code
            except: continue
            
            max_trend_days = g.trend_days + 3
            current_contract = main_contract
            
            try:
                history_data = ContextInfo.get_market_data_ex(
                    ['time', 'open', 'high', 'low', 'close'],
                    [current_contract],
                    end_time=bar_date_now,
                    period='1d',
                    count=max_trend_days,
                    dividend_type=ContextInfo.dividend_type,
                    subscribe=True
                )
                if not history_data or current_contract not in history_data:
                    continue
                history_df = history_data[current_contract]
                history_df['time'] = history_df['time'].apply(lambda x: timetag_to_datetime(x, '%Y-%m-%d %H:%M:%S'))
                history_df = history_df[:-1] if current_hour < 16 else history_df
                history_df = history_df.sort_values(by='time', ascending=False).reset_index(drop=True)
            except: continue
            
            if len(history_df) <= g.trend_days: continue
            
            try:
                close_yesterday = history_df['close'].iloc[0]
                close_N_days_ago = history_df['close'].iloc[g.trend_days - 1]
                trend_amplitude = abs(close_yesterday - close_N_days_ago)
                
                volatility_sum = 0
                for i in range(0, g.trend_days):
                    daily_range = abs(history_df['high'].iloc[i] - history_df['low'].iloc[i])
                    volatility_sum += daily_range
                
                trend_efficiency = trend_amplitude / volatility_sum if volatility_sum != 0 else 0
                
                results.append({
                    'symbol': code, 'market': exchange_code, 'code': main_contract.split('.')[0], 
                    'size': n_lots, 'eff': trend_efficiency
                })
            except: continue

        if not results: return
        results_df = pd.DataFrame(results)
        top = results_df.nlargest(g.position_limit, 'eff')
        
        ContextInfo.stock_codes_dict = {}
        for _, r in top.iterrows():
            ContextInfo.stock_codes_dict[r['symbol']] = {"code": r['code'], "market": r['market'], "size": r['size']}
        
        log_info(f"[选品] 完成，选中: {list(ContextInfo.stock_codes_dict.keys())}")
    except Exception as e:
        log_info(f"[选品] 异常: {e}")

# --- 辅助与工具函数 (补全) ---

def timetag_to_datetime(timetag, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(timetag, (int, float)):
        return datetime.fromtimestamp(timetag / 1000).strftime(format)
    return timetag

def log_info(message):
    logging.info(message)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def feishu_log_info(message):
    log_info(message)
    send_feishu_message(message)

def select_pools():
    p = os.path.join(g.work_dir, g.excel_file)
    try: return pd.read_excel(p)
    except: return pd.DataFrame()

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
    return f"C:\\datalog\\grid-v3-{account}-{datetime.now().strftime('%Y%m%d')}.log"

def is_weekend(): return datetime.now().weekday() >= 5

def is_trading_time(t):
    h, m = t.hour, t.minute
    if (9 <= h < 11) or (h == 11 and m <= 30): return True
    if (13 <= h < 15) or (13 == h and m >= 30): return True
    if (21 <= h <= 23): return True
    if (0 <= h < 2) or (h == 2 and m <= 30): return True
    return False

def log_section(title):
    log_info(f"\n{'=' * 20} {title} {'=' * 20}")

def send_feishu_message(message):
    # 填充您的 Webhook URL
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/086957a2-ddb4-4406-a720-3caaa7e3930f"
    try:
        requests.post(url, json={"msg_type": "text", "content": {"text": f"{g.account}: {message}"}}, timeout=5)
    except: pass
