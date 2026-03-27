#!/usr/bin/env python3
"""
Daily automated stock picker.

Runs daily scan, generates reports, and sends notifications.

Usage:
    python3 scripts/daily_stock_picker.py --market us --strategy baseline
    python3 scripts/daily_stock_picker.py --market tw --strategy balanced
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import logging

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from squeeze_strategy.engine import SqueezeStrategy
from squeeze_strategy.strategies import get_strategy_by_name, get_all_strategies
from squeeze_strategy.models import Market, StrategyConfig
from squeeze_strategy.data.loader import TickerUniverse, MarketDataDownloader, get_china_time, is_trading_day
from squeeze_strategy.data.tracker import PerformanceTracker
from squeeze_strategy.report.generator import ReportGenerator
from squeeze_strategy.notify.sender import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_daily_scan(
    market: str = "us",
    strategy_name: str = "baseline",
    send_notifications: bool = True,
    export_reports: bool = True,
    update_tracker: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run daily stock picking scan.

    Parameters:
    -----------
    market : str
        Market to scan (us, tw, cn)
    strategy_name : str
        Strategy to use
    send_notifications : bool
        Send email/LINE notifications
    export_reports : bool
        Export HTML/Markdown reports
    update_tracker : bool
        Update performance tracker
    force : bool
        Skip trading day check (for testing)

    Returns:
    --------
    Dict[str, Any] : Scan results
    """

    logger.info(f"Starting daily scan for {market.upper()} market with {strategy_name} strategy")

    now = get_china_time()

    # Check if trading day
    if not force and not is_trading_day(now, market):
        logger.info(f"Today is not a trading day for {market}. Skipping scan.")
        return {"status": "skipped", "reason": "not_trading_day"}
    
    results = {
        "status": "success",
        "timestamp": now.isoformat(),
        "market": market,
        "strategy": strategy_name,
    }
    
    # ============================================
    # 1. Load strategy and initialize
    # ============================================
    logger.info("Loading strategy configuration...")
    
    try:
        market_enum = Market(market.lower())
        config = get_strategy_by_name(strategy_name, market_enum)
    except ValueError as e:
        logger.error(f"Invalid strategy: {e}")
        return {"status": "error", "message": str(e)}
    
    strategy = SqueezeStrategy(config)
    
    # ============================================
    # 2. Load ticker universe
    # ============================================
    logger.info("Loading ticker universe...")
    
    universe_file = ROOT / "configs" / f"{market}_universe.json"
    if universe_file.exists():
        ticker_universe = TickerUniverse.load_from_file(str(universe_file), market)
    else:
        ticker_universe = TickerUniverse(market)
        # Save for future use
        universe_file.parent.mkdir(parents=True, exist_ok=True)
        ticker_universe.save_to_file(str(universe_file))
    
    tickers = ticker_universe.get_tickers()
    ticker_names = ticker_universe.get_names()
    
    logger.info(f"Loaded {len(tickers)} tickers")
    
    # ============================================
    # 3. Download market data
    # ============================================
    logger.info("Downloading market data...")
    
    downloader = MarketDataDownloader(market)
    
    try:
        # Download data for all tickers
        stock_data = {}
        for ticker in tickers[:50]:  # Limit for demo (remove limit in production)
            try:
                df = downloader.download_single(ticker, period="2y")
                if len(df) > 30:
                    stock_data[ticker] = df
            except Exception as e:
                logger.debug(f"Failed to download {ticker}: {e}")
                continue
        
        logger.info(f"Downloaded data for {len(stock_data)} tickers")
        
        if not stock_data:
            logger.warning("No data downloaded. Check network connection.")
            return {"status": "error", "message": "No data downloaded"}
        
    except Exception as e:
        logger.error(f"Failed to download data: {e}")
        return {"status": "error", "message": str(e)}
    
    # ============================================
    # 4. Update market regime
    # ============================================
    logger.info("Detecting market regime...")
    
    # Get benchmark data
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
        logger.info(f"Market regime: {market_regime}")
        results["market_regime"] = market_regime
    except Exception as e:
        logger.warning(f"Failed to get market regime: {e}")
        market_regime = "unknown"
        results["market_regime"] = "unknown"
    
    # ============================================
    # 5. Scan for signals
    # ============================================
    logger.info("Scanning for signals...")
    
    signals = strategy.scan_signals(stock_data, ticker_names)
    
    # Separate buy and sell signals
    buy_signals = [s.__dict__ for s in signals if '買入' in str(s.signal)]
    sell_signals = [s.__dict__ for s in signals if '賣出' in str(s.signal)]
    
    logger.info(f"Found {len(buy_signals)} buy signals, {len(sell_signals)} sell signals")
    
    results["buy_count"] = len(buy_signals)
    results["sell_count"] = len(sell_signals)
    results["signals"] = signals
    
    # ============================================
    # 6. Update performance tracker
    # ============================================
    tracker_summary = {}
    
    if update_tracker:
        logger.info("Updating performance tracker...")
        
        tracker = PerformanceTracker(str(ROOT / "recommendations.csv"))
        
        # Update current prices
        current_prices = downloader.get_current_prices(list(stock_data.keys()))
        tracker.update_performance(current_prices)
        
        # Record new recommendations
        if buy_signals:
            tracker.record_recommendations(buy_signals[:10], rec_type='buy')
        if sell_signals:
            tracker.record_recommendations(sell_signals[:10], rec_type='sell')
        
        # Get tracking summary
        tracker_summary = tracker.get_summary()
        results["tracker"] = tracker_summary
        
        # Get active tracking list
        tracking_list = tracker.get_active_list()
        results["tracking_list"] = tracking_list
    
    # ============================================
    # 7. Generate reports
    # ============================================
    if export_reports:
        logger.info("Generating reports...")
        
        report_gen = ReportGenerator(str(ROOT / "exports"))
        
        # Generate HTML report
        html_content = report_gen.generate_html_report(
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            tracking_list=results.get("tracking_list", []),
            market_regime=market_regime,
            strategy_name=strategy_name,
        )
        
        # Generate Markdown report
        md_content = report_gen.generate_markdown_report(
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            tracking_list=results.get("tracking_list", []),
            market_regime=market_regime,
        )
        
        # Save reports
        html_path = report_gen.save_report(html_content, f"daily_report_{market}", "html")
        md_path = report_gen.save_report(md_content, f"daily_report_{market}", "md")
        
        logger.info(f"Reports saved: {html_path}, {md_path}")
        
        results["reports"] = {
            "html": str(html_path),
            "markdown": str(md_path),
        }
        results["html_content"] = html_content
    
    # ============================================
    # 8. Send notifications
    # ============================================
    if send_notifications:
        logger.info("Sending notifications...")
        
        notifier = NotificationManager()
        
        # Prepare top picks for LINE
        top_picks = buy_signals[:5] if buy_signals else []
        
        # Send
        notification_results = notifier.send_daily_report(
            subject=f"Squeeze 每日選股報告 ({market.upper()}) - {now.strftime('%Y-%m-%d')}",
            html_content=html_content,
            attachments=None,  # Can add chart attachments here
            send_line_summary=True,
            buy_count=len(buy_signals),
            sell_count=len(sell_signals),
            tracking_count=tracker_summary.get('active_records', 0),
            top_picks=top_picks,
            market_regime=market_regime,
        )
        
        results["notifications"] = notification_results
        logger.info(f"Notification results: {notification_results}")
    
    logger.info(f"Daily scan completed successfully")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Daily automated stock picker")
    parser.add_argument(
        "--market", "-m",
        default="us",
        choices=["us", "tw", "cn"],
        help="Market to scan"
    )
    parser.add_argument(
        "--strategy", "-s",
        default="baseline",
        help="Strategy to use"
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable notifications"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Disable report export"
    )
    parser.add_argument(
        "--no-tracker",
        action="store_true",
        help="Disable tracker update"
    )
    parser.add_argument(
        "--force", "--dry-run",
        action="store_true",
        help="Force run (skip trading day check)"
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List available strategies"
    )

    args = parser.parse_args()

    # List strategies
    if args.list_strategies:
        strategies = get_all_strategies(Market(args.market.lower()))
        print(f"\nAvailable strategies for {args.market.upper()}:")
        for name in strategies.keys():
            print(f"  - {name}")
        return 0

    # Run scan
    results = run_daily_scan(
        market=args.market,
        strategy_name=args.strategy,
        send_notifications=not args.no_notify,
        export_reports=not args.no_export,
        update_tracker=not args.no_tracker,
        force=args.force,
    )
    
    # Print summary
    print("\n" + "="*60)
    print("  Daily Scan Summary")
    print("="*60)
    print(f"  Status: {results.get('status', 'unknown')}")
    print(f"  Market: {results.get('market', 'N/A').upper()}")
    print(f"  Strategy: {results.get('strategy', 'N/A')}")
    print(f"  Market Regime: {results.get('market_regime', 'N/A')}")
    print(f"  Buy Signals: {results.get('buy_count', 0)}")
    print(f"  Sell Signals: {results.get('sell_count', 0)}")
    
    if 'tracker' in results:
        print(f"\n  Tracker Summary:")
        print(f"    Active: {results['tracker'].get('active_records', 0)}")
        print(f"    Completed: {results['tracker'].get('completed_records', 0)}")
        print(f"    Avg Return: {results['tracker'].get('avg_return_pct', 0):.2f}%")
    
    if 'reports' in results:
        print(f"\n  Reports:")
        print(f"    HTML: {results['reports'].get('html', 'N/A')}")
        print(f"    Markdown: {results['reports'].get('markdown', 'N/A')}")
    
    if 'notifications' in results:
        print(f"\n  Notifications:")
        print(f"    Email: {'✓' if results['notifications'].get('email') else '✗'}")
        print(f"    LINE: {'✓' if results['notifications'].get('line') else '✗'}")
    
    print("="*60 + "\n")
    
    return 0 if results.get('status') == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())
