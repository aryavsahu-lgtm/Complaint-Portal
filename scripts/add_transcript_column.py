import sqlite3
import os

def migrate():
    db_path = 'complaints.db'
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'transcript' not in columns:
            print("Adding 'transcript' column to 'complaints' table...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN transcript TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("'transcript' column already exists.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
