"""
Public Information Pages:
- /departments (renders departments.html)
- /services (renders services.html)
- /get_stats (API for quick metrics)
"""

from flask import render_template, jsonify
from database import get_db
from . import complaints_bp

@complaints_bp.route('/departments')
def departments():
    govt_departments = [
        {'id': 'safety', 'icon': 'bi-shield-exclamation', 'image': 'images/mine_safety_strata.jpg'},
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

@complaints_bp.route('/get_stats')
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    return jsonify({"total": total})
