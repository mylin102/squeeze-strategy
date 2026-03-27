# Squeeze Strategy - 自動化每日選股系統

基於 Squeeze Momentum 策略的自動化每日選股系統，類似 squeeze-tw、squeeze-us、squeeze-cn 的功能。

## 功能特色

- ✅ **自動化掃描**: 每日自動執行選股掃描
- ✅ **多市場支援**: 美股 (US)、台股 (TW)、中國 A 股 (CN)
- ✅ **策略配置**: 6 種預設策略可選
- ✅ **績效追蹤**: 自動追蹤推薦標的 14 天表現
- ✅ **HTML 報表**: 生成美觀的 HTML Email 報表
- ✅ **LINE 通知**: 發送即時通知到 LINE
- ✅ **定時任務**: 支援 cron、systemd、GitHub Actions

## 安裝

```bash
cd /Users/mylin/Documents/mylin102/squeeze-strategy
pip install -e ".[dev]"
```

### 依賴套件

```bash
pip install pandas numpy yfinance jinja2 requests python-dotenv typer rich
```

## 環境設定

### 1. 複製環境變數範例

```bash
cp .env.example .env
```

### 2. 設定 Email (Gmail)

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # 使用應用程式密碼
SMTP_RECIPIENTS=recipient@example.com
```

### 3. 設定 LINE Notify

1. 取得 token: https://notify-bot.line.me/my/
2. 設定到 .env:

```bash
LINE_TOKEN=your_line_token_here
```

## 使用方式

### 手動執行

```bash
# 美股掃描
python3 scripts/daily_stock_picker.py --market us --strategy balanced

# 台股掃描
python3 scripts/daily_stock_picker.py --market tw --strategy baseline

# 列出可用策略
python3 scripts/daily_stock_picker.py --list-strategies

# 關閉通知
python3 scripts/daily_stock_picker.py --market us --no-notify

# 關閉報表匯出
python3 scripts/daily_stock_picker.py --market us --no-export
```

### 自動化設定

#### 方法 1: Cron (Linux/Mac)

```bash
# 編輯 crontab
crontab -e

# 複製範例配置
cat deploy/crontab.example >> ~/.crontab

# 重新載入
crontab -l
```

#### 方法 2: systemd (Linux)

```bash
# 複製服務文件
sudo cp deploy/systemd.example /etc/systemd/system/squeeze-daily.service
sudo cp deploy/systemd.example /etc/systemd/system/squeeze-daily.timer

# 啟用服務
sudo systemctl daemon-reload
sudo systemctl enable squeeze-daily.timer
sudo systemctl start squeeze-daily.timer

# 檢視狀態
sudo systemctl status squeeze-daily.timer
```

#### 方法 3: GitHub Actions

1. 設定 Secrets:
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_RECIPIENTS`
   - `LINE_TOKEN`

2. Workflow 會自動在平日執行

## 輸出檔案

### 報表位置

```
exports/
├── 2026-03-28_daily_report_us.html    # HTML 報表
├── 2026-03-28_daily_report_us.md      # Markdown 報表
└── recommendations.csv                 # 追蹤清單
```

### 日誌位置

```
logs/
├── daily_us.log
├── daily_tw.log
└── weekly.log
```

## 報表內容

### HTML Email 報表

包含：
- 📊 市場狀態 (多頭/空頭/盤整)
- 📈 買入信號 Top 15 (含停損/停利價位)
- 📉 賣出信號 Top 15
- 📋 追蹤清單 (最新 10 筆)
- 🏆 重點推薦

### LINE 通知

```
🐂 Squeeze 每日選股快報

📊 市場狀態：Bull Trend

📈 買入信號：12 檔
📉 賣出信號：5 檔
📋 追蹤中：18 檔

🏆 重點推薦:
1. AAPL Apple - 強烈買入 (爆發)
2. MSFT Microsoft - 買入 (動能增強)
3. NVDA NVIDIA - 強烈買入 (爆發)
...

詳細報告請查看 Email
```

