from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, abort, current_app
from database import get_db
from utils import login_required, admin_required, rate_limit, log_audit, check_complaint_owner, encrypt_data, decrypt_data
from werkzeug.utils import secure_filename
import os
import time
import uuid
import json
from datetime import datetime, timedelta
from ai_service import analyze_complaint_text
from ai_engine.fusion import AiFusionModule
from ai_engine.authenticity_engine import analyze_image_authenticity
from ai_engine.image_processor import preprocess_complaint_image
from ai_engine.vision_engine import analyze_vision_evidence
from ai_engine.audio_processor import AudioAIProcessor
from ai_engine.learning import LearningEngine
from ai_engine.location_engine import LocationEngine
import re

# Define complaints blueprint
complaints_bp = Blueprint('complaints', __name__)

@complaints_bp.route('/departments')
def departments():
    govt_departments = [
        {'id': 'pwd', 'icon': 'bi-truck', 'image': 'https://images.unsplash.com/photo-1541888946425-d81bb19240f5?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80'},
        {'id': 'water', 'icon': 'bi-droplet-fill', 'image': 'http://loremflickr.com/800/600/water,pipes'},
        {'id': 'sanitation', 'icon': 'bi-trash-fill', 'image': 'http://loremflickr.com/800/600/garbage,truck'},
        {'id': 'planning', 'icon': 'bi-building', 'image': 'https://images.unsplash.com/photo-1520697830682-bbb6e85e2b0b?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80'},
        {'id': 'revenue', 'icon': 'bi-cash-coin', 'image': 'http://loremflickr.com/800/600/finance,documents'},
        {'id': 'electrical', 'icon': 'bi-lightbulb-fill', 'image': 'http://loremflickr.com/800/600/electrician,streetlight'}
    ]
    return render_template('departments.html', departments=govt_departments)

@complaints_bp.route('/services')
def services():
    municipal_services = [
        {'id': 'civil_reg', 'icon': 'bi-person-badge', 'color': 'primary'},
        {'id': 'property_tax', 'icon': 'bi-receipt', 'color': 'success'},
        {'id': 'building_perm', 'icon': 'bi-house-check', 'color': 'info'},
        {'id': 'water_conn', 'icon': 'bi-water', 'color': 'warning'},
        {'id': 'trade_license', 'icon': 'bi-shop', 'color': 'danger'},
        {'id': 'hall_booking', 'icon': 'bi-calendar-event', 'color': 'secondary'}
    ]
    return render_template('services.html', services=municipal_services)

@complaints_bp.route('/track', methods=['GET', 'POST'])
def track_complaint():
    complaint = None
    ref_no = request.args.get('ref_no') or request.form.get('ref_no')
    if ref_no:
        db = get_db()
        complaint = db.execute("SELECT * FROM complaints WHERE ref_no = ?", (ref_no.strip(),)).fetchone()
        if not complaint:
            flash('Invalid Reference Number.', 'warning')
    return render_template('track_complaint.html', complaint=complaint, ref_no=ref_no)

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
        try:
            complaint['vision_results'] = json.loads(complaint['vision_data']) if complaint['vision_data'] else []
        except:
            complaint['vision_results'] = []
        complaints.append(complaint)
    
    notifications = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    return render_template('user_dashboard.html', complaints=complaints, notifications=notifications,
                         filter_search=filter_search, filter_category=filter_category, filter_city=filter_city, 
                         filter_status=filter_status, filter_priority=filter_priority)

