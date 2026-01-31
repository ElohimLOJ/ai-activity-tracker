from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE = 'ai_activities.db'

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
    conn.close()
    return jsonify(dict(activity)), 201

@app.route('/api/activities/<int:id>', methods=['PUT'])
def update_activity(id):
    data = request.json
    conn = get_db()
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
    conn.close()
    return jsonify(dict(activity))

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)