## 追蹤清單

`recommendations.csv` 包含以下欄位：

| 欄位 | 說明 |
|------|------|
| date | 推薦日期 |
| ticker | 股票代碼 |
| name | 股票名稱 |
| entry_price | 進場價 |
| signal | 信號類型 |
| current_price | 當前價 |
| return_pct | 報酬率 |
| strategy_return_pct | 策略報酬率 |
| days_tracked | 追蹤天數 |
| status | 狀態 (tracking/completed) |
| type | 類型 (buy/sell) |
| pattern | 形態 (squeeze/houyi/whale) |
| momentum | 動能 |
| energy_level | 能量等級 |
| stop_loss | 停損價 |
| take_profit | 停利價 |

## 策略選擇

| 市場 | 推薦策略 | 說明 |
|------|---------|------|
| **美股** | `balanced` | squeeze + whale 形態，回測 +199% |
| **台股** | `baseline` | 全形態，回測 +582% |
| **保守** | `conservative` | 高品質過濾，低風險 |
| **空頭** | `bear_market` | 防禦模式，緊停損 |

## 定時任務時間建議

### 美股掃描
- **台灣時間**: 凌晨 4:30 (美股收盤後)
- **美國時間**: 下午 4:30 (收盤後)

### 台股掃描
- **台灣時間**: 下午 5:00 (台股收盤後)

## 故障排除

### Email 發送失敗

```bash
# 檢查 Gmail 應用程式密碼
# https://myaccount.google.com/apppasswords

# 測試 SMTP 連線
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_password')
print('OK')
"
```

### LINE 通知失敗

```bash
# 檢查 token 是否有效
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  https://notify-api.line.me/api/notify \
  -d "message=test"
```

### 數據下載失敗

```bash
# 檢查 yfinance 是否正常
python3 -c "
import yfinance as yf
data = yf.download('AAPL', period='1d')
print(data)
"
```

## 專案結構

```
squeeze-strategy/
├── src/squeeze_strategy/
│   ├── __init__.py
│   ├── models.py              # 數據模型
│   ├── engine.py              # 策略引擎
│   ├── strategies.py          # 策略配置
│   ├── cli.py                 # 命令行工具
│   ├── data/
│   │   ├── loader.py          # 數據下載
│   │   └── tracker.py         # 績效追蹤
│   ├── report/
│   │   └── generator.py       # 報表生成
│   └── notify/
│       └── sender.py          # 通知發送
├── scripts/
│   └── daily_stock_picker.py  # 主自動化腳本
├── deploy/
│   ├── crontab.example        # Cron 配置
│   └── systemd.example        # systemd 配置
├── .github/workflows/
│   └── daily_scan.yml         # GitHub Actions
├── configs/                   # 配置文件
├── exports/                   # 輸出報表
├── logs/                      # 日誌檔案
├── recommendations.csv        # 追蹤清單
├── .env.example               # 環境變數範例
└── README.md                  # 本文件
```

## 與 screener 專案比較

| 功能 | squeeze-strategy | squeeze-tw/us/cn |
|------|-----------------|------------------|
| 自動化 | ✅ 完整 | ✅ 完整 |
| 策略選擇 | ✅ 6 種 | ⚠️ 單一 |
| 跨市場 | ✅ 支援 | ⚠️ 單一市場 |
| 停損/停利 | ✅ 內建 | ⚠️ 部分 |
| 空頭調整 | ✅ 自動 | ⚠️ 手動 |
| 回測整合 | ✅ 緊密 | ⚠️ 獨立 |

## 授權

MIT License

## 相關專案

- [squeeze-backtest](../squeeze-backtest) - 回測框架
- [squeeze-cn-screener](../squeeze-cn-screener) - 中國 A 股篩選
- [squeeze-tw-screener](../squeeze-tw-screener) - 台股篩選
- [squeeze-us-screener](../squeeze-us-screener) - 美股篩選

---

*版本：1.0.0*
*日期：2026-03-28*
