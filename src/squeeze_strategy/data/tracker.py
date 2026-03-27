"""
Performance tracker for stock recommendations.

Tracks buy and sell recommendations for 14 days.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

TRACKING_COLUMNS = [
    'date', 'ticker', 'name', 'entry_price', 'signal',
    'current_price', 'return_pct', 'strategy_return_pct', 'days_tracked',
    'last_updated', 'status', 'type', 'pattern', 'momentum',
    'prev_momentum', 'energy_level', 'squeeze_on', 'fired',
    'market_regime', 'benchmark_ticker', 'stop_loss', 'take_profit'
]


def normalize_tracking_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize tracking dataframe with default values"""
    if df is None or df.empty:
        return pd.DataFrame(columns=TRACKING_COLUMNS)
    
    normalized = df.copy()
    
    # Default values for optional columns
    defaults = {
        'strategy_return_pct': None,
        'type': 'buy',
        'pattern': 'squeeze',
        'momentum': 0.0,
        'prev_momentum': 0.0,
        'energy_level': 0,
        'squeeze_on': False,
        'fired': False,
        'market_regime': 'unknown',
        'benchmark_ticker': 'SPY',
        'stop_loss': None,
        'take_profit': None,
    }
    
    for column in TRACKING_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = defaults.get(column, None)
    
    # Normalize numeric columns
    normalized['return_pct'] = pd.to_numeric(normalized['return_pct'], errors='coerce').fillna(0.0)
    normalized['strategy_return_pct'] = pd.to_numeric(normalized['strategy_return_pct'], errors='coerce')
    
    # Calculate strategy_return_pct if missing
    missing = normalized['strategy_return_pct'].isna()
    normalized.loc[missing, 'strategy_return_pct'] = normalized.loc[missing].apply(
        lambda row: -row['return_pct'] if row.get('type') == 'sell' else row['return_pct'],
        axis=1,
    )
    
    normalized['days_tracked'] = pd.to_numeric(normalized['days_tracked'], errors='coerce').fillna(0).astype(int)
    normalized['momentum'] = pd.to_numeric(normalized['momentum'], errors='coerce').fillna(0.0)
    normalized['prev_momentum'] = pd.to_numeric(normalized['prev_momentum'], errors='coerce').fillna(0.0)
    normalized['energy_level'] = pd.to_numeric(normalized['energy_level'], errors='coerce').fillna(0).astype(int)
    normalized['squeeze_on'] = normalized['squeeze_on'].apply(lambda x: bool(x) if pd.notna(x) else False)
    normalized['fired'] = normalized['fired'].apply(lambda x: bool(x) if pd.notna(x) else False)
    
    return normalized[TRACKING_COLUMNS]


