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
        # Check if city column already exists
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'city' not in columns:
            print("Adding 'city' column to 'complaints' table...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN city TEXT DEFAULT 'Raipur'")
            conn.commit()
            print("Column added successfully.")
        else:
            print("'city' column already exists.")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
