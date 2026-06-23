import bcrypt

from review_app.auth import (
    get_reviewer_role,
    issue_session_token,
    validate_access,
    validate_session_token,
)


def test_bcrypt_individual_access_code() -> None:
    password_hash = bcrypt.hashpw(b"unique-code-123", bcrypt.gensalt()).decode()
    secrets = {
        "reviewers": {"reviewer_a": password_hash},
        "reviewer_roles": {"reviewer_a": "primary"},
    }
    assert validate_access("reviewer_a", "unique-code-123", secrets)
    assert not validate_access("reviewer_a", "wrong-code", secrets)
    assert get_reviewer_role("reviewer_a", secrets) == "primary"
    token = issue_session_token("reviewer_a", "primary", "session-secret")
    assert validate_session_token(
        "reviewer_a", "primary", token, "session-secret"
    )
    assert not validate_session_token(
        "reviewer_b", "primary", token, "session-secret"
    )
