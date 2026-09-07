"""
User Dashboard Module:
- /user/dashboard (renders user_dashboard.html)
- /api/update-location
- /api/toggle-tracking
- /user/mark-read/<notification_id>
- /api/notifications
- /user/rate-complaint/<complaint_id>
"""

import json
from flask import render_template, request, session, redirect, url_for, flash, jsonify
from database import get_db
from utils import login_required, decrypt_data
from . import complaints_bp

@complaints_bp.route('/user/dashboard')
@login_required
def user_dashboard():
    db = get_db()
    filter_search = request.args.get('search', '')
    filter_category = request.args.get('category', '')
    filter_city = request.args.get('city', '')
    filter_status = request.args.get('status', '')
    filter_priority = request.args.get('priority', '')
    
    query = "SELECT * FROM complaints WHERE user_id = ?"
    params = [session['user_id']]
    if filter_search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{filter_search}%', f'%{filter_search}%'])
    if filter_category and filter_category != 'All':
        query += " AND category = ?"
        params.append(filter_category)
    if filter_city and filter_city != 'All':
        query += " AND city = ?"
        params.append(filter_city)
    if filter_status and filter_status != 'All':
        query += " AND status = ?"
        params.append(filter_status)
    if filter_priority and filter_priority != 'All':
        query += " AND priority = ?"
        params.append(filter_priority)
    query += " ORDER BY created_at DESC"
    
    raw_complaints = db.execute(query, params).fetchall()
    complaints = []
    for row in raw_complaints:
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
        try:
            complaint['vision_results'] = json.loads(complaint['vision_data']) if complaint['vision_data'] else []
        except Exception:
            complaint['vision_results'] = []
        complaints.append(complaint)
    
    notifications = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    return render_template('user_dashboard.html', complaints=complaints, notifications=notifications,
                         filter_search=filter_search, filter_category=filter_category, filter_city=filter_city, 
                         filter_status=filter_status, filter_priority=filter_priority)

@complaints_bp.route('/api/update-location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    db = get_db()
    db.execute("INSERT INTO user_locations (user_id, latitude, longitude) VALUES (?, ?, ?)", (session['user_id'], str(data['lat']), str(data['lon'])))
    db.commit()
    return jsonify({"status": "success"})

@complaints_bp.route('/api/toggle-tracking', methods=['POST'])
@login_required
def toggle_tracking():
    enabled = bool(request.get_json().get('enabled', False))
    db = get_db()
    db.execute("UPDATE users SET tracking_consent = ? WHERE id = ?", (1 if enabled else 0, session['user_id']))
    db.commit()
    session['tracking_consent'] = enabled
    return jsonify({"status": "success"})

@complaints_bp.route('/user/mark-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, session['user_id']))
    db.commit()
    return redirect(url_for('complaints.user_dashboard'))

@complaints_bp.route('/api/notifications')
@login_required
def api_get_notifications():
    db = get_db()
    notifications = db.execute("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    return jsonify([dict(n) for n in notifications])

@complaints_bp.route('/user/rate-complaint/<int:complaint_id>', methods=['POST'])
@login_required
def rate_complaint(complaint_id):
    rating = request.form.get('rating')
    db = get_db()
    db.execute("UPDATE complaints SET rating = ? WHERE id = ? AND user_id = ?", (rating, complaint_id, session['user_id']))
    db.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('complaints.user_dashboard'))
