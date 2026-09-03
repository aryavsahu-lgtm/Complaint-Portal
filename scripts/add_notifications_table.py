import sqlite3

def add_notifications_table():
    db_path = 'complaints.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Creating notifications table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                complaint_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("Notifications table created successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_notifications_table()
