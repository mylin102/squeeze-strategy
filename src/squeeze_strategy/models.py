"""
Data models for squeeze strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class Market(str, Enum):
    US = "us"
    TW = "tw"
    CN = "cn"


class MarketRegime(str, Enum):
    BULL = "bull_trend"
    BEAR = "bear_trend"
    RANGE = "range_bound"


class SignalType(str, Enum):
    STRONG_BUY = "強烈買入 (爆發)"
    BUY = "買入 (動能增強)"
    WATCH = "觀察 (跌勢收斂)"
    STRONG_SELL = "強烈賣出 (跌破)"
    SELL = "賣出 (動能轉弱)"
    HOLD = "觀望 (動能減弱)"


@dataclass
class StockSignal:
    """Single stock signal"""
    ticker: str
    name: str
    signal: SignalType
    pattern: str  # squeeze, houyi, whale
    entry_price: float
    momentum: float
    energy_level: int
    squeeze_on: bool
    fired: bool
    market_regime: str
    timestamp: datetime
    
    # Additional metrics
    close: float = 0.0
    volume: float = 0.0
    market_cap: float = 0.0
    value_score: Optional[float] = None
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None


@dataclass
class StrategyConfig:
    """Strategy configuration"""
    # Market
    market: Market = Market.US
    
    # Position sizing
    position_size_pct: float = 100.0  # Total position %
    max_single_position: float = 10.0  # Max % per stock
    max_positions: int = 10  # Max simultaneous positions
    
    # Entry filters
    min_momentum: float = 0.0
    min_energy_level: int = 0
    require_squeeze_on: bool = False
    require_fired: bool = False
    min_value_score: Optional[float] = None
    
    # Pattern selection
    patterns: List[str] = field(default_factory=lambda: ["squeeze", "houyi", "whale"])
    signal_types: List[str] = field(default_factory=lambda: ["buy"])
    
    # Exit rules
    stop_loss_pct: float = 15.0
    take_profit_pct: float = 25.0
    holding_days: int = 14
    time_stop_days: Optional[int] = None
    
    # Market regime filter
    allowed_regimes: Optional[List[str]] = None
    
    # Bear market adjustments
    bear_market_mode: bool = False
    
    def apply_bear_market_adjustments(self):
        """Apply bear market adjustments"""
        self.bear_market_mode = True
        self.position_size_pct = 40.0  # Reduce to 40%
        self.max_single_position = 5.0  # Reduce to 5%
        self.stop_loss_pct = 6.0  # Tighter stop
        self.take_profit_pct = 12.0  # Earlier profit taking
        self.holding_days = 6  # Shorter holding
        self.min_momentum = 0.06  # Higher momentum requirement
        self.min_energy_level = 2  # Higher energy
        self.min_value_score = 0.6  # Higher quality
        self.patterns = ["squeeze"]  # Only squeeze pattern
        self.time_stop_days = 5  # Time stop


@dataclass
class BacktestResult:
    """Backtest result"""
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    avg_holding_days: float
    trades: List[Dict] = field(default_factory=list)


@dataclass
class PortfolioState:
    """Current portfolio state"""
    cash: float
    positions: List[Dict]
    total_value: float
    unrealized_pnl: float
    realized_pnl: float
    position_count: int
    cash_ratio: float
