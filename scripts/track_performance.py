#!/usr/bin/env python3
"""
績效追蹤腳本

追蹤每日建議操作名單的績效表現

Usage:
    python3 scripts/track_performance.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

# 設定顯示選項
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)


def load_recommendations(file_path: str) -> pd.DataFrame:
    """載入建議清單"""
    return pd.read_csv(file_path)


def simulate_current_prices(df: pd.DataFrame, days_held: int = 5) -> pd.DataFrame:
    """
    模擬當前價格
    
    Parameters:
    -----------
    df : pd.DataFrame
        建議清單
    days_held : int
        持有天數
    """
    np.random.seed(42)
    
    # 模擬價格變化 (-10% 到 +20%)
    df = df.copy()
    df['price_change_pct'] = np.random.uniform(-0.10, 0.20, len(df))
    df['current_price'] = df['entry_price'] * (1 + df['price_change_pct'])
    
    return df


def calculate_performance(df: pd.DataFrame) -> pd.DataFrame:
    """計算績效"""
    # 每股損益
    df['pnl_per_share'] = df['current_price'] - df['entry_price']
    
    # 總損益
    df['total_pnl'] = df['pnl_per_share'] * df['shares']
    
    # 報酬率
    df['return_pct'] = df['pnl_per_share'] / df['entry_price'] * 100
    
    # 是否觸及停損
    df['stopped_out'] = df['current_price'] <= df['stop_loss_price']
    df['status'] = df['stopped_out'].apply(lambda x: '🛑 已停損' if x else '📈 持有中')
    
    # 實際虧損 (如果停損)
    df['actual_loss'] = df.apply(
        lambda row: row['max_loss'] if row['stopped_out'] else -row['total_pnl'],
        axis=1
    )
    
    return df


def print_performance_report(df: pd.DataFrame):
    """列印績效報告"""
    print("="*130)
    print("  每日建議操作名單 - 績效追蹤報告")
    print("="*130)
    print()
    print(f"{'代號':<12} {'名稱':<15} {'進場價':>10} {'現價':>10} {'報酬率':>10} "
          f"{'每股損益':>10} {'總損益':>12} {'最大虧損':>10} {'狀態':<12} {'備註':<25}")
    print("-"*130)

    for _, row in df.iterrows():
        status = '🛑 已停損' if row['stopped_out'] else '📈 持有中'
        print(f"{row['ticker']:<12} {row['name']:<15} {row['entry_price']:>10.2f} "
              f"{row['current_price']:>10.2f} {row['return_pct']:>+10.2f}% "
              f"{row['pnl_per_share']:>+10.2f} {row['total_pnl']:>+12.2f} {row['max_loss']:>10.2f} "
              f"{status:<12} {row.get('note', ''):<25}")

    print("-"*130)

    # 統計
    total_pnl = df['total_pnl'].sum()
    total_max_loss = df['max_loss'].sum()
    winning = len(df[df['total_pnl'] > 0])
    losing = len(df[df['total_pnl'] < 0])
    stopped = len(df[df['stopped_out']])
    avg_return = df['return_pct'].mean()
    best_trade = df.loc[df['total_pnl'].idxmax()]
    worst_trade = df.loc[df['total_pnl'].idxmin()]

    print()
    print(f"總損益：{total_pnl:+,.2f} 元")
    print(f"總風險暴露：{total_max_loss:,.2f} 元")
    print(f"風險調整後報酬：{total_pnl/total_max_loss*100:+.2f}%")
    print()
    print(f"獲利：{winning} 檔 | 虧損：{losing} 檔 | 停損：{stopped} 檔")
    print(f"勝率：{winning/len(df)*100:.1f}%")
    print(f"平均報酬率：{avg_return:+.2f}%")
    print()
    print(f"最佳交易：{best_trade['ticker']} ({best_trade['total_pnl']:+,.2f}元)")
    print(f"最差交易：{worst_trade['ticker']} ({worst_trade['total_pnl']:+,.2f}元)")
    print("="*130)


def save_performance_report(df: pd.DataFrame, market: str = "tw", output_dir: str = "exports"):
    """儲存績效報告"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

    # CSV - 加入市場代碼避免覆蓋
    csv_path = output_path / f"performance_tracking_{market}_{today}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 績效報告已儲存至：{csv_path}")

    # Summary JSON - 加入市場代碼
    summary = {
        'date': today,
        'market': market.upper(),
        'total_positions': len(df),
        'total_pnl': float(df['total_pnl'].sum()),
        'total_max_loss': float(df['max_loss'].sum()),
        'risk_adjusted_return': float(df['total_pnl'].sum() / df['max_loss'].sum() * 100),
        'winning_count': int(len(df[df['total_pnl'] > 0])),
        'losing_count': int(len(df[df['total_pnl'] < 0])),
        'stopped_count': int(len(df[df['stopped_out']])),
        'win_rate': float(len(df[df['total_pnl'] > 0]) / len(df) * 100),
        'avg_return': float(df['return_pct'].mean()),
    }

    import json
    json_path = output_path / f"performance_summary_{market}_{today}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"✅ 績效摘要已儲存至：{json_path}")


def main():
    parser = argparse.ArgumentParser(description='績效追蹤')
    parser.add_argument('--market', default='tw', choices=['tw', 'us', 'cn'],
                       help='市場代碼')
    parser.add_argument('--input', type=str, 
                       help='輸入檔案路徑 (預設使用最新檔案)')
    
    args = parser.parse_args()
    print()
    print("載入每日建議操作名單...")
    
    # 載入建議清單 - 支援市場區分
    if args.input:
        file_path = Path(args.input)
    else:
        # 找最新的檔案 (包含市場代碼)
        output_path = Path('exports')
        files = sorted(output_path.glob(f'daily_recommendations_{args.market}_*.csv'))
        if files:
            file_path = files[-1]
        else:
            print("❌ 找不到建議清單檔案")
            return 1
    
    df = load_recommendations(str(file_path))
    if df.empty:
        return 1
    
    print(f"✅ 載入 {len(df)} 檔股票 ({args.market.upper()})")
    print()
    
    # 模擬當前價格
    print("模擬當前價格 (持有 5 天)...")
    df = simulate_current_prices(df, days_held=5)
    
    # 計算績效
    df = calculate_performance(df)
    
    # 列印報告
    print_performance_report(df)
    
    # 儲存 - 加入市場代碼
    save_performance_report(df, market=args.market)
    
    print()
    
    return 0