@complaints_bp.route('/user/submit-complaint', methods=['GET', 'POST'])
@login_required
@rate_limit
def submit_complaint():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        city = request.form.get('city', 'Raipur Municipal Corporation')
        priority = request.form.get('priority', 'Low')
        location = request.form.get('location', '')
        assigned_to = request.form.get('assigned_to', 'General Administration')
        
        browser_lat = request.form.get('browser_lat')
        browser_lon = request.form.get('browser_lon')
        final_lat = float(browser_lat) if browser_lat else None
        final_lon = float(browser_lon) if browser_lon else None
        gps_accuracy = 0.0
        upload_key = request.form.get('upload_key')
        
        db = get_db()
        workers = db.execute("SELECT id, name, skill, location_zone as location, current_load as load FROM workers WHERE is_active = 1").fetchall()
        workers_list = [dict(w) for w in workers]

        nlp_results = analyze_complaint_text(description, available_workers=workers_list, city=city)
        vision_data_raw = []
        vision_data = None
        authenticity_data_raw = {}
        authenticity_data = None
        is_authentic = 1
        attachment = request.files.get('attachment')
        attachment_filename = None
        
        if attachment and attachment.filename:
            filename = attachment.filename
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext in {'png', 'jpg', 'jpeg'}:
                timestamp = int(time.time())
                safe_filename = secure_filename(filename)
                final_filename = f"{timestamp}_{safe_filename}"
                upload_folder = current_app.config['UPLOAD_FOLDER']
                if not os.path.exists(upload_folder): os.makedirs(upload_folder)
                file_path = os.path.join(upload_folder, final_filename)
                attachment.save(file_path)
                attachment_filename = final_filename
                processed_path = preprocess_complaint_image(file_path)
                if processed_path:
                    img_lat, img_lon = LocationEngine.get_gps_metadata(file_path)
                    if img_lat and img_lon and LocationEngine.validate_gps(img_lat, img_lon):
                        final_lat, final_lon = img_lat, img_lon
                        gps_accuracy = 1.0
                    vision_data_raw = analyze_vision_evidence(processed_path)
                    vision_data = json.dumps(vision_data_raw)
                    authenticity_data_raw = analyze_image_authenticity(file_path)
                    authenticity_data = json.dumps(authenticity_data_raw)
                    is_authentic = 0 if authenticity_data_raw.get('is_suspicious') else 1

        fusion_results = AiFusionModule.fuse_analysis(nlp_results, vision_data_raw, authenticity_data_raw)
        priority = fusion_results['final_priority']
        category = fusion_results['final_category']
        assigned_to = fusion_results['assigned_to']
        is_escalated = 1 if fusion_results['is_escalated'] else 0
        sentiment_score = nlp_results['sentiment_score']
        emotion_data = json.dumps(nlp_results['emotions'])
        escalation_reason = " | ".join(fusion_results['escalation_reasons'])
        worker_id = nlp_results.get('worker_id')
        title = nlp_results.get('title', title)

        audio_file = request.files.get('audio_file')
        audio_filename = None
        if audio_file and audio_file.filename:
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else 'webm'
            final_audio_name = f"voice_{timestamp}_{unique_id}.{ext}"
            upload_folder = current_app.config['AUDIO_FOLDER']
            if not os.path.exists(upload_folder): os.makedirs(upload_folder)
            audio_file.save(os.path.join(upload_folder, final_audio_name))
            audio_filename = final_audio_name

        ref_date = datetime.now().strftime("%Y%m%d")
        ref_uuid = uuid.uuid4().hex[:4].upper()
        ref_no = f"GRV-{ref_date}-{ref_uuid}"

        cursor = db.execute(
            "INSERT INTO complaints (user_id, title, description, category, priority, attachment, audio_file, location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, city, latitude, longitude, gps_accuracy, upload_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session['user_id'], title, description, category, priority, attachment_filename, audio_filename, location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, city, encrypt_data(final_lat), encrypt_data(final_lon), gps_accuracy, upload_key)
        )
        complaint_id = cursor.lastrowid
        if worker_id:
            db.execute("UPDATE workers SET current_load = current_load + 1 WHERE id = ?", (worker_id,))
        db.commit()

        if audio_filename:
            AudioAIProcessor.process_background(complaint_id, os.path.join(upload_folder, audio_filename), current_app.app_context())

        if fusion_results.get('is_animal_hazard'):
            try:
                from app import socketio
                socketio.emit('animal_hazard_detected', {
                    "complaint_id": complaint_id, "title": title, "category": category, "latitude": final_lat or 0, "longitude": final_lon or 0,
                    "location": location or city, "timestamp": datetime.now().isoformat()
                }, to='admins')
            except: pass

        log_audit(action="Submit Complaint", target_type="complaint", target_id=complaint_id, details=f"Ref: {ref_no}")
        flash(f'Complaint submitted successfully! Ref: {ref_no}', 'success')
        return redirect(url_for('complaints.user_dashboard'))
    return render_template('submit_complaint.html')

