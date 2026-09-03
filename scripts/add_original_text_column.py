import sqlite3

def add_original_text_column():
    print("Connecting to database...")
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    try:
        print("Checking if 'original_text' column exists...")
        cursor.execute("SELECT original_text FROM complaints LIMIT 1")
        print("'original_text' column already exists.")
    except sqlite3.OperationalError:
        print("'original_text' column not found. Adding it now...")
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN original_text TEXT")
            print("'original_text' column added successfully.")
            conn.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_original_text_column()
