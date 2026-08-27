import sqlite3

def add_rating_columns():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'rating' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN rating INTEGER")
        print(" - Added 'rating' column to complaints.")
    
    if 'resolved_at' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN resolved_at TIMESTAMP")
        print(" - Added 'resolved_at' column to complaints.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_rating_columns()
