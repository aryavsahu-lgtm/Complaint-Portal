"""
Complaints Blueprint Package.
Sub-modules are aligned 1-to-1 with frontend pages for maintainability:
- public_pages.py   -> departments.html, services.html, stats
- noticeboard.py    -> noticeboard.html
- track.py          -> track_complaint.html
- submit.py         -> submit_complaint.html & multimodal AI analysis
- user_dashboard.py -> user_dashboard.html & user location/notification APIs
- admin_dashboard.py-> admin_dashboard.html & admin actions
"""

from flask import Blueprint

complaints_bp = Blueprint('complaints', __name__)

# Import modular route handlers so their routes are registered on complaints_bp
from . import public_pages
from . import noticeboard
from . import track
from . import submit
from . import report_incident
from . import user_dashboard
from . import admin_dashboard

__all__ = ['complaints_bp']
