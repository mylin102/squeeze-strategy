"""
Configuration Loader
載入 YAML 配置文件
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StrategyConfig:
    """策略配置數據類"""
    name: str
    version: str
    description: str
    
    # Entry filters
    min_momentum: float = 0.0
    max_momentum: Optional[float] = None
    min_energy_level: int = 0
    require_squeeze_on: bool = False
    require_fired: bool = False
    min_value_score: Optional[float] = None
    
    # Patterns
    patterns: list = None
    
    # Signal types
    signal_types: list = None
    
    # Exit rules
    stop_loss_pct: float = 15.0
    take_profit_pct: float = 25.0
    holding_days: int = 14
    
    # Position sizing
    position_size_pct: float = 100.0
    max_single_position: float = 10.0
    max_positions: int = 10
    
    # Market regime
    allowed_regimes: Optional[list] = None
    
    # Bear market mode
    bear_market_mode: bool = False
    
    def __post_init__(self):
        if self.patterns is None:
            self.patterns = ['squeeze', 'houyi', 'whale']
        if self.signal_types is None:
            self.signal_types = ['buy']


class ConfigLoader:
    """配置文件載入器"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.strategies_dir = self.config_dir / "strategies"
        self.markets_dir = self.config_dir / "markets"
    
    def load_strategy(self, name: str, version: str = "v1") -> StrategyConfig:
        """
        載入策略配置
        
        Parameters:
        -----------
        name : str
            策略名稱 (e.g., 'baseline', 'balanced')
        version : str
            版本號 (e.g., 'v1')
        
        Returns:
        --------
        StrategyConfig : 策略配置對象
        """
        config_file = self.strategies_dir / f"{name}_{version}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Strategy config not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Extract relevant fields
        entry_filters = data.get('entry_filters', {})
        exit_rules = data.get('exit_rules', {})
        position_sizing = data.get('position_sizing', {})
        
        config = StrategyConfig(
            name=data.get('name', name),
            version=data.get('version', version),
            description=data.get('description', ''),
            
            # Entry filters
            min_momentum=entry_filters.get('min_momentum', 0.0),
            max_momentum=entry_filters.get('max_momentum'),
            min_energy_level=entry_filters.get('min_energy_level', 0),
            require_squeeze_on=entry_filters.get('require_squeeze_on', False),
            require_fired=entry_filters.get('require_fired', False),
            min_value_score=entry_filters.get('min_value_score'),
            
            # Patterns
            patterns=data.get('patterns', ['squeeze', 'houyi', 'whale']),
            
            # Signal types
            signal_types=data.get('signal_types', ['buy']),
            
            # Exit rules
            stop_loss_pct=exit_rules.get('stop_loss_pct', 15.0),
            take_profit_pct=exit_rules.get('take_profit_pct', 25.0),
            holding_days=exit_rules.get('holding_days', 14),
            
            # Position sizing
            position_size_pct=position_sizing.get('position_size_pct', 100.0),
            max_single_position=position_sizing.get('max_single_position', 10.0),
            max_positions=position_sizing.get('max_positions', 10),
            
            # Market regime
            allowed_regimes=data.get('market_regime', {}).get('allowed_regimes'),
        )
        
        return config
    
    def load_sector_classification(self, market: str = 'tw') -> Dict:
        """
        載入產業分類配置
        
        Parameters:
        -----------
        market : str
            市場代碼 ('tw', 'us', 'cn')
        
        Returns:
        --------
        Dict : 產業分類數據
        """
        config_file = self.markets_dir / f"{market}_sectors.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Sector config not found: {config_file}")
        
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    def list_strategies(self) -> list:
        """列出所有可用策略"""
        if not self.strategies_dir.exists():
            return []
        
        strategies = []
        for file in self.strategies_dir.glob("*.yaml"):
            # Extract name and version from filename
            # e.g., baseline_v1.yaml -> ('baseline', 'v1')
            parts = file.stem.rsplit('_', 1)
            if len(parts) == 2:
                strategies.append({
                    'name': parts[0],
                    'version': parts[1],
                    'file': file.name
                })
        
        return strategies
    
    def get_strategy_info(self, name: str, version: str = "v1") -> Dict:
        """獲取策略詳細資訊"""
        config_file = self.strategies_dir / f"{name}_{version}.yaml"
        
        if not config_file.exists():
            return {'error': f'Strategy not found: {name}_{version}'}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return {
            'name': data.get('name'),
            'version': data.get('version'),
            'description': data.get('description'),
            'patterns': data.get('patterns'),
            'holding_days': data.get('exit_rules', {}).get('holding_days'),
            'stop_loss_pct': data.get('exit_rules', {}).get('stop_loss_pct'),
            'take_profit_pct': data.get('exit_rules', {}).get('take_profit_pct'),
        }


# 全域實例
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """獲取全域 ConfigLoader 實例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_strategy_config(name: str, version: str = "v1") -> StrategyConfig:
    """便捷函數：載入策略配置"""
    loader = get_config_loader()
    return loader.load_strategy(name, version)
