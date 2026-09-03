import sqlite3

def upgrade_workers_table():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(workers)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("avg_resolution_time", "FLOAT DEFAULT 0.0"),
        ("performance_rating", "FLOAT DEFAULT 5.0")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE workers ADD COLUMN {col_name} {col_type}")
            print(f" - Added '{col_name}' column to workers.")
        else:
            print(f" - '{col_name}' column already exists.")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_workers_table()
