import os
import sys
import traceback

# Ensure backend directory has the absolute highest priority in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
backend_path = os.path.join(root_dir, 'backend')

# Prepend backend and root paths in the correct priority order: backend first
sys.path = [backend_path, root_dir, current_dir] + [p for p in sys.path if p not in (backend_path, root_dir, current_dir)]

_import_error = None
_flask_app = None

try:
    from app import app as _flask_app
    from database import init_db
    try:
        with _flask_app.app_context():
            init_db()
    except Exception as _e:
        print(f"[Vercel Init DB Warning]: {_e}")
except Exception:
    _import_error = traceback.format_exc()
    print(f"[Vercel App Import Error]:\n{_import_error}")

class SafeWSGIHandler:
    def __init__(self, flask_app, import_error):
        self.flask_app = flask_app
        self.import_error = import_error

    def __call__(self, environ, start_response):
        if self.import_error or self.flask_app is None:
            error_html = (
                "<!DOCTYPE html>"
                "<html>"
                "<head><title>500 Startup Error</title><meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<style>body{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;padding:2rem;background:#0d1117;color:#ff7b72;line-height:1.5;}"
                "pre{background:#161b22;padding:1.25rem;border-radius:8px;overflow-x:auto;color:#c9d1d9;border:1px solid #30363d;}</style></head>"
                "<body>"
                "<h2>⚡ Server Startup Traceback</h2>"
                "<p>The application encountered an exception during startup:</p>"
                f"<pre>{self.import_error}</pre>"
                "</body></html>"
            )
            data = error_html.encode('utf-8')
            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(data)))
            ])
            return [data]

        try:
            return self.flask_app(environ, start_response)
        except Exception:
            err_trace = traceback.format_exc()
            print(f"[WSGI Runtime Error]:\n{err_trace}")
            error_html = (
                "<!DOCTYPE html>"
                "<html>"
                "<head><title>500 Application Error</title><meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<style>body{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;padding:2rem;background:#0d1117;color:#ff7b72;line-height:1.5;}"
                "pre{background:#161b22;padding:1.25rem;border-radius:8px;overflow-x:auto;color:#c9d1d9;border:1px solid #30363d;}</style></head>"
                "<body>"
                "<h2>⚡ Application Runtime Error</h2>"
                f"<pre>{err_trace}</pre>"
                "</body></html>"
            )
            data = error_html.encode('utf-8')
            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(data)))
            ])
            return [data]

app = SafeWSGIHandler(_flask_app, _import_error)
handler = app
application = app
app_entry = app
