"""
Admin Dashboard Module:
- /admin/dashboard (renders admin_dashboard.html)
- /admin/update-complaint/<complaint_id>
- /admin/delete-complaint/<complaint_id>
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import render_template, request, flash, redirect, url_for, current_app
from database import get_db
from utils import admin_required, decrypt_data, log_audit
from . import complaints_bp

logger = logging.getLogger(__name__)

@complaints_bp.route('/admin/dashboard')
@complaints_bp.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    filter_search = request.args.get('search', '')
    filter_category = request.args.get('category', '')
    filter_city = request.args.get('city', '')
    filter_status = request.args.get('status', '')
    filter_priority = request.args.get('priority', '')
    
    query = "SELECT c.*, COALESCE(u.username, 'Public / Anonymous') as username, COALESCE(u.email, 'Not Provided') as email FROM complaints c LEFT JOIN users u ON c.user_id = u.id WHERE 1=1"
    params = []
    if filter_search:
        query += " AND (c.title LIKE ? OR c.description LIKE ? OR c.ref_no LIKE ?)"
        params.extend([f'%{filter_search}%', f'%{filter_search}%', f'%{filter_search}%'])
    if filter_category and filter_category != 'All':
        query += " AND c.category = ?"
        params.append(filter_category)
    if filter_city and filter_city != 'All':
        query += " AND c.city = ?"
        params.append(filter_city)
    if filter_status and filter_status != 'All':
        query += " AND c.status = ?"
        params.append(filter_status)
    if filter_priority and filter_priority != 'All':
        query += " AND c.priority = ?"
        params.append(filter_priority)
    query += " ORDER BY c.created_at DESC"
    
    rows = db.execute(query, params).fetchall()
    complaints = []
    stats = {'total': 0, 'pending': 0, 'in_progress': 0, 'resolved': 0}
    category_counts = {}
    status_counts = {}
    emotion_totals = {"Anger": 0, "Fear": 0, "Urgency": 0, "Distress": 0}
    
    for row in rows:
        c = dict(row)
        c['description'] = decrypt_data(c.get('description')) or ''
        c['latitude'] = decrypt_data(c.get('latitude')) or 0
        c['longitude'] = decrypt_data(c.get('longitude')) or 0
        c['user_lat'] = decrypt_data(c.get('user_latitude')) or 0
        c['user_lon'] = decrypt_data(c.get('user_longitude')) or 0
        c['evidence_lat'] = decrypt_data(c.get('evidence_latitude')) or 0
        c['evidence_lon'] = decrypt_data(c.get('evidence_longitude')) or 0
        c['google_place_id'] = decrypt_data(c.get('google_place_id')) or ''
        try:
            c['latitude'] = float(c['latitude']) if c['latitude'] else None
            c['longitude'] = float(c['longitude']) if c['longitude'] else None
        except Exception:
            pass
        
        if c.get('emotion_data'):
            try:
                emotions = json.loads(c['emotion_data'])
                c['emotions'] = emotions
                for k, v in emotions.items():
                    key_map = {"Anger": "Anger", "Fear": "Fear", "Urgency": "Urgency", "Distress": "Distress"}
                    if k in key_map:
                        emotion_totals[key_map[k]] += v
            except Exception:
                c['emotions'] = {}
        else:
            c['emotions'] = {}

        if c.get('vision_data'):
            try:
                c['vision_results'] = json.loads(c['vision_data'])
            except Exception:
                c['vision_results'] = []
        else:
            c['vision_results'] = []

        if c.get('authenticity_data'):
            try:
                c['authenticity'] = json.loads(c['authenticity_data'])
            except Exception:
                c['authenticity'] = {}
        else:
            c['authenticity'] = {}

        complaints.append(c)
        stats['total'] += 1
        status_val = c.get('status') or 'Pending'
        s_key = status_val.lower().replace(' ', '_')
        stats[s_key] = stats.get(s_key, 0) + 1
        cat_val = c.get('category') or 'General'
        category_counts[cat_val] = category_counts.get(cat_val, 0) + 1
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

    try:
        technicians = [dict(w) for w in db.execute("SELECT * FROM workers WHERE is_active = 1").fetchall()]
    except Exception:
        technicians = []
    
    # Trends
    try:
        trends = db.execute("SELECT date(created_at) as day, COUNT(*) as count FROM complaints GROUP BY day ORDER BY day DESC LIMIT 7").fetchall()
        resolution_trends = [dict(t) for t in trends]
    except Exception:
        resolution_trends = []

    # Metrics
    try:
        total_chats_row = db.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_history").fetchone()
        total_chats = total_chats_row['count'] if total_chats_row and total_chats_row['count'] > 0 else 1
    except Exception:
        total_chats = 1
    
    try:
        escalated_chats_row = db.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_history WHERE intent = 'emergency'").fetchone()
        escalated_chats = escalated_chats_row['count'] if escalated_chats_row else 0
    except Exception:
        escalated_chats = 0
    
    chat_metrics = {
        'total_sessions': total_chats, 
        'escalation_rate': round((escalated_chats / total_chats) * 100, 1),
        'automation_rate': 85.5,
        'fallback_count': 12
    }

    # Live Sessions
    live_sessions = [dict(row) for row in db.execute("SELECT s.*, u.username FROM chat_sessions s LEFT JOIN users u ON s.user_id = u.id ORDER BY s.updated_at DESC LIMIT 5").fetchall()]
    
    # Category Trends for Pie Chart
    category_trends = [{'name': k, 'value': v} for k, v in category_counts.items()]
    
    # Escalated count
    escalated_count_row = db.execute("SELECT COUNT(*) as count FROM complaints WHERE is_escalated = 1").fetchone()
    escalated_count = escalated_count_row['count'] if escalated_count_row else 0
    
    # Live Citizen Locations (from user_locations table)
    limit_time = (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    citizen_loc_rows = db.execute("""
        SELECT ul.user_id, ul.latitude, ul.longitude, u.username, ul.created_at
        FROM user_locations ul
        JOIN users u ON ul.user_id = u.id
        WHERE ul.created_at > ?
        AND ul.id IN (SELECT MAX(id) FROM user_locations GROUP BY user_id)
    """, (limit_time,)).fetchall()
    
    citizen_locations = []
    for row in citizen_loc_rows:
        try:
            citizen_locations.append({
                "user_id": row['user_id'],
                "username": row['username'],
                "lat": float(row['latitude']),
                "lon": float(row['longitude']),
                "timestamp": row['created_at']
            })
        except Exception:
            pass

    # Fetch All Mining Locations for GIS Map & Officer Monitoring Hub
    mines_raw = db.execute("SELECT * FROM mines ORDER BY compliance_score DESC").fetchall()
    mines = []
    for m in mines_raw:
        m_dict = dict(m)
        try:
            capa_count = db.execute("SELECT COUNT(*) as count FROM capa_actions WHERE mine_id = ? AND status != 'Closed'", (m_dict['id'],)).fetchone()
            m_dict['open_capas'] = capa_count['count'] if capa_count else 0
        except Exception:
            m_dict['open_capas'] = 0
        mines.append(m_dict)
    
    # Fetch Officers Monitoring Hub Data
    try:
        capas = [dict(r) for r in db.execute("SELECT c.*, m.name as mine_name FROM capa_actions c JOIN mines m ON c.mine_id = m.id ORDER BY c.id DESC LIMIT 5").fetchall()]
    except Exception:
        capas = []
        
    try:
        telemetry_alerts = [dict(r) for r in db.execute("SELECT t.*, m.name as mine_name FROM mine_telemetry t JOIN mines m ON t.mine_id = m.id LIMIT 4").fetchall()]
    except Exception:
        telemetry_alerts = []

    try:
        inspections = [dict(r) for r in db.execute("SELECT fi.*, m.name as mine_name FROM field_inspections fi JOIN mines m ON fi.mine_id = m.id ORDER BY fi.id DESC LIMIT 5").fetchall()]
    except Exception:
        inspections = []

    return render_template('admin_dashboard.html', complaints=complaints, stats=stats, 
                         category_stats=category_counts, status_stats=status_counts,
                         technicians=technicians, resolution_trends=resolution_trends, chat_metrics=chat_metrics,
                         filter_search=filter_search, filter_category=filter_category,
                         filter_city=filter_city, filter_status=filter_status, filter_priority=filter_priority,
                         emotion_totals=emotion_totals, live_sessions=live_sessions,
                         category_trends=category_trends, escalated_count=escalated_count,
                         citizen_locations=citizen_locations, mines=mines,
                         capas=capas, telemetry_alerts=telemetry_alerts, inspections=inspections)

@complaints_bp.route('/admin/update-complaint/<int:complaint_id>', methods=['POST'])
@admin_required
def update_complaint(complaint_id):
    logger.info(f"DEBUG: Updating complaint {complaint_id}")
    logger.info(f"DEBUG: Form data: {request.form}")
    
    db = get_db()
    status = request.form.get('status', 'Pending')
    admin_response = request.form.get('admin_response', '')
    category = request.form.get('category')
    priority = request.form.get('priority')
    assigned_to = request.form.get('assigned_to')
    
    logger.info(f"DEBUG: Values - Status: {status}, Category: {category}, Priority: {priority}, Assigned: {assigned_to}")
    
    try:
        db.execute("""UPDATE complaints SET status = ?, admin_response = ?, category = ?, priority = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?""", 
                   (status, admin_response, category, priority, assigned_to, complaint_id))
        db.commit()
        flash('Complaint updated!', 'success')
        logger.info(f"✅ Complaint {complaint_id} updated successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to update complaint {complaint_id}: {e}")
        flash(f'Error updating complaint: {e}', 'danger')
        
    return redirect(url_for('complaints.admin_dashboard'))

@complaints_bp.route('/admin/delete-complaint/<int:complaint_id>', methods=['POST'])
@admin_required
def delete_complaint(complaint_id):
    db = get_db()
    try:
        row = db.execute("SELECT attachment, audio_file FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not row:
            flash('Complaint not found.', 'warning')
            return redirect(url_for('complaints.admin_dashboard'))

        if row['attachment']:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads'))
            attach_path = os.path.join(upload_folder, row['attachment'])
            if os.path.exists(attach_path) and os.path.isfile(attach_path):
                try:
                    os.remove(attach_path)
                except Exception as e:
                    logger.warning(f"Could not remove attachment file {attach_path}: {e}")

        if row['audio_file']:
            audio_folder = current_app.config.get('AUDIO_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads', 'audio'))
            audio_path = os.path.join(audio_folder, row['audio_file'])
            if os.path.exists(audio_path) and os.path.isfile(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.warning(f"Could not remove audio file {audio_path}: {e}")

        db.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        db.commit()
        log_audit(f"Admin deleted complaint #{complaint_id}")
        flash(f'Complaint #{complaint_id} has been permanently deleted.', 'success')
        logger.info(f"✅ Admin deleted complaint #{complaint_id}")
    except Exception as e:
        logger.error(f"❌ Failed to delete complaint {complaint_id}: {e}")
        flash(f'Error deleting complaint: {e}', 'danger')

    return redirect(url_for('complaints.admin_dashboard'))
