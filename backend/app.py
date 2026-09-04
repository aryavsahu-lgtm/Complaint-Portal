import os
from dotenv import load_dotenv
load_dotenv() # Load variables from .env
from flask import Flask, render_template, g, session, redirect, url_for, request
import ssl

# Fix SSL certificate issues for NLTK/AI downloads on Mac
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

from auth import auth_bp
from complaints import complaints_bp
from chatbot import chatbot_bp
from governance import governance_bp
from database import close_db, init_db

from translations import TRANSLATIONS, SUPPORTED_LANGUAGES, LANGUAGE_MAP, get_translations
from flask_socketio import SocketIO

# Resolve backend and frontend directories robustly across local and serverless environments
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_possible_frontend_dirs = [
    os.path.join(_BASE_DIR, '..', 'frontend'),
    os.path.join(_BASE_DIR, 'frontend'),
    os.path.join(os.getcwd(), 'frontend'),
    '/var/task/frontend',
    os.path.abspath('frontend'),
]
_FRONTEND_DIR = _possible_frontend_dirs[0]
for _p in _possible_frontend_dirs:
    if os.path.exists(os.path.join(_p, 'templates')):
        _FRONTEND_DIR = os.path.abspath(_p)
        break

_TEMPLATE_DIR = os.path.join(_FRONTEND_DIR, 'templates')
_STATIC_DIR = os.path.join(_FRONTEND_DIR, 'static')

app = Flask(
    __name__,
    template_folder=_TEMPLATE_DIR,
    static_folder=_STATIC_DIR
)
app.secret_key = 'your-secret-key-change-this-in-production'
# Use the threading async mode for compatibility with the Python 3.13 environment.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ==============================================================================
# Google Maps API Configuration & Context Injection
# Required APIs in Google Cloud Console:
# 1. Maps JavaScript API (for interactive map view, markers, navigation)
# 2. Places API (for Google Places Autocomplete address search)
# 3. Geocoding API (for coordinates <-> formatted address reverse geocoding)
# Configured via .env: GOOGLE_MAPS_API_KEY=<your_api_key>
# ==============================================================================
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
app.config['GOOGLE_MAPS_API_KEY'] = GOOGLE_MAPS_API_KEY

@app.context_processor
def inject_global_template_vars():
    lang = session.get('lang', 'en')
    current_lang_meta = LANGUAGE_MAP.get(lang, {'code': 'en', 'name': 'English', 'native': 'English'})
    return {
        't': get_translations(lang),
        'current_lang': lang,
        'current_lang_info': current_lang_meta,
        'supported_languages': SUPPORTED_LANGUAGES,
        'google_maps_api_key': os.getenv('GOOGLE_MAPS_API_KEY', '')
    }

app.config['DATABASE'] = os.path.join(_BASE_DIR, 'complaints.db')
app.config['STORAGE_FOLDER'] = os.path.join(_BASE_DIR, 'storage')
app.config['UPLOAD_FOLDER'] = os.path.join(_FRONTEND_DIR, 'static', 'uploads')
app.config['AUDIO_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(complaints_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(governance_bp)

# Teardown app context
app.teardown_appcontext(close_db)

@app.route('/')
def index():
    from database import get_db
    db = get_db()
    
    try:
        # Optimized: Get all stats in fewer queries with caching
        stats = {}
        
        # Single query for complaint counts
        count_data = db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
                AVG(CASE WHEN rating IS NOT NULL THEN rating END) as avg_rating
            FROM complaints
        """).fetchone()
        
        stats['total'] = count_data['total'] or 0
        stats['resolved'] = count_data['resolved'] or 0
        stats['resolution_rate'] = round((stats['resolved'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
        stats['avg_rating'] = round(count_data['avg_rating'], 1) if count_data['avg_rating'] else 4.7
        
        # Worker average resolution time
        avg_res = db.execute("SELECT AVG(avg_resolution_time) FROM workers WHERE is_active = 1").fetchone()[0]
        stats['avg_resolution_time'] = round(avg_res, 1) if avg_res else 48.5
        
        # Department Performance
        dept_stats = db.execute("""
            SELECT category, COUNT(*) as count 
            FROM complaints 
            GROUP BY category 
            ORDER BY count DESC 
            LIMIT 5
        """).fetchall()
        stats['dept_stats'] = [dict(row) for row in dept_stats]
        
        # City-wise Statistics
        city_stats = db.execute("""
            SELECT city, COUNT(*) as count 
            FROM complaints 
            WHERE city IS NOT NULL
            GROUP BY city
        """).fetchall()
        stats['city_stats'] = [dict(row) for row in city_stats]
        
    except Exception as e:
        print(f"[Error] Failed to fetch stats: {e}")
        # Return default stats on error
        stats = {
            'total': 0,
            'resolved': 0,
            'resolution_rate': 0,
            'avg_resolution_time': 48.5,
            'avg_rating': 4.7,
            'dept_stats': [],
            'city_stats': []
        }
    
    return render_template('index.html', stats=stats)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGE_MAP:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@socketio.on('connect')
def handle_connect():
    """Manage secure communication rooms based on roles."""
    from flask_socketio import join_room
    if session.get('is_admin'):
        join_room('admins')
        print(f"[Socket] Admin {session.get('username')} joined the command center vault.")
    else:
        join_room('citizens')

if __name__ == '__main__':
    # Initialize DB (create tables if not exist)
    with app.app_context():
        init_db()
        # Ensure secure storage directories exist
        folders = [
            os.path.join(_FRONTEND_DIR, 'static', 'uploads'),
            os.path.join(_FRONTEND_DIR, 'static', 'uploads', 'audio'),
            os.path.join(_BASE_DIR, 'storage'),
        ]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"[System] Initialized secure data directory: {folder}")
    
    port = int(os.getenv('PORT', 5001))
    socketio.run(app, debug=False, host='127.0.0.1', port=port, use_reloader=False, allow_unsafe_werkzeug=True)
