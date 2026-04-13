# -*- coding: utf-8 -*-
"""
QMT API Function Test Script
Test all functions extracted from customer service examples
"""

import sys
import time
import random

# Test results record
test_results = {
    "xtdata": {},
    "xttrader": {},
    "xttype": {},
    "xtconstant": {},
    "qmttools": {}
}

def test_xtdata():
    """Test xtdata market data interface"""
    print("\n" + "="*60)
    print("Testing xtdata module (Market Data)")
    print("="*60)
    
    try:
        from xtquant import xtdata
        print("[OK] xtdata module imported")
        test_results["xtdata"]["import"] = "OK Available"
    except Exception as e:
        print(f"[FAIL] xtdata import failed: {e}")
        test_results["xtdata"]["import"] = f"FAIL: {e}"
        return
    
    # Test getting stock list
    try:
        stocks = xtdata.get_stock_list_in_sector('沪深A股')
        print(f"[OK] get_stock_list_in_sector() - Got {len(stocks)} stocks")
        test_results["xtdata"]["get_stock_list_in_sector"] = f"OK ({len(stocks)} stocks)"
    except Exception as e:
        print(f"[FAIL] get_stock_list_in_sector() - {e}")
        test_results["xtdata"]["get_stock_list_in_sector"] = f"FAIL: {e}"
    
    # Test downloading history data
    try:
        result = xtdata.download_history_data('000001.SZ', '1d', '20240101', '20241231')
        print(f"[OK] download_history_data() - Result: {result}")
        test_results["xtdata"]["download_history_data"] = "OK"
    except Exception as e:
        print(f"[FAIL] download_history_data() - {e}")
        test_results["xtdata"]["download_history_data"] = f"FAIL: {e}"
    
    # Test getting market data
    try:
        data = xtdata.get_market_data_ex(
            field_list=['open', 'high', 'low', 'close', 'volume'],
            stock_list=['000001.SZ'],
            period='1d',
            count=10
        )
        if '000001.SZ' in data:
            print(f"[OK] get_market_data_ex() - Got {len(data['000001.SZ'])} rows")
            test_results["xtdata"]["get_market_data_ex"] = f"OK ({len(data['000001.SZ'])} rows)"
        else:
            print(f"[WARN] get_market_data_ex() - No data content")
            test_results["xtdata"]["get_market_data_ex"] = "WARN Empty"
    except Exception as e:
        print(f"[FAIL] get_market_data_ex() - {e}")
        test_results["xtdata"]["get_market_data_ex"] = f"FAIL: {e}"
    
    # Test subscribing quotes
    try:
        seq = xtdata.subscribe_quote('000001.SZ', period='1d', count=-1)
        print(f"[OK] subscribe_quote() - Seq: {seq}")
        test_results["xtdata"]["subscribe_quote"] = f"OK (seq:{seq})"
    except Exception as e:
        print(f"[FAIL] subscribe_quote() - {e}")
        test_results["xtdata"]["subscribe_quote"] = f"FAIL: {e}"
    
    # Test getting local data
    try:
        local_data = xtdata.get_local_data(['000001.SZ'], period='1d', count=5)
        print(f"[OK] get_local_data() - Available")
        test_results["xtdata"]["get_local_data"] = "OK"
    except Exception as e:
        print(f"[WARN] get_local_data() - {e}")
        test_results["xtdata"]["get_local_data"] = f"WARN: {e}"


