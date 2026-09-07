"""
Statutory Compliance & Reporting Module:
- /statutory-register (renders statutory_register.html)
- /statutory-register/add
- /statutory-register/update-status/<item_id>
- /statutory-reports (renders statutory_reports.html)
- /download_report (generates downloadable compliance PDF)
- /api/query-statute (AI statutory query API)
"""

import os
import sys
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_file
from database import get_db
from utils import login_required
from ai_engine.statutory_bot import StatutoryBotEngine
from . import governance_bp
from .helpers import _record_crypto_audit

# Add parent directory to path so we can import report_generator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from report_generator import generate_compliance_report
except ImportError:
    pass

# ==========================================
# REPORT GENERATION (AUTO-REPORTS)
# ==========================================
@governance_bp.route('/download_report')
@login_required
def download_report():
    db = get_db()
    
    # Fetch latest high risk violations
    violations = [dict(row) for row in db.execute("""
        SELECT fi.*, m.name as mine_name 
        FROM field_inspections fi 
        LEFT JOIN mines m ON fi.mine_id = m.id 
        WHERE fi.status != 'Resolved' AND fi.risk_level IN ('Critical', 'High')
        ORDER BY fi.created_at DESC LIMIT 10
    """).fetchall()]
    
    # Fetch recent escalations from complaints
    escalations = [dict(row) for row in db.execute("""
        SELECT id, title, updated_at, status 
        FROM complaints 
        WHERE is_escalated = 1 AND status != 'Resolved'
        ORDER BY updated_at DESC LIMIT 10
    """).fetchall()]
    
    data = {
        'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'violations': violations,
        'escalations': escalations
    }
    
    report_filename = f"Compliance_Report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
    os.makedirs(upload_folder, exist_ok=True)
    report_path = os.path.join(upload_folder, report_filename)
    
    try:
        generate_compliance_report(data, report_path)
        return send_file(report_path, as_attachment=True)
    except Exception as e:
        flash(f"Failed to generate report: {e}", "danger")
        return redirect(url_for('governance.safety_dashboard'))

# ==========================================
# STATUTORY COMPLIANCE REGISTER
# ==========================================
@governance_bp.route('/statutory-register')
def statutory_register():
    db = get_db()
    filter_body = request.args.get('body', 'All')
    filter_category = request.args.get('category', 'All')
    filter_status = request.args.get('status', 'All')
    search_query = request.args.get('q', '').strip()

    query = """
        SELECT sc.*, m.name as mine_name, m.subsidiary, m.area 
        FROM statutory_compliance sc 
        JOIN mines m ON sc.mine_id = m.id 
        WHERE 1=1
    """
    params = []
    if filter_body != 'All':
        query += " AND sc.regulatory_body = ?"
        params.append(filter_body)
    if filter_category != 'All':
        query += " AND sc.category = ?"
        params.append(filter_category)
    if filter_status != 'All':
        query += " AND sc.status = ?"
        params.append(filter_status)
    if search_query:
        query += " AND (sc.title LIKE ? OR sc.regulation_ref LIKE ? OR m.name LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += " ORDER BY sc.risk_score DESC, sc.due_date ASC"
    items = [dict(row) for row in db.execute(query, params).fetchall()]
    mines = [dict(row) for row in db.execute("SELECT id, name, subsidiary FROM mines ORDER BY name").fetchall()]

    return render_template('statutory_register.html',
                           compliances=items,
                           mines=mines,
                           filter_body=filter_body,
                           filter_category=filter_category,
                           filter_status=filter_status,
                           search_query=search_query)

