"""
Cryptographic Audit Ledger Engine
Provides SHA-256 hash-chained immutable logging for statutory actions,
field inspection sign-offs, and compliance modifications.
"""

import hashlib
import json
from datetime import datetime

class CryptoAuditLedger:
    """Manages tamper-evident hash chains for mining governance actions."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def calculate_block_hash(cls, index: int, previous_hash: str, timestamp: str, actor_id: str, action_type: str, payload_data: dict) -> str:
        """
        Generates SHA-256 digest of block contents.
        """
        payload_string = json.dumps(payload_data, sort_keys=True)
        block_content = f"{index}|{previous_hash}|{timestamp}|{actor_id}|{action_type}|{payload_string}"
        return hashlib.sha256(block_content.encode('utf-8')).hexdigest()

    @classmethod
    def create_audit_entry(cls, previous_hash: str, block_index: int, actor_id: str, actor_name: str, action_type: str, entity_affected: str, details: str, payload: dict = None) -> dict:
        """
        Creates a new cryptographically verified audit block.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = payload or {}
        payload['entity_affected'] = entity_affected
        payload['details'] = details
        payload['actor_name'] = actor_name

        current_hash = cls.calculate_block_hash(
            index=block_index,
            previous_hash=previous_hash or cls.GENESIS_HASH,
            timestamp=timestamp,
            actor_id=str(actor_id),
            action_type=action_type,
            payload_data=payload
        )

        return {
            'block_index': block_index,
            'previous_hash': previous_hash or cls.GENESIS_HASH,
            'current_hash': current_hash,
            'timestamp': timestamp,
            'actor_id': str(actor_id),
            'actor_name': actor_name,
            'action_type': action_type,
            'entity_affected': entity_affected,
            'details': details,
            'payload_json': json.dumps(payload)
        }

    @classmethod
    def verify_chain_integrity(cls, blocks: list) -> dict:
        """
        Verifies if the entire cryptographic hash chain is valid and untampered.
        """
        if not blocks:
            return {'is_valid': True, 'total_blocks': 0, 'tampered_block_index': None}

        sorted_blocks = sorted(blocks, key=lambda b: b.get('block_index', 0))

        for i, block in enumerate(sorted_blocks):
            # Check previous hash link
            if i > 0:
                expected_prev = sorted_blocks[i - 1].get('current_hash')
                if block.get('previous_hash') != expected_prev:
                    return {
                        'is_valid': False,
                        'total_blocks': len(sorted_blocks),
                        'tampered_block_index': block.get('block_index'),
                        'error': f"Hash chain broken at block #{block.get('block_index')}. Expected prev_hash {expected_prev[:12]}..., found {block.get('previous_hash')[:12]}..."
                    }

            # Recalculate hash to ensure data hasn't been altered
            try:
                payload = json.loads(block.get('payload_json', '{}')) if isinstance(block.get('payload_json'), str) else (block.get('payload_json') or {})
            except:
                payload = {}

            calculated = cls.calculate_block_hash(
                index=block.get('block_index'),
                previous_hash=block.get('previous_hash'),
                timestamp=block.get('timestamp'),
                actor_id=str(block.get('actor_id')),
                action_type=block.get('action_type'),
                payload_data=payload
            )

            if calculated != block.get('current_hash'):
                return {
                    'is_valid': False,
                    'total_blocks': len(sorted_blocks),
                    'tampered_block_index': block.get('block_index'),
                    'error': f"Cryptographic integrity failed at block #{block.get('block_index')}. Content modified."
                }

        return {
            'is_valid': True,
            'total_blocks': len(sorted_blocks),
            'tampered_block_index': None,
            'latest_hash': sorted_blocks[-1].get('current_hash') if sorted_blocks else cls.GENESIS_HASH
        }