def test_xtconstant():
    """Test xtconstant constants"""
    print("\n" + "="*60)
    print("Testing xtconstant module (Trading Constants)")
    print("="*60)
    
    try:
        from xtquant import xtconstant
        print("[OK] xtconstant imported")
        test_results["xtconstant"]["import"] = "OK"
    except Exception as e:
        print(f"[FAIL] xtconstant import failed: {e}")
        test_results["xtconstant"]["import"] = f"FAIL: {e}"
        return
    
    # Test stock constants
    constants_to_test = [
        ("STOCK_BUY", "Stock Buy"),
        ("STOCK_SELL", "Stock Sell"),
        ("LATEST_PRICE", "Latest Price"),
        ("FIX_PRICE", "Fix Price"),
        ("FUTURE_OPEN_LONG", "Future Open Long"),
        ("FUTURE_OPEN_SHORT", "Future Open Short"),
        ("FUTURE_CLOSE_LONG_TODAY_FIRST", "Future Close Long Today"),
        ("FUTURE_CLOSE_SHORT_TODAY_FIRST", "Future Close Short Today"),
        ("FUTURE_CLOSE_LONG_HISTORY_FIRST", "Future Close Long History"),
        ("FUTURE_CLOSE_SHORT_HISTORY_FIRST", "Future Close Short History"),
    ]
    
    for const_name, desc in constants_to_test:
        try:
            value = getattr(xtconstant, const_name)
            print(f"[OK] {const_name} = {value} ({desc})")
            test_results["xtconstant"][const_name] = f"OK ({value})"
        except Exception as e:
            print(f"[WARN] {const_name} - Not available")
            test_results["xtconstant"][const_name] = "WARN Not found"


def test_xttype():
    """Test xttype type definitions"""
    print("\n" + "="*60)
    print("Testing xttype module (Account Types)")
    print("="*60)
    
    try:
        from xtquant.xttype import StockAccount
        print("[OK] StockAccount imported")
        test_results["xttype"]["StockAccount"] = "OK"
        
        # Try creating account object
        try:
            acc = StockAccount('8886090521', 'STOCK')
            print(f"[OK] StockAccount() - Account: {acc.account_id}, Type: {acc.account_type}")
            test_results["xttype"]["StockAccount_init"] = "OK"
        except Exception as e:
            print(f"[WARN] StockAccount() - {e}")
            test_results["xttype"]["StockAccount_init"] = f"WARN: {e}"
            
    except Exception as e:
        print(f"[FAIL] StockAccount import failed: {e}")
        test_results["xttype"]["StockAccount"] = f"FAIL: {e}"
    
    try:
        from xtquant.xttrader import XtQuantTraderCallback
        print("[OK] XtQuantTraderCallback imported")
        test_results["xttype"]["XtQuantTraderCallback"] = "OK"
    except Exception as e:
        print(f"[WARN] XtQuantTraderCallback - {e}")
        test_results["xttype"]["XtQuantTraderCallback"] = f"WARN: {e}"


