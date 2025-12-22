import sqlite3
import os
import json
from datetime import datetime
import uuid

DB_NAME = "weblog_analyzer.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def generate_uuid():
    return str(uuid.uuid4())

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Create servers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            ipv4 TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            server_id TEXT NOT NULL,
            status TEXT,
            contents TEXT,
            FOREIGN KEY(server_id) REFERENCES servers(id)
        )
    ''')
    
    # Update/Create scan_history table with new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history(
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            filename TEXT NOT NULL,
            scan_date TEXT,
            total_requests INTEGER,
            unique_ips INTEGER,
            error_rate REAL,
            traffic_data TEXT,
            status_data TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    
    # Update/Create scan_threats table with new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_threats(
            id TEXT PRIMARY KEY,
            history_id TEXT,
            ip TEXT,
            severity TEXT,
            time TEXT,
            details TEXT,
            reconstruction_error REAL,
            FOREIGN KEY(history_id) REFERENCES scan_history(id)
        )
    ''')
    
    # Add missing columns to existing tables (if they don't exist)
    try:
        cursor.execute("ALTER TABLE scan_history ADD COLUMN owner_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE scan_history ADD COLUMN id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE scan_threats ADD COLUMN id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE scan_threats ADD COLUMN severity TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()
    
def save_manual_report(filename, stats, threats, owner_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    history_id = generate_uuid()
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    traffic_json = json.dumps(stats.get('traffic_chart', {}))
    status_json = json.dumps(stats.get('status_distribution', {}))
    
    cursor.execute('''
        INSERT INTO scan_history (id, owner_id, filename, scan_date, total_requests, unique_ips, error_rate, traffic_data, status_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (history_id,
            owner_id,
            filename, 
            scan_date, 
            stats['total_requests'], 
            stats['unique_ips'], 
            stats['error_rate'], 
            traffic_json, 
            status_json
        ))
    
    if threats:
        threat_data = []
        for t in threats:
            threat_data.append((
                generate_uuid(),
                history_id,
                t['ip'],
                t.get('severity', t.get('severity', 'unknown')),
                t['time'],
                t['details'],
                t['reconstruction_error']
            ))
        cursor.executemany('''
            INSERT INTO scan_threats (id, history_id, ip, severity, time, details, reconstruction_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        cursor.execute("DELETE FROM logs")
        cursor.execute("DELETE FROM servers")
        cursor.execute("DELETE FROM users")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing data: {e}")
        return False
    finally:
        conn.close()


# ==================== USER FUNCTIONS ====================

def create_user(fullname, username, password):
    """Create a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = generate_uuid()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute('''
            INSERT INTO users (id, fullname, username, password, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, fullname, username, password, created_at))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None  # Username already exists
    finally:
        conn.close()

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


# ==================== SERVER FUNCTIONS ====================

def create_server(owner_id, name, ipv4=None):
    """Create a new server"""
    conn = get_db_connection()
    cursor = conn.cursor()
    server_id = generate_uuid()
    
    cursor.execute('''
        INSERT INTO servers (id, owner_id, name, ipv4)
        VALUES (?, ?, ?, ?)
    ''', (server_id, owner_id, name, ipv4))
    conn.commit()
    conn.close()
    return server_id

def get_user_servers(owner_id):
    """Get all servers for a user"""
    conn = get_db_connection()
    servers = conn.execute('SELECT * FROM servers WHERE owner_id = ?', (owner_id,)).fetchall()
    conn.close()
    return [dict(row) for row in servers]

def get_server_by_id(server_id):
    """Get server by ID"""
    conn = get_db_connection()
    server = conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()
    conn.close()
    return dict(server) if server else None

def delete_server(server_id):
    """Delete server and its associated logs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM logs WHERE server_id = ?", (server_id,))
        cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting server: {e}")
        return False
    finally:
        conn.close()


# ==================== LOG FUNCTIONS ====================

def create_log(server_id, status, contents):
    """Create a new log entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    log_id = generate_uuid()
    
    cursor.execute('''
        INSERT INTO logs (id, server_id, status, contents)
        VALUES (?, ?, ?, ?)
    ''', (log_id, server_id, status, contents))
    conn.commit()
    conn.close()
    return log_id

def get_server_logs(server_id):
    """Get all logs for a server"""
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs WHERE server_id = ?', (server_id,)).fetchall()
    conn.close()
    return [dict(row) for row in logs]

def get_log_by_id(log_id):
    """Get log by ID"""
    conn = get_db_connection()
    log = conn.execute('SELECT * FROM logs WHERE id = ?', (log_id,)).fetchone()
    conn.close()
    return dict(log) if log else None

def delete_log(log_id):
    """Delete a log entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM logs WHERE id = ?", (log_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting log: {e}")
        return False
    finally:
        conn.close()