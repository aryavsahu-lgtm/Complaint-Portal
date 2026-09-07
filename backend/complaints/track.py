"""
Citizen Complaint Tracking Module:
- /track (renders track_complaint.html)
"""

from flask import render_template, request, flash
from database import get_db
from utils import decrypt_data
from . import complaints_bp

@complaints_bp.route('/track', methods=['GET', 'POST'])
def track_complaint():
    complaint = None
    ref_no = request.args.get('ref_no') or request.form.get('ref_no')
    if ref_no:
        db = get_db()
        row = db.execute("SELECT * FROM complaints WHERE ref_no = ?", (ref_no.strip(),)).fetchone()
        if not row:
            flash('Invalid Reference Number.', 'warning')
        else:
            complaint = dict(row)
            complaint['description'] = decrypt_data(complaint.get('description'))
            complaint['latitude'] = decrypt_data(complaint.get('latitude')) or 0
            complaint['longitude'] = decrypt_data(complaint.get('longitude')) or 0
            complaint['user_lat'] = decrypt_data(complaint.get('user_latitude')) or 0
            complaint['user_lon'] = decrypt_data(complaint.get('user_longitude')) or 0
            complaint['evidence_lat'] = decrypt_data(complaint.get('evidence_latitude')) or 0
            complaint['evidence_lon'] = decrypt_data(complaint.get('evidence_longitude')) or 0
            complaint['google_place_id'] = decrypt_data(complaint.get('google_place_id')) or ''
            try:
                complaint['latitude'] = float(complaint['latitude']) if complaint['latitude'] else None
                complaint['longitude'] = float(complaint['longitude']) if complaint['longitude'] else None
            except Exception:
                pass
    return render_template('track_complaint.html', complaint=complaint, ref_no=ref_no)
