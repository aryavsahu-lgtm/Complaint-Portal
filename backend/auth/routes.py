from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from pymongo.errors import DuplicateKeyError

def _safe_check_password(pw_hash, password):
    """Safely check password hash, returning False if hash algorithm unsupported (e.g. scrypt on LibreSSL)."""
    try:
        return check_password_hash(pw_hash, password)
    except (AttributeError, ValueError):
        return False

# Define the authentication blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    - Validates matching passwords
    - Hashes password for security
    - Checks for existing username/email
    """
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.register'))
        
        db = get_db()
        
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            # SECURITY: Strictly control admin account creation
            # SECURITY: Strictly control admin account creation
            is_admin = False
            if username.lower() == 'admin':
                # Check if an admin already exists to prevent hijacking
                existing_admin = db.execute("SELECT id FROM users WHERE is_admin = 1").fetchone()
                if not existing_admin:
                    is_admin = True
                else:
                    flash('An administrator already exists. Please register as a Citizen.', 'warning')
                    return redirect(url_for('auth.register'))
            
            # Explicitly cast to bool to satisfy MongoDB schema validation
            is_admin_bool = bool(is_admin)

            db.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, is_admin_bool)
            )
            # Get last row id for syncing
            sqlite_user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()


            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except (DuplicateKeyError, Exception) as e:
            if 'duplicate' in str(e).lower() or 'IntegrityError' in str(e) or isinstance(e, DuplicateKeyError):
                flash('Username or email already exists!', 'danger')
            else:
                flash(f'Registration error: {e}', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login across specialized coal mining governance roles:
    - Mine Manager -> Overall risk, incidents, mine comparison & trends dashboard
    - Safety Officer -> Live violations, incident telemetry & CAPA corrective action hub
    - Inspector -> Digital inspection checklist, evidence audits, violations log & reports
    - Admin -> Central system admin dashboard
    - Worker/Citizen -> Safety observation submission & status tracking dashboard
    """
    # Accept requested role from query param or form
    role = request.args.get('role', request.form.get('role', 'Mine Manager'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', role)
        
        db = get_db()
        # Allow login with either username or email
        user = db.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username)).fetchone()
        
        if user and _safe_check_password(user['password'], password):
            user_dict = dict(user) if hasattr(user, 'keys') else user
            user_role = user_dict.get('role') or ('Admin' if user_dict.get('is_admin') else 'Worker')
            is_admin = bool(user_dict.get('is_admin', 0))
            
            # Save comprehensive session info
            session['user_id'] = user_dict['id']
            session['username'] = user_dict['username']
            session['role'] = user_role
            session['is_admin'] = is_admin
            session['subsidiary'] = user_dict.get('subsidiary', 'SECL')
            session['tracking_consent'] = bool(user_dict.get('tracking_consent', 0))
            
            flash(f"Welcome back, {user_dict['username']} ({user_role})", 'success')
            
            # Role-Based Routing
            normalized_role = user_role.lower()
            if 'manager' in normalized_role:
                return redirect(url_for('governance.manager_dashboard'))
            elif 'safety' in normalized_role:
                return redirect(url_for('governance.safety_dashboard'))
            elif 'inspector' in normalized_role:
                return redirect(url_for('governance.inspector_dashboard'))
            elif is_admin or 'admin' in normalized_role:
                return redirect(url_for('complaints.admin_dashboard'))
            else:
                return redirect(url_for('complaints.user_dashboard'))
        else:
            flash('Invalid username or password. Try the 1-Click Demo Logins below!', 'danger')
    
    return render_template('login.html', role=role)

@auth_bp.route('/logout')
def logout():
    """Clear session and logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))
