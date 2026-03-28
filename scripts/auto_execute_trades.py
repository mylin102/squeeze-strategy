#!/usr/bin/env python3
"""
自動交易執行腳本

根據每日建議操作名單自動執行交易
支援券商 API 介接 (需自行配置)

Usage:
    python3 scripts/auto_execute_trades.py --mode paper  # 模擬交易
    python3 scripts/auto_execute_trades.py --mode live   # 實際交易
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class TradeExecutor:
    """交易執行器"""
    
    def __init__(self, mode: str = "paper"):
        """
        初始化交易執行器
        
        Parameters:
        -----------
        mode : str
            交易模式：paper (模擬) / live (實際)
        """
        self.mode = mode
        self.api = None
        self.orders = []
        
        if mode == "live":
            print("⚠️  警告：您正在使用實際交易模式！")
            print("   所有訂單將被實際執行！")
            confirm = input("   確定要繼續嗎？(yes/no): ")
            if confirm.lower() != "yes":
                print("   已取消交易")
                sys.exit(0)
        
        print(f"✅ 交易執行器已初始化 (模式：{mode})")
    
    def connect_broker_api(self):
        """連接券商 API"""
        # 根據不同券商實作
        # 範例：元大、凱基、富邦等
        print("📡 連接券商 API...")
        
        # TODO: 實作券商 API 連接
        # 範例代碼：
        # from broker_api import YuantaAPI
        # self.api = YuantaAPI(api_key="...", api_secret="...")
        # self.api.connect()
        
        if self.mode == "paper":
            print("   ✅ 模擬交易模式 - 不實際連接 API")
        else:
            print("   ⚠️  實際交易模式 - 需要實作 API 連接")
            print("   請參考 docs/BROKER_API_GUIDE.md")
    
    def place_order(self, ticker: str, action: str, price: float, 
                   quantity: int, stop_loss: float = None) -> Dict[str, Any]:
        """
        下單
        
        Parameters:
        -----------
        ticker : str
            股票代號
        action : str
            買賣動作：BUY / SELL
        price : float
            下單價格
        quantity : int
            下單數量
        stop_loss : float, optional
            停損價格
        
        Returns:
        --------
        Dict : 訂單資訊
        """
        order = {
            'ticker': ticker,
            'action': action,
            'price': price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'status': 'pending',
            'order_id': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{ticker}",
        }
        
        if self.mode == "paper":
            # 模擬交易
            print(f"   📝 [模擬] {action} {ticker} {quantity}股 @ {price}")
            order['status'] = 'filled'
            order['filled_price'] = price
        else:
            # 實際交易
            print(f"   🚀 [實際] {action} {ticker} {quantity}股 @ {price}")
            # TODO: 實作實際下單
            # response = self.api.place_order(...)
            # order['status'] = response.status
            # order['order_id'] = response.order_id
            order['status'] = 'pending'
        
        self.orders.append(order)
        return order
    
    def execute_recommendations(self, recommendations_file: str):
        """
        執行建議清單
        
        Parameters:
        -----------
        recommendations_file : str
            建議清單 CSV 路徑
        """
        print(f"\n📋 載入建議清單：{recommendations_file}")
        
        df = pd.read_csv(recommendations_file)
        print(f"✅ 載入 {len(df)} 檔股票")
        
        print(f"\n💰 開始執行交易...")
        print(f"   模式：{self.mode.upper()}")
        print(f"   總檔數：{len(df)}")
        print()
        
        for idx, row in df.iterrows():
            ticker = row['ticker']
            entry_price = row['entry_price']
            stop_loss_price = row['stop_loss_price']
            shares = int(row['shares'])
            
            print(f"[{idx+1}/{len(df)}] {ticker}")
            
            # 下買入單
            order = self.place_order(
                ticker=ticker,
                action='BUY',
                price=entry_price,
                quantity=shares,
                stop_loss=stop_loss_price
            )
            
            # 設定停損單 (條件單)
            if stop_loss_price:
                print(f"   🛑 設定停損單：{stop_loss_price}")
                # TODO: 實作條件單
                # self.api.place_conditional_order(...)
        
        print()
        print("="*60)
        print(f"✅ 交易執行完成")
        print(f"   總訂單數：{len(self.orders)}")
        print(f"   成功：{len([o for o in self.orders if o['status'] == 'filled'])}")
        print(f"   失敗：{len([o for o in self.orders if o['status'] == 'failed'])}")
        print("="*60)
        
        # 儲存訂單記錄
        self.save_orders()
        
        return self.orders
    
    def save_orders(self, output_dir: str = "exports"):
        """儲存訂單記錄"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
        
        # 儲存 CSV
        df = pd.DataFrame(self.orders)
        csv_path = output_path / f"trade_orders_{self.mode}_{today}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n📁 訂單記錄已儲存：{csv_path}")
        
        # 儲存 JSON
        json_path = output_path / f"trade_orders_{self.mode}_{today}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.orders, f, indent=2, ensure_ascii=False)
        print(f"📁 訂單詳情已儲存：{json_path}")


