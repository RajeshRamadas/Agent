#!/usr/bin/env python3
"""
Notification System for News Agent
Supports Email, Slack, Discord, Telegram, and Webhook notifications
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
import logging

class NotificationManager:
    """Manages all notification channels for the news agent"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize notification manager
        
        Args:
            config: Notification configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment if not provided
        if not self.config:
            self.load_config_from_env()
    
    def load_config_from_env(self):
        """Load notification config from environment variables"""
        self.config = {
            'email': {
                'enabled': os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('EMAIL_USERNAME', ''),
                'password': os.getenv('EMAIL_PASSWORD', ''),
                'from_email': os.getenv('EMAIL_FROM', ''),
                'to_emails': os.getenv('EMAIL_TO', '').split(',') if os.getenv('EMAIL_TO') else [],
                'use_tls': os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
            },
            'slack': {
                'enabled': os.getenv('SLACK_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
                'channel': os.getenv('SLACK_CHANNEL', '#news'),
                'username': os.getenv('SLACK_USERNAME', 'News Agent'),
                'icon_emoji': os.getenv('SLACK_ICON', ':newspaper:')
            },
            'discord': {
                'enabled': os.getenv('DISCORD_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'webhook_url': os.getenv('DISCORD_WEBHOOK_URL', ''),
                'username': os.getenv('DISCORD_USERNAME', 'News Agent')
            },
            'telegram': {
                'enabled': os.getenv('TELEGRAM_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
            },
            'webhook': {
                'enabled': os.getenv('WEBHOOK_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
                'url': os.getenv('WEBHOOK_URL', ''),
                'headers': json.loads(os.getenv('WEBHOOK_HEADERS', '{}'))
            }
        }
    
    def send_scraping_completed_notification(self, results: Dict):
        """Send notification when scraping cycle completes"""
        try:
            # Prepare message content
            total_articles = results.get('total_new_articles', 0)
            processing_time = results.get('processing_time', 0)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create message
            subject = f"📰 News Scraping Completed - {total_articles} Articles"
            
            message = f"""
📰 **News Scraping Cycle Completed**

🕒 **Time**: {timestamp}
📊 **Articles Found**: {total_articles}
⏱️ **Processing Time**: {processing_time:.1f} seconds
🧠 **Summarization**: {results.get('summarization_method', 'Local')}

**Source Breakdown:**
📈 LiveMint: {len(results.get('livemint', []))} articles
💰 MoneyControl: {len(results.get('moneycontrol', []))} articles
📊 Other Sources: {len(results.get('additional_sources', []))} articles

**Top Headlines:**
"""
            
            # Add top 5 headlines
            all_articles = []
            all_articles.extend(results.get('livemint', [])[:2])
            all_articles.extend(results.get('moneycontrol', [])[:2])
            all_articles.extend(results.get('additional_sources', [])[:1])
            
            for i, article in enumerate(all_articles[:5], 1):
                title = article.get('title', 'Unknown Title')[:60]
                message += f"{i}. {title}...\n"
            
            # Send to all enabled channels
            self.send_to_all_channels(subject, message, results)
            
        except Exception as e:
            self.logger.error(f"Error sending scraping completed notification: {e}")
    
    def send_breaking_news_alert(self, article: Dict):
        """Send urgent notification for breaking news"""
        try:
            title = article.get('title', 'Breaking News')
            summary = article.get('summary', '')
            url = article.get('url', '')
            source = article.get('source', 'Unknown').upper()
            
            subject = f"🚨 BREAKING: {title[:50]}..."
            
            message = f"""
🚨 **BREAKING NEWS ALERT** 🚨

**{title}**

📝 **Summary**: {summary}

📰 **Source**: {source}
🔗 **Link**: {url}

⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Send urgent notification
            self.send_to_all_channels(subject, message, {'urgent': True}, priority='high')
            
        except Exception as e:
            self.logger.error(f"Error sending breaking news alert: {e}")
    
    def send_daily_summary(self, articles: List[Dict], trending_topics: List[Dict]):
        """Send daily summary notification"""
        try:
            total_articles = len(articles)
            timestamp = datetime.now().strftime('%Y-%m-%d')
            
            subject = f"📊 Daily News Summary - {timestamp}"
            
            # Group articles by source
            sources = {}
            for article in articles:
                source = article.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            message = f"""
📊 **Daily News Summary - {timestamp}**

📈 **Total Articles**: {total_articles}
📰 **Sources**: {', '.join([f'{k.title()}({v})' for k, v in sources.items()])}

🔥 **Top Trending Topics:**
"""
            
            # Add trending topics
            for i, topic in enumerate(trending_topics[:5], 1):
                message += f"{i}. {topic['topic']}: {topic['frequency']} mentions\n"
            
            message += "\n📰 **Top Stories:**\n"
            
            # Add top stories
            for i, article in enumerate(articles[:5], 1):
                title = article.get('title', 'Unknown Title')[:50]
                message += f"{i}. {title}...\n"
            
            # Send summary
            self.send_to_all_channels(subject, message, {'type': 'daily_summary'})
            
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")
    
    def send_error_notification(self, error_message: str, context: str = ""):
        """Send error notification"""
        try:
            subject = f"❌ News Agent Error"
            
            message = f"""
❌ **News Agent Error**

🐛 **Error**: {error_message}
📍 **Context**: {context}
⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the logs for more details.
"""
            
            # Send error notification
            self.send_to_all_channels(subject, message, {'type': 'error'}, priority='high')
            
        except Exception as e:
            self.logger.error(f"Error sending error notification: {e}")
    
    def send_to_all_channels(self, subject: str, message: str, data: Dict = None, priority: str = 'normal'):
        """Send notification to all enabled channels"""
        success_count = 0
        
        # Email
        if self.config['email']['enabled']:
            if self.send_email(subject, message, data):
                success_count += 1
        
        # Slack
        if self.config['slack']['enabled']:
            if self.send_slack(subject, message, data):
                success_count += 1
        
        # Discord
        if self.config['discord']['enabled']:
            if self.send_discord(subject, message, data):
                success_count += 1
        
        # Telegram
        if self.config['telegram']['enabled']:
            if self.send_telegram(message, data):
                success_count += 1
        
        # Webhook
        if self.config['webhook']['enabled']:
            if self.send_webhook(subject, message, data):
                success_count += 1
        
        self.logger.info(f"Notification sent to {success_count} channels")
        return success_count > 0
    
    def send_email(self, subject: str, message: str, data: Dict = None) -> bool:
        """Send email notification"""
        try:
            email_config = self.config['email']
            
            if not email_config.get('username') or not email_config.get('to_emails'):
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config.get('from_email', email_config['username'])
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = subject
            
            # Create HTML and plain text versions
            html_message = message.replace('\n', '<br>').replace('**', '<strong>').replace('**', '</strong>')
            
            msg.attach(MIMEText(message, 'plain'))
            msg.attach(MIMEText(f"<html><body><pre>{html_message}</pre></body></html>", 'html'))
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            
            if email_config.get('use_tls', True):
                server.starttls()
            
            server.login(email_config['username'], email_config['password'])
            server.sendmail(msg['From'], email_config['to_emails'], msg.as_string())
            server.quit()
            
            self.logger.info("Email notification sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def send_slack(self, subject: str, message: str, data: Dict = None) -> bool:
        """Send Slack notification"""
        try:
            slack_config = self.config['slack']
            
            if not slack_config.get('webhook_url'):
                return False
            
            # Prepare Slack message
            color = '#ff0000' if data and data.get('urgent') else '#36a64f'
            
            payload = {
                'channel': slack_config.get('channel', '#news'),
                'username': slack_config.get('username', 'News Agent'),
                'icon_emoji': slack_config.get('icon_emoji', ':newspaper:'),
                'attachments': [{
                    'color': color,
                    'title': subject,
                    'text': message,
                    'footer': 'News Agent',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            # Send to Slack
            response = requests.post(
                slack_config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Slack notification sent successfully")
                return True
            else:
                self.logger.error(f"Slack notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def send_discord(self, subject: str, message: str, data: Dict = None) -> bool:
        """Send Discord notification"""
        try:
            discord_config = self.config['discord']
            
            if not discord_config.get('webhook_url'):
                return False
            
            # Prepare Discord message
            color = 0xff0000 if data and data.get('urgent') else 0x36a64f
            
            payload = {
                'username': discord_config.get('username', 'News Agent'),
                'embeds': [{
                    'title': subject,
                    'description': message,
                    'color': color,
                    'footer': {
                        'text': 'News Agent'
                    },
                    'timestamp': datetime.now().isoformat()
                }]
            }
            
            # Send to Discord
            response = requests.post(
                discord_config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                self.logger.info("Discord notification sent successfully")
                return True
            else:
                self.logger.error(f"Discord notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {e}")
            return False
    
    def send_telegram(self, message: str, data: Dict = None) -> bool:
        """Send Telegram notification"""
        try:
            telegram_config = self.config['telegram']
            
            if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
                return False
            
            # Prepare Telegram message
            url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': telegram_config['chat_id'],
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            # Send to Telegram
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Telegram notification sent successfully")
                return True
            else:
                self.logger.error(f"Telegram notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def send_webhook(self, subject: str, message: str, data: Dict = None) -> bool:
        """Send webhook notification"""
        try:
            webhook_config = self.config['webhook']
            
            if not webhook_config.get('url'):
                return False
            
            # Prepare webhook payload
            payload = {
                'timestamp': datetime.now().isoformat(),
                'subject': subject,
                'message': message,
                'data': data or {}
            }
            
            headers = webhook_config.get('headers', {})
            headers.setdefault('Content-Type', 'application/json')
            
            # Send webhook
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if 200 <= response.status_code < 300:
                self.logger.info("Webhook notification sent successfully")
                return True
            else:
                self.logger.error(f"Webhook notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
            return False
    
    def test_all_channels(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}
        test_subject = "🧪 News Agent Test Notification"
        test_message = f"""
🧪 **Test Notification**

This is a test message from the News Agent notification system.

⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ **Status**: All systems operational

If you receive this message, your notification channel is working correctly!
"""
        
        # Test each channel
        if self.config['email']['enabled']:
            results['email'] = self.send_email(test_subject, test_message)
        
        if self.config['slack']['enabled']:
            results['slack'] = self.send_slack(test_subject, test_message)
        
        if self.config['discord']['enabled']:
            results['discord'] = self.send_discord(test_subject, test_message)
        
        if self.config['telegram']['enabled']:
            results['telegram'] = self.send_telegram(test_message)
        
        if self.config['webhook']['enabled']:
            results['webhook'] = self.send_webhook(test_subject, test_message)
        
        return results

# Integration with News Agent
class NotificationIntegrator:
    """Integrates notifications with the news agent"""
    
    def __init__(self, news_agent, notification_manager: NotificationManager):
        self.news_agent = news_agent
        self.notifications = notification_manager
        self.logger = logging.getLogger(__name__)
    
    def setup_automatic_notifications(self):
        """Setup automatic notifications for news agent events"""
        
        # Override the run_complete_scraping_cycle method to add notifications
        original_scraping_method = self.news_agent.run_complete_scraping_cycle
        
        def enhanced_scraping_cycle():
            try:
                # Run original scraping
                results = original_scraping_method()
                
                # Send completion notification
                if results['total_new_articles'] > 0:
                    self.notifications.send_scraping_completed_notification(results)
                
                # Check for breaking news (articles with certain keywords)
                breaking_keywords = ['breaking', 'urgent', 'alert', 'crisis', 'emergency']
                
                all_articles = []
                all_articles.extend(results.get('livemint', []))
                all_articles.extend(results.get('moneycontrol', []))
                all_articles.extend(results.get('additional_sources', []))
                
                for article in all_articles:
                    title_lower = article.get('title', '').lower()
                    if any(keyword in title_lower for keyword in breaking_keywords):
                        self.notifications.send_breaking_news_alert(article)
                        break  # Only send one breaking news alert per cycle
                
                return results
                
            except Exception as e:
                # Send error notification
                self.notifications.send_error_notification(str(e), "Scraping cycle")
                raise
        
        # Replace the method
        self.news_agent.run_complete_scraping_cycle = enhanced_scraping_cycle
    
    def send_daily_summary_if_needed(self):
        """Send daily summary if it's the right time"""
        try:
            # Check if it's time for daily summary (e.g., 9 AM)
            current_hour = datetime.now().hour
            
            if current_hour == 9:  # 9 AM
                articles = self.news_agent.get_recent_summaries(24)
                trending = self.news_agent.get_trending_topics(24, 10)
                
                if articles:
                    self.notifications.send_daily_summary(articles, trending)
                    
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")

# Configuration helper
def create_notification_config_template():
    """Create a template .env file for notification configuration"""
    template = """
# Notification System Configuration
# Copy this to your .env file and configure as needed

# Email Notifications
EMAIL_NOTIFICATIONS_ENABLED=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=news-agent@yourcompany.com
EMAIL_TO=recipient1@example.com,recipient2@example.com
EMAIL_USE_TLS=true

# Slack Notifications
SLACK_NOTIFICATIONS_ENABLED=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#news
SLACK_USERNAME=News Agent
SLACK_ICON=:newspaper:

# Discord Notifications
DISCORD_NOTIFICATIONS_ENABLED=false
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK
DISCORD_USERNAME=News Agent

# Telegram Notifications
TELEGRAM_NOTIFICATIONS_ENABLED=false
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Webhook Notifications
WEBHOOK_NOTIFICATIONS_ENABLED=false
WEBHOOK_URL=https://your-webhook-endpoint.com/notify
WEBHOOK_HEADERS={"Authorization": "Bearer your-token"}
"""
    
    with open('.env.notifications.example', 'w') as f:
        f.write(template)
    
    print("📧 Notification configuration template created: .env.notifications.example")
    print("📝 Copy this to your .env file and configure your notification channels")

def main():
    """Test notification system"""
    print("🔔 NOTIFICATION SYSTEM TEST")
    print("=" * 40)
    
    # Create notification manager
    notification_manager = NotificationManager()
    
    # Test all channels
    print("🧪 Testing all configured notification channels...")
    results = notification_manager.test_all_channels()
    
    print("\n📊 Test Results:")
    for channel, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"   {channel.title()}: {status}")
    
    if not results:
        print("⚠️  No notification channels are enabled")
        print("📝 Configure channels in your .env file")
        
        # Create template
        create_template = input("\n📧 Create notification config template? (y/N): ").lower().strip()
        if create_template == 'y':
            create_notification_config_template()

if __name__ == "__main__":
    main()
