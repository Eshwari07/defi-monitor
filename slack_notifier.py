"""
Slack integration for sending alerts.

Configure SLACK_WEBHOOK_URL in your environment or .env file.
"""
import logging
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Sends alert notifications to Slack."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', None)
    
    async def send_alert(
        self,
        protocol_name: str,
        alert_type: str,
        severity: str,
        message: str
    ) -> bool:
        """
        Send an alert to Slack.
        
        Args:
            protocol_name: Protocol that triggered the alert
            alert_type: Type of alert (tvl_drop, apy_low, utilization_high)
            severity: Alert severity (critical, warning, info)
            message: Alert message
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured, skipping notification")
            return False
        
        # Choose emoji based on severity
        emoji = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }.get(severity, "📊")
        
        # Choose color based on severity
        color = {
            "critical": "#ff4757",
            "warning": "#ffcc00",
            "info": "#00d9ff"
        }.get(severity, "#00ff88")
        
        # Build Slack message
        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} {severity.upper()} Alert: {protocol_name.upper()}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Alert Type:*\n{alert_type.replace('_', ' ').title()}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Protocol:*\n{protocol_name}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Details:*\n{message}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "🤖 DeFi Protocol Monitor"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.webhook_url, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"Slack notification sent for {protocol_name}/{alert_type}")
                    return True
                else:
                    logger.error(f"Slack API error: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error("Timeout sending Slack notification")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    async def send_summary(self, protocols: list, alerts_count: int) -> bool:
        """
        Send a daily summary to Slack.
        
        Args:
            protocols: List of protocol status dicts
            alerts_count: Number of active alerts
            
        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            return False
        
        # Build protocol summary
        protocol_lines = []
        for p in protocols:
            status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}.get(p.get("status", ""), "⚪")
            tvl = p.get("tvl", 0)
            tvl_str = f"${tvl/1e6:.1f}M" if tvl else "N/A"
            protocol_lines.append(f"{status_emoji} *{p['name'].upper()}*: TVL {tvl_str}")
        
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Protocol Health Summary",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n".join(protocol_lines) if protocol_lines else "No protocols monitored"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Active Alerts:* {alerts_count}"
                    }
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Slack summary: {e}")
            return False


# Convenience function for quick alerts
async def notify_slack(
    protocol_name: str,
    alert_type: str,
    severity: str,
    message: str,
    webhook_url: Optional[str] = None
) -> bool:
    """Send a quick Slack notification."""
    notifier = SlackNotifier(webhook_url)
    return await notifier.send_alert(protocol_name, alert_type, severity, message)
