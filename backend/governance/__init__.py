"""
Governance Blueprint Package.
Sub-modules are aligned 1-to-1 with frontend templates for maintainability:
- dashboards.py           -> governance_dashboard.html, mine_manager_dashboard.html, safety_officer_dashboard.html, inspector_dashboard.html
- statutory_compliance.py -> statutory_register.html, statutory_reports.html, PDF report generator, AI statute query
- inspections.py          -> field_inspection.html, capa_manager.html, offline PWA sync
- contractors.py          -> contractor_hub.html & contractor management
- ocr_scanner.py          -> ocr_scanner.html & document digitization
- gis_map.py              -> gis_map.html & interactive GIS mine map
- crypto_audit.py         -> crypto_audit.html & SHA-256 ledger
- helpers.py              -> cryptographic audit logging helper
"""

from flask import Blueprint

governance_bp = Blueprint('governance', __name__, url_prefix='/governance')

# Import modular route handlers so their routes are registered on governance_bp
from . import helpers
from . import dashboards
from . import statutory_compliance
from . import inspections
from . import contractors
from . import ocr_scanner
from . import gis_map
from . import crypto_audit

__all__ = ['governance_bp']
