from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import sqlite3
import os
import csv
import io
import subprocess
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE = 'ai_activities.db'
ENABLE_NOTIFICATIONS = os.environ.get('AI_TRACKER_NOTIFICATIONS', 'true').lower() == 'true'
SERVER_PORT = int(os.environ.get('AI_TRACKER_PORT', '8080'))
AUTO_EXECUTE = os.environ.get('AI_TRACKER_AUTO_EXECUTE', 'true').lower() == 'true'
NOTIFICATION_CHANNEL = os.environ.get('AI_TRACKER_NOTIFICATION_CHANNEL', 'telegram')

# Integration settings
CLAWDBOT_TIMEOUT = 30  # seconds for Clawdbot operations
SESSION_CLEANUP_POLICY = 'keep'  # keep sessions for debugging
DEFAULT_BROWSER = 'Safari'  # macOS default

def execute_task_via_clawdbot(activity_data):
    """Enhanced task execution using full Clawdbot capabilities with proper tool routing"""
    try:
        title = activity_data.get('title', '')
        description = activity_data.get('description', '')
        ai_tool = activity_data.get('ai_tool', '')
        project = activity_data.get('project', '')
        task_id = activity_data.get('id')
        
        # Enhanced capability detection from description
        capabilities = {
            'browser': None,
            'needs_nodes': False,
            'needs_canvas': False,
            'file_operations': False,
            'system_commands': False,
            'screenshot': False,
            'location': False
        }
        
        desc_lower = description.lower()
        
        # Browser detection with profile preferences
        if any(browser in desc_lower for browser in ['chrome', 'google']):
            capabilities['browser'] = 'chrome'
        elif 'safari' in desc_lower:
            capabilities['browser'] = 'safari'
        elif 'firefox' in desc_lower:
            capabilities['browser'] = 'firefox'
        
        # Capability detection
        if any(word in desc_lower for word in ['screenshot', 'capture', 'snap']):
            capabilities['screenshot'] = True
        if any(word in desc_lower for word in ['file', 'create', 'write', 'save']):
            capabilities['file_operations'] = True
        if any(word in desc_lower for word in ['node', 'phone', 'mobile', 'camera']):
            capabilities['needs_nodes'] = True
        if any(word in desc_lower for word in ['present', 'canvas', 'display', 'show']):
            capabilities['needs_canvas'] = True
        if any(word in desc_lower for word in ['terminal', 'command', 'exec', 'run']):
            capabilities['system_commands'] = True
        if any(word in desc_lower for word in ['location', 'gps', 'where', 'address']):
            capabilities['location'] = True
        
        # Create enhanced task execution prompt
        task_prompt = f"""
🤖 AI ACTIVITY TRACKER - AUTOMATED TASK EXECUTION

📋 TASK CONTEXT:
• Title: {title}
• Project: {project or 'General'}
• Requested AI Tool: {ai_tool}
• Task ID: {task_id}
• Full Description: {description}

🎯 EXECUTION STRATEGY:
"""
        
        # Add tool-specific guidance
        if capabilities['browser']:
            if capabilities['browser'] == 'safari':
                task_prompt += """
🌐 BROWSER TASK (Safari Required):
• Use Safari specifically: open -a Safari "URL"  
• Do not use browser tool - use direct Safari commands
• For web automation, consider using AppleScript if needed
"""
            elif capabilities['browser'] == 'chrome':
                task_prompt += """
🌐 BROWSER TASK (Chrome Required):
• Use Chrome specifically: open -a "Google Chrome" "URL"
• Alternative: Use browser tool with profile="chrome"
• Can use Clawdbot browser extension if available
"""
        
        if capabilities['screenshot']:
            task_prompt += """
📸 SCREENSHOT TASK:
• Use screencapture command: screencapture -c (to clipboard)
• Or: screencapture ~/Desktop/screenshot.png (to file)
• Consider nodes tool if mobile device screenshot needed
"""
        
        if capabilities['file_operations']:
            task_prompt += """
📁 FILE OPERATIONS:
• Use appropriate commands: touch, echo, cat, mkdir
• Consider write tool for complex file operations
• Save to appropriate directory (~/Desktop, ~/Documents, etc.)
"""
        
        if capabilities['needs_nodes']:
            task_prompt += """
📱 NODE CAPABILITIES NEEDED:
• Use nodes tool for mobile/device interactions
• Available: camera_snap, screen_record, location_get
• Check nodes status first: nodes status
"""
        
        if capabilities['needs_canvas']:
            task_prompt += """
🖥️ CANVAS PRESENTATION:
• Use canvas tool for displaying content
• Consider canvas present for visual presentations
• Can snapshot canvas for documentation
"""
        
        # Add completion callback with dynamic port detection
        server_port = os.environ.get('AI_TRACKER_PORT', '8080')
        callback_url = f"http://localhost:{server_port}/api/activities/{task_id}/complete"
        
        task_prompt += f"""

✅ COMPLETION REQUIREMENTS:
1. Execute task following capability requirements above
2. Use specified tools/browsers as detected
3. Provide detailed outcome and notes
4. Call completion callback when done:

curl -X POST {callback_url} \\
  -H "Content-Type: application/json" \\
  -d '{{"outcome": "success/partial/failed", "outcome_notes": "detailed execution results with what was accomplished"}}'

🎯 SUCCESS CRITERIA:
• Task completed as described
• Appropriate tools used (Safari vs Chrome, etc.)
• Results documented in outcome_notes
• Status callback executed

Execute this task with full Clawdbot capabilities. Be precise about tool selection.
"""
        
        # Enhanced spawning with better session management
        session_label = f"ai-tracker-{ai_tool.lower() if ai_tool else 'auto'}-{task_id}"
        
        cmd = [
            'clawdbot', 'sessions', 'spawn',
            '--task', task_prompt,
            '--label', session_label,
            '--cleanup', 'keep',  # Keep for debugging and monitoring
        ]
        
        # Note: Removed agent-id routing since it's not in allowlist
        # All tasks will use current Claude session for now
        
        # Execute with better error capture
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"🤖 Task dispatched successfully: {title}")
            print(f"   Session: {session_label}")
            print(f"   Capabilities: {capabilities}")
            
            # Store session info for tracking
            conn = get_db()
            conn.execute(
                '''UPDATE activities 
                   SET status = ?, updated_at = ?, 
                       outcome_notes = ?
                   WHERE id = ?''',
                ('in-progress', datetime.now(),
                 f"Dispatched to Clawdbot session: {session_label}",
                 task_id)
            )
            conn.commit()
            conn.close()
        else:
            print(f"❌ Task dispatch failed: {result.stderr}")
            # Mark as failed
            conn = get_db()
            conn.execute(
                '''UPDATE activities 
                   SET status = ?, outcome = ?, outcome_notes = ?, updated_at = ?
                   WHERE id = ?''',
                ('todo', 'failed', f"Dispatch failed: {result.stderr}", 
                 datetime.now(), task_id)
            )
            conn.commit()
            conn.close()
        
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        # Update activity with error
        try:
            conn = get_db()
            conn.execute(
                '''UPDATE activities 
                   SET outcome = ?, outcome_notes = ?, updated_at = ?
                   WHERE id = ?''',
                ('failed', f"Execution error: {str(e)}", datetime.now(), task_id)
            )
            conn.commit()
            conn.close()
        except:
            pass

