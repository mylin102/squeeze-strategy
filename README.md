# Squeeze Strategy - 進階選股策略系統

基於全面回測分析的進階 Squeeze Momentum 選股系統。

## 特色功能

- **經過驗證的策略**: 基於 2026/01-03 期間的回測結果
- **動態市場調整**: 自動偵測空頭市場並調整策略
- **最佳停損設定**: 採用回測最優的 10% 固定停損
- **多市場支援**: 支援美股 (US)、台股 (TW)、中國 A 股 (CN)
- **全面覆蓋**: 支援 **1,212+ 檔股票** (TW: 219 檔，CN: 651 檔，US: 342 檔)
- **上市/上櫃支援**: 台股包含上市 (.TW) 和上櫃 (.TWO) 股票

## 安裝

```bash
cd /Users/mylin/Documents/mylin102/squeeze-strategy
pip install -e .
```

## 快速開始

### 1. 檢視可用策略

```bash
squeeze-strategy strategies
squeeze-strategy strategies -m tw  # 台股策略
```

### 2. 執行選股

```bash
# 使用基準策略
squeeze-strategy run -s baseline -m us

# 使用平衡策略 (美股最佳)
squeeze-strategy run -s balanced -m us

# 使用保守策略
squeeze-strategy run -s conservative -m tw
```

### 3. 掃描信號

```bash
squeeze-strategy scan -s baseline -m us
squeeze-strategy scan -s balanced -m tw --tickers 2330.TW 2317.TW
```

## 可用策略

### 策略比較

| 策略 | 適用市場 | 部位 | 停損 | 停利 | 持有期 | 特點 |
|------|---------|------|------|------|--------|------|
| `baseline` | US/TW | 100% | 10% | 25% | 14 天 | 最佳整體表現 |
| `balanced` | US | 100% | 10% | 20% | 14 天 | 美股最佳 (+199%) |
| `conservative` | 全部 | 60% | 8% | 18% | 10 天 | 低風險 |
| `aggressive` | 全部 | 100% | 15% | 35% | 14 天 | 高報酬 |
| `bear_market` | 全部 | 40% | 6% | 12% | 6 天 | 空頭防禦 |
| `scalping` | 全部 | 80% | 5% | 10% | 5 天 | 短線當沖 |

### 策略詳情

#### baseline (基準策略)
- **回測表現**: US +177-367%, TW +582%
- **特點**: 無額外過濾器，涵蓋最廣
- **適用**: 所有市場環境

#### balanced (平衡策略)
- **回測表現**: US +199.81%
- **特點**: 結合 squeeze + whale 形態
- **適用**: 美股市場

#### conservative (保守策略)
- **特點**: 高品質過濾，緊停損
- **適用**: 風險規避型投資者

#### bear_market (空頭市場策略)
- **特點**: 降低部位、緊停損、短持有
- **適用**: 空頭市場環境

## 股票清單

### 覆蓋範圍

| 市場 | 股票數量 | 組成 | 說明 |
|------|---------|------|------|
| **TW (台灣)** | **219 檔** | 95 檔上市 (.TW) + 124 檔上櫃 (.TWO) | 台灣 50 + 熱門上櫃 |
| **CN (中國)** | **651 檔** | 滬深 300 + 成長股 | A 股主要成份股 |
| **US (美國)** | **342 檔** | S&P 300 + 科技股 | 美股主要成份股 |
| **總計** | **1,212 檔** | - | 全球主要市場 |

### 台股詳細組成

```
上市股票 (.TW) - 95 檔:
├── 台灣 50 核心：台積電、鴻海、聯發科...
├── 金融：富邦金、國泰金、開發金...
├── 傳產：台塑、南亞、台化、中鋼...
└── 電子：華碩、宏碁、廣達、仁寶...

上櫃股票 (.TWO) - 124 檔:
├── 半導體：世芯-KY、信驊、穩懋...
├── 電子零組件：華新科、威剛、欣銓...
├── 生技醫療：神隆、國光生、東洋...
└── 科技服務：緯穎、漢唐、帆宣...
```

### 股票選擇邏輯

詳細說明請參考：[股票選擇邏輯說明](docs/STOCK_SELECTION_LOGIC.md)

**主要標準**:
1. **市值排名** (40%): 選擇各市場市值最大的公司
2. **指數成份股** (30%): 參考主要指數 (TW50, CSI300, S&P300)
3. **流動性** (20%): 日均交易量 > 門檻
4. **產業代表性** (10%): 涵蓋各主要產業

## 策略配置

### 多頭市場配置

```python
{
    "position_size": 100%,
    "stop_loss": 10%,
    "take_profit": 25%,
    "holding_days": 14,
    "patterns": ["squeeze", "houyi", "whale"],
    "signal_types": ["buy"],
}
```

### 空頭市場配置

```python
{
    "position_size": 40%,
    "stop_loss": 6%,
    "take_profit": 12%,
    "holding_days": 6,
    "patterns": ["squeeze"],
    "signal_types": ["sell"],
}
```

## 程式庫使用

```python
from squeeze_strategy import SqueezeStrategy, StrategyConfig, Market
from squeeze_strategy.strategies import get_baseline_strategy

# 建立策略
config = get_baseline_strategy(Market.US)
engine = SqueezeStrategy(config)

# 更新市場狀態
engine.update_market_regime(benchmark_data)

# 掃描信號
signals = engine.scan_signals(stock_data, ticker_names)

# 處理信號
for signal in signals:
    print(f"{signal.ticker}: {signal.signal.value}")
    print(f"  Stop Loss: {signal.stop_loss_price}")
    print(f"  Take Profit: {signal.take_profit_price}")
```

## 回測結果摘要

### 最佳策略

| 市場 | 最佳策略 | 總報酬 | Sharpe | 勝率 |
|------|---------|--------|--------|------|
| US | balanced | +199.81% | 1.72 | 47.5% |
| TW | baseline | +582.53% | 4.72 | 55.4% |

### 最佳停損

| 停損類型 | 總報酬 | 停損率 | Sharpe |
|---------|--------|-------|--------|
| fixed_10pct | +242.77% | 5.0% | 2.02 |
| no_stop | +238.66% | 0.0% | 1.94 |
| fixed_20pct | +238.66% | 0.0% | 1.94 |

## 檔案結構

```
squeeze-strategy/
├── src/squeeze_strategy/
│   ├── __init__.py       # 套件初始化
│   ├── models.py         # 數據模型
│   ├── engine.py         # 策略引擎
│   ├── strategies.py     # 預設策略配置
│   └── cli.py            # 命令行工具
├── strategies/           # 自定義策略
├── configs/             # 配置文件
├── reports/             # 報告輸出
├── backtests/           # 回測結果
├── exports/             # 匯出檔案
├── pyproject.toml
└── README.md
```

## 與回測框架整合

本專案與 `squeeze-backtest` 緊密整合：

```bash
# 1. 在 backtest 中測試策略
cd ../squeeze-backtest
PYTHONPATH=src python3 scripts/compare_all_strategies.py

# 2. 將最佳策略應用到 strategy
cd ../squeeze-strategy
squeeze-strategy run -s balanced -m us
```

## 注意事項

### 數據來源
本專案需要外部數據源支援：
- yfinance (美股、台股)
- 其他市場數據 API

### 風險管理
- 停損僅供參考，實際執行需考慮滑點
- 空頭市場自動調整功能需正確設定基準指數
- 建議先進行回測再實際使用

## 開發與測試

```bash
# 安裝開發依賴
pip install -e ".[dev]"

# 執行測試
pytest tests/
```

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
