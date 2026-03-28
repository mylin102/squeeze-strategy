#!/bin/bash
#
# Qwen-Squeeze-Strategy 每日自動選股腳本
# 
# 功能：
# 1. 執行台股、美股、中國 A 股每日選股
# 2. 自動執行模擬交易
# 3. 記錄日誌
# 4. 錯誤處理
#
# 使用方式：
#   ./scripts/run_daily_auto.sh --mode paper
#   ./scripts/run_daily_auto.sh --mode live
#

set -e

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_auto_$(date +%Y-%m-%d).log"
PYTHON="python3"

# 預設參數
MODE="${MODE:-paper}"
MARKET="${MARKET:-tw}"
MAX_POSITIONS="${MAX_POSITIONS:-10}"
MAX_LOSS="${MAX_LOSS:-1000}"
STOP_LOSS="${STOP_LOSS:-10}"

# 建立日誌目錄
mkdir -p "$LOG_DIR"

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# 開始
log "========================================"
log "  Qwen-Squeeze-Strategy 每日自動執行"
log "========================================"
log "  專案目錄：$PROJECT_DIR"
log "  模式：$MODE"
log "  市場：$MARKET"
log "  最大部位：$MAX_POSITIONS"
log "  停損比例：$STOP_LOSS%"
log "========================================"

# 切換到專案目錄
cd "$PROJECT_DIR"

# 步驟 1: 生成每日建議清單
log ""
log "[步驟 1/3] 生成每日建議清單..."
if $PYTHON scripts/daily_recommendations.py \
    --market "$MARKET" \
    --strategy baseline \
    --max-positions "$MAX_POSITIONS" \
    --max-loss "$MAX_LOSS" \
    --stop-loss "$STOP_LOSS" \
    2>&1 | tee -a "$LOG_FILE"; then
    log "✅ 建議清單生成成功"
else
    error "建議清單生成失敗"
    exit 1
fi

# 步驟 2: 執行模擬/實際交易 + 記錄資金變化
log ""
log "[步驟 2/3] 執行交易並記錄資金變化..."

# 讀取建議清單並更新投資組合
RECOMMENDATIONS_FILE=$(ls -t "$PROJECT_DIR/exports/daily_recommendations_${MARKET}_$(date +%Y-%m-%d).csv" 2>/dev/null | head -1)

if [ -n "$RECOMMENDATIONS_FILE" ] && [ -f "$RECOMMENDATIONS_FILE" ]; then
    log "   使用建議清單：$RECOMMENDATIONS_FILE"
    
    # 讀取 CSV 並逐筆更新投資組合
    tail -n +2 "$RECOMMENDATIONS_FILE" | while IFS=',' read -r ticker name entry_price stop_loss_price shares risk_per_share max_loss note; do
        # 買入並記錄
        $PYTHON scripts/portfolio_manager.py --action add \
            --ticker "$ticker" \
            --price "$entry_price" \
            --quantity "$shares" \
            >> "$LOG_FILE" 2>&1
    done
    
    log "✅ 投資組合已更新"
else
    log "⚠️  找不到建議清單，跳過交易執行"
fi

# 步驟 3: 生成投資組合績效報告
log ""
log "[步驟 3/3] 生成投資組合績效報告..."
if $PYTHON scripts/portfolio_manager.py \
    --action status \
    2>&1 | tee -a "$LOG_FILE"; then
    log "✅ 投資組合狀態檢視成功"
    
    # 生成報告
    $PYTHON scripts/portfolio_manager.py --action report >> "$LOG_FILE" 2>&1
else
    log "⚠️  投資組合狀態檢視失敗"
fi

# 完成
log ""
log "========================================"
log "  執行完成！"
log "========================================"
log "  日誌檔案：$LOG_FILE"
log "========================================"

# 輸出今日訂單摘要
if [ -f "$PROJECT_DIR/exports/trade_orders_${MODE}_$(date +%Y-%m-%d).csv" ]; then
    log ""
    log "📊 今日訂單摘要:"
    head -2 "$PROJECT_DIR/exports/trade_orders_${MODE}_$(date +%Y-%m-%d).csv" | tail -1 | cut -d',' -f1,2,3,4 | tee -a "$LOG_FILE"
fi

exit 0
