#!/usr/bin/env python3
"""
Historical backtest tracker.

Simulates daily scans from 2026-01-01 to present,
tracking all signals and performance over time.

Usage:
    python3 scripts/historical_backtest_tracker.py --start 2026-01-01 --end 2026-03-28
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import json

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from squeeze_strategy.engine import SqueezeStrategy
from squeeze_strategy.strategies import get_baseline_strategy, get_balanced_strategy
from squeeze_strategy.models import Market
from squeeze_strategy.data.loader import MarketDataDownloader, TickerUniverse


def get_trading_days(start: str, end: str) -> List[str]:
    """Get list of trading days (skip weekends)"""
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    
    trading_days = []
    current = start_date
    
    while current <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current.weekday() < 5:
            trading_days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return trading_days


def run_historical_backtest(
    market: str = "us",
    start_date: str = "2026-01-01",
    end_date: str = "2026-03-28",
    strategy_name: str = "balanced",
    output_dir: str = "backtests/historical",
) -> Dict[str, Any]:
    """
    Run historical backtest from start_date to end_date.
    
    Simulates daily scans and tracks all signals.
    """
    
    print(f"\n{'='*70}")
    print(f"  歷史回測追蹤 - {market.upper()} / {strategy_name}")
    print(f"  期間：{start_date} 至 {end_date}")
    print(f"{'='*70}\n")
    
    # Load strategy
    print(f"[1/5] 載入策略...")
    market_enum = Market(market.lower())
    
    if strategy_name == "baseline":
        config = get_baseline_strategy(market_enum)
    else:
        config = get_balanced_strategy(market_enum)
    
    # Disable bear market mode for historical analysis
    config.bear_market_mode = False
    
    strategy = SqueezeStrategy(config)
    print(f"      策略：{strategy_name}")
    print(f"      空頭模式：{config.bear_market_mode}")
    
    # Load ticker universe
    print(f"\n[2/5] 載入股票清單...")
    universe = TickerUniverse(market)
    tickers = universe.get_tickers()[:30]  # Limit for demo
    ticker_names = universe.get_names()
    print(f"      載入 {len(tickers)} 檔股票")
    
    # Download historical data
    print(f"\n[3/5] 下載歷史數據...")
    downloader = MarketDataDownloader(market)
    
    stock_data = {}
    for ticker in tickers:
        try:
            df = downloader.download_single(ticker, period="1y")
            if len(df) > 30:
                stock_data[ticker] = df
        except Exception:
            pass
    
    print(f"      下載 {len(stock_data)} 檔成功")
    
    # Get benchmark data
    try:
        benchmark = downloader.download_single("SPY" if market == "us" else "^TWII", period="1y")
    except:
        benchmark = None
    
    # Run daily backtest
    print(f"\n[4/5] 執行每日回測...")
    
    trading_days = get_trading_days(start_date, end_date)
    print(f"      交易日數：{len(trading_days)}")
    
    daily_results = []
    all_signals = []
    
    for i, day in enumerate(trading_days, 1):
        if i % 20 == 0:
            print(f"      [{i}/{len(trading_days)}] {day}...")
        
        # Filter data up to this day
        day_data = {}
        for ticker, df in stock_data.items():
            df_up_to_day = df[df.index <= day]
            if len(df_up_to_day) > 30:
                day_data[ticker] = df_up_to_day
        
        if not day_data:
            continue
        
        # Update market regime
        if benchmark is not None:
            bench_up_to_day = benchmark[benchmark.index <= day]
            if len(bench_up_to_day) > 30:
                strategy.update_market_regime(bench_up_to_day)
        
        # Scan for signals
        signals = strategy.scan_signals(day_data, ticker_names)
        
        buy_signals = [s for s in signals if '買入' in str(s.signal)]
        sell_signals = [s for s in signals if '賣出' in str(s.signal)]
        
        # Record daily summary
        daily_results.append({
            'date': day,
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals),
            'market_regime': strategy.current_regime.value,
        })
        
        # Record all signals
        for s in buy_signals:
            all_signals.append({
                'date': day,
                'ticker': s.ticker,
                'name': s.name,
                'signal': str(s.signal),
                'momentum': s.momentum,
                'energy_level': s.energy_level,
                'entry_price': s.entry_price,
            })
    
    # Generate report
    print(f"\n[5/5] 生成報告...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Summary statistics
    total_buy_signals = sum(r['buy_count'] for r in daily_results)
    total_sell_signals = sum(r['sell_count'] for r in daily_results)
    days_with_signals = sum(1 for r in daily_results if r['buy_count'] > 0)
    
    # Market regime distribution
    regime_counts = {}
    for r in daily_results:
        regime = r['market_regime']
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
    
    results = {
        'market': market,
        'strategy': strategy_name,
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': len(trading_days),
        'tickers_scanned': len(stock_data),
        'total_buy_signals': total_buy_signals,
        'total_sell_signals': total_sell_signals,
        'days_with_signals': days_with_signals,
        'market_regime_distribution': regime_counts,
        'daily_summary': daily_results,
        'all_signals': all_signals,
    }
    
    # Save results
    summary_path = output_path / f"{market}_{strategy_name}_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save daily CSV
    daily_df = pd.DataFrame(daily_results)
    daily_csv_path = output_path / f"{market}_{strategy_name}_daily.csv"
    daily_df.to_csv(daily_csv_path, index=False)
    
    # Save signals CSV
    if all_signals:
        signals_df = pd.DataFrame(all_signals)
        signals_csv_path = output_path / f"{market}_{strategy_name}_signals.csv"
        signals_df.to_csv(signals_csv_path, index=False)
    
    print(f"      已儲存至：{output_path}/")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"  回測完成！")
    print(f"{'='*70}")
    print()
    print(f"📊 回測摘要:")
    print(f"   交易日數：{len(trading_days)} 天")
    print(f"   掃描股票：{len(stock_data)} 檔")
    print(f"   買入信號總數：{total_buy_signals} 個")
    print(f"   賣出信號總數：{total_sell_signals} 個")
    print(f"   有信號的天數：{days_with_signals} 天 ({days_with_signals/len(trading_days)*100:.1f}%)")
    print()
    print(f"📈 市場狀態分佈:")
    for regime, count in regime_counts.items():
        pct = count / len(trading_days) * 100
        print(f"   {regime}: {count} 天 ({pct:.1f}%)")
    print()
    
    if all_signals:
        print(f"🏆 最活躍標的 (Top 10):")
        ticker_counts = {}
        for s in all_signals:
            ticker_counts[s['ticker']] = ticker_counts.get(s['ticker'], 0) + 1
        
        sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for ticker, count in sorted_tickers:
            print(f"   {ticker}: {count} 次")
    
    print()
    print(f"📁 輸出檔案:")
    print(f"   {summary_path}")
    print(f"   {daily_csv_path}")
    if all_signals:
        print(f"   {signals_csv_path}")
    print()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Historical backtest tracker")
    parser.add_argument("--market", "-m", default="us", choices=["us", "tw", "cn"])
    parser.add_argument("--start", default="2026-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-03-28", help="End date (YYYY-MM-DD)")
    parser.add_argument("--strategy", "-s", default="balanced")
    parser.add_argument("--output", "-o", default="backtests/historical")
    
    args = parser.parse_args()
    
    results = run_historical_backtest(
        market=args.market,
        start_date=args.start,
        end_date=args.end,
        strategy_name=args.strategy,
        output_dir=args.output,
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
