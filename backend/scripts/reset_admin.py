import sqlite3
from werkzeug.security import generate_password_hash

def reset_admin():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
    
    if admin:
        print("Admin exists. Updating password to 'admin123'...")
        cursor.execute("UPDATE users SET password = ?, is_admin = 1 WHERE username = 'admin'", (hashed_pw,))
    else:
        print("Admin does not exist. Creating admin user with password 'admin123'...")
        cursor.execute("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)", 
                       ('admin', 'admin@example.com', hashed_pw, 1))
    
    conn.commit()
    conn.close()
    print("Admin reset complete.")

if __name__ == "__main__":
    reset_admin()
