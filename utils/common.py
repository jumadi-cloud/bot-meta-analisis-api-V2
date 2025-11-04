import re
import threading
import time
from datetime import datetime, timedelta

# Global lock untuk thread-safe file access
history_lock = threading.Lock()

# Fungsi konversi markdown sederhana ke HTML
def markdown_to_html(text):
    if not text:
        return ""
    # Header
    text = re.sub(r'^####\s+(.*)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Unordered list
    lines = text.split('\n')
    in_list = False
    new_lines = []
    for line in lines:
        if re.match(r'^\s*[-*]\s+(.+)', line):
            if not in_list:
                new_lines.append('<ul>')
                in_list = True
            item = re.sub(r'^\s*[-*]\s+(.+)', r'<li>\1</li>', line)
            new_lines.append(item)
        else:
            if in_list:
                new_lines.append('</ul>')
                in_list = False
            new_lines.append(line)
    if in_list:
        new_lines.append('</ul>')
    text = '\n'.join(new_lines)
    # Paragraf dan line break
    paragraphs = re.split(r'\n{2,}', text.strip())
    html_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if re.search(r'<(h[1-6]|ul|ol|li|strong|em|p|br)', para):
            html_paragraphs.append(para)
        else:
            para = para.replace('\n', '<br>')
            html_paragraphs.append(f'<p>{para}</p>')
    return '\n'.join(html_paragraphs)

def get_session_history_file(session_id):
    if not session_id:
        return 'chat_history_default.txt'
    return f'chat_history_session_{session_id}.txt'

def append_history(role, message, session_id=None):
    history_file = get_session_history_file(session_id)
    with history_lock:
        with open(history_file, 'a', encoding='utf-8') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f'[{timestamp}] {role}: {message}\n')

def get_history(n=5, session_id=None):
    history_file = get_session_history_file(session_id)
    try:
        with history_lock:
            with open(history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        recent_lines = lines[-n:] if len(lines) > n else lines
        return ''.join(recent_lines)
    except FileNotFoundError:
        return ''

def clear_session_history(session_id=None):
    history_file = get_session_history_file(session_id)
    try:
        with history_lock:
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write('')
        return True
    except Exception:
        return False
