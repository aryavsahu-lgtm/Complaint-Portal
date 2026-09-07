"""
Governance & Role-Based Dashboards Module:
- /dashboard (renders governance_dashboard.html)
- /manager-dashboard, /manager_dashboard (renders mine_manager_dashboard.html)
- /safety-dashboard, /safety_dashboard (renders safety_officer_dashboard.html)
- /inspector-dashboard, /inspector_dashboard (renders inspector_dashboard.html)
"""

from datetime import datetime
from flask import render_template, request
from database import get_db
from ai_engine.predictive_risk import PredictiveRiskEngine
from . import governance_bp

# ==========================================
# 1. CENTRAL GOVERNANCE COMMAND DASHBOARD
# ==========================================
@governance_bp.route('/dashboard')
def dashboard():
    db = get_db()
    filter_subsidiary = request.args.get('subsidiary', 'All')
    filter_mine = request.args.get('mine_id', 'All')

    # Base query for mines
    query_mines = "SELECT * FROM mines WHERE 1=1"
    params_mines = []
    if filter_subsidiary != 'All':
        query_mines += " AND subsidiary = ?"
        params_mines.append(filter_subsidiary)
    query_mines += " ORDER BY compliance_score DESC"
    mines = [dict(row) for row in db.execute(query_mines, params_mines).fetchall()]

    # Compliances
    query_comp = """
        SELECT sc.*, m.name as mine_name, m.subsidiary 
        FROM statutory_compliance sc 
        JOIN mines m ON sc.mine_id = m.id 
        WHERE 1=1
    """
    params_comp = []
    if filter_subsidiary != 'All':
        query_comp += " AND m.subsidiary = ?"
        params_comp.append(filter_subsidiary)
    if filter_mine != 'All':
        query_comp += " AND sc.mine_id = ?"
        params_comp.append(filter_mine)
    query_comp += " ORDER BY sc.risk_score DESC, sc.due_date ASC"
    compliances = [dict(row) for row in db.execute(query_comp, params_comp).fetchall()]

    # Field Inspections & Violations
    query_insp = """
        SELECT fi.*, m.name as mine_name, m.subsidiary 
        FROM field_inspections fi 
        JOIN mines m ON fi.mine_id = m.id 
        WHERE 1=1
    """
    params_insp = []
    if filter_subsidiary != 'All':
        query_insp += " AND m.subsidiary = ?"
        params_insp.append(filter_subsidiary)
    query_insp += " ORDER BY fi.created_at DESC"
    inspections = [dict(row) for row in db.execute(query_insp, params_insp).fetchall()]

    # CAPAs
    query_capa = """
        SELECT ca.*, m.name as mine_name, m.subsidiary 
        FROM capa_actions ca 
        JOIN mines m ON ca.mine_id = m.id 
        WHERE 1=1
    """
    params_capa = []
    if filter_subsidiary != 'All':
        query_capa += " AND m.subsidiary = ?"
        params_capa.append(filter_subsidiary)
    query_capa += " ORDER BY ca.created_at DESC"
    capas = [dict(row) for row in db.execute(query_capa, params_capa).fetchall()]

    # Telemetry Readings
    telemetry_rows = [dict(row) for row in db.execute("""
        SELECT mt.*, m.name as mine_name, m.subsidiary 
        FROM mine_telemetry mt 
        JOIN mines m ON mt.mine_id = m.id 
        ORDER BY mt.timestamp DESC LIMIT 10
    """).fetchall()]

    # Telemetry Anomaly Scan
    analyzed_telemetry = []
    total_anomalies = 0
    for tel in telemetry_rows:
        analysis = PredictiveRiskEngine.analyze_telemetry_reading(tel)
        tel['analysis'] = analysis
        if analysis['has_anomalies']:
            total_anomalies += analysis['anomalies_count']
        analyzed_telemetry.append(tel)

    # Recurring Pattern Detection
    recurring_patterns = PredictiveRiskEngine.predict_recurring_violations(inspections)

    # Overall Metrics
    total_mines = len(mines)
    total_statutory = len(compliances)
    compliant_count = sum(1 for c in compliances if c['status'] == 'Compliant')
    approaching_count = sum(1 for c in compliances if c['status'] == 'Approaching Deadline')
    breach_count = sum(1 for c in compliances if c['status'] in ['Critical Breach', 'Non-Compliant'])

    overall_compliance_pct = round((compliant_count / total_statutory * 100), 1) if total_statutory > 0 else 100.0

    # Overdue CAPAs
    overdue_capas = [c for c in capas if c['status'] != 'Closed' and c['target_date'] and c['target_date'] < datetime.now().strftime('%Y-%m-%d')]

    # Composite Index for primary mine or average
    composite_stats = PredictiveRiskEngine.calculate_mine_compliance_index(compliances, inspections, overdue_capas)

    # Subsidiary List for filter dropdown
    all_subsidiaries = ['SECL', 'MCL', 'BCCL', 'CCL', 'ECL', 'WCL', 'NCL', 'SCCL']

    return render_template('governance_dashboard.html',
                           mines=mines,
                           compliances=compliances,
                           inspections=inspections,
                           capas=capas,
                           telemetry=analyzed_telemetry,
                           total_mines=total_mines,
                           total_statutory=total_statutory,
                           compliant_count=compliant_count,
                           approaching_count=approaching_count,
                           breach_count=breach_count,
                           overall_compliance_pct=overall_compliance_pct,
                           overdue_capas_count=len(overdue_capas),
                           composite_stats=composite_stats,
                           recurring_patterns=recurring_patterns,
                           filter_subsidiary=filter_subsidiary,
                           filter_mine=filter_mine,
                           all_subsidiaries=all_subsidiaries)

