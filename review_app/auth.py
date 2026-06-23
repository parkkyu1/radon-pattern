from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping

import bcrypt

from .config import reviewer_definitions


def validate_access(
    reviewer_id: str, access_code: str, secrets: Mapping[str, Any]
) -> bool:
    reviewer = reviewer_definitions(secrets).get(reviewer_id)
    if not reviewer or not access_code:
        return False
    password_hash, _ = reviewer
    try:
        return bcrypt.checkpw(
            access_code.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def get_reviewer_role(reviewer_id: str, secrets: Mapping[str, Any]) -> str:
    reviewer = reviewer_definitions(secrets).get(reviewer_id)
    if not reviewer:
        raise ValueError("Unknown reviewer.")
    return reviewer[1]


def issue_session_token(reviewer_id: str, role: str, session_secret: str) -> str:
    payload = f"{reviewer_id}|{role}".encode()
    return hmac.new(session_secret.encode(), payload, hashlib.sha256).hexdigest()


def validate_session_token(
    reviewer_id: str, role: str, token: str, session_secret: str
) -> bool:
    expected = issue_session_token(reviewer_id, role, session_secret)
    return hmac.compare_digest(token, expected)