class PerformanceTracker:
    """
    Tracks Buy and Sell recommendations for 14 days.
    
    Maintains:
    - Active tracking list (latest 25 recommendations)
    - Completed tracking history (for analysis)
    """
    
    def __init__(self, db_path: str = "recommendations.csv"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _get_china_time(self) -> datetime:
        """Get current China/Taiwan time"""
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    
    def _init_db(self):
        """Initialize database file if not exists"""
        if not self.db_path.exists():
            df = pd.DataFrame(columns=TRACKING_COLUMNS)
            df.to_csv(self.db_path, index=False)
            logger.info(f"Initialized tracking database: {self.db_path}")
    
    def _load_db(self) -> pd.DataFrame:
        """Load tracking database"""
        try:
            df = pd.read_csv(self.db_path)
        except Exception:
            self._init_db()
            df = pd.read_csv(self.db_path)
        return normalize_tracking_df(df)
    
    def _save_db(self, df: pd.DataFrame):
        """Save tracking database"""
        df.to_csv(self.db_path, index=False)
    
    def record_recommendations(
        self,
        signals: List[Dict[str, Any]],
        rec_type: str = 'buy',
        max_records: int = 10,
    ):
        """
        Record top recommendations.
        
        Parameters:
        -----------
        signals : List[Dict]
            List of signal dictionaries from strategy scan
        rec_type : str
            'buy' or 'sell'
        max_records : int
            Maximum number of recommendations to record
        """
        if not signals:
            logger.warning("No signals to record")
            return
        
        # Sort by momentum and take top N
        sorted_signals = sorted(
            signals,
            key=lambda x: x.get('momentum', 0),
            reverse=(rec_type == 'buy')
        )[:max_records]
        
        now_str = self._get_china_time().strftime("%Y-%m-%d")
        new_records = []
        
        for signal in sorted_signals:
            new_records.append({
                'date': now_str,
                'ticker': signal.get('ticker'),
                'name': signal.get('name', signal.get('ticker')),
                'entry_price': signal.get('entry_price', signal.get('close', 0)),
                'signal': str(signal.get('signal', '')),
                'current_price': signal.get('entry_price', signal.get('close', 0)),
                'return_pct': 0.0,
                'strategy_return_pct': 0.0,
                'days_tracked': 0,
                'last_updated': now_str,
                'status': 'tracking',
                'type': rec_type,
                'pattern': signal.get('pattern', 'squeeze'),
                'momentum': signal.get('momentum', 0.0),
                'prev_momentum': signal.get('prev_momentum', 0.0),
                'energy_level': signal.get('energy_level', 0),
                'squeeze_on': signal.get('squeeze_on', False),
                'fired': signal.get('fired', False),
                'market_regime': signal.get('market_regime', 'unknown'),
                'benchmark_ticker': signal.get('benchmark_ticker', 'SPY'),
                'stop_loss': signal.get('stop_loss_price'),
                'take_profit': signal.get('take_profit_price'),
            })
        
        # Load existing data
        df_old = self._load_db()
        
        # Add new records
        df_new = pd.DataFrame(new_records)
        if df_old.empty:
            df_combined = df_new.copy()
        else:
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        
        # Remove duplicates
        df_combined = df_combined.drop_duplicates(
            subset=['date', 'ticker', 'type', 'pattern'],
            keep='last',
        )
        
        # Limit active tracking to 25
        df_combined['date_dt'] = pd.to_datetime(df_combined['date'], errors='coerce')
        active = df_combined[df_combined['status'] == 'tracking'].sort_values(
            by=['date_dt', 'ticker'],
            ascending=[False, True],
        )
        completed = df_combined[df_combined['status'] != 'tracking']
        active = active.head(25)
        df_combined = pd.concat([active, completed], ignore_index=True)
        df_combined = df_combined.drop(columns=['date_dt'])
        
        # Save
        df_combined = normalize_tracking_df(df_combined)
        self._save_db(df_combined)
        
        logger.info(f"Recorded {len(new_records)} {rec_type} signals")
    
    def update_performance(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Update performance for all active tracking items.
        
        Parameters:
        -----------
        current_prices : Dict[str, float]
            Current prices for tracked tickers
        
        Returns:
        --------
        List[Dict] : Updated tracking records
        """
        df = self._load_db()
        
        if df.empty:
            return []
        
        # Get active tracking items
        active = df[df['status'] == 'tracking'].copy()
        
        if active.empty:
            return []
        
        now = self._get_china_time()
        now_str = now.strftime("%Y-%m-%d")
        
        # Skip if already updated today
        active = active[active['last_updated'] != now_str]
        
        if active.empty:
            return []
        
        results = []
        
        for index, row in active.iterrows():
            ticker = row['ticker']
            
            if ticker not in current_prices:
                continue
            
            price_now = current_prices[ticker]
            entry_price = float(row['entry_price'])
            
            # Calculate returns
            return_pct = ((price_now - entry_price) / entry_price) * 100
            strategy_return_pct = -return_pct if row.get('type') == 'sell' else return_pct
            
            # Calculate days tracked
            rec_date = datetime.strptime(row['date'], "%Y-%m-%d").replace(
                tzinfo=timezone(timedelta(hours=8))
            )
            days_passed = (now - rec_date).days
            
            # Update record
            df.at[index, 'current_price'] = price_now
            df.at[index, 'return_pct'] = return_pct
            df.at[index, 'strategy_return_pct'] = strategy_return_pct
            df.at[index, 'days_tracked'] = days_passed
            df.at[index, 'last_updated'] = now_str
            
            # Mark as completed after 14 days
            if days_passed >= 14:
                df.at[index, 'status'] = 'completed'
            
            results.append(df.loc[index].to_dict())
        
        # Save updates
        self._save_db(df)
        
        logger.info(f"Updated performance for {len(results)} active trackers")
        
        return results
    
    def get_active_list(self, rec_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active tracking list"""
        df = self._load_db()
        
        if df.empty:
            return []
        
        mask = df['status'] == 'tracking'
        
        if rec_type:
            if 'type' in df.columns:
                mask = mask & (df['type'] == rec_type)
            elif rec_type == 'buy':
                pass  # All legacy are buy
            else:
                return []
        
        active = df[mask].sort_values(by='date', ascending=False).head(25)
        return active.to_dict('records')
    
    def get_summary(self) -> Dict[str, Any]:
        """Get tracking summary"""
        df = self._load_db()
        
        if df.empty:
            return {
                'total_records': 0,
                'active_records': 0,
                'completed_records': 0,
                'avg_return_pct': 0.0,
            }
        
        active = df[df['status'] == 'tracking']
        completed = df[df['status'] == 'completed']
        
        avg_return = completed['strategy_return_pct'].mean() if len(completed) > 0 else 0.0
        win_rate = (completed['strategy_return_pct'] > 0).mean() * 100 if len(completed) > 0 else 0.0
        
        return {
            'total_records': len(df),
            'active_records': len(active),
            'completed_records': len(completed),
            'avg_return_pct': float(avg_return) if not pd.isna(avg_return) else 0.0,
            'win_rate_pct': float(win_rate) if not pd.isna(win_rate) else 0.0,
        }
