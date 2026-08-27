from functools import wraps
from flask import session, flash, redirect, url_for

import time
import base64
from cryptography.fernet import Fernet
from flask import current_app

# Hardcoded key for demo - in production, this should be an environment variable
DEMO_KEY = b'IEzbYB1bYn8esPu2AkHgD79YjE6Cez7TZ-XV_psaB0M=' 

def encrypt_data(data):
    """Encrypts a string or number using Fernet symmetric encryption."""
    if data is None: return None
    f = Fernet(DEMO_KEY)
    return f.encrypt(str(data).encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypts a Fernet-encrypted string."""
    if not encrypted_data: return None
    try:
        f = Fernet(DEMO_KEY)
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # Fallback: Return original data if decryption fails (assumes plaintext)
        return encrypted_data

# Rate Limiting Storage (Memory-based for demo)
request_history = {}

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id', 'anonymous')
        now = time.time()
        
        if user_id in request_history:
            last_request = request_history[user_id]
            if now - last_request < 1.0: # 1 request per second limit
                 flash('Too many requests. Please slow down.', 'warning')
                 return redirect(url_for('index'))
                 
        request_history[user_id] = now
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('complaints.user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function
def log_audit(action, target_type=None, target_id=None, details=None):
    """
    Step 9: Audit Logs for complaint actions.
    Records system and user actions for accountability.
    """
    from database import get_db
    from flask import request
    db = get_db()
    user_id = session.get('user_id')
    ip = request.remote_addr
    
    db.execute("""
        INSERT INTO audit_logs (user_id, action, target_type, target_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, action, target_type, target_id, details, ip))
    db.commit()


def check_complaint_owner(complaint_id):
    """
    RBAC: Ensure a user only accesses their own grievances or is an admin.
    """
    from database import get_db
    db = get_db()
    complaint = db.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        return False
    return session.get('is_admin') or complaint['user_id'] == session.get('user_id')