def send_notification(message, activity_data=None, notification_type='info'):
    """Enhanced notification system using full Clawdbot messaging capabilities"""
    if not ENABLE_NOTIFICATIONS:
        return
    
    try:
        # Format the notification message with enhanced context
        if activity_data:
            ai_tool = f" using {activity_data.get('ai_tool')}" if activity_data.get('ai_tool') else ""
            project = f" (Project: {activity_data.get('project')})" if activity_data.get('project') else ""
            status_emoji = {"todo": "📋", "in-progress": "⚡", "done": "✅"}.get(activity_data.get('status'), "📌")
            
            # Enhanced notification format with more context
            notification = f"{status_emoji} **AI Tracker Update**\n\n"
            notification += f"**{message}**\n"
            notification += f"📝 *{activity_data.get('title')}*{ai_tool}{project}\n"
            
            if activity_data.get('description'):
                desc_preview = activity_data.get('description')
                if len(desc_preview) > 150:
                    desc_preview = desc_preview[:150] + "..."
                notification += f"💬 {desc_preview}\n"
            
            # Add timing information if available
            if activity_data.get('time_spent') and activity_data.get('time_spent') > 0:
                minutes = activity_data.get('time_spent') // 60
                if minutes > 0:
                    notification += f"⏱ Time spent: {minutes}m\n"
            
            # Add outcome information
            if activity_data.get('outcome'):
                outcome_emoji = {"success": "✅", "partial": "🟡", "failed": "❌"}.get(activity_data.get('outcome'), "")
                notification += f"{outcome_emoji} Outcome: {activity_data.get('outcome').title()}\n"
            
            # Add iteration count if > 1
            if activity_data.get('iteration_count', 1) > 1:
                notification += f"🔄 Iterations: {activity_data.get('iteration_count')}\n"
            
            notification += f"📊 Status: **{activity_data.get('status', 'todo').replace('-', ' ').title()}**"
            
            # Add tracker access link
            notification += f"\n\n🔗 [View Tracker](http://localhost:8080)"
        else:
            notification = message
        
        # Enhanced message sending with error handling
        cmd = [
            'clawdbot', 'message', 'send',
            '--channel', 'telegram', 
            '--message', notification
        ]
        
        # Add message effects for certain notification types
        if notification_type == 'success':
            # Could add effects if supported: cmd.extend(['--effect', 'balloons'])
            pass
        elif notification_type == 'urgent':
            # Could add priority if supported
            pass
        
        # Execute with better error handling
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"📢 Notification sent successfully: {notification[:50]}...")
        else:
            print(f"⚠️  Notification warning: {result.stderr}")
            # Fallback: try without channel specification
            fallback_cmd = ['clawdbot', 'message', 'send', '--message', notification]
            subprocess.Popen(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    except subprocess.TimeoutExpired:
        print("⏰ Notification timeout - continuing without blocking")
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
            time_spent INTEGER DEFAULT 0,
            time_started TIMESTAMP,
            outcome TEXT,
            outcome_notes TEXT,
            failure_reason TEXT,
            iteration_count INTEGER DEFAULT 1,
            calendar_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
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
        '''INSERT INTO activities (title, description, ai_tool, project, status, position, 
           time_spent, outcome, outcome_notes, failure_reason, iteration_count, calendar_event_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('title'), data.get('description'), data.get('ai_tool'),
         data.get('project'), data.get('status', 'todo'), data.get('position', 0),
         data.get('time_spent', 0), data.get('outcome'), data.get('outcome_notes'),
         data.get('failure_reason'), data.get('iteration_count', 1), 
         data.get('calendar_event_id'))
    )
    activity_id = cursor.lastrowid
    conn.commit()
    
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (activity_id,)).fetchone()
    activity_dict = dict(activity)
    conn.close()
    
    # Send notification for new activity
    send_notification("New activity created!", activity_dict)
    
    # AUTO-EXECUTE: Attempt to execute the task via Clawdbot (if enabled)
    if AUTO_EXECUTE and activity_dict.get('status') == 'todo':
        execute_task_via_clawdbot(activity_dict)
    
    return jsonify(activity_dict), 201

@app.route('/api/activities/<int:id>', methods=['PUT'])
def update_activity(id):
    data = request.json
    conn = get_db()
    
    # Get the old activity to detect status changes
    old_activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    old_status = dict(old_activity)['status'] if old_activity else None
    
    # Check if status changed to done
    completed_at = None
    if data.get('status') == 'done':
        existing = conn.execute('SELECT status, completed_at FROM activities WHERE id = ?', (id,)).fetchone()
        if existing and existing['status'] != 'done':
            completed_at = datetime.now().isoformat()
        elif existing and existing['completed_at']:
            completed_at = existing['completed_at']
        else:
            completed_at = datetime.now().isoformat()
    
    conn.execute(
        '''UPDATE activities 
           SET title = ?, description = ?, ai_tool = ?, project = ?, 
               status = ?, position = ?, time_spent = ?, outcome = ?, 
               outcome_notes = ?, failure_reason = ?, iteration_count = ?, 
               calendar_event_id = ?, updated_at = ?, completed_at = ?
           WHERE id = ?''',
        (data.get('title'), data.get('description'), data.get('ai_tool'),
         data.get('project'), data.get('status'), data.get('position'),
         data.get('time_spent', 0), data.get('outcome'), data.get('outcome_notes'),
         data.get('failure_reason'), data.get('iteration_count', 1),
         data.get('calendar_event_id'), datetime.now(), completed_at, id)
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

@app.route('/api/activities/<int:id>/timer/start', methods=['POST'])
def start_timer(id):
    conn = get_db()
    conn.execute(
        'UPDATE activities SET time_started = ?, status = ? WHERE id = ?',
        (datetime.now().isoformat(), 'in-progress', id)
    )
    conn.commit()
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(activity))

@app.route('/api/activities/<int:id>/timer/stop', methods=['POST'])
def stop_timer(id):
    conn = get_db()
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    
    if activity and activity['time_started']:
        started = datetime.fromisoformat(activity['time_started'])
        elapsed = int((datetime.now() - started).total_seconds())
        new_time = (activity['time_spent'] or 0) + elapsed
        
        conn.execute(
            'UPDATE activities SET time_spent = ?, time_started = NULL WHERE id = ?',
            (new_time, id)
        )
        conn.commit()
    
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(activity))

@app.route('/api/activities/<int:id>/iteration', methods=['POST'])
def increment_iteration(id):
    conn = get_db()
    conn.execute(
        'UPDATE activities SET iteration_count = iteration_count + 1 WHERE id = ?',
        (id,)
    )
    conn.commit()
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(activity))

# Dashboard & Analytics
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = get_db()
    
    # Get date range from query params
    days = int(request.args.get('days', 30))
    start_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Overall stats
    total = conn.execute('SELECT COUNT(*) as count FROM activities').fetchone()['count']
    completed = conn.execute(
        'SELECT COUNT(*) as count FROM activities WHERE status = "done"'
    ).fetchone()['count']
    total_time = conn.execute(
        'SELECT SUM(time_spent) as total FROM activities'
    ).fetchone()['total'] or 0
    
    # Outcome stats
    outcomes = conn.execute('''
        SELECT outcome, COUNT(*) as count 
        FROM activities 
        WHERE outcome IS NOT NULL AND outcome != "" 
        GROUP BY outcome
    ''').fetchall()
    
    # Tool stats
    tool_stats = conn.execute('''
        SELECT ai_tool, COUNT(*) as total,
               SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
               SUM(CASE WHEN outcome = 'partial' THEN 1 ELSE 0 END) as partials,
               SUM(CASE WHEN outcome = 'failed' THEN 1 ELSE 0 END) as failures,
               SUM(time_spent) as total_time,
               AVG(time_spent) as avg_time,
               AVG(iteration_count) as avg_iterations
        FROM activities 
        WHERE ai_tool IS NOT NULL AND ai_tool != ""
        GROUP BY ai_tool
    ''').fetchall()
    
    # Failure reasons
    failure_reasons = conn.execute('''
        SELECT failure_reason, COUNT(*) as count 
        FROM activities 
        WHERE failure_reason IS NOT NULL AND failure_reason != ""
        GROUP BY failure_reason 
        ORDER BY count DESC
    ''').fetchall()
    
    # Project stats
    project_stats = conn.execute('''
        SELECT project, COUNT(*) as total,
               SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
               SUM(time_spent) as total_time
        FROM activities 
        WHERE project IS NOT NULL AND project != ""
        GROUP BY project
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'overview': {
            'total': total,
            'completed': completed,
            'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
            'total_time': total_time,
            'avg_time': round(total_time / completed, 1) if completed > 0 else 0
        },
        'outcomes': [dict(row) for row in outcomes],
        'tool_stats': [dict(row) for row in tool_stats],
        'failure_reasons': [dict(row) for row in failure_reasons],
        'project_stats': [dict(row) for row in project_stats]
    })

