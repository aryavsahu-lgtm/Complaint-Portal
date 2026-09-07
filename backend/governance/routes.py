"""
Backward-compatibility stub for governance routes.

The routes in this module have been modularized and separated to match the frontend templates:
- dashboards.py           -> governance_dashboard.html, mine_manager_dashboard.html, safety_officer_dashboard.html, inspector_dashboard.html
- statutory_compliance.py -> statutory_register.html, statutory_reports.html, PDF report generator, AI statute query
- inspections.py          -> field_inspection.html, capa_manager.html, offline PWA sync
- contractors.py          -> contractor_hub.html & contractor management
- ocr_scanner.py          -> ocr_scanner.html & document digitization
- gis_map.py              -> gis_map.html & interactive GIS mine map
- crypto_audit.py         -> crypto_audit.html & SHA-256 ledger
- helpers.py              -> cryptographic audit logging helper
"""

from . import governance_bp
from .helpers import _record_crypto_audit

__all__ = ['governance_bp', '_record_crypto_audit']
