import sqlite3
import uuid
from datetime import datetime

DB_NAME = "weblog_analyzer.db"

def migrate_database():
    """Migrate database from INTEGER IDs to UUID (TEXT) IDs"""
    conn = sqlite3.connect(DB_NAME, timeout=10.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔄 Starting database migration...")
    
    # Step 1: Backup old data
    print("📦 Backing up old data...")
    old_history = cursor.execute("SELECT * FROM scan_history").fetchall()
    old_threats = cursor.execute("SELECT * FROM scan_threats").fetchall()
    
    print(f"   - Found {len(old_history)} history records")
    print(f"   - Found {len(old_threats)} threat records")
    
    # Step 2: Drop old tables
    print("🗑️  Dropping old tables...")
    cursor.execute("DROP TABLE IF EXISTS scan_threats")
    cursor.execute("DROP TABLE IF EXISTS scan_history")
    
    # Step 3: Create new tables with UUID
    print("🔨 Creating new tables with UUID schema...")
    
    cursor.execute('''
        CREATE TABLE scan_history(
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
    
    cursor.execute('''
        CREATE TABLE scan_threats(
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
    
    # Step 4: Migrate data with new UUIDs
    print("📥 Migrating data with new UUIDs...")
    id_mapping = {}  # Map old INTEGER id to new UUID
    
    for old_record in old_history:
        old_id = old_record['id']
        new_id = str(uuid.uuid4())
        id_mapping[old_id] = new_id
        
        cursor.execute('''
            INSERT INTO scan_history (id, owner_id, filename, scan_date, total_requests, unique_ips, error_rate, traffic_data, status_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_id,
            old_record['owner_id'] if 'owner_id' in old_record.keys() else None,
            old_record['filename'],
            old_record['scan_date'],
            old_record['total_requests'],
            old_record['unique_ips'],
            old_record['error_rate'],
            old_record['traffic_data'],
            old_record['status_data']
        ))
    
    print(f"   ✅ Migrated {len(old_history)} history records")
    
    # Migrate threats with mapped IDs
    for old_threat in old_threats:
        old_history_id = old_threat['history_id']
        new_history_id = id_mapping.get(old_history_id)
        
        if new_history_id:
            cursor.execute('''
                INSERT INTO scan_threats (id, history_id, ip, severity, time, details, reconstruction_error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                new_history_id,
                old_threat['ip'],
                old_threat['severity'] if 'severity' in old_threat.keys() else 'unknown',
                old_threat['time'],
                old_threat['details'],
                old_threat['reconstruction_error']
            ))
    
    print(f"   ✅ Migrated {len(old_threats)} threat records")
    
    # Step 5: Commit changes
    conn.commit()
    conn.close()
    
    print("✨ Migration completed successfully!")
    print("\n📋 Summary:")
    print(f"   - History records: {len(old_history)}")
    print(f"   - Threat records: {len(old_threats)}")
    print("   - All IDs converted from INTEGER to UUID (TEXT)")

if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
