import sqlite3
import os
import json
from datetime import datetime

DB_NAME = "weblog_analyzer.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            scan_date TEXT,
            total_requests INTEGER,
            unique_ips INTEGER,
            error_rate REAL,
            traffic_data TEXT,
            status_data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_threats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER,
            ip TEXT,
            severity TEXT,
            time TEXT,
            details TEXT,
            reconstruction_error REAL,
            FOREIGN KEY(history_id) REFERENCES scan_history(id)
        )
    ''')
    conn.commit()
    conn.close()
    
def save_manual_report(filename , stats, threats):
    conn = get_db_connection()
    cursor = conn.cursor()
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    traffic_json = json.dumps(stats.get('traffic_chart', {}))
    status_json = json.dumps(stats.get('status_distribution', {}))
    cursor.execute('''
        INSERT INTO scan_history (filename, scan_date, total_requests, unique_ips, error_rate, traffic_data, status_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (filename, 
            scan_date, 
            stats['total_requests'], 
            stats['unique_ips'], 
            stats['error_rate'], 
            traffic_json, 
            status_json
        ))
    history_id = cursor.lastrowid
    if threats:
        threat_data = []
        for t in threats:
            threat_data.append((
                history_id,
                t['ip'],
                t['severity'],
                t['time'],
                t['details'],
                t['reconstruction_error']
            ))
        cursor.executemany('''
            INSERT INTO scan_threats (history_id, ip, severity, time, details, reconstruction_error)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', threat_data)
    conn.commit()
    conn.close()

    return history_id

def get_all_history():
    conn = get_db_connection()
    history = conn.execute('SELECT id, filename, scan_date, total_requests, error_rate FROM scan_history ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(row) for row in history]

def get_scan_details(history_id):
    conn = get_db_connection()
    history = conn.execute('SELECT * FROM scan_history WHERE id = ?', (history_id,)).fetchone()
    threats = conn.execute('SELECT * FROM scan_threats WHERE history_id = ?', (history_id,)).fetchall()
    conn.close()
    if history:
        history_dict = dict(history)
        history_dict['traffic_data'] = json.loads(history_dict['traffic_data']) if history_dict['traffic_data'] else {}
        history_dict['status_data'] = json.loads(history_dict['status_data']) if history_dict['status_data'] else {}
        history_dict['threats'] = [dict(row) for row in threats]
        return history_dict
    return None

def delete_scan_history(history_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM scan_threats WHERE history_id = ?", (history_id,))        
        cursor.execute("DELETE FROM scan_history WHERE id = ?", (history_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting history: {e}")
        return False
    finally:
        conn.close()
        
def clear_all_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM scan_threats")
        cursor.execute("DELETE FROM scan_history")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='scan_history'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='scan_threats'")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing data: {e}")
        return False
    finally:
        conn.close()