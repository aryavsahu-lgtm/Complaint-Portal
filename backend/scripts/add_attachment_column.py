import sqlite3

def add_attachment_column():
    db_path = 'complaints.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'attachment' not in columns:
            print("Adding attachment column...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN attachment TEXT")
            conn.commit()
            print("Attachment column added successfully.")
        else:
            print("Attachment column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_attachment_column()
