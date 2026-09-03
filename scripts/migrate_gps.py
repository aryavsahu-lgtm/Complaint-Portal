import sqlite3
import os

def migrate():
    db_path = 'instance/complaints.db'
    if not os.path.exists(db_path):
        db_path = 'complaints.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN user_latitude TEXT")
        cursor.execute("ALTER TABLE complaints ADD COLUMN user_longitude TEXT")
        cursor.execute("ALTER TABLE complaints ADD COLUMN evidence_latitude TEXT")
        cursor.execute("ALTER TABLE complaints ADD COLUMN evidence_longitude TEXT")
        print("Columns added successfully.")
    except sqlite3.OperationalError as e:
        print(f"OperationalError (possibly columns already exist): {e}")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
