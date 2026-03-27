"""
Core strategy engine with market regime detection and dynamic adjustments.

Based on backtest results:
- Best strategies: baseline, balanced
- Optimal stop-loss: 10% fixed
- Bear market adjustments implemented
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from .models import (
    Market, MarketRegime, SignalType, 
    StockSignal, StrategyConfig, PortfolioState
)


class MarketRegimeDetector:
    """Detect market regime based on technical indicators"""
    
    def __init__(self, benchmark: str = "SPY"):
        self.benchmark = benchmark
    
    def detect_regime(self, df: pd.DataFrame) -> Tuple[MarketRegime, Dict[str, float]]:
        """
        Detect market regime from price data.
        
        Returns:
            Tuple of (MarketRegime, metrics_dict)
        """
        if len(df) < 60:
            return MarketRegime.RANGE, {}
        
        latest = df.iloc[-1]
        close = latest['Close']
        
        # Calculate MAs
        ma20 = latest.get('MA20', df['Close'].rolling(20).mean().iloc[-1])
        ma60 = latest.get('MA60', df['Close'].rolling(60).mean().iloc[-1])
        
        # Calculate slopes (20-day change)
        ma20_20d = df['Close'].rolling(20).mean().iloc[-21] if len(df) > 20 else ma20
        ma60_20d = df['Close'].rolling(60).mean().iloc[-61] if len(df) > 60 else ma60
        
        ma20_slope = (ma20 - ma20_20d) / ma20_20d * 100
        ma60_slope = (ma60 - ma60_20d) / ma60_20d * 100
        
        # Price position
        price_vs_ma20 = (close - ma20) / ma20 * 100
        price_vs_ma60 = (close - ma60) / ma60 * 100
        
        # Recent returns
        ret_20d = (close - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100 if len(df) > 20 else 0
        ret_60d = (close - df['Close'].iloc[-61]) / df['Close'].iloc[-61] * 100 if len(df) > 60 else 0
        
        # Volatility
        returns = df['Close'].pct_change().dropna()
        volatility = returns.tail(20).std() * 100 * np.sqrt(252)
        
        # Scoring
        score = 0
        
        # MA alignment
        if ma20 > ma60:
            score += 1
        else:
            score -= 1
        
        # Price vs MA
        if close > ma20 > ma60:
            score += 2
        elif close < ma20 < ma60:
            score -= 2
        
        # MA slopes
        if ma20_slope > 0 and ma60_slope > 0:
            score += 1
        elif ma20_slope < 0 and ma60_slope < 0:
            score -= 1
        
        # Recent returns
        if ret_20d > 0 and ret_60d > 0:
            score += 1
        elif ret_20d < 0 and ret_60d < 0:
            score -= 1
        
        # Classify
        if score >= 3:
            regime = MarketRegime.BULL
        elif score <= -3:
            regime = MarketRegime.BEAR
        else:
            regime = MarketRegime.RANGE
        
        metrics = {
            'score': score,
            'ma20_slope': ma20_slope,
            'ma60_slope': ma60_slope,
            'price_vs_ma20': price_vs_ma20,
            'price_vs_ma60': price_vs_ma60,
            'ret_20d': ret_20d,
            'ret_60d': ret_60d,
            'volatility': volatility,
        }
        
        return regime, metrics


class SqueezeStrategy:
    """
    Main squeeze momentum strategy engine.
    
    Incorporates learnings from backtest analysis:
    - Best performing strategies (baseline, balanced)
    - Optimal stop-loss (10% fixed)
    - Bear market adjustments
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.regime_detector = MarketRegimeDetector()
        self.current_regime = MarketRegime.RANGE
        self.regime_metrics = {}
    
    def update_market_regime(self, benchmark_data: pd.DataFrame):
        """Update market regime based on latest data"""
        self.current_regime, self.regime_metrics = self.regime_detector.detect_regime(
            benchmark_data
        )
        
        # Note: Auto bear market adjustments disabled for backtesting
        # To enable defensive mode, manually set config.bear_market_mode = True
        # if self.current_regime == MarketRegime.BEAR and not self.config.bear_market_mode:
        #     self.config.apply_bear_market_adjustments()
        #     print(f"[INFO] Bear market detected! Applied defensive adjustments.")
        
        print(f"[INFO] Market regime: {self.current_regime.value}")
        return self.current_regime
    
    def scan_signals(
        self,
        stock_data: Dict[str, pd.DataFrame],
        ticker_names: Dict[str, str],
    ) -> List[StockSignal]:
        """
        Scan stocks for squeeze signals.
        
        Parameters:
        -----------
        stock_data : Dict[str, pd.DataFrame]
            Dictionary of ticker -> OHLCV data
        ticker_names : Dict[str, str]
            Dictionary of ticker -> name
        
        Returns:
        --------
        List[StockSignal] : List of detected signals
        """
        signals = []
        
        for ticker, df in stock_data.items():
            if len(df) < 30:
                continue
            
            # Calculate indicators
            df_with_ind = self._calculate_indicators(df)
            latest = df_with_ind.iloc[-1]
            prev = df_with_ind.iloc[-2] if len(df_with_ind) > 1 else latest
            
            # Apply filters
            if not self._passes_filters(latest, df_with_ind):
                continue
            
            # Determine signal
            signal = self._determine_signal(latest, prev)
            
            # Create signal object
            stock_signal = StockSignal(
                ticker=ticker,
                name=ticker_names.get(ticker, ticker),
                signal=signal,
                pattern=self._detect_pattern(latest),
                entry_price=float(latest['Open']),
                momentum=float(latest.get('Momentum', 0)),
                energy_level=int(latest.get('Energy_Level', 0)),
                squeeze_on=bool(latest.get('Squeeze_On', False)),
                fired=bool(latest.get('Fired', False)),
                market_regime=self.current_regime.value,
                timestamp=latest.name,
                close=float(latest['Close']),
                volume=float(latest.get('Volume', 0)),
                stop_loss_price=self._calculate_stop_loss(float(latest['Open'])),
                take_profit_price=self._calculate_take_profit(float(latest['Open'])),
            )
            
            signals.append(stock_signal)
        
        # Sort by signal strength
        signals = self._rank_signals(signals)
        
        return signals
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate squeeze indicators"""
        import pandas_ta as ta

        result = df.copy()
        
        # Ensure column names are uppercase
        result.columns = result.columns.str.upper()
        
        # TTM Squeeze - pass OHLC data explicitly
        try:
            sqz = ta.squeeze(
                high=result['HIGH'],
                low=result['LOW'],
                close=result['CLOSE'],
                bb_length=20, bb_std=2.0,
                kc_length=20, kc_scalar=1.5,
                lazy=True
            )

            # Find squeeze columns
            sqz_on_col = [c for c in sqz.columns if 'SQZ_ON' in c.upper()]
            mom_col = [c for c in sqz.columns if c.upper().startswith('SQZ_') and c.upper() not in ['SQZ_ON', 'SQZ_OFF', 'SQZ_NO']]

            if sqz_on_col:
                result['Squeeze_On'] = sqz[sqz_on_col[0]].astype(bool)
            if mom_col:
                result['Momentum'] = sqz[mom_col[0]].fillna(0)

            # Fired detection
            result['Fired'] = (~result['Squeeze_On']) & (result['Squeeze_On'].shift(1) == True)
            result['Fired'] = result['Fired'].fillna(False)

        except Exception as e:
            print(f"Indicator calculation error: {e}")
            result['Squeeze_On'] = False
            result['Momentum'] = 0
            result['Fired'] = False
        
        # Energy level
        try:
            bb = ta.bbands(length=20, std=2.0)
            kc = ta.kc(length=20, scalar=1.5)
            
            bb_upper = bb.filter(like='BBU').iloc[:, 0]
            bb_lower = bb.filter(like='BBL').iloc[:, 0]
            kc_upper = kc.filter(like='KCU').iloc[:, 0]
            kc_lower = kc.filter(like='KCL').iloc[:, 0]
            
            bb_width = bb_upper - bb_lower
            kc_width = kc_upper - kc_lower
            
            squeeze_ratio = (kc_width - bb_width) / kc_width
            squeeze_ratio = squeeze_ratio.clip(lower=0, upper=1)
            
            result['Energy_Level'] = pd.cut(
                squeeze_ratio,
                bins=[-np.inf, 0.3, 0.5, 0.7, np.inf],
                labels=[0, 1, 2, 3]
            ).fillna(0).astype(int)
            
        except Exception:
            result['Energy_Level'] = 0
        
        # Previous momentum
        result['Prev_Momentum'] = result['Momentum'].shift(1).fillna(0)
        
        return result
    
    def _passes_filters(self, latest: pd.Series, df: pd.DataFrame) -> bool:
        """Check if stock passes entry filters"""
        # Momentum filter
        if self.config.min_momentum is not None:
            if latest.get('Momentum', 0) < self.config.min_momentum:
                return False
        
        # Energy level filter
        if latest.get('Energy_Level', 0) < self.config.min_energy_level:
            return False
        
        # Squeeze state filter
        if self.config.require_squeeze_on and not latest.get('Squeeze_On', False):
            return False
        
        # Fired filter
        if self.config.require_fired and not latest.get('Fired', False):
            return False
        
        # Pattern filter
        pattern = self._detect_pattern(latest)
        if pattern not in self.config.patterns:
            return False
        
        return True
    
    def _determine_signal(self, latest: pd.Series, prev: pd.Series) -> SignalType:
        """Determine trading signal"""
        mom = latest.get('Momentum', 0)
        prev_mom = latest.get('Prev_Momentum', 0)
        fired = latest.get('Fired', False)
        squeeze_on = latest.get('Squeeze_On', False)
        
        if fired and mom > 0:
            return SignalType.STRONG_BUY
        elif fired and mom < 0:
            return SignalType.STRONG_SELL
        elif mom > 0:
            if mom > prev_mom:
                return SignalType.BUY
            else:
                return SignalType.HOLD
        else:
            if mom > prev_mom:
                return SignalType.WATCH
            else:
                return SignalType.SELL
    
    def _detect_pattern(self, latest: pd.Series) -> str:
        """Detect pattern type"""
        if latest.get('Fired', False):
            return 'squeeze'
        elif latest.get('Energy_Level', 0) >= 2:
            return 'houyi'
        else:
            return 'squeeze'
    
    def _calculate_stop_loss(self, entry_price: float) -> float:
        """Calculate stop-loss price"""
        return entry_price * (1 - self.config.stop_loss_pct / 100)
    
    def _calculate_take_profit(self, entry_price: float) -> float:
        """Calculate take-profit price"""
        return entry_price * (1 + self.config.take_profit_pct / 100)
    
    def _rank_signals(self, signals: List[StockSignal]) -> List[StockSignal]:
        """Rank signals by strength"""
        signal_priority = {
            SignalType.STRONG_BUY: 5,
            SignalType.BUY: 4,
            SignalType.WATCH: 3,
            SignalType.HOLD: 2,
            SignalType.SELL: 1,
            SignalType.STRONG_SELL: 0,
        }
        
        def score(s: StockSignal) -> float:
            return (
                signal_priority.get(s.signal, 0) * 100 +
                s.momentum * 10 +
                s.energy_level * 5
            )
        
        # Filter by signal type
        allowed_signals = self.config.signal_types
        if 'buy' in allowed_signals:
            allowed_signals.extend(['強烈買入 (爆發)', '買入 (動能增強)'])
        if 'sell' in allowed_signals:
            allowed_signals.extend(['強烈賣出 (跌破)', '賣出 (動能轉弱)'])
        
        filtered = [s for s in signals if s.signal.value in allowed_signals or str(s.signal) in allowed_signals]
        
        return sorted(filtered, key=score, reverse=True)
    
    def get_portfolio_state(
        self,
        positions: List[Dict],
        cash: float,
        current_prices: Dict[str, float]
    ) -> PortfolioState:
        """Calculate current portfolio state"""
        total_value = cash
        unrealized_pnl = 0
        
        for pos in positions:
            ticker = pos['ticker']
            shares = pos['shares']
            entry_price = pos['entry_price']
            
            current_price = current_prices.get(ticker, entry_price)
            position_value = shares * current_price
            total_value += position_value
            
            pnl = (current_price - entry_price) * shares
            unrealized_pnl += pnl
        
        realized_pnl = sum(pos.get('realized_pnl', 0) for pos in positions)
        position_count = len(positions)
        cash_ratio = cash / total_value if total_value > 0 else 1
        
        return PortfolioState(
            cash=cash,
            positions=positions,
            total_value=total_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            position_count=position_count,
            cash_ratio=cash_ratio,
        )
