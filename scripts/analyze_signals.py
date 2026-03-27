#!/usr/bin/env python3
"""
Detailed backtest analysis with signal review.

Analyzes historical data and shows why signals were/weren't generated.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from squeeze_strategy.data.loader import MarketDataDownloader

def analyze_squeeze_indicators(ticker: str = "NVDA"):
    """
    Analyze Squeeze indicators for a single stock.
    Shows detailed metrics to understand why signals are generated.
    """
    
    print(f"\n{'='*70}")
    print(f"  Squeeze 指標分析 - {ticker}")
    print(f"{'='*70}\n")
    
    # Download data
    downloader = MarketDataDownloader("us")
    df = downloader.download_single(ticker, period="6mo")
    
    if len(df) < 50:
        print(f"數據不足：{len(df)} 天")
        return
    
    print(f"數據範圍：{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"最新收盤：${df['Close'].iloc[-1]:.2f}\n")
    
    # Calculate indicators manually
    import pandas_ta as ta
    
    # TTM Squeeze - use correct column names
    df.columns = df.columns.str.upper()
    
    # Calculate BB and KC
    bb = ta.bbands(df['CLOSE'], length=20, std=2.0)
    kc = ta.kc(df['HIGH'], df['LOW'], df['CLOSE'], length=20, scalar=1.5)
    
    # Squeeze detection
    bb_upper = bb['BBU_20_2.0']
    bb_lower = bb['BBL_20_2.0']
    kc_upper = kc['KCU_20_1.5']
    kc_lower = kc['KCL_20_1.5']
    
    df['Squeeze_On'] = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    
    # Momentum (using ROC)
    df['Momentum'] = ta.roc(df['CLOSE'], length=12).fillna(0)
    
    # Fired detection
    df['Fired'] = (~df['Squeeze_On']) & (df['Squeeze_On'].shift(1) == True)
    
    # Show recent data
    print("最近 10 個交易日數據:\n")
    print(f"{'日期':<12} {'收盤價':>10} {'Squeeze':>10} {'Momentum':>12} {'Fired':>8}")
    print("-" * 55)
    
    for idx, row in df.tail(10).iterrows():
        date_str = idx.strftime("%Y-%m-%d")
        close = f"${row['Close']:.2f}"
        squeeze = "ON" if row['Squeeze_On'] else "OFF"
        momentum = f"{row['Momentum']:.4f}"
        fired = "✓" if row['Fired'] else ""
        
        print(f"{date_str:<12} {close:>10} {squeeze:>10} {momentum:>12} {fired:>8}")
    
    # Find squeeze periods
    squeeze_periods = df[df['Squeeze_On'] == True]
    fired_dates = df[df['Fired'] == True]
    
    print(f"\n📊 統計:")
    print(f"   擠壓天數：{len(squeeze_periods)} 天 ({len(squeeze_periods)/len(df)*100:.1f}%)")
    print(f"   突破天數：{len(fired_dates)} 天")
    
    if len(fired_dates) > 0:
        print(f"\n🔥 最近突破日期:")
        for idx in fired_dates.tail(5).index:
            print(f"   {idx.strftime('%Y-%m-%d')} - 收盤 ${df.loc[idx, 'Close']:.2f}, 動能 {df.loc[idx, 'Momentum']:.4f}")
    
    # Show momentum distribution
    recent_momentum = df['Momentum'].tail(20)
    print(f"\n📈 動能分析 (最近 20 天):")
    print(f"   平均值：{recent_momentum.mean():.4f}")
    print(f"   最大值：{recent_momentum.max():.4f}")
    print(f"   最小值：{recent_momentum.min():.4f}")
    print(f"   最新：{recent_momentum.iloc[-1]:.4f}")
    
    # Signal criteria check
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    print(f"\n🎯 信號條件檢查:")
    print(f"   Squeeze ON: {'✓' if latest['Squeeze_On'] else '✗'}")
    print(f"   Fired: {'✓' if latest['Fired'] else '✗'}")
    print(f"   Momentum > 0: {'✓' if latest['Momentum'] > 0 else '✗'} ({latest['Momentum']:.4f})")
    print(f"   Momentum increasing: {'✓' if latest['Momentum'] > prev['Momentum'] else '✗'}")
    
    if latest['Fired'] and latest['Momentum'] > 0:
        print(f"\n✅ 符合「強烈買入」條件！")
    elif latest['Squeeze_On']:
        print(f"\n⏳ 處於擠壓狀態，等待突破")
    else:
        print(f"\n💤 無明確信號")


def main():
    # Analyze multiple stocks
    tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"]
    
    for ticker in tickers:
        try:
            analyze_squeeze_indicators(ticker)
        except Exception as e:
            print(f"分析 {ticker} 失敗：{e}")
    
    print(f"\n{'='*70}")
    print(f"  分析完成！")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
