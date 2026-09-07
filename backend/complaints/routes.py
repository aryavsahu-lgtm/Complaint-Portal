"""
Backward-compatibility stub for complaints routes.

The routes in this module have been modularized and separated to match the frontend templates:
- public_pages.py   -> departments.html, services.html, stats
- noticeboard.py    -> noticeboard.html
- track.py          -> track_complaint.html
- submit.py         -> submit_complaint.html & multimodal AI analysis
- user_dashboard.py -> user_dashboard.html & notifications / location APIs
- admin_dashboard.py-> admin_dashboard.html & complaint actions
"""

from . import complaints_bp

__all__ = ['complaints_bp']
