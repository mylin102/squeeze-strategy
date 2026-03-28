# 自動交易執行指南

## 📊 概述

本系統提供完整的自動交易功能，從選股到下單全流程自動化。

---

## ⚙️ 使用方式

### 1. 模擬交易 (推薦先測試)

```bash
# 使用最新建議清單執行模擬交易
python3 scripts/auto_execute_trades.py --mode paper --market tw

# 指定建議清單
python3 scripts/auto_execute_trades.py --mode paper \
  --input exports/daily_recommendations_tw_2026-03-28.csv

# 預覽模式 (不下單)
python3 scripts/auto_execute_trades.py --mode paper --dry-run
```

### 2. 實際交易

```bash
# ⚠️ 警告：會實際下單！
python3 scripts/auto_execute_trades.py --mode live --market tw
```

---

## 🔧 參數說明

| 參數 | 說明 | 預設 | 選項 |
|------|------|------|------|
| `--mode` | 交易模式 | paper | paper / live |
| `--market` | 市場代碼 | tw | tw / cn / us |
| `--input` | 建議清單路徑 | 最新檔案 | 檔案路徑 |
| `--dry-run` | 預覽模式 | False | Flag |

---

## 📋 輸出檔案

### 訂單記錄

```
exports/
├── trade_orders_paper_2026-03-28.csv     # 模擬訂單
├── trade_orders_paper_2026-03-28.json    # 模擬訂單詳情
├── trade_orders_live_2026-03-28.csv      # 實際訂單
└── trade_orders_live_2026-03-28.json     # 實際訂單詳情
```

### 訂單格式

```csv
ticker,action,price,quantity,stop_loss,timestamp,status,order_id,filled_price
2330.TW,BUY,1820.0,100,1638.0,2026-03-28T14:00:00+08:00,filled,ORD-20260328140000-2330.TW,1820.0
```

---

## 🏦 券商 API 介接

### 支援券商

| 券商 | 狀態 | 文件 |
|------|------|------|
| 元大證券 | 🔄 開發中 | docs/brokers/yuanta.md |
| 凱基證券 | 🔄 開發中 | docs/brokers/kgi.md |
| 富邦證券 | 🔄 開發中 | docs/brokers/fubon.md |
| 國泰證券 | 🔄 開發中 | docs/brokers/cathay.md |
| 永豐金證券 | 🔄 開發中 | docs/brokers/sinopac.md |

### 自行介接

請參考 `docs/BROKER_API_GUIDE.md` 了解如何自行介接券商 API。

### 範例代碼

```python
# 元大證券範例
from broker_api import YuantaAPI

api = YuantaAPI(
    api_key="your_api_key",
    api_secret="your_api_secret",
    account_id="your_account_id"
)

api.connect()

# 下單
order = api.place_order(
    ticker="2330.TW",
    action="BUY",
    price=1820.0,
    quantity=1000,
    order_type="LIMIT"
)

# 設定停損單
api.place_conditional_order(
    ticker="2330.TW",
    trigger_price=1638.0,
    action="SELL",
    quantity=1000
)
```

---

## ⚠️ 風險管理

### 建議設定

| 參數 | 建議值 | 說明 |
|------|--------|------|
| 單筆最大虧損 | 1000 TWD | 每筆交易最大可承受虧損 |
| 停損比例 | 10% | 建議停損點 |
| 總部位上限 | 10 檔 | 同時持有最大股票數 |
| 總風險暴露 | 100,000 TWD | 總最大可承受虧損 |

### 風險檢查清單

- [ ] 確認帳戶餘額充足
- [ ] 設定停損點
- [ ] 確認單筆風險在可承受範圍
- [ ] 確認總部位不超過上限
- [ ] 確認總風險暴露不超過上限
- [ ] 定期檢視持倉狀況

詳細說明請參考 `docs/RISK_MANAGEMENT.md`

---

## 📝 執行流程

```
1. 生成建議清單
   ↓
2. 載入建議清單
   ↓
3. 連接券商 API
   ↓
4. 執行風險檢查
   ↓
5. 下買入單
   ↓
6. 設定停損單
   ↓
7. 儲存訂單記錄
   ↓
8. 定期檢視持倉
```

---

## 🔍 訂單狀態追蹤

### 檢視訂單

```bash
# 檢視今日訂單
python3 scripts/view_orders.py --date 2026-03-28

# 檢視特定股票訂單
python3 scripts/view_orders.py --ticker 2330.TW

# 檢視未平倉訂單
python3 scripts/view_orders.py --status open
```

### 訂單狀態

| 狀態 | 說明 |
|------|------|
| pending | 等待成交 |
| filled | 已成交 |
| cancelled | 已取消 |
| rejected | 被拒絕 |
| stopped_out | 已停損 |

---

## 📊 績效追蹤

### 檢視持倉績效

```bash
# 檢視目前持倉
python3 scripts/view_positions.py

# 檢視已了結交易
python3 scripts/view_closed_positions.py

# 生成績效報告
python3 scripts/generate_performance_report.py
```

---

## ⚡ 定時任務設定

### 使用 cron (Linux/Mac)

```bash
# 編輯 crontab
crontab -e

# 加入每日執行任務 (台股開盤時間 09:00)
0 9 * * 1-5 cd /path/to/squeeze-strategy && \
  python3 scripts/daily_recommendations.py --market tw && \
  python3 scripts/auto_execute_trades.py --mode paper --market tw
```

### 使用 GitHub Actions

```yaml
# .github/workflows/auto_trade.yml
name: Auto Trading

on:
  schedule:
    - cron: '0 1 * * 1-5'  # 台北時間 09:00

jobs:
  trade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Execute Trades
        run: |
          python3 scripts/daily_recommendations.py --market tw
          python3 scripts/auto_execute_trades.py --mode paper --market tw
```

---

## 🆘 常見問題

### Q1: 模擬交易和實際交易有什麼差別？

**A:** 
- **模擬交易 (paper)**: 不會實際下單，僅記錄訂單資訊，供測試用
- **實際交易 (live)**: 會實際透過券商 API 下單

### Q2: 如何確認訂單已成交？

**A:** 
1. 檢視訂單記錄：`python3 scripts/view_orders.py --status filled`
2. 登入券商 APP 或網站查詢
3. 接收券商通知簡訊/Email

### Q3: 停損單如何設定？

**A:** 
目前需要在券商 APP 或網站手動設定條件單，或參考 `docs/BROKER_API_GUIDE.md` 自行實作 API 介接。

### Q4: 如何停止自動交易？

**A:** 
1. 停止 cron 任務：`crontab -r`
2. 停用 GitHub Actions：在 GitHub 倉庫設定中停用
3. 修改腳本中的 `--mode live` 為 `--mode paper`

---

## 📞 技術支援

如有問題請參考：
- [GitHub Issues](https://github.com/mylin102/squeeze-strategy/issues)
- [完整文件](docs/)

---

## ⚠️ 免責聲明

**使用本系統進行自動交易有風險，請謹慎評估：**

1. 過往績效不代表未來表現
2. 自動交易可能因系統問題產生錯誤
3. 請自行承擔交易風險
4. 建議先用模擬模式充分測試
5. 實際交易前請諮詢專業理財顧問

**本系統不提供投資建議，所有交易決策由使用者自行承擔。**
