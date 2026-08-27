import sqlite3

def upgrade_database():
    """
    Upgrades the existing database schema to support AI features.
    Adds 'workers' table and modifies 'complaints' table.
    """
    print("Upgrading database schema...")
    
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    # 1. Create 'workers' table
    # This table stores the field technicians who will be assigned to complaints.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            skill TEXT NOT NULL,         -- e.g., Electrical, Plumbing, Civil
            location_zone TEXT,          -- e.g., Hostel A, Academic Block
            current_load INTEGER DEFAULT 0, -- Number of active jobs
            contact TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    print(" - Created 'workers' table.")
    
    # 2. Add new columns to 'complaints' table
    # We use PRAGMA to check if columns exist to avoid errors on re-run
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'worker_id' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN worker_id INTEGER REFERENCES workers(id)")
        print(" - Added 'worker_id' column to complaints.")
        
    if 'sentiment_score' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN sentiment_score FLOAT DEFAULT 0.0")
        print(" - Added 'sentiment_score' column to complaints.")

    # 3. Seed some initial workers for testing
    # Check if workers exist
    cursor.execute("SELECT count(*) FROM workers")
    if cursor.fetchone()[0] == 0:
        print(" - Seeding initial workers...")
        initial_workers = [
            ('Ramesh Kumar', 'Infrastructure', 'Hostel A', 0, '9876543210'),
            ('Suresh Singh', 'Electrical', 'Academic Block', 0, '9876543211'),
            ('Mahesh Gupta', 'Plumbing', 'Hostel B', 1, '9876543212'),
            ('Abdul Khan', 'Academics', 'Library', 0, '9876543213')
        ]
        cursor.executemany(
            "INSERT INTO workers (name, skill, location_zone, current_load, contact) VALUES (?, ?, ?, ?, ?)",
            initial_workers
        )
        
    conn.commit()
    conn.close()
    print("Database upgrade complete! 🚀")

if __name__ == "__main__":
    upgrade_database()
