"""
Database migration: Add chat_history table
"""

import sqlite3

def migrate_chat_history():
    """Create chat_history table for chatbot conversations"""
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                intent TEXT,
                emotion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_session 
            ON chat_history(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_user 
            ON chat_history(user_id)
        """)
        
        # Update complaints table to track source
        cursor.execute("""
            PRAGMA table_info(complaints)
        """)
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'source' not in columns:
            cursor.execute("""
                ALTER TABLE complaints 
                ADD COLUMN source TEXT DEFAULT 'web'
            """)
            print("[Migration] Added 'source' column to complaints table")
        
        conn.commit()
        print("[Migration] Chat history table created successfully!")
        
    except Exception as e:
        print(f"[Migration Error] {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_chat_history()
