import sqlite3

def add_location_column():
    print("Connecting to database...")
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    try:
        print("Checking if 'location' column exists...")
        cursor.execute("SELECT location FROM complaints LIMIT 1")
        print("'location' column already exists.")
    except sqlite3.OperationalError:
        print("'location' column not found. Adding it now...")
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN location TEXT")
            print("'location' column added successfully.")
            conn.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_location_column()
