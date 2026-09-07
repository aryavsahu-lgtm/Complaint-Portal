"""
Contractors & Workforce Safety Hub Module:
- /contractor-hub (renders contractor_hub.html)
- /contractor/add
"""

from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from database import get_db
from . import governance_bp

@governance_bp.route('/contractor-hub')
def contractor_hub():
    db = get_db()
    query = """
        SELECT c.*, m.name as mine_name, m.subsidiary 
        FROM contractors c 
        JOIN mines m ON c.mine_id = m.id 
        ORDER BY c.safety_rating DESC, c.compliance_score DESC
    """
    contractors = [dict(row) for row in db.execute(query).fetchall()]
    mines = [dict(row) for row in db.execute("SELECT id, name FROM mines ORDER BY name").fetchall()]
    return render_template('contractor_hub.html', contractors=contractors, mines=mines)

@governance_bp.route('/contractor/add', methods=['POST'])
def add_contractor():
    db = get_db()
    company_name = request.form.get('company_name')
    license_no = request.form.get('license_no')
    subsidiary = request.form.get('subsidiary', 'SECL')
    mine_id = request.form.get('mine_id', 1)
    contact_person = request.form.get('contact_person')
    contact_phone = request.form.get('contact_phone')
    active_workers = int(request.form.get('active_workers', 50))
    safety_rating = float(request.form.get('safety_rating', 4.5))
    compliance_score = float(request.form.get('compliance_score', 90.0))
    vtc_training_pct = float(request.form.get('vtc_training_pct', 95.0))
    form_o_medical_pct = float(request.form.get('form_o_medical_pct', 95.0))
    license_expiry = request.form.get('license_expiry', '2028-12-31')

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute("""INSERT INTO contractors 
        (company_name, license_no, subsidiary, mine_id, contact_person, contact_phone, active_workers, safety_rating, compliance_score, pf_esi_compliant, vtc_training_pct, form_o_medical_pct, license_expiry, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""", (
        company_name, license_no, subsidiary, mine_id, contact_person, contact_phone, active_workers, safety_rating, compliance_score, vtc_training_pct, form_o_medical_pct, license_expiry, now_str
    ))
    db.commit()

    flash(f"Contractor '{company_name}' registered successfully.", 'success')
    return redirect(url_for('governance.contractor_hub'))
