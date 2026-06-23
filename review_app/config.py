from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    order_seed: str
    session_secret: str


def normalize_database_url(value: str) -> str:
    """Accept Supabase's postgres/postgresql URL and select psycopg 3."""
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


def _get(mapping: Mapping[str, Any] | None, key: str, default: Any = None) -> Any:
    return mapping.get(key, default) if mapping is not None else default


def load_config(secrets: Mapping[str, Any] | None = None) -> AppConfig:
    database_url = normalize_database_url(
        str(_get(secrets, "DATABASE_URL", "") or os.getenv("DATABASE_URL", ""))
    )
    auth = _get(secrets, "auth", {}) or {}
    order_seed = str(auth.get("order_seed", os.getenv("ORDER_SEED", "")))
    session_secret = str(auth.get("session_secret", os.getenv("SESSION_SECRET", "")))
    missing = [
        name
        for name, value in (
            ("DATABASE_URL", database_url),
            ("auth.order_seed", order_seed),
            ("auth.session_secret", session_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("Missing deployment configuration: " + ", ".join(missing))
    return AppConfig(database_url, order_seed, session_secret)


def reviewer_definitions(secrets: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    hashes = secrets.get("reviewers", {})
    roles = secrets.get("reviewer_roles", {})
    result: dict[str, tuple[str, str]] = {}
    for reviewer_id, password_hash in hashes.items():
        role = str(roles.get(reviewer_id, "")).lower()
        if role not in {"primary", "adjudicator", "admin"}:
            raise RuntimeError(f"Invalid or missing role for {reviewer_id}.")
        result[str(reviewer_id)] = (str(password_hash), role)
    return result
