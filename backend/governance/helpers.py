"""
Governance helper utilities:
- _record_crypto_audit: Helper to record an immutable SHA-256 block into the audit ledger.
"""

from flask import session
from database import get_db
from ai_engine.crypto_audit import CryptoAuditLedger

def _record_crypto_audit(actor_name: str, action_type: str, entity: str, details: str, payload: dict = None):
    """Helper to record an immutable SHA-256 block into the audit ledger."""
    try:
        db = get_db()
        last_block = db.execute("SELECT block_index, current_hash FROM audit_ledger ORDER BY block_index DESC LIMIT 1").fetchone()
        prev_hash = last_block['current_hash'] if last_block else CryptoAuditLedger.GENESIS_HASH
        next_index = (last_block['block_index'] + 1) if last_block else 1

        actor_id = str(session.get('user_id', 'SYSTEM'))
        entry = CryptoAuditLedger.create_audit_entry(
            previous_hash=prev_hash,
            block_index=next_index,
            actor_id=actor_id,
            actor_name=actor_name,
            action_type=action_type,
            entity_affected=entity,
            details=details,
            payload=payload
        )
        db.execute("""INSERT INTO audit_ledger (block_index, previous_hash, current_hash, timestamp, actor_id, actor_name, action_type, entity_affected, details, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            entry['block_index'], entry['previous_hash'], entry['current_hash'], entry['timestamp'],
            entry['actor_id'], entry['actor_name'], entry['action_type'], entry['entity_affected'],
            entry['details'], entry['payload_json']
        ))
        db.commit()
    except Exception as e:
        print(f"[CryptoAudit Error] Failed to write block: {e}")
