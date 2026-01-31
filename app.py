from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE = 'ai_activities.db'

# Notification configuration
CLAWDBOT_WEBHOOK = "http://localhost:8076/webhook"  # Clawdbot Gateway webhook
ENABLE_NOTIFICATIONS = True

def send_notification(message, activity_data=None):
    """Send notification via Clawdbot message tool to Telegram"""
    if not ENABLE_NOTIFICATIONS:
        return
    
    try:
        # Format the notification message
        if activity_data:
            ai_tool = f" using {activity_data.get('ai_tool')}" if activity_data.get('ai_tool') else ""
            project = f" (Project: {activity_data.get('project')})" if activity_data.get('project') else ""
            status_emoji = {"todo": "📋", "in-progress": "⚡", "done": "✅"}.get(activity_data.get('status'), "📌")
            
            notification = f"{status_emoji} **AI Tracker Update**\n\n"
            notification += f"**{message}**\n"
            notification += f"📝 *{activity_data.get('title')}*{ai_tool}{project}\n"
            
            if activity_data.get('description'):
                notification += f"💬 {activity_data.get('description')[:100]}{'...' if len(activity_data.get('description', '')) > 100 else ''}\n"
            
            notification += f"📊 Status: **{activity_data.get('status', 'todo').replace('-', ' ').title()}**"
        else:
            notification = message
        
        # Send directly via Clawdbot subprocess call
        import subprocess
        cmd = [
            'clawdbot', 'message', 'send',
            '--channel', 'telegram', 
            '--message', notification
        ]
        
        # Run in background to avoid blocking the web request
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"📢 Notification queued: {notification[:50]}...")
        
    except Exception as e:
        print(f"❌ Notification failed: {e}")
        pass  # Don't break the app if notifications fail

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            ai_tool TEXT,
            project TEXT,
            status TEXT DEFAULT 'todo',
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/activities', methods=['GET'])
def get_activities():
    conn = get_db()
    activities = conn.execute(
        'SELECT * FROM activities ORDER BY status, position'
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in activities])

@app.route('/api/activities', methods=['POST'])
def create_activity():
    data = request.json
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO activities (title, description, ai_tool, project, status, position)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (data.get('title'), data.get('description'), data.get('ai_tool'),
         data.get('project'), data.get('status', 'todo'), data.get('position', 0))
    )
    activity_id = cursor.lastrowid
    conn.commit()
    
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (activity_id,)).fetchone()
    activity_dict = dict(activity)
    conn.close()
    
    # Send notification for new activity
    send_notification("New activity created!", activity_dict)
    
    return jsonify(activity_dict), 201

@app.route('/api/activities/<int:id>', methods=['PUT'])
def update_activity(id):
    data = request.json
    conn = get_db()
    
    # Get the old activity to detect status changes
    old_activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    old_status = dict(old_activity)['status'] if old_activity else None
    
    conn.execute(
        '''UPDATE activities 
           SET title = ?, description = ?, ai_tool = ?, project = ?, 
               status = ?, position = ?, updated_at = ?
           WHERE id = ?''',
        (data.get('title'), data.get('description'), data.get('ai_tool'),
         data.get('project'), data.get('status'), data.get('position'),
         datetime.now(), id)
    )
    conn.commit()
    
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    activity_dict = dict(activity)
    conn.close()
    
    # Send notification for status changes (drag & drop between columns)
    new_status = data.get('status')
    if old_status and old_status != new_status:
        status_names = {"todo": "To Do", "in-progress": "In Progress", "done": "Done"}
        send_notification(
            f"Activity moved: {status_names.get(old_status, old_status)} → {status_names.get(new_status, new_status)}", 
            activity_dict
        )
    
    return jsonify(activity_dict)

@app.route('/api/activities/<int:id>', methods=['DELETE'])
def delete_activity(id):
    conn = get_db()
    conn.execute('DELETE FROM activities WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/api/activities/reorder', methods=['POST'])
def reorder_activities():
    data = request.json
    conn = get_db()
    for item in data.get('items', []):
        conn.execute(
            'UPDATE activities SET status = ?, position = ?, updated_at = ? WHERE id = ?',
            (item['status'], item['position'], datetime.now(), item['id'])
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/notifications/toggle', methods=['POST'])
def toggle_notifications():
    """Toggle notifications on/off"""
    global ENABLE_NOTIFICATIONS
    ENABLE_NOTIFICATIONS = not ENABLE_NOTIFICATIONS
    return jsonify({'enabled': ENABLE_NOTIFICATIONS})

@app.route('/api/notifications/status', methods=['GET'])
def notification_status():
    """Get notification status"""
    return jsonify({'enabled': ENABLE_NOTIFICATIONS})

@app.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Test notification system"""
    send_notification("🧪 Test notification from AI Activity Tracker!")
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)