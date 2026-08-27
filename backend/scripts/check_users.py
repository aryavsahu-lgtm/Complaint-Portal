import sqlite3

def check():
    try:
        conn = sqlite3.connect('complaints.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        users = cur.execute('SELECT * FROM users').fetchall()
        print("Users in DB:")
        for u in users:
            print(dict(u))
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check()
