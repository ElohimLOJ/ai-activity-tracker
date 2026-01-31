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

DATABASE = 'ai_activities.db'

# Notification configuration (preserved from original)
ENABLE_NOTIFICATIONS = True

def execute_task_via_clawdbot(activity_data):
    """Execute the task using Clawdbot's automation capabilities with proper AI tool routing"""
    try:
        title = activity_data.get('title', '')
        description = activity_data.get('description', '')
        ai_tool = activity_data.get('ai_tool', '')
        task_id = activity_data.get('id')
        
        # Parse browser preference from description
        browser_preference = 'Safari'  # Default to Safari for macOS
        if 'chrome' in description.lower():
            browser_preference = 'Chrome'
        elif 'firefox' in description.lower():
            browser_preference = 'Firefox'
        elif 'safari' in description.lower():
            browser_preference = 'Safari'
        
        # Create a comprehensive task execution prompt with specific requirements
        task_prompt = f"""
AUTOMATED TASK EXECUTION - AI Activity Tracker

TASK DETAILS:
Title: {title}
Description: {description}
Required AI Tool: {ai_tool}
Required Browser: {browser_preference}
Task ID: {task_id}

EXECUTION REQUIREMENTS:
1. Use EXACTLY the AI tool specified: {ai_tool}
2. Use EXACTLY the browser specified: {browser_preference}
3. Follow the description precisely
4. For web tasks: Use the specified browser, not browser tool defaults
5. For Safari: Use 'open -a Safari "URL"' commands
6. For Chrome: Use 'open -a "Google Chrome" "URL"' commands

COMPLETION CALLBACK:
When task is complete, call:
curl -X POST http://localhost:8080/api/activities/{task_id}/complete \\
-H "Content-Type: application/json" \\
-d '{{"outcome": "success/partial/failed", "outcome_notes": "detailed results"}}'

Execute this task precisely as specified. Do not substitute tools or browsers.
"""
        
        # Route to appropriate AI tool if not using current session
        if ai_tool and ai_tool.lower() != 'claude':
            # For non-Claude tools, specify the agent/model
            agent_map = {
                'chatgpt': 'openai/gpt-4',  # If available
                'gpt': 'openai/gpt-4',
                'gemini': 'google/gemini-pro',  # If available
            }
            
            agent_id = agent_map.get(ai_tool.lower(), None)
            
            cmd = [
                'clawdbot', 'sessions', 'spawn',
                '--task', task_prompt,
                '--label', f"ai-tracker-{ai_tool.lower()}-{task_id}",
                '--cleanup', 'keep'
            ]
            
            if agent_id:
                cmd.extend(['--agent-id', agent_id])
        else:
            # Use current Clawdbot session (Claude)
            cmd = [
                'clawdbot', 'sessions', 'spawn', 
                '--task', task_prompt,
                '--label', f"ai-tracker-claude-{task_id}",
                '--cleanup', 'keep'
            ]
        
        # Execute in background
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"🤖 Task dispatched to {ai_tool or 'Clawdbot'}: {title} (Browser: {browser_preference})")
        
        # Update activity to show it's being executed with proper AI tool
        conn = get_db()
        conn.execute(
            'UPDATE activities SET status = ?, updated_at = ? WHERE id = ?',
            ('in-progress', datetime.now(), task_id)
        )
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        pass

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
    
    # AUTO-EXECUTE: Attempt to execute the task via Clawdbot
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
        send_notification("Task completed successfully!", activity_dict)
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)