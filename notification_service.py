#!/usr/bin/env python3
"""
AI Activity Tracker - Notification Service
Monitors the notification queue and sends messages via Clawdbot
"""

import time
import json
import os
import subprocess
from datetime import datetime

def send_telegram_notification(message):
    """Send notification via Clawdbot message tool"""
    try:
        # Use clawdbot message tool to send to Telegram
        cmd = [
            'clawdbot', 'message', 'send',
            '--channel', 'telegram',
            '--message', message
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Notification sent: {message[:50]}...")
            return True
        else:
            print(f"❌ Failed to send notification: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Notification timeout")
        return False
    except Exception as e:
        print(f"💥 Notification error: {e}")
        return False

def monitor_notifications():
    """Monitor for notification requests"""
    notification_file = '/tmp/ai_tracker_notification.txt'
    last_modified = 0
    
    print("🔍 Starting AI Tracker notification monitor...")
    
    while True:
        try:
            if os.path.exists(notification_file):
                current_modified = os.path.getmtime(notification_file)
                
                if current_modified > last_modified:
                    # Read and send notification
                    with open(notification_file, 'r') as f:
                        message = f.read().strip()
                    
                    if message:
                        success = send_telegram_notification(message)
                        if success:
                            # Clear the notification file
                            os.remove(notification_file)
                    
                    last_modified = current_modified
            
            time.sleep(2)  # Check every 2 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Notification monitor stopped")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    monitor_notifications()