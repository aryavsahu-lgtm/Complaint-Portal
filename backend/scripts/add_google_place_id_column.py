"""
Migration Script: Add google_place_id column to complaints table.
Stores Google Place IDs returned by Google Places Autocomplete / Geocoding APIs.
"""

import sqlite3
import os

def add_google_place_id_column():
    db_path = os.path.join(os.getcwd(), 'complaints.db')
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if google_place_id exists in complaints table
    cursor.execute("PRAGMA table_info(complaints)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    columns_to_verify = [
        ("google_place_id", "TEXT"),
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("location", "TEXT"),
    ]
    
    for col_name, col_type in columns_to_verify:
        if col_name not in existing_columns:
            print(f"Adding '{col_name}' ({col_type}) to 'complaints' table...")
            try:
                cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"✅ Added column '{col_name}' successfully.")
            except Exception as e:
                print(f"⚠️ Error adding column '{col_name}': {e}")
        else:
            print(f"ℹ️ Column '{col_name}' already exists in 'complaints'.")
            
    conn.close()
    print("Database migration check complete! 🚀")

if __name__ == '__main__':
    add_google_place_id_column()
