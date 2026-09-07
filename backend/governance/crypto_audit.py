"""
Immutable SHA-256 Crypto Audit Ledger Module:
- /crypto-audit, /crypto_audit, /crypto_ledger, /crypto-ledger (renders crypto_audit.html)
"""

from flask import render_template
from database import get_db
from ai_engine.crypto_audit import CryptoAuditLedger
from . import governance_bp

@governance_bp.route('/crypto-audit')
@governance_bp.route('/crypto_audit')
@governance_bp.route('/crypto_ledger')
@governance_bp.route('/crypto-ledger')
def crypto_audit():
    db = get_db()
    blocks = [dict(row) for row in db.execute("SELECT * FROM audit_ledger ORDER BY block_index ASC").fetchall()]
    integrity = CryptoAuditLedger.verify_chain_integrity(blocks)
    return render_template('crypto_audit.html', blocks=reversed(blocks), integrity=integrity)
