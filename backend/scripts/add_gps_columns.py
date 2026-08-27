import sqlite3

def add_gps_columns():
    print("Connecting to database...")
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    columns_to_add = [
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("gps_accuracy", "FLOAT")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            print(f"Checking if '{col_name}' column exists...")
            cursor.execute(f"SELECT {col_name} FROM complaints LIMIT 1")
            print(f"'{col_name}' column already exists.")
        except sqlite3.OperationalError:
            print(f"'{col_name}' column not found. Adding it now...")
            try:
                cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col_name} {col_type}")
                print(f"'{col_name}' column added successfully.")
                conn.commit()
            except Exception as e:
                print(f"Error adding column {col_name}: {e}")
    
    conn.close()

if __name__ == '__main__':
    add_gps_columns()
