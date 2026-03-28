#!/usr/bin/env python3
"""
每日建議操作名單與績效追蹤

生成每日買入建議，包含停損價、股數、風險計算
並追蹤歷史建議的績效表現

Usage:
    python3 scripts/daily_recommendations.py --market tw --strategy baseline
    python3 scripts/daily_recommendations.py --track  # 追蹤既有部位績效
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
import json

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from squeeze_strategy.engine import SqueezeStrategy
from squeeze_strategy.strategies import get_strategy_by_name
from squeeze_strategy.models import Market
from squeeze_strategy.data.loader import TickerUniverse, MarketDataDownloader


def get_china_time() -> datetime:
    """Get current China/Taiwan time"""
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


def calculate_position_size(
    entry_price: float,
    stop_loss_pct: float = 10.0,
    max_loss_per_trade: float = 1000.0
) -> int:
    """
    計算建議股數
    
    Parameters:
    -----------
    entry_price : float
        進場價格
    stop_loss_pct : float
        停損百分比 (預設 10%)
    max_loss_per_trade : float
        單筆交易最大可承受虧損 (預設 1000 元)
    
    Returns:
    --------
    int : 建議股數 (1000 股為一張)
    """
    # 每股風險 = 進場價 * 停損%
    risk_per_share = entry_price * (stop_loss_pct / 100)
    
    # 建議股數 = 最大可承受虧損 / 每股風險
    shares = int(max_loss_per_trade / risk_per_share)
    
    # 無條件取整到百位
    shares = (shares // 100) * 100
    
    # 最少 100 股
    return max(100, shares)


def generate_daily_recommendations(
    market: str = "tw",
    strategy_name: str = "baseline",
    max_positions: int = 10,
    max_loss_per_trade: float = 1000.0,
    stop_loss_pct: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    生成每日建議操作名單
    
    Parameters:
    -----------
    market : str
        市場 (tw, us, cn)
    strategy_name : str
        策略名稱
    max_positions : int
        最大建議檔數
    max_loss_per_trade : float
        單筆最大虧損
    stop_loss_pct : float
        停損百分比
    
    Returns:
    --------
    List[Dict] : 建議操作清單
    """
    print(f"生成 {market.upper()} 市場每日建議操作名單...")
    print(f"策略：{strategy_name}")
    print(f"最大建議檔數：{max_positions}")
    print(f"單筆最大虧損：{max_loss_per_trade} 元")
    print(f"停損比例：{stop_loss_pct}%")
    print()
    
    # 載入策略
    strategy = SqueezeStrategy(get_strategy_by_name(strategy_name, Market(market)))
    
    # 載入股票清單
    universe = TickerUniverse(market)
    tickers = universe.get_tickers()  # 使用完整清單
    ticker_names = universe.get_names()
    
    # 下載數據
    print(f"下載 {len(tickers)} 檔股票數據...")
    downloader = MarketDataDownloader(market)
    
    stock_data = {}
    for ticker in tickers:
        try:
            df = downloader.download_single(ticker, period="3mo")
            if len(df) > 30:
                stock_data[ticker] = df
        except Exception:
            pass
    
    print(f"成功下載 {len(stock_data)} 檔")
    print()
    
    # 掃描信號
    print("掃描買入信號...")
    signals = strategy.scan_signals(stock_data, ticker_names)
    
    # 過濾買入信號 (包含所有多頭信號)
    from squeeze_strategy.models import SignalType
    buy_signal_types = [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WATCH]
    buy_signals = [s for s in signals if s.signal in buy_signal_types]
    
    # 如果沒有信號，顯示診斷資訊
    if not buy_signals:
        print(f"\n⚠️  沒有找到買入信號，診斷資訊:")
        print(f"   掃描股票數：{len(signals)}")
        if signals:
            print(f"   信號類型分佈:")
            from collections import Counter
            signal_counts = Counter(s.signal for s in signals)
            for signal_type, count in signal_counts.most_common(5):
                print(f"     {signal_type.value}: {count}")
            
            # 顯示動能最高的前 5 檔
            print(f"   動能 Top 5:")
            top_momentum = sorted(signals, key=lambda x: x.momentum, reverse=True)[:5]
            for s in top_momentum:
                print(f"     {s.ticker}: 動能={s.momentum:.2f}, 信號={s.signal.value}")
    
    # 依動能排序
    buy_signals = sorted(buy_signals, key=lambda x: x.momentum, reverse=True)
    
    # 取前 N 檔
    top_signals = buy_signals[:max_positions]
    
    print(f"找到 {len(buy_signals)} 個買入信號")
    print(f"選取前 {len(top_signals)} 檔")
    print()
    
    # 生成建議清單
    recommendations = []
    for signal in top_signals:
        entry_price = signal.entry_price
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        shares = calculate_position_size(entry_price, stop_loss_pct, max_loss_per_trade)
        risk_per_share = entry_price - stop_loss_price
        max_loss = risk_per_share * shares
        
        recommendations.append({
            'date': get_china_time().strftime('%Y-%m-%d'),
            'ticker': signal.ticker,
            'name': signal.name,
            'signal': str(signal.signal),
            'entry_price': round(entry_price, 2),
            'stop_loss_price': round(stop_loss_price, 2),
            'stop_loss_pct': stop_loss_pct,
            'shares': shares,
            'risk_per_share': round(risk_per_share, 2),
            'max_loss': round(max_loss, 2),
            'momentum': round(signal.momentum, 4),
            'pattern': signal.pattern,
            'note': f"{signal.pattern} | 動能:{signal.momentum:.2f}",
        })
    
    return recommendations


