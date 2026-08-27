import sqlite3
import os

def add_ref_no_column():
    db_path = 'complaints.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if ref_no column already exists
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'ref_no' not in columns:
            print("Adding 'ref_no' column to 'complaints' table...")
            cursor.execute("ALTER TABLE complaints ADD COLUMN ref_no TEXT")
            conn.commit()
            print("Column 'ref_no' added successfully.")
            
            # Populate existing rows with a default reference number
            cursor.execute("SELECT id FROM complaints")
            rows = cursor.fetchall()
            for row in rows:
                complaint_id = row[0]
                ref_no = f"REF-{1000 + complaint_id}"
                cursor.execute("UPDATE complaints SET ref_no = ? WHERE id = ?", (ref_no, complaint_id))
            conn.commit()
            print("Existing rows updated with default reference numbers.")
        else:
            print("Column 'ref_no' already exists.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_ref_no_column()
