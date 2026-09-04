import os
import sys
import importlib.util

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_BASE_DIR, 'backend')
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Explicitly load backend/app.py without circular naming collision
_spec = importlib.util.spec_from_file_location("backend_main_app", os.path.join(_BACKEND_DIR, "app.py"))
_module = importlib.util.module_from_spec(_spec)
sys.modules["backend_main_app"] = _module
_spec.loader.exec_module(_module)

app = _module.app
socketio = _module.socketio
handler = app
application = app

if __name__ == '__main__':
    from database import init_db
    with app.app_context():
        init_db()
    port = int(os.getenv('PORT', 5001))
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