# ==========================================
# 2. MINE MANAGER DEDICATED DASHBOARD
# ==========================================
@governance_bp.route('/manager-dashboard')
@governance_bp.route('/manager_dashboard')
def manager_dashboard():
    """
    Dedicated Mine Manager Executive Command:
    - Overall statutory compliance risk scorecard
    - Critical incident & high-risk breach alert stream
    - Mine comparison and benchmarking matrix
    - Historical compliance & safety trend analytics
    """
    db = get_db()
    filter_subsidiary = request.args.get('subsidiary', 'All')

    # Fetch all mines
    query_mines = "SELECT * FROM mines WHERE 1=1"
    params_mines = []
    if filter_subsidiary != 'All':
        query_mines += " AND subsidiary = ?"
        params_mines.append(filter_subsidiary)
    query_mines += " ORDER BY compliance_score DESC"
    mines = [dict(row) for row in db.execute(query_mines, params_mines).fetchall()]

    # Fetch Compliances
    compliances = [dict(row) for row in db.execute("""
        SELECT sc.*, m.name as mine_name, m.subsidiary 
        FROM statutory_compliance sc 
        JOIN mines m ON sc.mine_id = m.id 
        ORDER BY sc.risk_score DESC, sc.due_date ASC
    """).fetchall()]

    # Fetch Field Inspections (Violations)
    inspections = [dict(row) for row in db.execute("""
        SELECT fi.*, m.name as mine_name, m.subsidiary 
        FROM field_inspections fi 
        JOIN mines m ON fi.mine_id = m.id 
        ORDER BY fi.created_at DESC
    """).fetchall()]

    # Fetch CAPAs
    capas = [dict(row) for row in db.execute("""
        SELECT ca.*, m.name as mine_name, m.subsidiary 
        FROM capa_actions ca 
        JOIN mines m ON ca.mine_id = m.id 
        ORDER BY ca.created_at DESC
    """).fetchall()]

    # Critical Incidents (Critical / High risk violations + critical compliance breaches)
    critical_incidents = [
        insp for insp in inspections if insp.get('risk_level') in ['Critical', 'High']
    ]
    critical_statutory_breaches = [
        comp for comp in compliances if comp.get('status') in ['Critical Breach', 'Non-Compliant']
    ]

    # Calculate Multi-Mine Benchmark Summary
    mine_benchmarks = []
    for mine in mines:
        mine_id = mine['id']
        m_compliances = [c for c in compliances if c['mine_id'] == mine_id]
        m_inspections = [i for i in inspections if i['mine_id'] == mine_id]
        m_capas = [ca for ca in capas if ca['mine_id'] == mine_id]
        
        open_hazards = sum(1 for i in m_inspections if i['status'] in ['Open', 'Under Investigation'])
        critical_hazards = sum(1 for i in m_inspections if i.get('risk_level') == 'Critical')
        open_capas_count = sum(1 for ca in m_capas if ca['status'] != 'Closed')
        
        mine_benchmarks.append({
            'id': mine['id'],
            'name': mine['name'],
            'subsidiary': mine['subsidiary'],
            'area': mine['area'],
            'mine_type': mine['mine_type'],
            'capacity': mine.get('ec_capacity_mtpa', 0),
            'compliance_score': mine.get('compliance_score', 85.0),
            'safety_rating': mine.get('safety_rating', 4.5),
            'colliery_manager': mine.get('colliery_manager', 'Colliery GM'),
            'safety_officer': mine.get('safety_officer', 'Safety Head'),
            'open_hazards': open_hazards,
            'critical_hazards': critical_hazards,
            'open_capas': open_capas_count,
            'status': mine.get('status', 'Active')
        })

    # Overall Compliance Metrics
    total_stat = len(compliances)
    compliant_count = sum(1 for c in compliances if c['status'] == 'Compliant')
    overall_compliance_pct = round((compliant_count / total_stat * 100), 1) if total_stat > 0 else 92.4
    
    # 6-Month Trend Data for Charts
    trend_labels = ['Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026', 'Jul 2026', 'Aug 2026']
    trend_compliance = [84.2, 86.0, 88.5, 87.1, 90.8, overall_compliance_pct]
    trend_incidents = [14, 11, 9, 12, 7, len(critical_incidents)]

    # Category Distribution
    category_counts = {
        'Strata & Roof': sum(1 for i in inspections if 'Strata' in i.get('violation_category', '') or 'Safety' in i.get('violation_category', '')),
        'Gas & Ventilation': sum(1 for i in inspections if 'Ventilation' in i.get('violation_category', '') or 'Gas' in i.get('violation_category', '')),
        'HEMM & Haul Road': sum(1 for i in inspections if 'Equipment' in i.get('violation_category', '') or 'Haul' in i.get('violation_title', '')),
        'Environmental / Dust': sum(1 for i in inspections if 'Environment' in i.get('violation_category', '') or 'Dust' in i.get('violation_title', '')),
        'Electrical & Plant': sum(1 for i in inspections if 'Operations' in i.get('violation_category', ''))
    }

    all_subsidiaries = ['SECL', 'MCL', 'BCCL', 'CCL', 'ECL', 'WCL', 'NCL', 'SCCL']

    return render_template('mine_manager_dashboard.html',
                           mines=mines,
                           mine_benchmarks=mine_benchmarks,
                           compliances=compliances,
                           inspections=inspections,
                           capas=capas,
                           critical_incidents=critical_incidents,
                           critical_statutory_breaches=critical_statutory_breaches,
                           overall_compliance_pct=overall_compliance_pct,
                           total_mines_count=len(mines),
                           total_critical_count=len(critical_incidents) + len(critical_statutory_breaches),
                           total_open_capas=sum(1 for c in capas if c['status'] != 'Closed'),
                           trend_labels=trend_labels,
                           trend_compliance=trend_compliance,
                           trend_incidents=trend_incidents,
                           category_counts=category_counts,
                           filter_subsidiary=filter_subsidiary,
                           all_subsidiaries=all_subsidiaries)

