import os
import sys

# Ensure backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app import app
from database import init_db

# Initialize database on cold start
try:
    with app.app_context():
        init_db()
except Exception as e:
    print(f"[Vercel Init DB Warning]: {e}")

# Vercel entrypoint
app_entry = app
