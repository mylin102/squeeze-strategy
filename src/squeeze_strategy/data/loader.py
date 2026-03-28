"""
Data module for automated stock picking.

Handles:
- Ticker universe management
- Market data downloading
- Fundamentals fetching
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

try:
    import yfinance as yf
except ImportError:
    yf = None


class TickerUniverse:
    """Manage ticker universe for different markets"""
    
    def __init__(self, market: str = "us"):
        self.market = market.lower()
        self.tickers = self._load_universe()
    
    def _load_universe(self) -> Dict[str, str]:
        """Load ticker universe based on market"""
        if self.market == "us":
            return self._load_us_universe()
        elif self.market == "tw":
            return self._load_tw_universe()
        elif self.market == "cn":
            return self._load_cn_universe()
        else:
            return {}
    
    def _load_us_universe(self) -> Dict[str, str]:
        """Load US stock universe - 300 stocks"""
        import configparser
        
        # Try to load from config file first
        config_file = Path(__file__).parent.parent.parent.parent / "configs" / "markets" / "us_stocks_300.ini"
        
        if config_file.exists():
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            universe = dict(config['stocks'])
            return universe
        
        # Fallback to basic 63 stocks if config file not found
        sp500 = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
            "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL",
            "BAC", "VZ", "ADBE", "CMCSA", "NFLX", "XOM", "PFE", "KO",
            "PEP", "T", "MRK", "ABT", "WMT", "CSCO", "CVX", "INTC", "VZ",
            "CRM", "ORCL", "IBM", "QCOM", "TXN", "AMD", "AVGO", "ACN",
            "COST", "NKE", "MCD", "LLY", "TMO", "ABBV", "DHR", "NEE",
        ]

        nasdaq100 = [
            "AMGN", "GILD", "ISRG", "REGN", "VRTX", "BIIB", "ILMN",
            "MNST", "KDP", "LULU", "MRVL", "PANW", "ADSK", "NXPI",
        ]

        all_tickers = list(set(sp500 + nasdaq100))
        return {ticker: ticker for ticker in all_tickers}
    
    def _load_tw_universe(self) -> Dict[str, str]:
        """Load Taiwan stock universe - 100+ major stocks"""
        import configparser
        
        # Try to load from config file first
        config_file = Path(__file__).parent.parent.parent.parent / "configs" / "markets" / "tw_stocks_100.ini"
        
        if config_file.exists():
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            universe = dict(config['stocks'])
            return universe
        
        # Fallback to basic 50 stocks if config file not found
        tw50 = [
            "2330.TW", "2317.TW", "2454.TW", "2303.TW", "2357.TW", "2353.TW",
            "2881.TW", "2882.TW", "2883.TW", "2884.TW", "2885.TW", "2886.TW",
            "2891.TW", "2892.TW", "1301.TW", "1303.TW", "1326.TW", "2002.TW",
            "1216.TW", "1231.TW", "2382.TW", "2324.TW", "2308.TW", "2345.TW",
            "2376.TW", "2360.TW", "2369.TW", "2379.TW", "2393.TW", "2355.TW",
            "2409.TW", "2412.TW", "2466.TW", "2467.TW", "3081.TWO", "3211.TWO",
            "3680.TWO", "5284.TW", "6285.TW", "6854.TW", "7734.TWO", "7880.TWO",
            "8021.TW", "2204.TW", "2207.TW", "2603.TW", "2606.TW", "2609.TW",
            "2337.TW",
        ]

        names = {
            "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2303.TW": "聯電",
            "2357.TW": "華碩", "2353.TW": "宏碁", "2881.TW": "富邦金", "2882.TW": "國泰金",
            "2883.TW": "開發金", "2884.TW": "玉山金", "2885.TW": "元大金", "2886.TW": "兆豐金",
            "2891.TW": "中信金", "2892.TW": "第一金", "1301.TW": "台塑", "1303.TW": "南亞",
            "1326.TW": "台化", "2002.TW": "中鋼", "1216.TW": "統一", "1231.TW": "味全",
            "2382.TW": "廣達", "2324.TW": "仁寶", "2308.TW": "台達電", "2345.TW": "明泰",
            "2376.TW": "技嘉", "2360.TW": "致茂", "2369.TW": "聯詠", "2379.TW": "瑞昱",
            "2393.TW": "億光", "2355.TW": "敬鵬", "2409.TW": "友達", "2412.TW": "中華電",
            "2466.TW": "神達", "2467.TW": "志聖", "3081.TWO": "聯亞", "3211.TWO": "順達",
            "3680.TWO": "家登", "5284.TW": "jpp-KY", "6285.TW": "啟碁", "6854.TW": "錼創-KY",
            "7734.TWO": "印能", "7880.TWO": "聖凰", "8021.TW": "尖點",
            "2204.TW": "中華", "2207.TW": "和泰車", "2603.TW": "長榮", "2606.TW": "裕民",
            "2609.TW": "陽明", "2337.TW": "旺宏",
        }

        universe = {}
        for ticker in tw50:
            universe[ticker] = names.get(ticker, ticker.split('.')[0])

        return universe
    
    def _load_cn_universe(self) -> Dict[str, str]:
        """Load China A-share universe - 300 stocks"""
        import configparser
        
        # Try to load from config file first
        config_file = Path(__file__).parent.parent.parent.parent / "configs" / "markets" / "cn_stocks_100.ini"
        
        if config_file.exists():
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            universe = dict(config['stocks'])
            return universe
        
        # Fallback to basic 20 stocks if config file not found
        cn_stocks = [
            "600519.SS", "000001.SZ", "300750.SZ", "002594.SZ", "601318.SS",
            "600036.SS", "000333.SZ", "600276.SS", "000858.SZ", "601888.SS",
            "600030.SS", "601166.SS", "000002.SZ", "600887.SS", "002415.SZ",
            "600900.SS", "601398.SS", "600585.SS", "000651.SZ", "600016.SS",
        ]

        names = {
            "600519.SS": "貴州茅台", "000001.SZ": "平安銀行", "300750.SZ": "寧德時代",
            "002594.SZ": "比亞迪", "601318.SS": "中國平安", "600036.SS": "招商銀行",
        }

        universe = {}
        for ticker in cn_stocks:
            universe[ticker] = names.get(ticker, ticker.split('.')[0])

        return universe
    
    def get_tickers(self) -> List[str]:
        """Get ticker list"""
        return list(self.tickers.keys())
    
    def get_names(self) -> Dict[str, str]:
        """Get ticker name mapping"""
        return self.tickers
    
    def save_to_file(self, path: str):
        """Save universe to JSON file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.tickers, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, path: str, market: str = "us") -> TickerUniverse:
        """Load universe from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            tickers = json.load(f)
        
        instance = cls(market)
        instance.tickers = tickers
        return instance


class MarketDataDownloader:
    """Download market data from yfinance"""
    
    def __init__(self, market: str = "us"):
        self.market = market.lower()
    
    def download(
        self,
        tickers: List[str],
        period: str = "2y",
        interval: str = "1d",
        threads: bool = True,
    ) -> pd.DataFrame:
        """
        Download historical data for multiple tickers.
        
        Parameters:
        -----------
        tickers : List[str]
            List of ticker symbols
        period : str
            Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval : str
            Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        threads : bool
            Use multithreading for faster download
        
        Returns:
        --------
        pd.DataFrame
            MultiIndex DataFrame with ticker data
        """
        if yf is None:
            raise ImportError("yfinance is required. Install with: pip install yfinance")
        
        # Download data
        data = yf.download(tickers, period=period, interval=interval, 
                          threads=threads, progress=False)
        
        return data
    
    def download_single(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Download data for single ticker"""
        if yf is None:
            raise ImportError("yfinance is required")
        
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Get current/latest prices for tickers"""
        prices = {}
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                data = t.history(period="1d")
                if len(data) > 0:
                    prices[ticker] = float(data['Close'].iloc[-1])
            except Exception:
                pass
        return prices
    
    def get_fundamentals(self, tickers: List[str]) -> pd.DataFrame:
        """Get fundamental data for tickers"""
        fundamentals = []
        
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.info
                
                fundamentals.append({
                    'ticker': ticker,
                    'marketCap': info.get('marketCap', None),
                    'peRatio': info.get('trailingPE', None),
                    'pbRatio': info.get('priceToBook', None),
                    'dividendYield': info.get('dividendYield', None),
                    'averageVolume': info.get('averageVolume', None),
                    'sector': info.get('sector', None),
                    'industry': info.get('industry', None),
                })
            except Exception:
                continue
        
        return pd.DataFrame(fundamentals)


def get_china_time() -> datetime:
    """Get current China/Taiwan time"""
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


def is_trading_day(date: datetime, market: str = "us") -> bool:
    """Check if date is a trading day (skip weekends and holidays)"""
    # Skip weekends
    if date.weekday() >= 5:
        return False
    
    # Simple holiday check (can be enhanced)
    holidays_us = [
        "2026-01-01",  # New Year
        "2026-01-19",  # MLK Day
        "2026-02-16",  # Presidents Day
        "2026-04-03",  # Good Friday
        "2026-05-25",  # Memorial Day
        "2026-06-19",  # Juneteenth
        "2026-07-03",  # Independence Day
        "2026-09-07",  # Labor Day
        "2026-11-26",  # Thanksgiving
        "2026-12-25",  # Christmas
    ]
    
    holidays_tw = [
        "2026-01-01",  # ROC
        "2026-02-17",  # CNY
        "2026-02-18",  # CNY
        "2026-02-19",  # CNY
        "2026-02-20",  # CNY
        "2026-02-21",  # CNY
        "2026-03-29",  # YMA
        "2026-04-03",  # CQ
        "2026-05-01",  # LD
        "2026-06-19",  # DB
        "2026-09-25",  # MAF
        "2026-10-10",  # ND
    ]
    
    date_str = date.strftime("%Y-%m-%d")
    
    if market == "us" and date_str in holidays_us:
        return False
    elif market == "tw" and date_str in holidays_tw:
        return False
    
    return True
