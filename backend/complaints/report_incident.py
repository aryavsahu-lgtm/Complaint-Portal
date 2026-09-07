"""
Direct Public Incident Reporting Module (Zero-Barrier / No Login Required):
- /report-incident (renders report_incident.html)
- /report_incident (alias)

Provides direct, instant access to report mine hazards, safety incidents,
and statutory violations without requiring user authentication.
Includes full Multimodal AI analysis (Speech, Vision, GPS, NLP, Authenticity)
and anonymous whistleblower protection under DGMS regulations.
"""

import os
import time
import uuid
import json
import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.utils import secure_filename

from database import get_db
from utils import rate_limit, log_audit, encrypt_data, decrypt_data
from ai_service import analyze_complaint_text
from ai_engine.fusion import AiFusionModule
from ai_engine.authenticity_engine import analyze_image_authenticity
from ai_engine.image_processor import preprocess_complaint_image
from ai_engine.vision_engine import analyze_vision_evidence
from ai_engine.audio_processor import AudioAIProcessor
from ai_engine.location_engine import LocationEngine
from . import complaints_bp

logger = logging.getLogger(__name__)

@complaints_bp.route('/report-incident', methods=['GET', 'POST'])
@complaints_bp.route('/report_incident', methods=['GET', 'POST'])
@rate_limit
def report_incident():
    """
    Dedicated Public Incident Desk:
    Direct access to submit safety incidents, hazards, or grievances without login.
    """
    db = get_db()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'General Safety').strip()
        severity = request.form.get('severity', 'Medium').strip()
        location = request.form.get('location', '').strip()
        city = request.form.get('city', 'SECL Mining Zone').strip()
        mine_id = request.form.get('mine_id')
        
        # Reporter identity preferences
        is_anonymous = request.form.get('is_anonymous') == '1' or request.form.get('reporter_mode') == 'anonymous'
        reporter_name = request.form.get('reporter_name', '').strip()
        reporter_phone = request.form.get('reporter_phone', '').strip()
        reporter_email = request.form.get('reporter_email', '').strip()
        reporter_id_num = request.form.get('reporter_id', '').strip()

        if not title or not description:
            flash('Please provide both an incident title and description.', 'danger')
            return redirect(url_for('complaints.report_incident'))

        # If citizen provided contact info and not anonymous, append metadata securely
        reporter_details = []
        if not is_anonymous:
            if reporter_name: reporter_details.append(f"Reporter: {reporter_name}")
            if reporter_phone: reporter_details.append(f"Phone: {reporter_phone}")
            if reporter_email: reporter_details.append(f"Email: {reporter_email}")
            if reporter_id_num: reporter_details.append(f"Worker/Contractor ID: {reporter_id_num}")
        else:
            reporter_details.append("Filed Anonymously (Whistleblower Protection Active)")

        contact_meta_str = " | ".join(reporter_details)

        # Geolocation parsing
        raw_lat = request.form.get('latitude') or request.form.get('browser_lat')
        raw_lon = request.form.get('longitude') or request.form.get('browser_lon')
        google_place_id = request.form.get('google_place_id', '').strip() or None

        user_lat = None
        user_lon = None
        if raw_lat:
            try: user_lat = float(raw_lat)
            except (ValueError, TypeError): user_lat = None
        if raw_lon:
            try: user_lon = float(raw_lon)
            except (ValueError, TypeError): user_lon = None

        evidence_lat = None
        evidence_lon = None
        gps_accuracy = None
        if user_lat and user_lon:
            gps_accuracy = 1.0

        # Fetch active workers for AI dispatch allocation
        try:
            workers = db.execute("SELECT id, name, skill, location_zone as location, current_load as load FROM workers WHERE is_active = 1").fetchall()
            workers_list = [dict(w) for w in workers]
        except Exception:
            try:
                workers = db.execute("SELECT id, name, skill, current_load as load FROM workers WHERE is_active = 1").fetchall()
                workers_list = [dict(w) for w in workers]
            except Exception:
                workers_list = []

        # AI NLP Analysis (sentiment, emotions, categorization)
        nlp_results = analyze_complaint_text(description, available_workers=workers_list, city=city)
        
        # Photo Evidence Processing & Authenticity Analysis
        attachment_filename = None
        vision_data = None
        vision_data_raw = {}
        authenticity_data = None
        authenticity_data_raw = {}
        is_authentic = 1
        upload_key = None

        if 'attachment' in request.files:
            attachment = request.files['attachment']
            if attachment and attachment.filename != '':
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex[:8]
                orig_name = secure_filename(attachment.filename)
                ext = orig_name.rsplit('.', 1)[1].lower() if '.' in orig_name else 'jpg'
                final_filename = f"{timestamp}_{unique_id}.{ext}"
                upload_key = f"{timestamp}_{unique_id}"

                upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads'))
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder, exist_ok=True)
                
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

        final_lat = evidence_lat if evidence_lat is not None else user_lat
        final_lon = evidence_lon if evidence_lon is not None else user_lon

        # Multimodal AI Fusion
        fusion_results = AiFusionModule.fuse_analysis(nlp_results, vision_data_raw, authenticity_data_raw)
        priority = fusion_results.get('final_priority', severity)
        if severity == 'Critical':
            priority = 'Critical' # Force override if user declared emergency
        
        category = fusion_results.get('final_category', category)
        assigned_to = fusion_results.get('assigned_to', 'Mine Safety & Colliery Control Room')
        is_escalated = 1 if (fusion_results.get('is_escalated') or priority in ['Critical', 'High']) else 0
        sentiment_score = nlp_results.get('sentiment_score', 0.5)
        emotion_data = json.dumps(nlp_results.get('emotions', {}))
        escalation_reasons = fusion_results.get('escalation_reasons', [])
        if priority == 'Critical':
            escalation_reasons.append("Reported as Critical/Urgent Incident")
        escalation_reason = " | ".join(escalation_reasons)
        worker_id = nlp_results.get('worker_id')

        # Audio File Upload & Processing
        audio_file = request.files.get('audio_file')
        audio_filename = None
        if audio_file and audio_file.filename:
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else 'webm'
            final_audio_name = f"public_voice_{timestamp}_{unique_id}.{ext}"
            audio_folder = current_app.config.get('AUDIO_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads', 'audio'))
            if not os.path.exists(audio_folder):
                os.makedirs(audio_folder, exist_ok=True)
            audio_file.save(os.path.join(audio_folder, final_audio_name))
            audio_filename = final_audio_name

        # Resolve User ID (Zero Login Requirement)
        if session.get('user_id') and not is_anonymous:
            user_id = session['user_id']
        else:
            # Check or create dedicated 'anonymous_reporter' in database
            guest_user = db.execute("SELECT id FROM users WHERE username = 'anonymous_reporter'").fetchone()
            if not guest_user:
                try:
                    db.execute("""INSERT INTO users 
                        (username, email, password, is_admin, role, subsidiary, created_at) 
                        VALUES ('anonymous_reporter', 'anonymous@mineguard.gov.in', 'whistleblower123', 0, 'Whistleblower', 'Public', CURRENT_TIMESTAMP)""")
                    db.commit()
                    guest_user = db.execute("SELECT id FROM users WHERE username = 'anonymous_reporter'").fetchone()
                except Exception as e:
                    logger.warning(f"Error creating guest user: {e}")
                    guest_user = db.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
            user_id = guest_user['id'] if guest_user else 1

        # Generate Unique Reference Number
        ref_date = datetime.now().strftime("%Y%m%d")
        ref_uuid = uuid.uuid4().hex[:4].upper()
        ref_no = f"INC-{ref_date}-{ref_uuid}"

        # Combine description with contact metadata if non-anonymous
        full_description = f"{description}\n\n[Contact / Reporter Info]: {contact_meta_str}" if contact_meta_str else description

        # Save to database
        cursor = db.execute(
            """INSERT INTO complaints (
                user_id, title, description, category, priority, attachment, audio_file, 
                location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, 
                escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, 
                city, latitude, longitude, user_latitude, user_longitude, 
                evidence_latitude, evidence_longitude, gps_accuracy, upload_key, google_place_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, title, full_description, category, priority, attachment_filename, audio_filename, 
                location, assigned_to, sentiment_score, is_escalated, worker_id, emotion_data, 
                escalation_reason, vision_data, is_authentic, authenticity_data, ref_no, 
                city, encrypt_data(final_lat), encrypt_data(final_lon), encrypt_data(user_lat), encrypt_data(user_lon), 
                encrypt_data(evidence_lat), encrypt_data(evidence_lon), gps_accuracy, upload_key, encrypt_data(google_place_id)
            )
        )
        complaint_id = cursor.lastrowid
        
        if worker_id:
            try:
                db.execute("UPDATE workers SET current_load = current_load + 1 WHERE id = ?", (worker_id,))
            except Exception:
                pass
        db.commit()

        # Asynchronous Audio AI Processing
        if audio_filename:
            try:
                audio_path = os.path.join(audio_folder, audio_filename)
                AudioAIProcessor.process_background(complaint_id, audio_path, current_app.app_context())
            except Exception as e:
                logger.warning(f"Audio processing error: {e}")

        # Real-time WebSockets dispatch to Control Room Admins
        try:
            from app import socketio
            socketio.emit('new_public_incident', {
                "complaint_id": complaint_id,
                "ref_no": ref_no,
                "title": title,
                "category": category,
                "priority": priority,
                "is_escalated": is_escalated,
                "latitude": final_lat,
                "longitude": final_lon,
                "location": location or city,
                "is_anonymous": is_anonymous,
                "timestamp": datetime.now().isoformat()
            }, to='admins')
        except Exception as e:
            logger.warning(f"SocketIO notification error: {e}")

        log_audit(action="Direct Incident Filed", target_type="complaint", target_id=complaint_id, details=f"Ref: {ref_no} | Priority: {priority}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
            return jsonify({
                "status": "success",
                "ref_no": ref_no,
                "complaint_id": complaint_id,
                "priority": priority,
                "category": category,
                "message": f"Incident reported successfully! Your Reference No is {ref_no}"
            })

        flash(f'Incident reported successfully! Reference Number: {ref_no}. Keep this safe to track your case.', 'success')
        return redirect(url_for('complaints.report_incident', submitted_ref=ref_no))

    # --- GET Request Handling ---
    submitted_ref = request.args.get('submitted_ref', '').strip()
    submitted_case = None
    if submitted_ref:
        row = db.execute("SELECT * FROM complaints WHERE ref_no = ?", (submitted_ref,)).fetchone()
        if row:
            submitted_case = dict(row)
            submitted_case['description'] = decrypt_data(submitted_case.get('description'))

    # Fetch active mines for colliery selector
    try:
        mines = [dict(m) for m in db.execute("SELECT id, name, subsidiary, area, latitude, longitude FROM mines ORDER BY name").fetchall()]
    except Exception:
        mines = []

    # Fetch recent active circulars/advisories for public transparency feed
    try:
        notices = [
            {'title': 'Monsoon Inundation Warning & Sump Pumping Protocol', 'body': 'Mandatory dual pump inspection across all underground collieries under CMR 2017 Reg. 148.', 'date': 'Today', 'badge': 'Emergency DGMS Alert', 'badge_class': 'danger'},
            {'title': 'Daily CO & Gas Tube Bundle Scanning', 'body': 'Continuous gas chromatography monitoring active for Degree-II & III seams.', 'date': 'Active', 'badge': 'Gas Safety', 'badge_class': 'warning'},
            {'title': 'Zero-Harm Whistleblower Protection Charter', 'body': 'Workers and citizens reporting hazardous strata or gas conditions are protected from retaliation under Section 22 of Mines Act 1952.', 'date': 'Policy', 'badge': 'Statutory Charter', 'badge_class': 'info'}
        ]
    except Exception:
        notices = []

    return render_template(
        'report_incident.html',
        mines=mines,
        notices=notices,
        submitted_case=submitted_case,
        submitted_ref=submitted_ref
    )
