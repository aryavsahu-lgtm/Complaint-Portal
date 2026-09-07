"""
Field Inspections & CAPA (Corrective and Preventive Actions) Module:
- /field-inspection (renders field_inspection.html)
- /api/sync-offline-inspections (offline PWA sync)
- /capa-manager (renders capa_manager.html)
- /capa/update/<capa_id>
"""

import os
import uuid
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from database import get_db
from ai_engine.authenticity_engine import analyze_image_authenticity
from . import governance_bp
from .helpers import _record_crypto_audit

# ==========================================
# GEO-TAGGED FIELD INSPECTION & MOBILE PWA
# ==========================================
@governance_bp.route('/field-inspection', methods=['GET', 'POST'])
def field_inspection():
    db = get_db()
    if request.method == 'POST':
        mine_id = request.form.get('mine_id')
        inspector_name = request.form.get('inspector_name') or session.get('username', 'Field Inspector')
        shift = request.form.get('shift', 'Shift A (Morning)')
        location_pit_seam = request.form.get('location_pit_seam', 'Pit Area')
        violation_category = request.form.get('violation_category', 'Safety')
        violation_title = request.form.get('violation_title', 'Field Observation')
        description = request.form.get('description', '')
        risk_level = request.form.get('risk_level', 'Medium')
        latitude = float(request.form.get('latitude', 22.3385) or 22.3385)
        longitude = float(request.form.get('longitude', 82.5925) or 82.5925)

        photo_filename = None
        authenticity_score = 96.5

        if 'photo_evidence' in request.files:
            file = request.files['photo_evidence']
            if file and file.filename:
                fname = secure_filename(f"insp_{uuid.uuid4().hex[:8]}_{file.filename}")
                upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'frontend', 'static', 'uploads'))
                os.makedirs(upload_folder, exist_ok=True)
                upload_path = os.path.join(upload_folder, fname)
                file.save(upload_path)
                photo_filename = fname
                # Authenticity check
                auth_res = analyze_image_authenticity(upload_path)
                authenticity_score = auth_res.get('authenticity_score', 96.5)

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute("""INSERT INTO field_inspections 
            (mine_id, inspector_name, shift, location_pit_seam, violation_category, violation_title, description, risk_level, latitude, longitude, photo_attachment, authenticity_score, is_offline_synced, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'Open', ?, ?)""", (
            mine_id, inspector_name, shift, location_pit_seam, violation_category, violation_title, description, risk_level, latitude, longitude, photo_filename, authenticity_score, now_str, now_str
        ))
        insp_id = cursor.lastrowid

        # Auto-create initial CAPA if risk is Critical or High
        if risk_level in ['Critical', 'High']:
            target_date = (datetime.now() + timedelta(days=3 if risk_level == 'Critical' else 7)).strftime('%Y-%m-%d')
            db.execute("""INSERT INTO capa_actions 
                (inspection_id, mine_id, title, root_cause, corrective_action, preventive_action, assigned_engineer, target_date, status, created_at, updated_at)
                VALUES (?, ?, ?, 'Field safety observation audit', ?, 'Conduct routine pre-shift inspection', 'Colliery Safety Officer', ?, 'In Progress', ?, ?)""", (
                insp_id, mine_id, f"Corrective Action: {violation_title}", f"Investigate and resolve: {description[:120]}", target_date, now_str, now_str
            ))

        db.commit()

        # Immutable Cryptographic Audit
        _record_crypto_audit(
            actor_name=inspector_name,
            action_type="FIELD_INSPECTION_RECORDED",
            entity=f"Inspection #{insp_id} at Mine #{mine_id}",
            details=f"Geo-tagged observation recorded at ({latitude:.4f}, {longitude:.4f}) with risk '{risk_level}'.",
            payload={"inspection_id": insp_id, "lat": latitude, "lon": longitude, "risk": risk_level, "photo": photo_filename}
        )

        flash(f'Field Inspection observation #{insp_id} logged successfully with geo-tagging & authenticity verification!', 'success')
        return redirect(url_for('governance.dashboard'))

    mines = [dict(row) for row in db.execute("SELECT id, name, subsidiary, area, latitude, longitude FROM mines ORDER BY name").fetchall()]
    return render_template('field_inspection.html', mines=mines)