# Export
@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    conn = get_db()
    activities = conn.execute('''
        SELECT id, title, description, ai_tool, project, status, time_spent, 
               outcome, outcome_notes, failure_reason, iteration_count, 
               created_at, completed_at
        FROM activities 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Title', 'Description', 'AI Tool', 'Project', 'Status',
        'Time Spent (seconds)', 'Time Spent (formatted)', 'Outcome', 
        'Outcome Notes', 'Failure Reason', 'Iterations', 'Created', 'Completed'
    ])
    
    # Data
    for activity in activities:
        time_spent = activity['time_spent'] or 0
        hours = time_spent // 3600
        minutes = (time_spent % 3600) // 60
        time_formatted = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        writer.writerow([
            activity['id'], activity['title'], activity['description'],
            activity['ai_tool'], activity['project'], activity['status'],
            time_spent, time_formatted, activity['outcome'],
            activity['outcome_notes'], activity['failure_reason'],
            activity['iteration_count'], activity['created_at'], activity['completed_at']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ai_activities_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@app.route('/api/export/report', methods=['GET'])
def export_report():
    conn = get_db()
    
    # Get summary data
    overview = conn.execute('''
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
               SUM(time_spent) as total_time,
               AVG(CASE WHEN status = 'done' THEN time_spent END) as avg_time
        FROM activities
    ''').fetchone()
    
    tool_stats = conn.execute('''
        SELECT ai_tool, COUNT(*) as total,
               SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
               ROUND(SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) * 100.0 / 
                     NULLIF(COUNT(CASE WHEN outcome IS NOT NULL AND outcome != '' THEN 1 END), 0), 1) as success_rate,
               SUM(time_spent) as total_time
        FROM activities 
        WHERE ai_tool IS NOT NULL AND ai_tool != ""
        GROUP BY ai_tool
    ''').fetchall()
    
    conn.close()
    
    # Format time helper
    def format_time(seconds):
        if not seconds:
            return "0m"
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    # Build report
    report = []
    report.append("=" * 60)
    report.append("AI ACTIVITY TRACKER - SUMMARY REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 60)
    report.append("")
    report.append("OVERVIEW")
    report.append("-" * 40)
    report.append(f"Total Activities: {overview['total']}")
    report.append(f"Completed: {overview['completed']}")
    report.append(f"Completion Rate: {round(overview['completed'] / overview['total'] * 100, 1) if overview['total'] > 0 else 0}%")
    report.append(f"Total Time Tracked: {format_time(overview['total_time'])}")
    report.append(f"Avg Time per Task: {format_time(overview['avg_time'])}")
    report.append("")
    report.append("TOOL PERFORMANCE")
    report.append("-" * 40)
    for tool in tool_stats:
        report.append(f"  {tool['ai_tool']}:")
        report.append(f"    Activities: {tool['total']}")
        report.append(f"    Success Rate: {tool['success_rate'] or 0}%")
        report.append(f"    Time Spent: {format_time(tool['total_time'])}")
        report.append("")
    
    return Response(
        "\n".join(report),
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename=ai_report_{datetime.now().strftime("%Y%m%d")}.txt'}
    )

# Calendar Integration (ICS format)
@app.route('/api/calendar/ics', methods=['GET'])
def export_ics():
    conn = get_db()
    activities = conn.execute('''
        SELECT * FROM activities 
        WHERE created_at >= date('now', '-30 days')
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Activity Tracker//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for activity in activities:
        created = datetime.fromisoformat(activity['created_at'].replace(' ', 'T'))
        duration = activity['time_spent'] or 1800  # Default 30 min
        end = created + timedelta(seconds=duration)
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{activity['id']}@ai-tracker",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{created.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:[{activity['ai_tool'] or 'AI'}] {activity['title']}",
            f"DESCRIPTION:Project: {activity['project'] or 'N/A'}\\nOutcome: {activity['outcome'] or 'N/A'}\\nIterations: {activity['iteration_count']}",
            f"CATEGORIES:{activity['ai_tool'] or 'AI'},{activity['project'] or 'General'}",
            "END:VEVENT"
        ])
    
    ics_lines.append("END:VCALENDAR")
    
    return Response(
        "\r\n".join(ics_lines),
        mimetype='text/calendar',
        headers={'Content-Disposition': 'attachment; filename=ai_activities.ics'}
    )

