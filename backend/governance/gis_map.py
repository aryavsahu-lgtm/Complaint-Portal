"""
Interactive GIS Mine Map Module:
- /gis-map, /gis_map (renders gis_map.html)
"""

from flask import render_template
from database import get_db
from . import governance_bp

@governance_bp.route('/gis-map')
@governance_bp.route('/gis_map')
def gis_map():
    db = get_db()
    mines = [dict(row) for row in db.execute("SELECT * FROM mines").fetchall()]
    inspections = [dict(row) for row in db.execute("""
        SELECT fi.*, m.name as mine_name, m.subsidiary 
        FROM field_inspections fi 
        JOIN mines m ON fi.mine_id = m.id
    """).fetchall()]
    return render_template('gis_map.html', mines=mines, inspections=inspections)
