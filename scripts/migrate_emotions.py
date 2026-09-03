import sqlite3

def add_emotion_data_column():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'emotion_data' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN emotion_data TEXT")
        print(" - Added 'emotion_data' column to complaints.")
    else:
        print(" - 'emotion_data' column already exists.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_emotion_data_column()
