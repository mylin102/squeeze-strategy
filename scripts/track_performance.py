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
    df['current_price'] = df['進場價'] * (1 + df['price_change_pct'])
    
    return df


def calculate_performance(df: pd.DataFrame) -> pd.DataFrame:
    """計算績效"""
    # 每股損益
    df['每股損益'] = df['current_price'] - df['進場價']
    
    # 總損益
    df['總損益'] = df['每股損益'] * df['股數']
    
    # 報酬率
    df['報酬率'] = df['每股損益'] / df['進場價'] * 100
    
    # 是否觸及停損
    df['已停損'] = df['current_price'] <= df['停損價']
    df['狀態'] = df['已停損'].apply(lambda x: '🛑 已停損' if x else '📈 持有中')
    
    # 實際虧損 (如果停損)
    df['實際虧損'] = df.apply(
        lambda row: row['最大虧損'] if row['已停損'] else -row['總損益'],
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
        print(f"{row['代號']:<12} {row['名稱']:<15} {row['進場價']:>10.2f} "
              f"{row['current_price']:>10.2f} {row['報酬率']:>+10.2f}% "
              f"{row['每股損益']:>+10.2f} {row['總損益']:>+12.2f} {row['最大虧損']:>10.2f} "
              f"{row['狀態']:<12} {row['備註']:<25}")
    
    print("-"*130)
    
    # 統計
    total_pnl = df['總損益'].sum()
    total_max_loss = df['最大虧損'].sum()
    winning = len(df[df['總損益'] > 0])
    losing = len(df[df['總損益'] < 0])
    stopped = len(df[df['已停損']])
    avg_return = df['報酬率'].mean()
    best_trade = df.loc[df['總損益'].idxmax()]
    worst_trade = df.loc[df['總損益'].idxmin()]
    
    print()
    print(f"總損益：{total_pnl:+,.2f} 元")
    print(f"總風險暴露：{total_max_loss:,.2f} 元")
    print(f"風險調整後報酬：{total_pnl/total_max_loss*100:+.2f}%")
    print()
    print(f"獲利：{winning} 檔 | 虧損：{losing} 檔 | 停損：{stopped} 檔")
    print(f"勝率：{winning/len(df)*100:.1f}%")
    print(f"平均報酬率：{avg_return:+.2f}%")
    print()
    print(f"最佳交易：{best_trade['代號']} ({best_trade['總損益']:+,.2f}元)")
    print(f"最差交易：{worst_trade['代號']} ({worst_trade['總損益']:+,.2f}元)")
    print("="*130)


def save_performance_report(df: pd.DataFrame, output_dir: str = "exports"):
    """儲存績效報告"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    
    # CSV
    csv_path = output_path / f"performance_tracking_{today}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 績效報告已儲存至：{csv_path}")
    
    # Summary JSON
    summary = {
        'date': today,
        'total_positions': len(df),
        'total_pnl': float(df['總損益'].sum()),
        'total_max_loss': float(df['最大虧損'].sum()),
        'risk_adjusted_return': float(df['總損益'].sum() / df['最大虧損'].sum() * 100),
        'winning_count': int(len(df[df['總損益'] > 0])),
        'losing_count': int(len(df[df['總損益'] < 0])),
        'stopped_count': int(len(df[df['已停損']])),
        'win_rate': float(len(df[df['總損益'] > 0]) / len(df) * 100),
        'avg_return': float(df['報酬率'].mean()),
    }
    
    import json
    json_path = output_path / f"performance_summary_{today}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"✅ 績效摘要已儲存至：{json_path}")


def main():
    print()
    print("載入每日建議操作名單...")
    
    # 載入建議清單
    recommendations_file = 'exports/daily_recommendations_2026-03-28.csv'
    df = load_recommendations(recommendations_file)
    print(f"✅ 載入 {len(df)} 檔股票")
    print()
    
    # 模擬當前價格
    print("模擬當前價格 (持有 5 天)...")
    df = simulate_current_prices(df, days_held=5)
    
    # 計算績效
    df = calculate_performance(df)
    
    # 列印報告
    print_performance_report(df)
    
    # 儲存
    save_performance_report(df)
    
    print()


if __name__ == "__main__":
    main()
