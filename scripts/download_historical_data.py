#!/usr/bin/env python3
"""
Historical data downloader and backtest runner.

Downloads full year 2026 data and runs backtest for strategy review.

Usage:
    python3 scripts/download_historical_data.py --market us --start 2026-01-01 --end 2026-03-28
    python3 scripts/download_historical_data.py --market tw --strategy balanced
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

from squeeze_strategy.data.loader import TickerUniverse, MarketDataDownloader
from squeeze_strategy.engine import SqueezeStrategy
from squeeze_strategy.strategies import get_strategy_by_name, get_all_strategies
from squeeze_strategy.models import Market


def download_historical_data(
    market: str = "us",
    start_date: str = "2026-01-01",
    end_date: str = "2026-03-28",
    output_dir: str = "backtests",
) -> Dict[str, Any]:
    """
    Download historical data for backtesting.
    
    Parameters:
    -----------
    market : str
        Market to download (us, tw, cn)
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    output_dir : str
        Output directory for data files
    
    Returns:
    --------
    Dict[str, Any] : Download results
    """
    
    print(f"\n{'='*70}")
    print(f"  歷史數據下載 - {market.upper()} 市場")
    print(f"{'='*70}\n")
    
    # Load ticker universe
    print(f"[1/4] 載入股票清單...")
    universe = TickerUniverse(market)
    tickers = universe.get_tickers()[:30]  # Limit to 30 for demo
    ticker_names = universe.get_names()
    
    print(f"      載入 {len(tickers)} 檔股票")
    
    # Download data
    print(f"\n[2/4] 下載歷史數據 ({start_date} 至 {end_date})...")
    downloader = MarketDataDownloader(market)
    
    results = {
        "market": market,
        "start_date": start_date,
        "end_date": end_date,
        "tickers": {},
        "summary": {
            "total": len(tickers),
            "success": 0,
            "failed": 0,
        }
    }
    
    all_data = {}
    
    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"      [{i}/{len(tickers)}] {ticker}...", end=" ")
            
            df = downloader.download_single(ticker, period="1y")
            
            if len(df) > 0:
                all_data[ticker] = df
                results["tickers"][ticker] = {
                    "days": len(df),
                    "start": df.index[0].strftime("%Y-%m-%d"),
                    "end": df.index[-1].strftime("%Y-%m-%d"),
                    "latest_close": float(df["Close"].iloc[-1]),
                }
                results["summary"]["success"] += 1
                print(f"✓ {len(df)}天")
            else:
                results["summary"]["failed"] += 1
                print("✗ 無數據")
                
        except Exception as e:
            results["summary"]["failed"] += 1
            print(f"✗ 錯誤：{e}")
    
    # Save data
    print(f"\n[3/4] 儲存數據...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV files
    data_dir = output_path / f"{market}_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    for ticker, df in all_data.items():
        csv_path = data_dir / f"{ticker.replace('.', '_')}.csv"
        df.to_csv(csv_path)
    
    # Save summary
    summary_path = output_path / f"{market}_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"      已儲存至：{output_path}/")
    
    # Run backtest
    print(f"\n[4/4] 執行回測分析...")
    
    return results


def run_backtest_on_data(
    market: str = "us",
    strategy_name: str = "baseline",
    data_dir: str = "backtests",
) -> Dict[str, Any]:
    """
    Run backtest on downloaded historical data.
    
    Parameters:
    -----------
    market : str
        Market (us, tw, cn)
    strategy_name : str
        Strategy to use
    data_dir : str
        Directory containing historical data
    
    Returns:
    --------
    Dict[str, Any] : Backtest results
    """
    
    print(f"\n{'='*70}")
    print(f"  策略回測 - {market.upper()} / {strategy_name}")
    print(f"{'='*70}\n")
    
    # Load strategy
    print(f"[1/3] 載入策略：{strategy_name}...")
    market_enum = Market(market.lower())
    config = get_strategy_by_name(strategy_name, market_enum)
    strategy = SqueezeStrategy(config)
    
    # Load data
    print(f"[2/3] 載入歷史數據...")
    data_dir = Path(data_dir) / f"{market}_data"
    
    if not data_dir.exists():
        print(f"      ✗ 數據目錄不存在：{data_dir}")
        return {"error": "Data not found"}
    
    # Load all CSV files
    stock_data = {}
    for csv_file in data_dir.glob("*.csv"):
        ticker = csv_file.stem.replace('_', '.')
        df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
        if len(df) > 30:
            stock_data[ticker] = df
    
    print(f"      載入 {len(stock_data)} 檔股票數據")
    
    # Run backtest simulation
    print(f"[3/3] 執行回測掃描...")
    
    # Get benchmark data for market regime
    downloader = MarketDataDownloader(market)
    benchmark_map = {
        "us": "SPY",
        "tw": "^TWII",
        "cn": "000300.SS",
    }
    benchmark = benchmark_map.get(market, "SPY")
    
    try:
        benchmark_data = downloader.download_single(benchmark, period="1y")
        strategy.update_market_regime(benchmark_data)
        market_regime = strategy.current_regime.value
    except:
        market_regime = "unknown"
    
    print(f"      市場狀態：{market_regime}")
    
    # Scan for signals
    ticker_names = {t: t for t in stock_data.keys()}
    signals = strategy.scan_signals(stock_data, ticker_names)
    
    buy_signals = [s.__dict__ for s in signals if '買入' in str(s.signal)]
    sell_signals = [s.__dict__ for s in signals if '賣出' in str(s.signal)]
    
    print(f"\n      找到 {len(buy_signals)} 個買入信號")
    print(f"      找到 {len(sell_signals)} 個賣出信號")
    
    # Generate report
    results = {
        "market": market,
        "strategy": strategy_name,
        "market_regime": market_regime,
        "tickers_scanned": len(stock_data),
        "buy_signals": len(buy_signals),
        "sell_signals": len(sell_signals),
        "top_picks": buy_signals[:10],
    }
    
    # Save results
    output_path = Path(data_dir).parent / f"{market}_{strategy_name}_backtest.json"
    
    # Convert for JSON serialization
    json_results = results.copy()
    for signal in json_results.get("top_picks", []):
        if "timestamp" in signal and signal["timestamp"]:
            signal["timestamp"] = str(signal["timestamp"])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n      回測結果已儲存至：{output_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Download historical data and run backtest")
    parser.add_argument("--market", "-m", default="us", choices=["us", "tw", "cn"])
    parser.add_argument("--start", default="2026-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-03-28", help="End date (YYYY-MM-DD)")
    parser.add_argument("--strategy", "-s", default="baseline", help="Strategy for backtest")
    parser.add_argument("--output", "-o", default="backtests", help="Output directory")
    
    args = parser.parse_args()
    
    # Download data
    download_results = download_historical_data(
        market=args.market,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output,
    )
    
    # Run backtest
    backtest_results = run_backtest_on_data(
        market=args.market,
        strategy_name=args.strategy,
        data_dir=args.output,
    )
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"  回測完成！")
    print(f"{'='*70}")
    
    print(f"\n📊 數據下載摘要:")
    print(f"   總計：{download_results['summary']['total']} 檔")
    print(f"   成功：{download_results['summary']['success']} 檔")
    print(f"   失敗：{download_results['summary']['failed']} 檔")
    
    print(f"\n📈 回測結果:")
    print(f"   市場：{backtest_results.get('market', 'N/A').upper()}")
    print(f"   策略：{backtest_results.get('strategy', 'N/A')}")
    print(f"   市場狀態：{backtest_results.get('market_regime', 'N/A')}")
    print(f"   掃描股票：{backtest_results.get('tickers_scanned', 0)} 檔")
    print(f"   買入信號：{backtest_results.get('buy_signals', 0)} 個")
    print(f"   賣出信號：{backtest_results.get('sell_signals', 0)} 個")
    
    if backtest_results.get('top_picks'):
        print(f"\n🏆 重點推薦:")
        for i, pick in enumerate(backtest_results['top_picks'][:5], 1):
            print(f"   {i}. {pick.get('ticker', '')} - {pick.get('signal', '')}")
    
    print(f"\n{'='*70}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
