#!/usr/bin/env python3
"""
市場時段檢查工具

檢查當前時間是否在交易時段內
- 台股：週一至五 09:00-13:30 TW
- 美股：週一至五 09:30-16:00 ET
- 中國 A 股：週一至五 09:30-15:00 CN

Usage:
    python3 scripts/check_market_hours.py --market us
    python3 scripts/check_market_hours.py --market tw
    python3 scripts/check_market_hours.py --market cn
"""

import sys
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_market_hours(market: str) -> dict:
    """
    獲取各市場交易時間
    
    Returns:
        dict: {
            'open': (hour, minute),
            'close': (hour, minute),
            'timezone': str
        }
    """
    markets = {
        'tw': {
            'open': (9, 0),
            'close': (13, 30),
            'timezone': 'Asia/Taipei',
            'name': '台灣股市'
        },
        'us': {
            'open': (9, 30),
            'close': (16, 0),
            'timezone': 'America/New_York',
            'name': '美股'
        },
        'cn': {
            'open': (9, 30),
            'close': (15, 0),
            'timezone': 'Asia/Shanghai',
            'name': '中國 A 股'
        }
    }
    
    return markets.get(market.lower())


def check_market_hours(market: str, verbose: bool = False) -> bool:
    """
    檢查當前時間是否在交易時段內
    
    Parameters:
    -----------
    market : str
        市場代碼：tw, us, cn
    verbose : bool
        是否顯示詳細資訊
    
    Returns:
    --------
    bool : True (在交易時段內) / False (不在交易時段內)
    """
    market_info = get_market_hours(market)
    
    if not market_info:
        print(f"❌ 未知的市場：{market}")
        return False
    
    # 獲取當地時間
    tz = ZoneInfo(market_info['timezone'])
    local_now = datetime.now(tz)
    
    # 檢查是否為週末
    weekday = local_now.weekday()  # 0=Monday, 4=Friday
    is_weekend = weekday >= 5
    
    # 獲取當前時間
    current_time = local_now.time()
    open_time = local_now.replace(
        hour=market_info['open'][0], 
        minute=market_info['open'][1], 
        second=0, 
        microsecond=0
    ).time()
    close_time = local_now.replace(
        hour=market_info['close'][0], 
        minute=market_info['close'][1], 
        second=0, 
        microsecond=0
    ).time()
    
    # 檢查是否在交易時段內
    is_trading_time = open_time <= current_time <= close_time
    is_trading_day = not is_weekend
    
    if verbose:
        print("="*60)
        print(f"  {market_info['name']} 交易時段檢查")
        print("="*60)
        print()
        print(f"📍 時區：{market_info['timezone']}")
        print(f"🕐 當地時間：{local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 星期：{local_now.strftime('%A')}")
        print()
        print(f"交易時間：{market_info['open'][0]:02d}:{market_info['open'][1]:02d} - "
              f"{market_info['close'][0]:02d}:{market_info['close'][1]:02d}")
        print(f"當前時間：{current_time.strftime('%H:%M:%S')}")
        print()
        
        if is_weekend:
            print("❌ 狀況：週末 (非交易日)")
        elif not is_trading_time:
            if current_time < open_time:
                until_open = (open_time - current_time).total_seconds() / 60
                print(f"❌ 狀況：尚未開盤 (距離開盤還有 {until_open:.0f} 分鐘)")
            else:
                after_close = (current_time - close_time).total_seconds() / 60
                print(f"❌ 狀況：已收盤 (收盤已 {after_close:.0f} 分鐘)")
        else:
            print("✅ 狀況：交易時間中")
        
        print()
        print("="*60)
    
    # 返回結果
    return is_trading_day and is_trading_time


def main():
    parser = argparse.ArgumentParser(description='檢查市場交易時段')
    parser.add_argument('--market', required=True, choices=['tw', 'us', 'cn'],
                       help='市場代碼')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細資訊')
    parser.add_argument('--exit-code', action='store_true',
                       help='使用退出碼 (0=在交易時段，1=不在)')
    
    args = parser.parse_args()
    
    is_trading = check_market_hours(args.market, verbose=args.verbose)
    
    if args.exit_code:
        sys.exit(0 if is_trading else 1)
    else:
        if is_trading:
            print(f"✅ {args.market.upper()} 目前在交易時段內")
            return 0
        else:
            print(f"❌ {args.market.upper()} 目前不在交易時段內")
            return 1


if __name__ == "__main__":
    sys.exit(main())
