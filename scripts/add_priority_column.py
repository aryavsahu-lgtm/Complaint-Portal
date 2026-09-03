import sqlite3

def add_priority_column():
    db_path = 'complaints.db' # Root path as per app.py
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'priority' not in columns:
            print("Adding priority column...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN priority TEXT DEFAULT 'Low'")
            conn.commit()
            print("Priority column added successfully.")
        else:
            print("Priority column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_priority_column()
