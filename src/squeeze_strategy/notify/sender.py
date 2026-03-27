"""
Notification module for sending reports.

Supports:
- Email (SMTP)
- LINE Notify
"""

from __future__ import annotations

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications with HTML reports"""
    
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        recipients: Optional[List[str]] = None,
    ):
        """
        Initialize email notifier.
        
        Parameters can be passed directly or via environment variables:
        - SMTP_SERVER (default: smtp.gmail.com)
        - SMTP_PORT (default: 587)
        - SMTP_USERNAME
        - SMTP_PASSWORD
        - SMTP_RECIPIENTS (comma-separated)
        """
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')
        
        # Parse recipients
        if recipients:
            self.recipients = recipients
        else:
            recipients_env = os.getenv('SMTP_RECIPIENTS', '')
            self.recipients = [r.strip() for r in recipients_env.split(',') if r.strip()]
        
        self.enabled = bool(self.username and self.password and self.recipients)
        
        if not self.enabled:
            logger.warning("Email notifier not configured. Set SMTP_USERNAME, SMTP_PASSWORD, SMTP_RECIPIENTS")
    
    def send_report(
        self,
        subject: str,
        html_content: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        Send HTML email report.
        
        Parameters:
        -----------
        subject : str
            Email subject
        html_content : str
            HTML content
        attachments : List[str], optional
            List of file paths to attach
        
        Returns:
        --------
        bool : True if sent successfully
        """
        if not self.enabled:
            logger.warning("Email not configured, skipping send")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            
            # Attach HTML
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Attach files
            if attachments:
                for filepath in attachments:
                    self._attach_file(msg, filepath)
            
            # Send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Attach file to email"""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Attachment not found: {filepath}")
            return
        
        with open(path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{path.name}"'
        )
        msg.attach(part)


class LineNotifier:
    """Send LINE Notify messages"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize LINE notifier.
        
        Token can be passed directly or via LINE_TOKEN environment variable.
        """
        self.token = token or os.getenv('LINE_TOKEN')
        self.enabled = bool(self.token)
        
        if not self.enabled:
            logger.warning("LINE notifier not configured. Set LINE_TOKEN")
    
    def send_message(self, message: str) -> bool:
        """
        Send LINE Notify message.
        
        Parameters:
        -----------
        message : str
            Message text (max 1000 characters)
        
        Returns:
        --------
        bool : True if sent successfully
        """
        if not self.enabled:
            logger.warning("LINE not configured, skipping send")
            return False
        
        try:
            url = 'https://notify-api.line.me/api/notify'
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {'message': message}
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                logger.info("LINE message sent successfully")
                return True
            else:
                logger.error(f"LINE API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send LINE message: {e}")
            return False
    
    def send_summary(
        self,
        buy_count: int,
        sell_count: int,
        tracking_count: int,
        top_picks: List[Dict[str, Any]],
        market_regime: str = "unknown",
    ) -> bool:
        """
        Send summary notification.
        
        Parameters:
        -----------
        buy_count : int
            Number of buy signals
        sell_count : int
            Number of sell signals
        tracking_count : int
            Number of active tracking items
        top_picks : List[Dict]
            Top pick signals
        market_regime : str
            Current market regime
        
        Returns:
        --------
        bool : True if sent successfully
        """
        # Format message
        regime_emoji = {
            'bull_trend': '🐂',
            'bear_trend': '🐻',
            'range_bound': '➡️',
        }.get(market_regime.split('_')[0], '📊')
        
        message = f"""{regime_emoji} Squeeze 每日選股快報

📊 市場狀態：{market_regime.replace('_', ' ').title()}

📈 買入信號：{buy_count} 檔
📉 賣出信號：{sell_count} 檔
📋 追蹤中：{tracking_count} 檔

🏆 重點推薦:
"""
        
        for i, pick in enumerate(top_picks[:5], 1):
            ticker = pick.get('ticker', '')
            name = pick.get('name', '')
            signal = pick.get('signal', '')
            message += f"\n{i}. {ticker} {name} - {signal}"
        
        message += "\n\n詳細報告請查看 Email"
        
        return self.send_message(message)


class NotificationManager:
    """Manage multiple notification channels"""
    
    def __init__(self):
        self.email = EmailNotifier()
        self.line = LineNotifier()
    
    def send_daily_report(
        self,
        subject: str,
        html_content: str,
        attachments: Optional[List[str]] = None,
        send_line_summary: bool = True,
        buy_count: int = 0,
        sell_count: int = 0,
        tracking_count: int = 0,
        top_picks: Optional[List[Dict]] = None,
        market_regime: str = "unknown",
    ) -> Dict[str, bool]:
        """
        Send daily report through all channels.
        
        Returns:
        --------
        Dict[str, bool] : Status of each channel
        """
        results = {}
        
        # Send email
        results['email'] = self.email.send_report(subject, html_content, attachments)
        
        # Send LINE summary
        if send_line_summary and self.line.enabled:
            results['line'] = self.line.send_summary(
                buy_count=buy_count,
                sell_count=sell_count,
                tracking_count=tracking_count,
                top_picks=top_picks or [],
                market_regime=market_regime,
            )
        else:
            results['line'] = False
        
        return results
