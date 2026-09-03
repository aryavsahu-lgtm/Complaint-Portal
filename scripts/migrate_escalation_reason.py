import sqlite3

def add_escalation_reason_column():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'escalation_reason' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN escalation_reason TEXT")
        print(" - Added 'escalation_reason' column to complaints.")
    else:
        print(" - 'escalation_reason' column already exists.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_escalation_reason_column()