def get_latest_recommendations(market: str) -> Optional[str]:
    """獲取最新的建議清單檔案"""
    output_path = Path('exports')
    files = sorted(output_path.glob(f'daily_recommendations_{market}_*.csv'))
    
    if files:
        return str(files[-1])
    else:
        return None


def main():
    parser = argparse.ArgumentParser(description='自動交易執行腳本')
    parser.add_argument('--mode', default='paper', choices=['paper', 'live'],
                       help='交易模式：paper (模擬) / live (實際)')
    parser.add_argument('--market', default='tw', choices=['tw', 'cn', 'us'],
                       help='市場代碼')
    parser.add_argument('--input', type=str, 
                       help='建議清單 CSV 路徑 (預設使用最新檔案)')
    parser.add_argument('--dry-run', action='store_true',
                       help='預覽模式 (不下單)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("  自動交易執行系統")
    print("="*60)
    print()
    
    # 獲取建議清單
    if args.input:
        recommendations_file = args.input
    else:
        recommendations_file = get_latest_recommendations(args.market)
    
    if not recommendations_file:
        print(f"❌ 找不到建議清單檔案")
        print(f"   市場：{args.market.upper()}")
        print(f"   請先執行：python3 scripts/daily_recommendations.py --market {args.market}")
        return 1
    
    print(f"📋 使用建議清單：{recommendations_file}")
    
    # 檢查檔案是否存在
    if not Path(recommendations_file).exists():
        print(f"❌ 檔案不存在：{recommendations_file}")
        return 1
    
    # 建立交易執行器
    executor = TradeExecutor(mode=args.mode)
    
    # 連接券商 API
    executor.connect_broker_api()
    
    # 執行交易
    if args.dry_run:
        print("\n👁️  預覽模式 - 不會實際下單")
        df = pd.read_csv(recommendations_file)
        print(f"\n將執行以下訂單:")
        for idx, row in df.iterrows():
            print(f"  {idx+1}. {row['ticker']}: 買入 {int(row['shares'])}股 @ {row['entry_price']} (停損：{row['stop_loss_price']})")
    else:
        executor.execute_recommendations(recommendations_file)
    
    print()
    print("="*60)
    print("  系統說明")
    print("="*60)
    print()
    print("📖 完整文件:")
    print("   - docs/AUTO_TRADING_GUIDE.md: 自動交易完整指南")
    print("   - docs/BROKER_API_GUIDE.md: 券商 API 介接說明")
    print("   - docs/RISK_MANAGEMENT.md: 風險管理說明")
    print()
    print("⚠️  重要提醒:")
    print("   1. 模擬交易 (paper): 不會實際下單，僅供測試")
    print("   2. 實際交易 (live): 會實際下單，請謹慎使用")
    print("   3. 建議先用模擬模式測試，確認無誤後再使用實際模式")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
