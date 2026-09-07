"""
Incident Submission & Multimodal AI Ingestion Module:
- /user/submit-complaint (renders submit_complaint.html)
"""

from flask import render_template, request, redirect, url_for, flash, session, current_app
from database import get_db
from utils import login_required, rate_limit, log_audit, encrypt_data
from werkzeug.utils import secure_filename
import os
import time
import uuid
import json
from datetime import datetime

from ai_service import analyze_complaint_text
from ai_engine.fusion import AiFusionModule
from ai_engine.authenticity_engine import analyze_image_authenticity
from ai_engine.image_processor import preprocess_complaint_image
from ai_engine.vision_engine import analyze_vision_evidence
from ai_engine.audio_processor import AudioAIProcessor
from ai_engine.location_engine import LocationEngine
from . import complaints_bp

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
            except Exception:
                pass

        log_audit(action="Submit Complaint", target_type="complaint", target_id=complaint_id, details=f"Ref: {ref_no}")
        flash(f'Complaint submitted successfully! Ref: {ref_no}', 'success')
        return redirect(url_for('complaints.user_dashboard'))
    return render_template('submit_complaint.html')