def save_recommendations(
    recommendations: List[Dict[str, Any]],
    output_dir: str = "exports"
) -> Path:
    """
    儲存建議清單到 CSV 和 JSON
    
    Parameters:
    -----------
    recommendations : List[Dict]
        建議清單
    output_dir : str
        輸出目錄
    
    Returns:
    --------
    Path : 輸出的 CSV 路徑
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    today = get_china_time().strftime('%Y-%m-%d')
    
    # 儲存 CSV
    df = pd.DataFrame(recommendations)
    csv_path = output_path / f"daily_recommendations_{today}.csv"
    
    # 選擇要輸出的欄位
    columns = ['ticker', 'name', 'entry_price', 'stop_loss_price', 'shares', 
               'risk_per_share', 'max_loss', 'note']
    
    if len(df) > 0:
        df[columns].to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✅ 已儲存至：{csv_path}")
    else:
        print("⚠️  無建議股票")
    
    # 儲存 JSON
    json_path = output_path / f"daily_recommendations_{today}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    return csv_path


def track_performance(
    recommendations_file: Optional[str] = None,
    current_prices: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    追蹤建議清單的績效
    
    Parameters:
    -----------
    recommendations_file : str, optional
        建議清單 CSV 路徑
    current_prices : Dict, optional
        當前價格
    
    Returns:
    --------
    pd.DataFrame : 績效追蹤結果
    """
    output_path = Path('exports')
    
    # 載入最新的建議清單
    if recommendations_file:
        file_path = Path(recommendations_file)
    else:
        # 找最新的檔案
        files = sorted(output_path.glob('daily_recommendations_*.csv'))
        if files:
            file_path = files[-1]
        else:
            print("❌ 找不到建議清單檔案")
            return pd.DataFrame()
    
    print(f"載入建議清單：{file_path}")
    df = pd.read_csv(file_path)
    
    # 模擬當前價格 (實際使用時應從 API 獲取)
    if current_prices is None:
        print("使用模擬當前價格...")
        # 模擬價格波動 ±5%
        import numpy as np
        np.random.seed(42)
        df['current_price'] = df['entry_price'] * (1 + np.random.uniform(-0.05, 0.15, len(df)))
    else:
        df['current_price'] = df['ticker'].map(current_prices)
    
    # 計算績效
    df['return_pct'] = (df['current_price'] - df['entry_price']) / df['entry_price'] * 100
    df['pnl_per_share'] = df['current_price'] - df['entry_price']
    df['total_pnl'] = df['pnl_per_share'] * df['shares']
    
    # 判斷是否觸及停損
    df['stopped_out'] = df['current_price'] <= df['stop_loss_price']
    df['status'] = df['stopped_out'].apply(lambda x: '已停損' if x else '持有中')
    
    # 計算實際虧損 (如果停損)
    df['actual_loss'] = df.apply(
        lambda row: row['max_loss'] if row['stopped_out'] else -row['total_pnl'],
        axis=1
    )
    
    # 排序
    df = df.sort_values('return_pct', ascending=False)
    
    return df


