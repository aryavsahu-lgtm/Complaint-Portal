import sqlite3
import os

def migrate_categories():
    db_path = 'complaints.db'
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Mapping old categories to new ones
    mapping = {
        'Academics': 'Government Service Delays',
        'Hostel': 'Road & Infrastructure',
        'Infrastructure': 'Road & Infrastructure'
    }

    try:
        for old, new in mapping.items():
            cursor.execute("UPDATE complaints SET category = ? WHERE category = ?", (new, old))
            print(f"Migrated '{old}' to '{new}' ({cursor.rowcount} records updated)")
        
        # Also ensure workers have valid categories
        for old, new in mapping.items():
            cursor.execute("UPDATE workers SET skill = ? WHERE skill = ?", (new, old))
            print(f"Updated worker skills: '{old}' to '{new}' ({cursor.rowcount} records updated)")

        conn.commit()
        print("Category migration completed successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_categories()