# Notification endpoints (preserved from original)
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
    send_notification("🧪 Test notification from Enhanced AI Activity Tracker!")
    return jsonify({'success': True})

@app.route('/api/activities/<int:id>/execute', methods=['POST'])
def execute_task(id):
    """Manually execute a task via Clawdbot"""
    conn = get_db()
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    activity_dict = dict(activity)
    execute_task_via_clawdbot(activity_dict)
    
    return jsonify({'success': True, 'message': f'Task "{activity_dict["title"]}" dispatched to Clawdbot'})

@app.route('/api/activities/<int:id>/complete', methods=['POST'])
def complete_task(id):
    """Mark task as completed (called by Clawdbot when task is done)"""
    data = request.json
    conn = get_db()
    
    conn.execute(
        '''UPDATE activities 
           SET status = 'done', outcome = ?, outcome_notes = ?, 
               completed_at = ?, updated_at = ?
           WHERE id = ?''',
        (data.get('outcome', 'success'), 
         data.get('outcome_notes', 'Task completed by Clawdbot'),
         datetime.now().isoformat(),
         datetime.now(),
         id)
    )
    conn.commit()
    
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if activity:
        activity_dict = dict(activity)
        outcome = activity_dict.get('outcome', 'success')
        outcome_emoji = {"success": "✅", "partial": "🟡", "failed": "❌"}.get(outcome, "✅")
        send_notification(f"Task completed: {outcome_emoji} {outcome.title()}", activity_dict)
    
    return jsonify({'success': True})

