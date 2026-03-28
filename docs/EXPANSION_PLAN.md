# Squeeze Strategy 股票清單擴大執行計劃

## 📊 目標

擴大 CN 和 US 市場的股票清單，提升選股覆蓋率。

---

## 🎯 目標數量

| 市場 | 目前數量 | 目標數量 | 來源 |
|------|---------|---------|------|
| **TW** | 100 檔 | 100 檔 | ✅ 已完成 |
| **CN** | 651 檔 | **300 檔** (滬深 300) | 手動整理 |
| **US** | 146 檔 | **300 檔** (S&P 300) | 手動整理 |

---

## 🔄 V-Cycle 驗證計劃

### 左側：需求分解

```
用戶需求
├── CN 和 US 股票數量需要擴大
├── 避免反覆偵錯
└── 需要清晰的執行計劃

功能需求
├── TW: 100 檔 ✓
├── CN: 300 檔 (滬深 300)
└── US: 300 檔 (S&P 300)

技術需求
├── 配置文件格式：INI
├── 自動去重機制
└── 向後兼容（fallback）
```

### 右側：驗證計劃

```
單元測試
├── 配置文件可讀取
├── 無重複項目
└── 股票數量正確

整合測試
├── TickerUniverse 可載入
├── get_tickers() 返回正確數量
└── 無錯誤訊息

系統測試
├── daily_recommendations.py 可執行
├── 輸出檔案正確命名
└── 不會互相覆蓋
```

---

## 📝 執行步驟

### Step 1: 準備股票清單資料

#### CN 市場 (滬深 300)
- [ ] 收集滬深 300 成份股
- [ ] 整理股票代碼和名稱
- [ ] 移除重複項目

#### US 市場 (S&P 300)
- [ ] 收集 S&P 300 成份股
- [ ] 整理股票代碼和名稱
- [ ] 移除重複項目

### Step 2: 建立配置文件

#### CN 配置文件
```ini
# configs/markets/cn_stocks_300.ini
[stocks]
600519.SS = 貴州茅台
000001.SZ = 平安銀行
...
```

#### US 配置文件
```ini
# configs/markets/us_stocks_300.ini
[stocks]
AAPL = Apple Inc
MSFT = Microsoft Corp
...
```

### Step 3: 更新 loader.py

```python
def _load_cn_universe(self) -> Dict[str, str]:
    """Load China A-share universe - 300 stocks"""
    # 讀取 cn_stocks_300.ini

def _load_us_universe(self) -> Dict[str, str]:
    """Load US stock universe - 300 stocks"""
    # 讀取 us_stocks_300.ini
```

### Step 4: 單元測試

```bash
# 測試配置文件可讀取
python3 -c "from squeeze_strategy.data.loader import TickerUniverse; u = TickerUniverse('cn'); print(len(u.get_tickers()))"
python3 -c "from squeeze_strategy.data.loader import TickerUniverse; u = TickerUniverse('us'); print(len(u.get_tickers()))"
```

### Step 5: 整合測試

```bash
# 測試各市場股票數量
python3 << 'EOF'
from squeeze_strategy.data.loader import TickerUniverse
for market in ['tw', 'cn', 'us']:
    u = TickerUniverse(market)
    tickers = u.get_tickers()
    print(f'{market.upper()}: {len(tickers)} 檔')
EOF
```

### Step 6: 系統測試

```bash
# 測試各市場推薦清單生成
python3 scripts/daily_recommendations.py --market tw --max-positions 5
python3 scripts/daily_recommendations.py --market cn --max-positions 5
python3 scripts/daily_recommendations.py --market us --max-positions 5

# 檢查輸出檔案
ls -lh exports/daily_recommendations_*.csv
```

### Step 7: 提交

```bash
git add -A
git commit -m "feat: Expand stock universe to 300 stocks per market"
git push origin main
```

---

## 📋 驗收標準

- [ ] TW: 100 檔 ✓
- [ ] CN: 300 檔 (誤差 ±10)
- [ ] US: 300 檔 (誤差 ±10)
- [ ] 配置文件無重複
- [ ] 所有測試通過
- [ ] 系統正常運作

---

## 🚀 tmux 並行執行計劃

### Session: stock-expansion

```
Window 1: CN Market
├── Pane 1: 收集滬深 300 清單
├── Pane 2: 建立 cn_stocks_300.ini
└── Pane 3: 測試 CN 載入

Window 2: US Market
├── Pane 1: 收集 S&P 300 清單
├── Pane 2: 建立 us_stocks_300.ini
└── Pane 3: 測試 US 載入

Window 3: Integration
├── Pane 1: 整合測試
├── Pane 2: 系統測試
└── Pane 3: Git 提交
```

---

## 📅 時程預估

| 步驟 | 預估時間 | 備註 |
|------|---------|------|
| Step 1: 準備清單 | 30 分鐘 | 並行執行 |
| Step 2: 建立配置 | 15 分鐘 | 並行執行 |
| Step 3: 更新程式碼 | 10 分鐘 | |
| Step 4: 單元測試 | 5 分鐘 | |
| Step 5: 整合測試 | 10 分鐘 | |
| Step 6: 系統測試 | 10 分鐘 | |
| Step 7: 提交 | 5 分鐘 | |
| **總計** | **約 85 分鐘** | 並行後約 50 分鐘 |

---

## ⚠️ 風險管理

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 配置文件有重複 | 載入失敗 | 自動去重腳本 |
| 股票代碼錯誤 | 數據下載失敗 | 驗證代碼格式 |
| 名稱編碼問題 | 顯示亂碼 | 使用 UTF-8 編碼 |
| 網路問題 | API 失敗 | 使用離線配置文件 |

---

## 📞 聯絡資訊

如有問題，請隨時提出！
