from flask import Flask, request, jsonify
import sqlite3
import uuid
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DB_PATH = 'chat_history.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        message TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/sessions', methods=['GET'])
def list_sessions():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT session_id FROM sessions ORDER BY created_at DESC')
    sessions = [{'session_id': row['session_id']} for row in c.fetchall()]
    conn.close()
    return jsonify(sessions)

@app.route('/sessions', methods=['POST'])
def create_session():
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO sessions (session_id, created_at) VALUES (?, ?)', (session_id, now))
    conn.commit()
    conn.close()
    return jsonify({'session_id': session_id})

@app.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT role, message, timestamp FROM history WHERE session_id = ? ORDER BY id ASC', (session_id,))
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"history": history})

@app.route('/history/<session_id>', methods=['POST'])
def add_history(session_id):
    data = request.get_json()
    role = data.get('role')
    message = data.get('message')
    timestamp = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO history (session_id, role, message, timestamp) VALUES (?, ?, ?, ?)', (session_id, role, message, timestamp))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(port=8001, debug=True)
