"""
Pre-configured strategies based on backtest analysis.

Best performing strategies:
1. baseline - Best overall for US and TW
2. balanced - Best for US (squeeze + whale)
3. optimized_squeeze - High win rate
"""

from typing import Dict, Any
from .models import StrategyConfig, Market


def get_baseline_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Baseline strategy - Best overall performer.
    
    Backtest results:
    - US: +177-367% total return
    - TW: +582% total return
    """
    return StrategyConfig(
        market=market,
        position_size_pct=100.0,
        max_single_position=10.0,
        max_positions=10,
        min_momentum=0.0,
        min_energy_level=0,
        require_squeeze_on=False,
        require_fired=False,
        min_value_score=None,
        patterns=["squeeze", "houyi", "whale"],
        signal_types=["buy"],
        stop_loss_pct=10.0,  # Optimal from backtest
        take_profit_pct=25.0,
        holding_days=14,
        time_stop_days=None,
        allowed_regimes=None,
        bear_market_mode=False,
    )


def get_balanced_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Balanced strategy - Best for US market.
    
    Combines squeeze and whale patterns.
    Backtest: US +199.81%
    
    Note: Bear market mode disabled for signal generation
    """
    config = StrategyConfig(
        market=market,
        position_size_pct=100.0,
        max_single_position=10.0,
        max_positions=10,
        min_momentum=0.0,
        min_energy_level=0,
        require_squeeze_on=False,
        require_fired=False,
        min_value_score=None,
        patterns=["squeeze", "whale"],  # Key difference
        signal_types=["buy"],
        stop_loss_pct=10.0,
        take_profit_pct=20.0,
        holding_days=14,
        time_stop_days=None,
        allowed_regimes=None,
        bear_market_mode=False,  # Disabled for testing
    )
    return config


def get_conservative_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Conservative strategy - Lower risk.
    
    Features:
    - Higher quality filter
    - Tighter stop-loss
    - Lower position size
    """
    return StrategyConfig(
        market=market,
        position_size_pct=60.0,
        max_single_position=5.0,
        max_positions=8,
        min_momentum=0.02,
        min_energy_level=1,
        require_squeeze_on=True,
        require_fired=False,
        min_value_score=0.5,
        patterns=["squeeze", "whale"],
        signal_types=["buy"],
        stop_loss_pct=8.0,
        take_profit_pct=18.0,
        holding_days=10,
        time_stop_days=7,
        allowed_regimes=None,
        bear_market_mode=False,
    )


def get_aggressive_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Aggressive strategy - Maximum returns.
    
    Features:
    - Full position size
    - Wider stop-loss
    - All patterns
    """
    return StrategyConfig(
        market=market,
        position_size_pct=100.0,
        max_single_position=15.0,
        max_positions=12,
        min_momentum=0.05,
        min_energy_level=1,
        require_squeeze_on=False,
        require_fired=True,
        min_value_score=0.3,
        patterns=["squeeze", "houyi", "whale"],
        signal_types=["buy"],
        stop_loss_pct=15.0,
        take_profit_pct=35.0,
        holding_days=14,
        time_stop_days=None,
        allowed_regimes=["bull_trend", "range_bound"],
        bear_market_mode=False,
    )


def get_bear_market_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Bear market defensive strategy.
    
    Features:
    - Reduced position size (30-50%)
    - Tight stop-loss (5-8%)
    - Short holding period (5-7 days)
    - Focus on squeeze pattern
    - Sell signals enabled
    """
    config = StrategyConfig(
        market=market,
        position_size_pct=40.0,
        max_single_position=5.0,
        max_positions=6,
        min_momentum=0.06,
        min_energy_level=2,
        require_squeeze_on=True,
        require_fired=False,
        min_value_score=0.6,
        patterns=["squeeze"],
        signal_types=["sell"],  # Focus on short
        stop_loss_pct=6.0,
        take_profit_pct=12.0,
        holding_days=6,
        time_stop_days=5,
        allowed_regimes=None,
        bear_market_mode=True,
    )
    return config


def get_scalping_strategy(market: Market = Market.US) -> StrategyConfig:
    """
    Short-term scalping strategy.
    
    Features:
    - Very short holding period (3-5 days)
    - Quick profit taking
    - Tight stop-loss
    """
    return StrategyConfig(
        market=market,
        position_size_pct=80.0,
        max_single_position=8.0,
        max_positions=10,
        min_momentum=0.08,
        min_energy_level=1,
        require_squeeze_on=False,
        require_fired=True,
        min_value_score=None,
        patterns=["squeeze"],
        signal_types=["buy"],
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        holding_days=5,
        time_stop_days=3,
        allowed_regimes=None,
        bear_market_mode=False,
    )


def get_all_strategies(market: Market = Market.US) -> Dict[str, StrategyConfig]:
    """Get all available strategies"""
    return {
        "baseline": get_baseline_strategy(market),
        "balanced": get_balanced_strategy(market),
        "conservative": get_conservative_strategy(market),
        "aggressive": get_aggressive_strategy(market),
        "bear_market": get_bear_market_strategy(market),
        "scalping": get_scalping_strategy(market),
    }


def get_strategy_by_name(name: str, market: Market = Market.US) -> StrategyConfig:
    """Get strategy by name"""
    strategies = get_all_strategies(market)
    if name not in strategies:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(strategies.keys())}")
    return strategies[name]