@complaints_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    filter_search = request.args.get('search', '')
    filter_category = request.args.get('category', '')
    filter_city = request.args.get('city', '')
    filter_status = request.args.get('status', '')
    filter_priority = request.args.get('priority', '')
    
    query = "SELECT c.*, u.username, u.email FROM complaints c JOIN users u ON c.user_id = u.id WHERE 1=1"
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
        c['description'] = decrypt_data(c['description'])
        c['latitude'] = decrypt_data(c['latitude']) or 0
        c['longitude'] = decrypt_data(c['longitude']) or 0
        
        # Parse emotion data if available
        if c['emotion_data']:
            try:
                emotions = json.loads(c['emotion_data'])
                for k, v in emotions.items():
                    if k in emotion_totals:
                        emotion_totals[k] += v
            except: pass
            
        complaints.append(c)
        stats['total'] += 1
        s_key = c['status'].lower().replace(' ', '_')
        stats[s_key] = stats.get(s_key, 0) + 1
        category_counts[c['category']] = category_counts.get(c['category'], 0) + 1
        status_counts[c['status']] = status_counts.get(c['status'], 0) + 1

    workers = [dict(w) for w in db.execute("SELECT * FROM workers WHERE is_active = 1").fetchall()]
    
    # Trends
    trends = db.execute("SELECT date(created_at) as day, COUNT(*) as count FROM complaints GROUP BY day ORDER BY day DESC LIMIT 7").fetchall()
    resolution_trends = [dict(t) for t in trends]

    # Metrics
    total_chats = db.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_history").fetchone()['count'] or 1
    escalated_chats = db.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_history WHERE intent = 'emergency'").fetchone()['count'] or 0
    chat_metrics = {'total_sessions': total_chats, 'escalation_rate': round((escalated_chats/total_chats)*100, 1)}

    # Live Sessions
    live_sessions = [dict(row) for row in db.execute("SELECT s.*, u.username FROM chat_sessions s LEFT JOIN users u ON s.user_id = u.id ORDER BY s.updated_at DESC LIMIT 5").fetchall()]
    
    # Category Trends for Pie Chart
    category_trends = [{'name': k, 'value': v} for k, v in category_counts.items()]
    
    # Escalated count
    escalated_count = db.execute("SELECT COUNT(*) FROM complaints WHERE is_escalated = 1").fetchone()[0]
    
    # Live Citizen Locations (from user_locations table)
    # Get last location for each person within last 15 mins
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
        citizen_locations.append({
            "user_id": row['user_id'],
            "username": row['username'],
            "lat": float(row['latitude']),
            "lon": float(row['longitude']),
            "timestamp": row['created_at']
        })

    return render_template('admin_dashboard.html', complaints=complaints, stats=stats, 
                         category_stats=category_counts, status_stats=status_counts,
                         workers=workers, resolution_trends=resolution_trends, chat_metrics=chat_metrics,
                         filter_search=filter_search, filter_category=filter_category,
                         filter_city=filter_city, filter_status=filter_status, filter_priority=filter_priority,
                         emotion_totals=emotion_totals, live_sessions=live_sessions,
                         category_trends=category_trends, escalated_count=escalated_count,
                         citizen_locations=citizen_locations)

@complaints_bp.route('/admin/update-complaint/<int:complaint_id>', methods=['POST'])
@admin_required
def update_complaint(complaint_id):
    db = get_db()
    status = request.form['status']
    admin_response = request.form['admin_response']
    db.execute("UPDATE complaints SET status = ?, admin_response = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, admin_response, complaint_id))
    db.commit()
    flash('Complaint updated!', 'success')
    return redirect(url_for('complaints.admin_dashboard'))

@complaints_bp.route('/api/update-location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    db = get_db()
    # Check if user has tracking consent
    user = db.execute("SELECT tracking_consent FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if not user or not user['tracking_consent']:
        return jsonify({"status": "blocked", "message": "Tracking consent not given"}), 403
        
    db.execute("INSERT INTO user_locations (user_id, latitude, longitude) VALUES (?, ?, ?)", (session['user_id'], str(data['lat']), str(data['lon'])))
    db.commit()
    
    # Broadcast to admins
    try:
        from app import socketio
        socketio.emit('citizen_location_update', {
            "user_id": session['user_id'],
            "username": session.get('username', 'Citizen'),
            "lat": data['lat'],
            "lon": data['lon'],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }, to='admins')
    except: pass
    
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

@complaints_bp.route('/api/stats')
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    resolved = db.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'").fetchone()[0]
    return jsonify({
        "total": total,
        "resolved": resolved,
        "pending": total - resolved
    })
