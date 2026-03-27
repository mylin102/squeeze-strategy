"""
Report generator for daily stock picks.

Generates:
- HTML email reports
- Markdown reports
- Chart attachments
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from jinja2 import Template


def get_china_time() -> datetime:
    """Get current China/Taiwan time"""
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


class ReportGenerator:
    """Generate daily stock pick reports"""
    
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_html_report(
        self,
        buy_signals: List[Dict[str, Any]],
        sell_signals: List[Dict[str, Any]],
        tracking_list: List[Dict[str, Any]],
        market_regime: str = "unknown",
        strategy_name: str = "baseline",
    ) -> str:
        """Generate HTML email report"""
        
        now = get_china_time()
        date_str = now.strftime("%Y-%m-%d %H:%M")
        
        template = Template(self._get_html_template())
        
        # Prepare data for template
        buy_rows = self._prepare_signal_rows(buy_signals[:15])  # Top 15
        sell_rows = self._prepare_signal_rows(sell_signals[:15])
        tracking_rows = self._prepare_tracking_rows(tracking_list[:10])  # Top 10
        
        html = template.render(
            date=date_str,
            strategy=strategy_name,
            market_regime=market_regime,
            buy_count=len(buy_signals),
            sell_count=len(sell_signals),
            tracking_count=len(tracking_list),
            buy_rows=buy_rows,
            sell_rows=sell_rows,
            tracking_rows=tracking_rows,
        )
        
        return html
    
    def _prepare_signal_rows(self, signals: List[Dict]) -> List[Dict]:
        """Prepare signal data for HTML table"""
        rows = []
        for sig in signals:
            signal_display = str(sig.get('signal', ''))
            # Color code signals
            if '強烈買入' in signal_display or '買入' in signal_display:
                color = '#28a745'
            elif '強烈賣出' in signal_display or '賣出' in signal_display:
                color = '#dc3545'
            else:
                color = '#6c757d'
            
            rows.append({
                'ticker': sig.get('ticker', ''),
                'name': sig.get('name', ''),
                'signal': signal_display,
                'signal_color': color,
                'price': f"{sig.get('entry_price', 0):.2f}",
                'momentum': f"{sig.get('momentum', 0):.4f}",
                'energy': str(sig.get('energy_level', 0)),
                'stop_loss': f"{sig.get('stop_loss_price', 0):.2f}" if sig.get('stop_loss_price') else 'N/A',
                'target': f"{sig.get('take_profit_price', 0):.2f}" if sig.get('take_profit_price') else 'N/A',
            })
        return rows
    
    def _prepare_tracking_rows(self, tracking: List[Dict]) -> List[Dict]:
        """Prepare tracking data for HTML table"""
        rows = []
        for t in tracking:
            return_pct = float(t.get('return_pct', 0))
            if return_pct > 0:
                color = '#28a745'
            elif return_pct < 0:
                color = '#dc3545'
            else:
                color = '#6c757d'
            
            rows.append({
                'ticker': t.get('ticker', ''),
                'name': t.get('name', ''),
                'entry_price': f"{t.get('entry_price', 0):.2f}",
                'current_price': f"{t.get('current_price', 0):.2f}",
                'return_pct': f"{return_pct:+.2f}%",
                'return_color': color,
                'days': str(t.get('days_tracked', 0)),
                'signal': t.get('signal', ''),
            })
        return rows
    
    def _get_html_template(self) -> str:
        """Get HTML email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .meta { color: #888; font-size: 14px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #007bff; color: white; padding: 12px 8px; text-align: left; font-weight: 600; }
        td { padding: 10px 8px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }
        .buy-signal { color: #28a745; font-weight: bold; }
        .sell-signal { color: #dc3545; font-weight: bold; }
        .positive { color: #28a745; font-weight: bold; }
        .negative { color: #dc3545; font-weight: bold; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .summary-card { flex: 1; background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #555; font-size: 14px; }
        .summary-card .value { font-size: 24px; font-weight: bold; color: #007bff; }
        .regime { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: 600; }
        .regime-bull { background: #d4edda; color: #155724; }
        .regime-bear { background: #f8d7da; color: #721c24; }
        .regime-range { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Squeeze 每日選股報告</h1>
        <div class="meta">
            報告時間：{{ date }} | 策略：{{ strategy }} | 
            <span class="regime regime-{{ market_regime.split('_')[0] }}">{{ market_regime.replace('_', ' ').title() }}</span>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>買入信號</h3>
                <div class="value">{{ buy_count }}</div>
            </div>
            <div class="summary-card">
                <h3>賣出信號</h3>
                <div class="value">{{ sell_count }}</div>
            </div>
            <div class="summary-card">
                <h3>追蹤中</h3>
                <div class="value">{{ tracking_count }}</div>
            </div>
        </div>
        
        {% if buy_rows %}
        <h2>🟢 買入信號 (Top {{ buy_rows|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>代碼</th>
                    <th>名稱</th>
                    <th>信號</th>
                    <th>進場價</th>
                    <th>動能</th>
                    <th>能量</th>
                    <th>停損</th>
                    <th>目標</th>
                </tr>
            </thead>
            <tbody>
                {% for row in buy_rows %}
                <tr>
                    <td><strong>{{ row.ticker }}</strong></td>
                    <td>{{ row.name }}</td>
                    <td style="color: {{ row.signal_color }}">{{ row.signal }}</td>
                    <td>{{ row.price }}</td>
                    <td>{{ row.momentum }}</td>
                    <td>{{ '⭐' * row.energy|int }}</td>
                    <td>{{ row.stop_loss }}</td>
                    <td>{{ row.target }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        
        {% if sell_rows %}
        <h2>🔴 賣出信號 (Top {{ sell_rows|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>代碼</th>
                    <th>名稱</th>
                    <th>信號</th>
                    <th>進場價</th>
                    <th>動能</th>
                    <th>能量</th>
                </tr>
            </thead>
            <tbody>
                {% for row in sell_rows %}
                <tr>
                    <td><strong>{{ row.ticker }}</strong></td>
                    <td>{{ row.name }}</td>
                    <td style="color: {{ row.signal_color }}">{{ row.signal }}</td>
                    <td>{{ row.price }}</td>
                    <td>{{ row.momentum }}</td>
                    <td>{{ '⭐' * row.energy|int }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        
        {% if tracking_rows %}
        <h2>📊 追蹤清單 (Top {{ tracking_rows|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>代碼</th>
                    <th>名稱</th>
                    <th>進場價</th>
                    <th>現價</th>
                    <th>報酬率</th>
                    <th>天數</th>
                    <th>信號</th>
                </tr>
            </thead>
            <tbody>
                {% for row in tracking_rows %}
                <tr>
                    <td><strong>{{ row.ticker }}</strong></td>
                    <td>{{ row.name }}</td>
                    <td>{{ row.entry_price }}</td>
                    <td>{{ row.current_price }}</td>
                    <td style="color: {{ row.return_color }}">{{ row.return_pct }}</td>
                    <td>{{ row.days }}天</td>
                    <td>{{ row.signal }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px; text-align: center;">
            本報告由 Squeeze Strategy 自動生成 | 投資有風險，入市需謹慎
        </div>
    </div>
</body>
</html>
"""
    
    def generate_markdown_report(
        self,
        buy_signals: List[Dict[str, Any]],
        sell_signals: List[Dict[str, Any]],
        tracking_list: List[Dict[str, Any]],
        market_regime: str = "unknown",
    ) -> str:
        """Generate Markdown report"""
        
        now = get_china_time()
        date_str = now.strftime("%Y-%m-%d %H:%M")
        
        md = f"""# Squeeze 每日選股報告

**報告時間**: {date_str}
**市場狀態**: {market_regime.replace('_', ' ').title()}

---

## 摘要

| 買入信號 | 賣出信號 | 追蹤中 |
|---------|---------|-------|
| {len(buy_signals)} | {len(sell_signals)} | {len(tracking_list)} |

---

## 買入信號 (Top 15)

| 代碼 | 名稱 | 信號 | 進場價 | 動能 | 能量 | 停損 | 目標 |
|------|------|------|--------|------|------|------|------|
"""
        
        for sig in buy_signals[:15]:
            energy_stars = '⭐' * sig.get('energy_level', 0)
            md += f"| {sig.get('ticker', '')} | {sig.get('name', '')} | {sig.get('signal', '')} | {sig.get('entry_price', 0):.2f} | {sig.get('momentum', 0):.4f} | {energy_stars} | {sig.get('stop_loss_price', 'N/A')} | {sig.get('take_profit_price', 'N/A')} |\n"
        
        md += f"""
---

## 賣出信號 (Top 15)

| 代碼 | 名稱 | 信號 | 進場價 | 動能 | 能量 |
|------|------|------|--------|------|------|
"""
        
        for sig in sell_signals[:15]:
            energy_stars = '⭐' * sig.get('energy_level', 0)
            md += f"| {sig.get('ticker', '')} | {sig.get('name', '')} | {sig.get('signal', '')} | {sig.get('entry_price', 0):.2f} | {sig.get('momentum', 0):.4f} | {energy_stars} |\n"
        
        md += f"""
---

## 追蹤清單

| 代碼 | 名稱 | 進場價 | 現價 | 報酬率 | 天數 | 信號 |
|------|------|--------|------|--------|------|------|
"""
        
        for t in tracking_list[:10]:
            return_pct = t.get('return_pct', 0)
            return_str = f"{return_pct:+.2f}%"
            md += f"| {t.get('ticker', '')} | {t.get('name', '')} | {t.get('entry_price', 0):.2f} | {t.get('current_price', 0):.2f} | {return_str} | {t.get('days_tracked', 0)}天 | {t.get('signal', '')} |\n"
        
        md += f"""
---

*本報告由 Squeeze Strategy 自動生成*
"""
        
        return md
    
    def save_report(
        self,
        content: str,
        filename: str,
        report_type: str = "html",
    ) -> Path:
        """Save report to file"""
        today = get_china_time().strftime("%Y-%m-%d")
        filepath = self.output_dir / f"{today}_{filename}.{report_type}"
        
        filepath.write_text(content, encoding='utf-8')
        
        return filepath
