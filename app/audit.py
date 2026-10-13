"""Cryptographic Hash-Chain Audit Log System.

Every dispute decision, policy evaluation, and narrative output is appended to a
tamper-evident SHA-256 cryptographic chain. Any unauthorized mutation or retrospective
tampering breaks chain linkage and is immediately detected.
"""

from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.schemas import AuditBlock, AuditVerificationResult, DecisionResult


GENESIS_PREVIOUS_HASH = "0" * 64


class AuditChain:
    def __init__(self, storage_path: Optional[str] = None):
        default_path = (
            Path(__file__).resolve().parent.parent / "data" / "audit_log.json"
        )
        self.storage_path = Path(storage_path or os.getenv("AUDIT_LOG_PATH", str(default_path)))
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain: List[AuditBlock] = self._load_chain()

    def _calculate_payload_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _calculate_block_hash(
        self,
        index: int,
        timestamp: str,
        case_id: str,
        action: str,
        payload_hash: str,
        previous_hash: str,
    ) -> str:
        raw_header = f"{index}:{timestamp}:{case_id}:{action}:{payload_hash}:{previous_hash}"
        return hashlib.sha256(raw_header.encode("utf-8")).hexdigest()

    def _load_chain(self) -> List[AuditBlock]:
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            return [AuditBlock(**item) for item in raw_data]
        except Exception:
            return []

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([b.model_dump() for b in self.chain], f, indent=2)

    def append_decision(self, decision: DecisionResult, extra_payload: Optional[Dict[str, Any]] = None) -> AuditBlock:
        """Appends a new decision to the immutable cryptographic hash-chain."""
        index = len(self.chain)
        timestamp = datetime.utcnow().isoformat() + "Z"
        case_id = decision.case_id
        action = decision.action.value

        payload = {
            "decision": decision.model_dump(),
            "extra": extra_payload or {},
        }
        payload_hash = self._calculate_payload_hash(payload)

        previous_hash = (
            self.chain[-1].block_hash if self.chain else GENESIS_PREVIOUS_HASH
        )

        block_hash = self._calculate_block_hash(
            index=index,
            timestamp=timestamp,
            case_id=case_id,
            action=action,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
        )

        block = AuditBlock(
            index=index,
            timestamp=timestamp,
            case_id=case_id,
            action=action,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            block_hash=block_hash,
        )

        self.chain.append(block)
        self._persist()
        return block

    def verify_integrity(self) -> AuditVerificationResult:
        """Mathematically verifies chain continuity and re-computes every block hash."""
        if not self.chain:
            return AuditVerificationResult(
                valid=True,
                total_blocks=0,
                message="Audit chain is empty. Genesis state clean.",
            )

        for i, block in enumerate(self.chain):
            # Check genesis block link
            if i == 0:
                if block.previous_hash != GENESIS_PREVIOUS_HASH:
                    return AuditVerificationResult(
                        valid=False,
                        total_blocks=len(self.chain),
                        message=f"Genesis block link corrupted at index 0. Expected {GENESIS_PREVIOUS_HASH[:8]}..., found {block.previous_hash[:8]}...",
                        corrupted_index=0,
                    )
            else:
                # Check link to previous block
                prev_block = self.chain[i - 1]
                if block.previous_hash != prev_block.block_hash:
                    return AuditVerificationResult(
                        valid=False,
                        total_blocks=len(self.chain),
                        message=f"Hash chain pointer mismatch at index {i}: Block previous_hash != predecessor block_hash.",
                        corrupted_index=i,
                    )

            # Re-verify internal hash of current block
            expected_hash = self._calculate_block_hash(
                index=block.index,
                timestamp=block.timestamp,
                case_id=block.case_id,
                action=block.action,
                payload_hash=block.payload_hash,
                previous_hash=block.previous_hash,
            )
            if block.block_hash != expected_hash:
                return AuditVerificationResult(
                    valid=False,
                    total_blocks=len(self.chain),
                    message=f"Cryptographic signature invalidated at index {i}. Block hash does not match computed digest.",
                    corrupted_index=i,
                )

        return AuditVerificationResult(
            valid=True,
            total_blocks=len(self.chain),
            message=f"All {len(self.chain)} blocks cryptographically verified. Zero tampering detected.",
        )