def test_xttrader():
    """Test xttrader trading interface"""
    print("\n" + "="*60)
    print("Testing xttrader module (Trading Interface)")
    print("="*60)
    
    try:
        from xtquant.xttrader import XtQuantTrader
        print("[OK] XtQuantTrader imported")
        test_results["xttrader"]["import"] = "OK"
    except Exception as e:
        print(f"[FAIL] XtQuantTrader import failed: {e}")
        test_results["xttrader"]["import"] = f"FAIL: {e}"
        return
    
    # Create trader object
    MINI_QMT_PATH = r'C:\QMT001\userdata_mini'
    session_id = random.randint(100000, 999999)
    
    try:
        xt_trader = XtQuantTrader(MINI_QMT_PATH, session_id)
        print(f"[OK] XtQuantTrader() created (session: {session_id})")
        test_results["xttrader"]["XtQuantTrader_init"] = "OK"
    except Exception as e:
        print(f"[FAIL] XtQuantTrader() - {e}")
        test_results["xttrader"]["XtQuantTrader_init"] = f"FAIL: {e}"
        return
    
    # Test method existence
    methods = [
        "start", "connect", "subscribe", "order_stock", "order_stock_async",
        "query_stock_positions", "query_position_statistics", "query_stock_trades",
        "query_stock_orders", "query_stock_asset", "cancel_order_stock", "register_callback"
    ]
    
    for method in methods:
        if hasattr(xt_trader, method):
            print(f"[OK] xt_trader.{method}() - Exists")
            test_results["xttrader"][method] = "OK"
        else:
            print(f"[WARN] xt_trader.{method}() - Not found")
            test_results["xttrader"][method] = "WARN Not found"
    
    # Test connection
    print("\n[INFO] Testing MiniQMT connection...")
    try:
        xt_trader.start()
        result = xt_trader.connect()
        if result == 0:
            print("[OK] MiniQMT connected")
            test_results["xttrader"]["connect_test"] = "OK Connected"
            
            # Test account subscription
            from xtquant.xttype import StockAccount
            account = StockAccount('8886090521', 'STOCK')
            sub_result = xt_trader.subscribe(account)
            if sub_result == 0:
                print("[OK] Account subscribed")
                test_results["xttrader"]["subscribe_test"] = "OK Subscribed"
                
                # Test query asset
                try:
                    asset = xt_trader.query_stock_asset(account)
                    print(f"[OK] query_stock_asset() - Total: {asset.total_asset}, Cash: {asset.cash}")
                    test_results["xttrader"]["query_stock_asset"] = f"OK (Asset:{asset.total_asset})"
                except Exception as e:
                    print(f"[WARN] query_stock_asset() - {e}")
                    test_results["xttrader"]["query_stock_asset"] = f"WARN: {e}"
                
                # Test query positions
                try:
                    positions = xt_trader.query_stock_positions(account)
                    print(f"[OK] query_stock_positions() - Positions: {len(positions)}")
                    test_results["xttrader"]["query_stock_positions"] = f"OK ({len(positions)} positions)"
                except Exception as e:
                    print(f"[WARN] query_stock_positions() - {e}")
                    test_results["xttrader"]["query_stock_positions"] = f"WARN: {e}"
                    
            else:
                print(f"[WARN] Account subscribe failed: {sub_result}")
                test_results["xttrader"]["subscribe_test"] = f"WARN: {sub_result}"
        else:
            print(f"[WARN] MiniQMT connect failed (code: {result}) - Please ensure MiniQMT is running")
            test_results["xttrader"]["connect_test"] = f"WARN: {result}"
    except Exception as e:
        print(f"[WARN] Connection test failed: {e}")
        test_results["xttrader"]["connect_test"] = f"WARN: {e}"


def test_qmttools():
    """Test qmttools functions"""
    print("\n" + "="*60)
    print("Testing qmttools module (Big QMT Tools)")
    print("="*60)
    
    try:
        from xtquant.qmttools.functions import passorder, get_trade_detail_data
        print("[OK] passorder imported")
        print("[OK] get_trade_detail_data imported")
        test_results["qmttools"]["passorder"] = "OK"
        test_results["qmttools"]["get_trade_detail_data"] = "OK"
    except Exception as e:
        print(f"[WARN] qmttools import - {e}")
        test_results["qmttools"]["import"] = f"WARN: {e}"


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for module, results in test_results.items():
        if results:
            print(f"\n[{module}]")
            for func, result in results.items():
                total_tests += 1
                if result.startswith("OK"):
                    passed_tests += 1
                print(f"  {func}: {result}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    # Save results to file
    with open('api_test_results.txt', 'w', encoding='utf-8') as f:
        f.write("QMT API Function Test Results\n")
        f.write("="*60 + "\n\n")
        for module, results in test_results.items():
            if results:
                f.write(f"[{module}]\n")
                for func, result in results.items():
                    f.write(f"  {func}: {result}\n")
                f.write("\n")
        f.write(f"\nTotal: {passed_tests}/{total_tests} tests passed\n")
    
    print("\nResults saved to api_test_results.txt")
    return test_results


if __name__ == '__main__':
    print("="*60)
    print("QMT API Function Availability Test")
    print("="*60)
    print("\nThis script tests all functions extracted from customer examples")
    print("Please ensure MiniQMT is running for complete results\n")
    
    # Run all tests
    test_xtdata()
    test_xtconstant()
    test_xttype()
    test_xttrader()
    test_qmttools()
    
    # Print summary
    final_results = print_summary()
