import os
import sys

# Ensure backend and root directories are in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
backend_path = os.path.join(root_dir, 'backend')

for path in [backend_path, root_dir, current_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app import app
from database import init_db

# Initialize database on cold start safely
try:
    with app.app_context():
        init_db()
except Exception as e:
    print(f"[Vercel Init DB Warning]: {e}")

# Vercel Serverless Function entrypoints
handler = app
application = app
app_entry = app