def print_recommendations_table(recommendations: List[Dict[str, Any]]):
    """列印建議清單表格"""
    if not recommendations:
        print("無建議股票")
        return
    
    print("="*100)
    print(f"  每日建議操作名單 ({get_china_time().strftime('%Y-%m-%d %H:%M')})")
    print("="*100)
    print()
    print(f"{'代號':<12} {'名稱':<15} {'進場價':>10} {'停損價':>10} {'股數':>8} "
          f"{'每股風險':>10} {'最大虧損':>10} {'備註':<30}")
    print("-"*100)
    
    for rec in recommendations:
        print(f"{rec['ticker']:<12} {rec['name']:<15} {rec['entry_price']:>10.2f} "
              f"{rec['stop_loss_price']:>10.2f} {rec['shares']:>8} "
              f"{rec['risk_per_share']:>10.2f} {rec['max_loss']:>10.2f} {rec['note']:<30}")
    
    print("-"*100)
    print(f"總計：{len(recommendations)} 檔")
    total_risk = sum(rec['max_loss'] for rec in recommendations)
    print(f"總風險暴露：{total_risk:.2f} 元")
    print("="*100)


def print_performance_table(df: pd.DataFrame):
    """列印績效追蹤表格"""
    if df.empty:
        print("無追蹤資料")
        return
    
    print("="*120)
    print(f"  績效追蹤報告")
    print("="*120)
    print()
    print(f"{'代號':<12} {'名稱':<15} {'進場價':>10} {'現價':>10} {'報酬率':>10} "
          f"{'每股損益':>10} {'總損益':>12} {'狀態':<10} {'備註':<20}")
    print("-"*120)
    
    for _, row in df.iterrows():
        status = '🛑 已停損' if row['stopped_out'] else '📈 持有中'
        print(f"{row['ticker']:<12} {row['name']:<15} {row['entry_price']:>10.2f} "
              f"{row['current_price']:>10.2f} {row['return_pct']:>+10.2f}% "
              f"{row['pnl_per_share']:>+10.2f} {row['total_pnl']:>+12.2f} {status:<10} {row.get('note', ''):<20}")
    
    print("-"*120)
    
    # 統計
    total_pnl = df['total_pnl'].sum()
    winning = len(df[df['total_pnl'] > 0])
    losing = len(df[df['total_pnl'] < 0])
    stopped = len(df[df['stopped_out']])
    
    print(f"總損益：{total_pnl:+.2f} 元")
    print(f"獲利：{winning} 檔 | 虧損：{losing} 檔 | 停損：{stopped} 檔")
    print(f"勝率：{winning/len(df)*100:.1f}%")
    print("="*120)


def main():
    parser = argparse.ArgumentParser(description='每日建議操作名單與績效追蹤')
    parser.add_argument('--market', default='tw', choices=['tw', 'us', 'cn'])
    parser.add_argument('--strategy', default='baseline', help='策略名稱')
    parser.add_argument('--max-positions', type=int, default=10, help='最大建議檔數')
    parser.add_argument('--max-loss', type=float, default=1000.0, help='單筆最大虧損')
    parser.add_argument('--stop-loss', type=float, default=10.0, help='停損百分比')
    parser.add_argument('--track', action='store_true', help='追蹤績效模式')
    parser.add_argument('--input', type=str, help='輸入檔案 (追蹤模式)')
    
    args = parser.parse_args()
    
    if args.track:
        # 追蹤績效模式
        print()
        df = track_performance(args.input)
        if not df.empty:
            print_performance_table(df)
            
            # 儲存績效報告
            today = get_china_time().strftime('%Y-%m-%d')
            output_path = Path('exports') / f"performance_tracking_{today}.csv"
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"\n✅ 績效報告已儲存至：{output_path}")
    else:
        # 生成建議模式
        print()
        recommendations = generate_daily_recommendations(
            market=args.market,
            strategy_name=args.strategy,
            max_positions=args.max_positions,
            max_loss_per_trade=args.max_loss,
            stop_loss_pct=args.stop_loss,
        )
        
        print_recommendations_table(recommendations)
        
        # 儲存
        csv_path = save_recommendations(recommendations)
        print(f"\n✅ 建議清單已儲存")
        print(f"   CSV: {csv_path}")
        print(f"   JSON: {csv_path.with_suffix('.json')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
