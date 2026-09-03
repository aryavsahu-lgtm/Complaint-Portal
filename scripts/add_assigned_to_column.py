import sqlite3

def add_assigned_to_column():
    print("Connecting to database...")
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    try:
        print("Checking if 'assigned_to' column exists...")
        cursor.execute("SELECT assigned_to FROM complaints LIMIT 1")
        print("'assigned_to' column already exists.")
    except sqlite3.OperationalError:
        print("'assigned_to' column not found. Adding it now...")
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN assigned_to TEXT DEFAULT 'General'")
            print("'assigned_to' column added successfully.")
            conn.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_assigned_to_column()