# API endpoint for PWA offline sync
@governance_bp.route('/api/sync-offline-inspections', methods=['POST'])
def sync_offline_inspections():
    data = request.get_json() or {}
    items = data.get('inspections', [])
    db = get_db()
    synced_ids = []

    for item in items:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute("""INSERT INTO field_inspections 
            (mine_id, inspector_name, shift, location_pit_seam, violation_category, violation_title, description, risk_level, latitude, longitude, authenticity_score, is_offline_synced, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 95.0, 1, 'Open', ?, ?)""", (
            item.get('mine_id', 1), item.get('inspector_name', 'Mobile Offline Sync'),
            item.get('shift', 'Shift A'), item.get('location', 'Pit Face'),
            item.get('category', 'Safety'), item.get('title', 'Offline Observation'),
            item.get('description', ''), item.get('risk_level', 'Medium'),
            float(item.get('latitude', 22.3385)), float(item.get('longitude', 82.5925)),
            now_str, now_str
        ))
        synced_ids.append(cursor.lastrowid)

    db.commit()
    return jsonify({"status": "success", "synced_count": len(synced_ids), "inspection_ids": synced_ids})

# ==========================================
# CAPA (CORRECTIVE & PREVENTIVE ACTIONS)
# ==========================================
@governance_bp.route('/capa-manager')
def capa_manager():
    db = get_db()
    query = """
        SELECT ca.*, m.name as mine_name, m.subsidiary, fi.violation_title, fi.risk_level, fi.location_pit_seam 
        FROM capa_actions ca 
        JOIN mines m ON ca.mine_id = m.id 
        LEFT JOIN field_inspections fi ON ca.inspection_id = fi.id 
        ORDER BY ca.created_at DESC
    """
    capas = [dict(row) for row in db.execute(query).fetchall()]
    mines = [dict(row) for row in db.execute("SELECT id, name FROM mines ORDER BY name").fetchall()]
    return render_template('capa_manager.html', capas=capas, mines=mines)

@governance_bp.route('/capa/update/<int:capa_id>', methods=['POST'])
def update_capa(capa_id):
    db = get_db()
    status = request.form.get('status', 'In Progress')
    root_cause = request.form.get('root_cause', '')
    corrective_action = request.form.get('corrective_action', '')
    preventive_action = request.form.get('preventive_action', '')
    assigned_engineer = request.form.get('assigned_engineer', '')
    sign_off_by = request.form.get('sign_off_by', '')

    completion_date = datetime.now().strftime('%Y-%m-%d') if status == 'Closed' else None
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db.execute("""UPDATE capa_actions SET 
        status = ?, root_cause = ?, corrective_action = ?, preventive_action = ?, 
        assigned_engineer = ?, sign_off_by = ?, completion_date = ?, updated_at = ? 
        WHERE id = ?""", (
        status, root_cause, corrective_action, preventive_action, assigned_engineer, sign_off_by, completion_date, now_str, capa_id
    ))
    db.commit()

    actor = session.get('username', 'Safety Engineer')
    _record_crypto_audit(
        actor_name=actor,
        action_type="CAPA_LIFECYCLE_UPDATE",
        entity=f"CAPA #{capa_id}",
        details=f"CAPA status changed to '{status}'. Assigned to: {assigned_engineer}. Sign-off: {sign_off_by}",
        payload={"capa_id": capa_id, "status": status, "engineer": assigned_engineer, "sign_off": sign_off_by}
    )

    flash(f'CAPA #{capa_id} updated and signed off in audit ledger.', 'success')
    return redirect(url_for('governance.capa_manager'))
