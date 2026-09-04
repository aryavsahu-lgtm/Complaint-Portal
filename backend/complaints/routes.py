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
import logging

# Define logger
logger = logging.getLogger(__name__)

# Define complaints blueprint
complaints_bp = Blueprint('complaints', __name__)

@complaints_bp.route('/departments')
def departments():
    govt_departments = [
        {'id': 'safety', 'icon': 'bi-shield-exclamation', 'image': 'https://images.unsplash.com/photo-1578496480240-32d3b6f9e5b1?auto=format&fit=crop&w=800&q=80'},
        {'id': 'operations', 'icon': 'bi-truck-front-fill', 'image': 'https://images.unsplash.com/photo-1513828583688-c52646db42da?auto=format&fit=crop&w=800&q=80'},
        {'id': 'ventilation', 'icon': 'bi-wind', 'image': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80'},
        {'id': 'environment', 'icon': 'bi-tree', 'image': 'https://images.unsplash.com/photo-1509391366360-2e959784a276?auto=format&fit=crop&w=800&q=80'},
        {'id': 'regulatory', 'icon': 'bi-journal-check', 'image': 'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=800&q=80'},
        {'id': 'welfare', 'icon': 'bi-people-fill', 'image': 'https://images.unsplash.com/photo-1521791055366-0d553872125f?auto=format&fit=crop&w=800&q=80'}
    ]
    return render_template('departments.html', departments=govt_departments)

@complaints_bp.route('/services')
def services():
    municipal_services = [
        {'id': 'risk_register', 'icon': 'bi-clipboard2-pulse', 'color': 'primary'},
        {'id': 'inspections', 'icon': 'bi-search', 'color': 'success'},
        {'id': 'permits', 'icon': 'bi-file-earmark-check', 'color': 'info'},
        {'id': 'environment', 'icon': 'bi-droplet-half', 'color': 'warning'},
        {'id': 'worker_welfare', 'icon': 'bi-person-hearts', 'color': 'danger'},
        {'id': 'audit_trail', 'icon': 'bi-clock-history', 'color': 'secondary'}
    ]
    return render_template('services.html', services=municipal_services)


@complaints_bp.route('/noticeboard')
def noticeboard():
    """Noticeboard & Acknowledgements page with DGMS circulars, notices, and system acknowledgements."""
    notices = [
        {
            'id': 'NB-2026-001',
            'badge': 'DGMS Mandatory',
            'badge_color': 'danger',
            'icon': 'bi-exclamation-triangle-fill',
            'date': '20 Feb 2026',
            'title': 'CMR 2017 Reg 144: Mandatory Continuous CO & Spontaneous Heating Monitoring',
            'body': 'All colliery managers are directed to ensure daily tube bundle gas chromatography '
                    'and handheld sensor scanning across all underground Degree-II and Degree-III seams '
                    'in compliance with Coal Mines Regulation 2017, Regulation 144.',
            'reference': 'DGMS/CMR/2026/144',
            'status': 'Active'
        },
        {
            'id': 'NB-2026-002',
            'badge': 'MoEF&CC Clearance',
            'badge_color': 'success',
            'icon': 'bi-tree-fill',
            'date': '15 Jan 2026',
            'title': 'Half-Yearly Environmental Compliance Statement Submission Deadline',
            'body': 'All mine operators holding Environmental Clearances must upload verified air/water '
                    'quality test certificates, ground water monitoring reports, and green-belt '
                    'afforestation progress reports before the quarterly deadline.',
            'reference': 'MoEFCC/EC/Q1/2026',
            'status': 'Active'
        },
        {
            'id': 'NB-2026-003',
            'badge': 'Labour Safety',
            'badge_color': 'warning',
            'icon': 'bi-person-badge-fill',
            'date': '10 Jan 2026',
            'title': 'Mines Rules 1955: 100% Form O PME Health Screenings for Contract Workers',
            'body': 'Ensure all contractual overburden truck operators, drillers and blasters '
                    'complete triennial periodic medical examinations (Form O) and Vocational Safety '
                    'Training (VTC) before deployment on active mining faces.',
            'reference': 'DGMSLab/MR1955/PME/2026',
            'status': 'Active'
        },
        {
            'id': 'NB-2025-014',
            'badge': 'Mine Safety',
            'badge_color': 'primary',
            'icon': 'bi-shield-fill-check',
            'date': '28 Nov 2025',
            'title': 'Implementation of SCAMP Strata Support Plan across all Underground Seams',
            'body': 'All mine managers are directed to submit updated Strata Control Action and Management '
                    'Plans (SCAMP) for each active underground face within 30 days. Non-compliance will '
                    'attract action under Section 22 of the Mines Act 1952.',
            'reference': 'DGMS/SCAMP/2025/022',
            'status': 'Acknowledged'
        },
        {
            'id': 'NB-2025-009',
            'badge': 'Digital India',
            'badge_color': 'info',
            'icon': 'bi-pc-display-horizontal',
            'date': '05 Sep 2025',
            'title': 'MineGuard Portal Launched — Digital Complaint & Compliance Management System',
            'body': 'The Ministry of Coal, in association with DGMS and NIC, has officially launched the '
                    'MineGuard AI-enabled compliance and complaint management portal. All subsidiaries of '
                    'Coal India Limited are required to onboard by Q4 2025.',
            'reference': 'MoC/DIG/MineGuard/2025',
            'status': 'Acknowledged'
        },
    ]
    acknowledgements = [
        {
            'icon': 'bi-flag-fill',
            'color': 'text-saffron',
            'title': 'Government of India',
            'body': 'Ministry of Coal & Directorate General of Mines Safety (DGMS)'
        },
        {
            'icon': 'bi-pc-display-horizontal',
            'color': 'text-primary',
            'title': 'National Informatics Centre (NIC)',
            'body': 'Platform design, cloud hosting & Digital India integration'
        },
        {
            'icon': 'bi-tree',
            'color': 'text-success',
            'title': 'MoEF&CC',
            'body': 'Ministry of Environment, Forest and Climate Change — Environmental Compliance Framework'
        },
        {
            'icon': 'bi-people-fill',
            'color': 'text-warning',
            'title': 'Coal India Limited (CIL) & Subsidiaries',
            'body': 'SECL, CCL, WCL, ECL, NCL, BCCL, MCL, NEC — Field operations and compliance data'
        },
    ]
    return render_template('noticeboard.html', notices=notices, acknowledgements=acknowledgements)

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
            except: pass
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
        except: pass
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
        location = request.form.get('location', '').strip()
        assigned_to = request.form.get('assigned_to', 'General Administration')
        
        # Location & Coordinates Handling (from Google Maps Autocomplete or Geolocation)
        raw_lat = request.form.get('latitude') or request.form.get('browser_lat')
        raw_lon = request.form.get('longitude') or request.form.get('browser_lon')
        google_place_id = request.form.get('google_place_id', '').strip() or None

        user_lat = None
        user_lon = None
        if raw_lat:
            try: user_lat = float(raw_lat)
            except: user_lat = None
        if raw_lon:
            try: user_lon = float(raw_lon)
            except: user_lon = None
        
        evidence_lat = None
        evidence_lon = None
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
                        evidence_lat, evidence_lon = img_lat, img_lon
                        gps_accuracy = 1.0
                    vision_data_raw = analyze_vision_evidence(processed_path)
                    vision_data = json.dumps(vision_data_raw)
                    authenticity_data_raw = analyze_image_authenticity(file_path)
                    authenticity_data = json.dumps(authenticity_data_raw)
                    is_authentic = 0 if authenticity_data_raw.get('is_suspicious') else 1

        # Determine "final" location for map (prioritize evidence if present, otherwise user selected/pin/GPS location)
        final_lat = evidence_lat if evidence_lat is not None else user_lat
        final_lon = evidence_lon if evidence_lon is not None else user_lon

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
            "INSERT INTO complaints (user_id, title, description, category, priority, attachment, audio_file, location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, city, latitude, longitude, user_latitude, user_longitude, evidence_latitude, evidence_longitude, gps_accuracy, upload_key, google_place_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session['user_id'], title, description, category, priority, attachment_filename, audio_filename, location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, city, encrypt_data(final_lat), encrypt_data(final_lon), encrypt_data(user_lat), encrypt_data(user_lon), encrypt_data(evidence_lat), encrypt_data(evidence_lon), gps_accuracy, upload_key, encrypt_data(google_place_id))
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
                    "complaint_id": complaint_id, "title": title, "category": category, "latitude": final_lat, "longitude": final_lon,
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
    
    # Mock some metrics for now if not in DB to avoid UndefinedError
    chat_metrics = {
        'total_sessions': total_chats, 
        'escalation_rate': round((escalated_chats/total_chats)*100, 1),
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
        except: pass

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
    
    # Also update other fields if present in form
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
        # Fetch attachment and audio file path before deleting
        row = db.execute("SELECT attachment, audio_file FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not row:
            flash('Complaint not found.', 'warning')
            return redirect(url_for('complaints.admin_dashboard'))

        # Delete associated attachment if it exists on disk
        if row['attachment']:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads'))
            attach_path = os.path.join(upload_folder, row['attachment'])
            if os.path.exists(attach_path) and os.path.isfile(attach_path):
                try:
                    os.remove(attach_path)
                except Exception as e:
                    logger.warning(f"Could not remove attachment file {attach_path}: {e}")

        # Delete associated audio file if it exists
        if row['audio_file']:
            audio_folder = current_app.config.get('AUDIO_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads', 'audio'))
            audio_path = os.path.join(audio_folder, row['audio_file'])
            if os.path.exists(audio_path) and os.path.isfile(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.warning(f"Could not remove audio file {audio_path}: {e}")

        # Delete the complaint record
        db.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        db.commit()
        log_audit(f"Admin deleted complaint #{complaint_id}")
        flash(f'Complaint #{complaint_id} has been permanently deleted.', 'success')
        logger.info(f"✅ Admin deleted complaint #{complaint_id}")
    except Exception as e:
        logger.error(f"❌ Failed to delete complaint {complaint_id}: {e}")
        flash(f'Error deleting complaint: {e}', 'danger')

    return redirect(url_for('complaints.admin_dashboard'))

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

@complaints_bp.route('/get_stats')
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    return jsonify({"total": total})

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
