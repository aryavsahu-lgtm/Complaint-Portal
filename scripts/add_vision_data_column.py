import sqlite3
import os

def migrate():
    db_path = 'complaints.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking for vision_data column...")
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'vision_data' not in columns:
            print("Adding vision_data column to complaints table...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN vision_data TEXT")
            print("Column vision_data added successfully.")
        else:
            print("Column vision_data already exists.")

        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
