"""Version helpers for canonical TEP records."""

from __future__ import annotations


CURRENT_RECORD_CONTRACT_VERSION = "0.4"
CURRENT_RECORD_VERSION = 1
SUPPORTED_RECORD_CONTRACT_VERSIONS = {CURRENT_RECORD_CONTRACT_VERSION}
RECORD_VERSION_REQUIRED_TYPES = {"map"}


def record_contract_version(record: dict) -> str:
    """Return the canonical record contract version."""

    return str(record.get("contract_version", "")).strip()


def is_current_record_contract(record: dict) -> bool:
    return record_contract_version(record) == CURRENT_RECORD_CONTRACT_VERSION


def validate_record_version(record_type: str, record: dict) -> list[str]:
    errors: list[str] = []

    contract_version = record_contract_version(record)
    if contract_version and contract_version not in SUPPORTED_RECORD_CONTRACT_VERSIONS:
        errors.append(f"unsupported contract_version: {contract_version}")

    raw_record_version = record.get("record_version")
    if raw_record_version is None:
        if record_type in RECORD_VERSION_REQUIRED_TYPES:
            errors.append(f"{record_type} record_version is required")
        return errors
    if not contract_version:
        errors.append("contract_version is required when record_version is set")

    if isinstance(raw_record_version, bool) or not isinstance(raw_record_version, int):
        errors.append("record_version must be a positive integer")
        return errors
    if raw_record_version <= 0:
        errors.append("record_version must be a positive integer")
    if raw_record_version > CURRENT_RECORD_VERSION:
        errors.append(f"unsupported record_version: {raw_record_version}")
    return errors
