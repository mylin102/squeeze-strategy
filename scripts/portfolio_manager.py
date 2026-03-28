#!/usr/bin/env python3
"""
投資組合資金管理系統

追蹤初始資金、持倉、現金、損益變化

Usage:
    python3 scripts/portfolio_manager.py --action init --amount 1000000
    python3 scripts/portfolio_manager.py --action status
    python3 scripts/portfolio_manager.py --action report
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd


class PortfolioManager:
    """投資組合管理器"""
    
    def __init__(self, portfolio_file: str = "exports/portfolio.json"):
        self.portfolio_file = Path(portfolio_file)
        self.portfolio = self.load_portfolio()
    
    def load_portfolio(self) -> Dict[str, Any]:
        """載入投資組合資料"""
        if self.portfolio_file.exists():
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self.create_default_portfolio()
    
    def create_default_portfolio(self) -> Dict[str, Any]:
        """建立預設投資組合"""
        return {
            'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'initial_capital': 1000000.0,  # 預設 100 萬
            'currency': 'TWD',
            'cash': 1000000.0,
            'positions': {},
            'closed_positions': [],
            'daily_records': [],
            'statistics': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'total_return_pct': 0.0,
                'max_drawdown_pct': 0.0,
                'sharpe_ratio': 0.0,
            }
        }
    
    def save_portfolio(self):
        """儲存投資組合"""
        self.portfolio_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(self.portfolio, f, indent=2, ensure_ascii=False)
    
    def initialize(self, amount: float):
        """初始化資金"""
        print(f"💰 初始化投資組合")
        print(f"   初始資金：{amount:,.2f} {self.portfolio['currency']}")
        
        self.portfolio['initial_capital'] = amount
        self.portfolio['cash'] = amount
        self.portfolio['created_at'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        
        self.save_portfolio()
        print(f"   ✅ 已儲存至：{self.portfolio_file}")
    
    def add_position(self, ticker: str, action: str, price: float, 
                    quantity: int, filled_at: str = None):
        """新增持倉"""
        if action != 'BUY':
            return
        
        cost = price * quantity
        
        if self.portfolio['cash'] < cost:
            print(f"⚠️  資金不足！需要 {cost:,.2f}，可用 {self.portfolio['cash']:,.2f}")
            return False
        
        # 扣除現金
        self.portfolio['cash'] -= cost
        
        # 新增持倉
        if ticker not in self.portfolio['positions']:
            self.portfolio['positions'][ticker] = {
                'ticker': ticker,
                'quantity': 0,
                'avg_cost': 0.0,
                'trades': []
            }
        
        pos = self.portfolio['positions'][ticker]
        
        # 計算平均成本
        old_value = pos['avg_cost'] * pos['quantity']
        new_value = cost
        new_qty = pos['quantity'] + quantity
        pos['avg_cost'] = (old_value + new_value) / new_qty if new_qty > 0 else 0.0
        pos['quantity'] = new_qty
        
        # 記錄交易
        trade = {
            'action': action,
            'price': price,
            'quantity': quantity,
            'cost': cost,
            'timestamp': filled_at or datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
        pos['trades'].append(trade)
        
        print(f"📈 買入 {ticker} {quantity}股 @ {price:,.2f}")
        print(f"   成本：{cost:,.2f}")
        print(f"   平均成本：{pos['avg_cost']:,.2f}")
        print(f"   剩餘現金：{self.portfolio['cash']:,.2f}")
        
        self.save_portfolio()
        return True
    
    def remove_position(self, ticker: str, action: str, price: float, 
                       quantity: int, filled_at: str = None):
        """移除持倉（賣出）"""
        if action != 'SELL':
            return
        
        if ticker not in self.portfolio['positions']:
            print(f"⚠️  沒有 {ticker} 的持倉")
            return False
        
        pos = self.portfolio['positions'][ticker]
        
        if pos['quantity'] < quantity:
            print(f"⚠️  持倉不足！持有 {pos['quantity']}，欲賣出 {quantity}")
            return False
        
        # 計算損益
        cost_basis = pos['avg_cost'] * quantity
        proceeds = price * quantity
        pnl = proceeds - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        # 增加現金
        self.portfolio['cash'] += proceeds
        
        # 更新持倉
        pos['quantity'] -= quantity
        if pos['quantity'] == 0:
            # 全部賣出，移到已結算
            closed_pos = {
                **pos,
                'sell_price': price,
                'sell_date': filled_at or datetime.now(timezone(timedelta(hours=8))).isoformat(),
                'pnl': pnl,
                'pnl_pct': pnl_pct
            }
            self.portfolio['closed_positions'].append(closed_pos)
            del self.portfolio['positions'][ticker]
        else:
            # 部分賣出，平均成本不變
            pass
        
        # 更新統計
        self.portfolio['statistics']['total_trades'] += 1
        if pnl > 0:
            self.portfolio['statistics']['winning_trades'] += 1
        else:
            self.portfolio['statistics']['losing_trades'] += 1
        
        self.portfolio['statistics']['total_pnl'] += pnl
        
        print(f"📉 賣出 {ticker} {quantity}股 @ {price:,.2f}")
        print(f"   收入：{proceeds:,.2f}")
        print(f"   成本：{cost_basis:,.2f}")
        print(f"   損益：{pnl:,.2f} ({pnl_pct:+.2f}%)")
        print(f"   剩餘現金：{self.portfolio['cash']:,.2f}")
        
        self.save_portfolio()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """獲取投資組合狀態"""
        # 計算持倉總值
        positions_value = 0.0
        positions_detail = []
        
        for ticker, pos in self.portfolio['positions'].items():
            # 這裡應該要獲取當前價格，暫時用平均成本代替
            current_price = pos['avg_cost']  # TODO: 從 API 獲取
            market_value = current_price * pos['quantity']
            cost_basis = pos['avg_cost'] * pos['quantity']
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            positions_value += market_value
            
            positions_detail.append({
                'ticker': ticker,
                'quantity': pos['quantity'],
                'avg_cost': pos['avg_cost'],
                'current_price': current_price,
                'market_value': market_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct
            })
        
        total_value = self.portfolio['cash'] + positions_value
        total_cost_basis = self.portfolio['initial_capital']
        total_pnl = total_value - total_cost_basis
        total_return_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
        
        return {
            'cash': self.portfolio['cash'],
            'positions_value': positions_value,
            'total_value': total_value,
            'initial_capital': self.portfolio['initial_capital'],
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'positions': positions_detail,
            'closed_count': len(self.portfolio['closed_positions']),
            'statistics': self.portfolio['statistics']
        }
    
    def print_status(self):
        """列印投資組合狀態"""
        status = self.get_status()
        
        print("="*70)
        print("  投資組合狀態")
        print("="*70)
        print()
        print(f"💰 初始資金：{status['initial_capital']:,.2f} {self.portfolio['currency']}")
        print(f"💵 可用現金：{status['cash']:,.2f}")
        print(f"📈 持倉總值：{status['positions_value']:,.2f}")
        print(f"💎 總價值：{status['total_value']:,.2f}")
        print()
        print(f"📊 總損益：{status['total_pnl']:+,.2f} ({status['total_return_pct']:+.2f}%)")
        print()
        
        if status['positions']:
            print("📈 目前持倉:")
            print(f"{'代號':<12} {'數量':>8} {'均價':>12} {'市價':>12} {'價值':>12} {'損益':>12}")
            print("-"*70)
            for pos in status['positions']:
                print(f"{pos['ticker']:<12} {pos['quantity']:>8} {pos['avg_cost']:>12,.2f} "
                      f"{pos['current_price']:>12,.2f} {pos['market_value']:>12,.2f} "
                      f"{pos['unrealized_pnl']:>+12,.2f}")
            print()
        
        print(f"📊 統計數據:")
        stats = status['statistics']
        print(f"   總交易次數：{stats['total_trades']}")
        print(f"   獲利：{stats['winning_trades']} | 虧損：{stats['losing_trades']}")
        print(f"   勝率：{stats['winning_trades']/stats['total_trades']*100:.1f}%" if stats['total_trades'] > 0 else "   勝率：N/A")
        print(f"   總損益：{stats['total_pnl']:+,.2f}")
        print()
        print(f"✅ 已結算交易：{status['closed_count']} 筆")
        print("="*70)
    
    def generate_report(self, output_file: str = None):
        """生成績效報告"""
        if not output_file:
            output_file = f"exports/portfolio_report_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # 建立報告
        report_data = []
        
        # 持倉明細
        for ticker, pos in self.portfolio['positions'].items():
            report_data.append({
                'type': 'position',
                'ticker': ticker,
                'quantity': pos['quantity'],
                'avg_cost': pos['avg_cost'],
                'trades': len(pos['trades'])
            })
        
        # 已結算明細
        for closed in self.portfolio['closed_positions']:
            report_data.append({
                'type': 'closed',
                'ticker': closed.get('ticker', 'N/A'),
                'pnl': closed.get('pnl', 0),
                'pnl_pct': closed.get('pnl_pct', 0),
                'sell_date': closed.get('sell_date', 'N/A')
            })
        
        df = pd.DataFrame(report_data)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"📄 報告已儲存：{output_file}")


def main():
    parser = argparse.ArgumentParser(description='投資組合資金管理')
    parser.add_argument('--action', required=True, 
                       choices=['init', 'status', 'report', 'add', 'remove'],
                       help='操作類型')
    parser.add_argument('--amount', type=float, help='初始金額')
    parser.add_argument('--ticker', type=str, help='股票代號')
    parser.add_argument('--price', type=float, help='價格')
    parser.add_argument('--quantity', type=int, help='數量')
    parser.add_argument('--output', type=str, help='輸出檔案')
    
    args = parser.parse_args()
    
    pm = PortfolioManager()
    
    if args.action == 'init':
        if not args.amount:
            print("❌ 請指定 --amount")
            return 1
        pm.initialize(args.amount)
    
    elif args.action == 'status':
        pm.print_status()
    
    elif args.action == 'report':
        pm.generate_report(args.output)
    
    elif args.action in ['add', 'remove']:
        if not all([args.ticker, args.price, args.quantity]):
            print("❌ 請指定 --ticker, --price, --quantity")
            return 1
        
        action = 'BUY' if args.action == 'add' else 'SELL'
        if action == 'BUY':
            pm.add_position(args.ticker, action, args.price, args.quantity)
        else:
            pm.remove_position(args.ticker, action, args.price, args.quantity)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
