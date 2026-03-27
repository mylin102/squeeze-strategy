"""
Command-line interface for Squeeze Strategy.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .models import Market, StrategyConfig
from .engine import SqueezeStrategy
from .strategies import get_all_strategies, get_strategy_by_name

app = typer.Typer(
    name="squeeze-strategy",
    help="Advanced Squeeze Momentum Stock Selection Strategy"
)
console = Console()


@app.command(name="run")
def run_strategy(
    strategy: str = typer.Option("baseline", "--strategy", "-s", help="Strategy name"),
    market: str = typer.Option("us", "--market", "-m", help="Market: us, tw, cn"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Run stock selection strategy.
    
    Examples:
    
        squeeze-strategy run -s baseline -m us
        
        squeeze-strategy run -s balanced -m tw --output signals.json
    """
    console.print(f"[yellow]Running {strategy} strategy for {market.upper()} market...[/yellow]")
    
    # Get strategy config
    try:
        market_enum = Market(market.lower())
        config = get_strategy_by_name(strategy, market_enum)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    
    # Display config
    _display_strategy_config(config)
    
    console.print(f"\n[green]✓ Strategy loaded successfully![/green]")
    console.print(f"[dim]Ready to scan. Use 'scan' command to find signals.[/dim]")


@app.command(name="scan")
def scan_signals(
    strategy: str = typer.Option("baseline", "--strategy", "-s"),
    market: str = typer.Option("us", "--market", "-m"),
    tickers: Optional[List[str]] = typer.Option(None, "--tickers", "-t"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
):
    """
    Scan for squeeze signals.
    
    Note: Requires data source configuration.
    """
    console.print(f"[yellow]Scanning for signals...[/yellow]")
    
    # Get strategy
    market_enum = Market(market.lower())
    config = get_strategy_by_name(strategy, market_enum)
    
    # Create strategy engine
    engine = SqueezeStrategy(config)
    
    console.print(f"  Strategy: {strategy}")
    console.print(f"  Market: {market.upper()}")
    console.print(f"  Max positions: {config.max_positions}")
    console.print(f"  Stop loss: {config.stop_loss_pct}%")
    console.print(f"  Take profit: {config.take_profit_pct}%")
    
    # Placeholder for actual scanning
    console.print(f"\n[yellow]Data source integration required for live scanning.[/yellow]")
    console.print(f"[dim]See documentation for data source setup.[/dim]")


@app.command(name="strategies")
def list_strategies(
    market: str = typer.Option("us", "--market", "-m"),
):
    """List all available strategies"""
    market_enum = Market(market.lower())
    strategies = get_all_strategies(market_enum)
    
    table = Table(title="Available Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Position %", justify="right")
    table.add_column("Stop Loss", justify="right")
    table.add_column("Take Profit", justify="right")
    table.add_column("Holding Days", justify="right")
    table.add_column("Patterns")
    table.add_column("Description", style="yellow")
    
    descriptions = {
        "baseline": "Best overall performer",
        "balanced": "Squeeze + Whale patterns",
        "conservative": "Lower risk, quality focus",
        "aggressive": "Maximum returns",
        "bear_market": "Defensive for bear markets",
        "scalping": "Short-term trading",
    }
    
    for name, config in strategies.items():
        table.add_row(
            name,
            f"{config.position_size_pct:.0f}%",
            f"{config.stop_loss_pct:.1f}%",
            f"{config.take_profit_pct:.1f}%",
            str(config.holding_days),
            ", ".join(config.patterns),
            descriptions.get(name, ""),
        )
    
    console.print(table)


@app.command(name="backtest")
def run_backtest(
    strategy: str = typer.Option("baseline", "--strategy", "-s"),
    market: str = typer.Option("us", "--market", "-m"),
    start: str = typer.Option("2026-01-01", "--start", help="Start date"),
    end: str = typer.Option("2026-03-28", "--end", help="End date"),
    initial_capital: float = typer.Option(1000000, "--capital", help="Initial capital"),
):
    """
    Run backtest (requires data source).
    """
    console.print(f"[yellow]Backtest requires data source integration.[/yellow]")
    console.print(f"[dim]See squeeze-backtest project for backtesting.[/dim]")


def _display_strategy_config(config: StrategyConfig):
    """Display strategy configuration"""
    config_table = Table(title=f"Strategy: {config.market.value.upper()}")
    config_table.add_column("Parameter", style="cyan")
    config_table.add_column("Value", style="white")
    
    rows = [
        ("Position Size", f"{config.position_size_pct:.0f}%"),
        ("Max Single Position", f"{config.max_single_position:.1f}%"),
        ("Max Positions", str(config.max_positions)),
        ("Stop Loss", f"{config.stop_loss_pct:.1f}%"),
        ("Take Profit", f"{config.take_profit_pct:.1f}%"),
        ("Holding Days", str(config.holding_days)),
        ("Patterns", ", ".join(config.patterns)),
        ("Signal Types", ", ".join(config.signal_types)),
        ("Min Momentum", str(config.min_momentum)),
        ("Min Energy", str(config.min_energy_level)),
        ("Bear Market Mode", "Yes" if config.bear_market_mode else "No"),
    ]
    
    for key, value in rows:
        config_table.add_row(key, value)
    
    console.print(config_table)


if __name__ == "__main__":
    app()
