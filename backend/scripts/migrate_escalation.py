import sqlite3

def add_escalation_column():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'is_escalated' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN is_escalated BOOLEAN DEFAULT 0")
        print(" - Added 'is_escalated' column to complaints.")
    else:
        print(" - 'is_escalated' column already exists.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_escalation_column()