@app.route('/api/sessions/status', methods=['GET'])
def get_sessions_status():
    """Get status of Clawdbot sessions related to activities"""
    try:
        # Use sessions_list to get current spawned sessions
        result = subprocess.run(['clawdbot', 'sessions', 'list', '--limit', '20'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Parse session info (this would need proper JSON parsing)
            return jsonify({'sessions': result.stdout, 'success': True})
        else:
            return jsonify({'error': result.stderr, 'success': False})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False})

@app.route('/api/integration/health', methods=['GET'])
def integration_health():
    """Check integration health with Clawdbot"""
    health_status = {
        'clawdbot_available': False,
        'notifications_enabled': ENABLE_NOTIFICATIONS,
        'sessions_spawn_available': False,
        'message_tool_available': False,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Test clawdbot availability
        result = subprocess.run(['clawdbot', '--version'], 
                              capture_output=True, text=True, timeout=5)
        health_status['clawdbot_available'] = result.returncode == 0
        
        # Test sessions spawn
        result = subprocess.run(['clawdbot', 'sessions', 'list'], 
                              capture_output=True, text=True, timeout=5)
        health_status['sessions_spawn_available'] = result.returncode == 0
        
        # Test message tool (just command availability)
        result = subprocess.run(['clawdbot', 'message', '--help'], 
                              capture_output=True, text=True, timeout=5)
        health_status['message_tool_available'] = result.returncode == 0
        
    except Exception as e:
        health_status['error'] = str(e)
    
    return jsonify(health_status)

@app.route('/api/activities/<int:id>/retry', methods=['POST'])
def retry_task(id):
    """Retry a failed task execution"""
    conn = get_db()
    activity = conn.execute('SELECT * FROM activities WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    activity_dict = dict(activity)
    
    # Reset status and clear previous failure notes
    conn = get_db()
    conn.execute(
        '''UPDATE activities 
           SET status = 'todo', outcome = NULL, outcome_notes = NULL, 
               updated_at = ?, iteration_count = iteration_count + 1
           WHERE id = ?''',
        (datetime.now(), id)
    )
    conn.commit()
    conn.close()
    
    # Re-execute the task
    execute_task_via_clawdbot(activity_dict)
    
    return jsonify({'success': True, 'message': f'Task "{activity_dict["title"]}" retry dispatched'})

@app.route('/api/capabilities', methods=['GET'])
def get_capabilities():
    """Get available Clawdbot capabilities for task planning"""
    capabilities = {
        'browsers': ['Safari', 'Chrome', 'Firefox'],
        'tools': {
            'browser': 'Web automation and browsing',
            'exec': 'System command execution',
            'write': 'File creation and editing', 
            'read': 'File reading',
            'nodes': 'Mobile device integration',
            'canvas': 'Visual presentations',
            'message': 'Notifications and messaging'
        },
        'node_features': [
            'camera_snap', 'screen_record', 'location_get', 
            'notify', 'run (command execution)'
        ],
        'browser_profiles': ['chrome', 'clawd'],
        'export_formats': ['CSV', 'Text Report', 'Calendar ICS']
    }
    
    return jsonify(capabilities)

def check_clawdbot_integration():
    """Check Clawdbot integration on startup"""
    print("🔍 Checking Clawdbot integration...")
    
    try:
        # Check if clawdbot is available
        result = subprocess.run(['clawdbot', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Clawdbot is available")
        else:
            print("⚠️  Clawdbot not available - tasks won't auto-execute")
            return False
            
        # Check sessions capability
        result = subprocess.run(['clawdbot', 'sessions', 'list', '--limit', '1'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Sessions spawn capability available")
        else:
            print("⚠️  Sessions not available - limited functionality")
            
        # Check message capability  
        result = subprocess.run(['clawdbot', 'message', '--help'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Message tool available for notifications")
        else:
            print("⚠️  Message tool not available - notifications disabled")
            global ENABLE_NOTIFICATIONS
            ENABLE_NOTIFICATIONS = False
            
        print("🎯 Integration check complete")
        return True
        
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        print("⚠️  Running in standalone mode - no auto-execution")
        return False

if __name__ == '__main__':
    print("🚀 Starting AI Activity Tracker Pro...")
    print(f"📊 Server port: {SERVER_PORT}")
    print(f"🔔 Notifications: {'Enabled' if ENABLE_NOTIFICATIONS else 'Disabled'}")
    print(f"🤖 Auto-execute: {'Enabled' if AUTO_EXECUTE else 'Disabled'}")
    print(f"📱 Notification channel: {NOTIFICATION_CHANNEL}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Check Clawdbot integration
    integration_ok = check_clawdbot_integration()
    
    if integration_ok:
        print("🎉 AI Activity Tracker Pro ready with full Clawdbot integration!")
    else:
        print("📋 AI Activity Tracker Pro ready in tracking-only mode")
    
    print(f"🌐 Access your tracker at: http://localhost:{SERVER_PORT}")
    print("=" * 60)
    
    # Start Flask server
    app.run(debug=True, port=SERVER_PORT, host='127.0.0.1')