@governance_bp.route('/statutory-register/add', methods=['POST'])
def add_statutory_obligation():
    db = get_db()
    mine_id = request.form.get('mine_id')
    regulatory_body = request.form.get('regulatory_body', 'DGMS')
    regulation_ref = request.form.get('regulation_ref', '')
    title = request.form.get('title', '')
    category = request.form.get('category', 'Safety')
    frequency = request.form.get('frequency', 'Annual')
    due_date = request.form.get('due_date', '')
    responsible_officer = request.form.get('responsible_officer', '')
    risk_score = float(request.form.get('risk_score', 20.0))
    remarks = request.form.get('remarks', '')

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = db.execute("""INSERT INTO statutory_compliance 
        (mine_id, regulatory_body, regulation_ref, title, category, frequency, due_date, status, risk_score, responsible_officer, remarks, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Compliant', ?, ?, ?, ?, ?)""", (
        mine_id, regulatory_body, regulation_ref, title, category, frequency, due_date, risk_score, responsible_officer, remarks, now_str, now_str
    ))
    db.commit()
    comp_id = cursor.lastrowid

    # Record Cryptographic Audit Ledger
    actor = session.get('username', 'Statutory Officer')
    _record_crypto_audit(
        actor_name=actor,
        action_type="STATUTORY_OBLIGATION_CREATED",
        entity=f"Statutory Obligation #{comp_id}: {regulation_ref}",
        details=f"Created obligation '{title}' under {regulatory_body} for Mine ID {mine_id}.",
        payload={"obligation_id": comp_id, "ref": regulation_ref, "due_date": due_date, "risk_score": risk_score}
    )

    flash('New statutory compliance requirement registered and cryptographic block created.', 'success')
    return redirect(url_for('governance.statutory_register'))

@governance_bp.route('/statutory-register/update-status/<int:item_id>', methods=['POST'])
def update_statutory_status(item_id):
    db = get_db()
    new_status = request.form.get('status', 'Compliant')
    remarks = request.form.get('remarks', '')
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db.execute("UPDATE statutory_compliance SET status = ?, remarks = ?, updated_at = ? WHERE id = ?", (new_status, remarks, now_str, item_id))
    db.commit()

    actor = session.get('username', 'Safety Auditor')
    _record_crypto_audit(
        actor_name=actor,
        action_type="STATUTORY_STATUS_CHANGED",
        entity=f"Statutory Obligation #{item_id}",
        details=f"Status updated to '{new_status}'. Remarks: {remarks}",
        payload={"item_id": item_id, "new_status": new_status, "remarks": remarks}
    )

    flash('Statutory compliance status updated.', 'success')
    return redirect(url_for('governance.statutory_register'))

# ==========================================
# STATUTORY REPORTS
# ==========================================
@governance_bp.route('/statutory-reports')
def statutory_reports():
    db = get_db()
    report_type = request.args.get('type', 'form_iv')
    mine_id = request.args.get('mine_id', 1)

    mine = dict(db.execute("SELECT * FROM mines WHERE id = ?", (mine_id,)).fetchone() or {})
    compliances = [dict(row) for row in db.execute("SELECT * FROM statutory_compliance WHERE mine_id = ?", (mine_id,)).fetchall()]
    inspections = [dict(row) for row in db.execute("SELECT * FROM field_inspections WHERE mine_id = ? ORDER BY created_at DESC", (mine_id,)).fetchall()]
    contractors = [dict(row) for row in db.execute("SELECT * FROM contractors WHERE mine_id = ?", (mine_id,)).fetchall()]
    telemetry = [dict(row) for row in db.execute("SELECT * FROM mine_telemetry WHERE mine_id = ? ORDER BY timestamp DESC LIMIT 5", (mine_id,)).fetchall()]
    mines = [dict(row) for row in db.execute("SELECT id, name, subsidiary FROM mines ORDER BY name").fetchall()]

    return render_template('statutory_reports.html',
                           report_type=report_type,
                           mine=mine,
                           mines=mines,
                           compliances=compliances,
                           inspections=inspections,
                           contractors=contractors,
                           telemetry=telemetry,
                           current_date=datetime.now().strftime('%d-%m-%Y'))

# ==========================================
# AI STATUTORY BOT QUERY API
# ==========================================
@governance_bp.route('/api/query-statute', methods=['POST'])
def api_query_statute():
    data = request.get_json() or {}
    query = data.get('query', '')
    res = StatutoryBotEngine.query_statute(query)
    return jsonify(res)
