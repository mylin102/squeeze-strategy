#!/usr/bin/env python3
"""
Sector Rotation Strategy - 分群選股策略

1. 按產業分類股票
2. 計算各產業相對強度
3. 挑選強勢產業
4. 從強勢產業中挑選強勢股

Usage:
    python3 scripts/sector_rotation.py --market tw --top-sectors 5 --top-stocks 10
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# 台灣主要產業分類 (精簡實用版 - 使用 TWSE 正式分類)
TW_SECTORS = {
    # 傳統產業
    '水泥': ['1101.TW', '1102.TW', '1103.TW', '1104.TW'],
    '食品': ['1216.TW', '1231.TW', '1217.TW', '1218.TW', '1227.TW', '1229.TW'],
    '塑膠': ['1301.TW', '1303.TW', '1304.TW', '1326.TW'],
    '紡織': ['1402.TW', '1404.TW', '1409.TW', '1414.TW'],
    '電機': ['1503.TW', '1504.TW', '1506.TW', '1507.TW'],
    '化學': ['1701.TW', '1702.TW', '1712.TW', '1717.TW'],
    '鋼鐵': ['2002.TW', '2006.TW', '2007.TW', '2008.TW'],
    '航運': ['2603.TW', '2606.TW', '2609.TW', '2610.TW'],
    '汽車': ['2201.TW', '2204.TW', '2207.TW', '2211.TW'],
    
    # 電子科技產業 (按 TWSE 正式分類)
    '半導體': ['2330.TW', '2303.TW', '2454.TW', '2327.TW', '2377.TW', '2341.TW', '2342.TW', '2408.TW', '2431.TW', '2432.TW'],
    '電腦及週邊': ['2357.TW', '2353.TW', '2382.TW', '2324.TW', '2354.TW', '2360.TW'],
    '光電': ['2409.TW', '2389.TW', '2355.TW', '2393.TW', '2348.TW', '2301.TW', '2461.TW', '2471.TW'],
    '通信網路': ['2345.TW', '2379.TW', '2385.TW', '2392.TW', '2466.TW', '2498.TW', '3045.TW'],
    '電子零組件': ['2374.TW', '2383.TW', '2478.TW', '2492.TW', '2497.TW', '2368.TW'],
    'IC 設計': ['2454.TW', '2379.TW', '2369.TW', '2451.TW', '2458.TW', '2494.TW', '3034.TW', '3035.TW'],
    'PCB': ['2313.TW', '2323.TW', '2383.TW', '2368.TW', '2393.TW'],
    '被動元件': ['2478.TW', '2492.TW', '2497.TW'],
    '散熱': ['2471.TW', '2474.TW', '2475.TW'],
    '連接器': ['2351.TW', '2352.TW', '2426.TW'],
    
    # 金融業
    '金控': ['2881.TW', '2882.TW', '2883.TW', '2884.TW', '2885.TW', '2886.TW', '2891.TW', '2892.TW'],
    '銀行': ['2800.TW', '2801.TW', '2802.TW', '2803.TW', '2804.TW', '2805.TW', '2806.TW', '2807.TW', '2808.TW', '2809.TW', '2810.TW', '2811.TW', '2812.TW', '2820.TW', '2821.TW', '2822.TW', '2823.TW'],
    '證券': ['2820.TW', '2821.TW', '2822.TW', '2823.TW', '2832.TW', '2834.TW', '2840.TW', '2841.TW', '2845.TW', '2849.TW', '2850.TW', '2851.TW', '2852.TW', '2853.TW', '2855.TW', '2880.TW'],
    '保險': ['2823.TW', '2824.TW', '2825.TW', '2826.TW', '2827.TW', '2828.TW', '2829.TW', '2830.TW', '2831.TW', '2833.TW'],
    
    # 服務業
    '貿易百貨': ['2901.TW', '2903.TW', '2904.TW', '2905.TW', '2911.TW', '2912.TW'],
    '觀光': ['2701.TW', '2704.TW', '2705.TW', '2707.TW', '2718.TW', '2723.TW'],
    '油電': ['1314.TW', '1315.TW', '1316.TW'],
}


def calculate_sector_strength(data_dir: Path, period: int = 20) -> Dict[str, Dict]:
    """計算各產業相對強度"""
    print(f"\n[1/3] 計算產業相對強度 (期間：{period}天)...")
    
    sector_data = {}
    
    for sector_name, tickers in TW_SECTORS.items():
        returns = []
        
        for ticker in tickers:
            csv_file = data_dir / f"{ticker.replace('.', '_')}.csv"
            if csv_file.exists():
                try:
                    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                    if len(df) > period:
                        close_now = df['Close'].iloc[-1]
                        close_ago = df['Close'].iloc[-period]
                        ret = (close_now / close_ago - 1) * 100
                        returns.append(ret)
                except Exception:
                    pass
        
        if returns:
            sector_data[sector_name] = {
                'avg_return': np.mean(returns),
                'median_return': np.median(returns),
                'stocks_count': len(returns),
                'top_return': np.max(returns),
            }
    
    # Sort by average return
    sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1]['avg_return'], reverse=True)
    
    print(f"\n  產業強度排名:")
    for i, (sector, data) in enumerate(sorted_sectors, 1):
        print(f"  {i}. {sector:<12} 平均：{data['avg_return']:>+7.2f}% 中位：{data['median_return']:>+7.2f}% ({data['stocks_count']}檔)")
    
    return sector_data


def select_top_stocks(data_dir: Path, top_sectors: List[str], top_n: int = 10, period: int = 20) -> pd.DataFrame:
    """從強勢產業中挑選強勢股"""
    print(f"\n[2/3] 從強勢產業中挑選強勢股...")
    
    all_stocks = []
    
    for sector in top_sectors:
        tickers = TW_SECTORS.get(sector, [])
        
        for ticker in tickers:
            csv_file = data_dir / f"{ticker.replace('.', '_')}.csv"
            if not csv_file.exists():
                continue
            
            try:
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                if len(df) <= period:
                    continue
                
                close_now = df['Close'].iloc[-1]
                close_ago = df['Close'].iloc[-period]
                ret = (close_now / close_ago - 1) * 100
                
                # Momentum (12 日)
                mom = (close_now / df['Close'].iloc[-12] - 1) * 100 if len(df) > 12 else 0
                
                all_stocks.append({
                    'ticker': ticker,
                    'sector': sector,
                    f'return_{period}d': ret,
                    'momentum': mom,
                    'price': close_now,
                })
            except Exception:
                pass
    
    df_stocks = pd.DataFrame(all_stocks)
    
    # Sort by return within each sector
    if len(df_stocks) > 0:
        df_stocks = df_stocks.sort_values(by=['sector', f'return_{period}d'], ascending=[True, False])
        df_stocks = df_stocks.groupby('sector').head(top_n)
    
    return df_stocks


def main():
    parser = argparse.ArgumentParser(description='Sector Rotation Strategy')
    parser.add_argument('--market', default='tw', choices=['tw', 'us', 'cn'])
    parser.add_argument('--top-sectors', type=int, default=5, help='Number of top sectors')
    parser.add_argument('--top-stocks', type=int, default=10, help='Top stocks per sector')
    parser.add_argument('--period', type=int, default=20, help='Lookback period')
    parser.add_argument('--data-dir', default='backtests/tw_data', help='Data directory')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    
    if not data_dir.exists():
        print(f"錯誤：數據目錄不存在：{data_dir}")
        return 1
    
    print("="*70)
    print("  分群選股策略 - 先挑強勢族群再挑強勢股")
    print("="*70)
    
    # Calculate sector strength
    sector_data = calculate_sector_strength(data_dir, args.period)
    
    if not sector_data:
        print("錯誤：無法計算產業強度")
        return 1
    
    # Select top sectors
    top_sectors = list(sector_data.keys())[:args.top_sectors]
    print(f"\n  選取前 {args.top_sectors} 個強勢產業:")
    for i, sector in enumerate(top_sectors, 1):
        data = sector_data[sector]
        print(f"  {i}. {sector:<12} 平均報酬：{data['avg_return']:>+7.2f}%")
    
    # Select top stocks
    df_stocks = select_top_stocks(data_dir, top_sectors, args.top_stocks, args.period)
    
    if len(df_stocks) == 0:
        print("錯誤：找不到股票數據")
        return 1
    
    # Display results
    print(f"\n[3/3] 強勢股清單:")
    print("="*70)
    
    for sector in top_sectors:
        sector_stocks = df_stocks[df_stocks['sector'] == sector]
        print(f"\n{sector}:")
        print(f"  {'代碼':<12} {'報酬率':>10} {'動能':>10} {'股價':>10}")
        print(f"  {'-'*46}")
        
        for _, row in sector_stocks.iterrows():
            print(f"  {row['ticker']:<12} {row[f'return_{args.period}d']:>+9.2f}% {row['momentum']:>+9.2f}% {row['price']:>10.2f}")
    
    # Save to CSV
    output_file = data_dir.parent / f"sector_rotation_{datetime.now().strftime('%Y%m%d')}.csv"
    df_stocks.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n  已儲存至：{output_file}")
    
    print("\n" + "="*70)
    print(f"  總計：{len(df_stocks)} 檔強勢股")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