# ==========================================
# 3. SAFETY OFFICER DEDICATED DASHBOARD
# ==========================================
@governance_bp.route('/safety-dashboard')
@governance_bp.route('/safety_dashboard')
def safety_dashboard():
    """
    Dedicated Safety Officer Hub:
    - Real-time live violations & pit hazard feed
    - Active incident & atmospheric IoT telemetry monitor (CH4, CO, Dust, Slope)
    - Corrective & Preventive Action (CAPA) lifecycle management
    - Contractor & workforce safety compliance tracking
    """
    db = get_db()
    filter_mine = request.args.get('mine_id', 'All')

    # Mines
    mines = [dict(row) for row in db.execute("SELECT id, name, subsidiary, area FROM mines ORDER BY name").fetchall()]

    # Violations (Field Inspections)
    query_insp = """
        SELECT fi.*, m.name as mine_name, m.subsidiary 
        FROM field_inspections fi 
        JOIN mines m ON fi.mine_id = m.id 
        WHERE 1=1
    """
    params_insp = []
    if filter_mine != 'All':
        query_insp += " AND fi.mine_id = ?"
        params_insp.append(filter_mine)
    query_insp += " ORDER BY fi.created_at DESC"
    violations = [dict(row) for row in db.execute(query_insp, params_insp).fetchall()]

    # CAPA Actions
    query_capa = """
        SELECT ca.*, m.name as mine_name, m.subsidiary, fi.violation_title, fi.risk_level, fi.location_pit_seam 
        FROM capa_actions ca 
        JOIN mines m ON ca.mine_id = m.id 
        LEFT JOIN field_inspections fi ON ca.inspection_id = fi.id 
        WHERE 1=1
    """
    params_capa = []
    if filter_mine != 'All':
        query_capa += " AND ca.mine_id = ?"
        params_capa.append(filter_mine)
    query_capa += " ORDER BY ca.created_at DESC"
    capas = [dict(row) for row in db.execute(query_capa, params_capa).fetchall()]

    # Real-Time Telemetry
    query_tel = """
        SELECT mt.*, m.name as mine_name, m.subsidiary 
        FROM mine_telemetry mt 
        JOIN mines m ON mt.mine_id = m.id 
        WHERE 1=1
    """
    params_tel = []
    if filter_mine != 'All':
        query_tel += " AND mt.mine_id = ?"
        params_tel.append(filter_mine)
    query_tel += " ORDER BY mt.timestamp DESC LIMIT 15"
    telemetry_rows = [dict(row) for row in db.execute(query_tel, params_tel).fetchall()]

    # Analyze telemetry for breaches
    analyzed_telemetry = []
    telemetry_breaches = []
    for tel in telemetry_rows:
        analysis = PredictiveRiskEngine.analyze_telemetry_reading(tel)
        tel['analysis'] = analysis
        if analysis['has_anomalies']:
            telemetry_breaches.append(tel)
        analyzed_telemetry.append(tel)

    # Contractors Safety Status
    contractors = [dict(row) for row in db.execute("""
        SELECT c.*, m.name as mine_name 
        FROM contractors c 
        JOIN mines m ON c.mine_id = m.id 
        ORDER BY c.safety_rating DESC
    """).fetchall()]

    # Summary Counts
    crit_violations = sum(1 for v in violations if v.get('risk_level') == 'Critical')
    high_violations = sum(1 for v in violations if v.get('risk_level') == 'High')
    open_capas_count = sum(1 for c in capas if c.get('status') != 'Closed')
    active_hazard_count = len(telemetry_breaches)

    # ---------------------------------------------
    # Spotting Risky Areas (Pandas)
    # ---------------------------------------------
    hotspots = []
    try:
        import pandas as pd
        if violations:
            df = pd.DataFrame(violations)
            risk_counts = df.groupby(['mine_name', 'location_pit_seam']).size().reset_index(name='count')
            risk_counts = risk_counts.sort_values('count', ascending=False).head(5)
            hotspots = risk_counts.to_dict('records')
    except Exception as e:
        print(f"Hotspot calculation failed: {e}")

    return render_template('safety_officer_dashboard.html',
                           mines=mines,
                           violations=violations,
                           capas=capas,
                           telemetry=analyzed_telemetry,
                           telemetry_breaches=telemetry_breaches,
                           contractors=contractors,
                           crit_violations=crit_violations,
                           high_violations=high_violations,
                           open_capas_count=open_capas_count,
                           active_hazard_count=active_hazard_count,
                           hotspots=hotspots,
                           filter_mine=filter_mine)

