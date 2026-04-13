# -*- coding: utf-8 -*-
"""
QMT连接测试脚本
测试MiniQMT行情和交易连接
"""

import random
import time

# ================== 配置区域 ==================
# MiniQMT路径
MINI_QMT_PATH = r'C:\QMT001\userdata_mini'

# 资金账号（需要替换为实际的账号）
# 请从QMT客户端中查看你的资金账号
ACCOUNT_ID = '8886090521'  # 资金账号

# 账号类型: 'STOCK' 股票账号, 'FUTURE' 期货账号
ACCOUNT_TYPE = 'STOCK'

# 测试股票代码
TEST_CODE = '000001.SZ'
# =============================================


def test_xtdata_connection():
    """测试行情数据连接 (xtdata)"""
    print("=" * 50)
    print("[测试1] 行情数据连接 (xtdata)")
    print("=" * 50)
    
    try:
        from xtquant import xtdata
        print("[OK] xtdata 模块导入成功")
        
        # 获取本地数据路径
        print("  数据路径: %s" % MINI_QMT_PATH)
        
        # 尝试获取单只股票的历史数据
        print("\n  尝试获取 %s 的历史数据..." % TEST_CODE)
        
        # 先下载数据
        xtdata.download_history_data(TEST_CODE, period='1d', start_time='20240101', end_time='20241231')
        time.sleep(1)
        
        # 获取数据
        data = xtdata.get_market_data_ex(
            field_list=['open', 'high', 'low', 'close', 'volume'],
            stock_list=[TEST_CODE],
            period='1d',
            count=10
        )
        
        if data and TEST_CODE in data:
            print("[OK] 成功获取数据!")
            print("  数据条数: %d" % len(data[TEST_CODE]))
            print("  最新数据: %s" % (data[TEST_CODE][-1] if data[TEST_CODE] else '无数据'))
            return True
        else:
            print("[FAIL] 获取数据为空")
            return False
            
    except Exception as e:
        print("[FAIL] 行情连接失败: %s" % e)
        return False


def test_xttrader_connection():
    """测试交易连接 (xttrader)"""
    print("\n" + "=" * 50)
    print("[测试2] 交易接口连接 (xttrader)")
    print("=" * 50)
    
    if not ACCOUNT_ID:
        print("[!] 未设置资金账号，跳过交易连接测试")
        print("  请在脚本中设置 ACCOUNT_ID = '你的资金账号'")
        return None
    
    try:
        from xtquant.xttrader import XtQuantTrader
        from xtquant.xttype import StockAccount
        
        print("[OK] xttrader 模块导入成功")
        
        # 创建session_id
        session_id = int(random.randint(100000, 999999))
        print("  Session ID: %d" % session_id)
        
        # 创建交易对象
        xt_trader = XtQuantTrader(MINI_QMT_PATH, session_id)
        print("  MiniQMT路径: %s" % MINI_QMT_PATH)
        
        # 启动交易对象
        xt_trader.start()
        print("  交易对象已启动")
        
        # 连接客户端
        connect_result = xt_trader.connect()
        
        if connect_result == 0:
            print("[OK] MiniQMT连接成功!")
            
            # 创建账号对象
            account = StockAccount(ACCOUNT_ID, ACCOUNT_TYPE)
            print("  账号: %s (%s)" % (ACCOUNT_ID, ACCOUNT_TYPE))
            
            # 订阅账号
            subscribe_result = xt_trader.subscribe(account)
            if subscribe_result == 0:
                print("[OK] 账号订阅成功!")
                
                # 查询资金
                try:
                    asset = xt_trader.query_stock_asset(account)
                    print("\n  资金信息:")
                    print("    总资产: %s" % asset.total_asset)
                    print("    可用资金: %s" % asset.cash)
                except Exception as e:
                    print("  查询资金信息失败: %s" % e)
                
                # 查询持仓
                try:
                    positions = xt_trader.query_stock_positions(account)
                    print("\n  持仓数量: %d" % len(positions))
                    if positions:
                        print("    第一只持仓: %s" % positions[0].stock_code)
                except Exception as e:
                    print("  查询持仓失败: %s" % e)
                
                return True
            else:
                print("[FAIL] 账号订阅失败: %d" % subscribe_result)
                return False
        else:
            print("[FAIL] MiniQMT连接失败，错误码: %d" % connect_result)
            print("  请检查:")
            print("    1. MiniQMT是否已启动并登录")
            print("    2. 路径是否正确")
            print("    3. 账号权限是否开通")
            return False
            
    except Exception as e:
        print("[FAIL] 交易连接失败: %s" % e)
        import traceback
        traceback.print_exc()
        return False


def test_get_account_list():
    """尝试从配置中获取账号列表"""
    print("\n" + "=" * 50)
    print("[测试3] 查看可用账号")
    print("=" * 50)
    
    # 尝试读取QMT配置文件
    try:
        import json
        import os
        config_path = r'C:\QMT001\config\accounts.json'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print("  找到配置: %s" % config)
        else:
            print("  配置文件不存在: %s" % config_path)
            print("  请手动在QMT客户端查看资金账号")
    except Exception as e:
        print("  读取配置失败: %s" % e)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("        QMT (MiniQMT) 连接测试")
    print("=" * 60)
    print("测试时间: %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
    print("MiniQMT路径: %s" % MINI_QMT_PATH)
    print("=" * 60)
    
    # 测试1: 行情数据
    data_ok = test_xtdata_connection()
    
    # 测试2: 交易接口
    trade_ok = test_xttrader_connection()
    
    # 测试3: 查看账号
    test_get_account_list()
    
    # 总结
    print("\n" + "=" * 60)
    print("                    测试总结")
    print("=" * 60)
    print("行情数据连接: %s" % ('[OK] 成功' if data_ok else '[FAIL] 失败'))
    if trade_ok is None:
        print("交易接口连接: [!] 跳过 (未设置账号)")
    else:
        print("交易接口连接: %s" % ('[OK] 成功' if trade_ok else '[FAIL] 失败'))
    print("=" * 60)


if __name__ == '__main__':
    main()