# ==========================================
# 4. INSPECTOR DEDICATED DASHBOARD (DGMS)
# ==========================================
@governance_bp.route('/inspector-dashboard')
@governance_bp.route('/inspector_dashboard')
def inspector_dashboard():
    """
    Dedicated Inspector Portal (DGMS / Statutory Auditor):
    - Digital inspection checklist (CMR 2017 & Mines Act 1952)
    - Geo-tagged photo/audio evidence management with authenticity score
    - Historical violations & contravention archive
    - Daily compliance status & statutory report / notice generator
    """
    db = get_db()
    filter_mine = request.args.get('mine_id', 'All')
    filter_category = request.args.get('category', 'All')

    mines = [dict(row) for row in db.execute("SELECT id, name, subsidiary, area, latitude, longitude FROM mines ORDER BY name").fetchall()]

    # Field Inspections / Historical Violations
    query_insp = """
        SELECT fi.*, m.name as mine_name, m.subsidiary, m.area 
        FROM field_inspections fi 
        JOIN mines m ON fi.mine_id = m.id 
        WHERE 1=1
    """
    params_insp = []
    if filter_mine != 'All':
        query_insp += " AND fi.mine_id = ?"
        params_insp.append(filter_mine)
    if filter_category != 'All':
        query_insp += " AND fi.violation_category = ?"
        params_insp.append(filter_category)
    query_insp += " ORDER BY fi.created_at DESC"
    historical_violations = [dict(row) for row in db.execute(query_insp, params_insp).fetchall()]

    # Statutory Compliance Daily Status
    compliances = [dict(row) for row in db.execute("""
        SELECT sc.*, m.name as mine_name, m.subsidiary 
        FROM statutory_compliance sc 
        JOIN mines m ON sc.mine_id = m.id 
        ORDER BY sc.due_date ASC
    """).fetchall()]

    # Audit Blocks for Evidence Integrity
    audit_blocks = [dict(row) for row in db.execute("""
        SELECT * FROM audit_ledger ORDER BY block_index DESC LIMIT 8
    """).fetchall()]

    total_audited = len(historical_violations)
    critical_contraventions = sum(1 for v in historical_violations if v.get('risk_level') in ['Critical', 'High'])
    verified_evidence_count = sum(1 for v in historical_violations if v.get('photo_attachment') or v.get('authenticity_score', 0) > 90)

    return render_template('inspector_dashboard.html',
                           mines=mines,
                           historical_violations=historical_violations,
                           compliances=compliances,
                           audit_blocks=audit_blocks,
                           total_audited=total_audited,
                           critical_contraventions=critical_contraventions,
                           verified_evidence_count=verified_evidence_count,
                           filter_mine=filter_mine,
                           filter_category=filter_category,
                           current_date=datetime.now().strftime('%d %b %Y'))
