from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_app.security import assert_public_package_safe

FORBIDDEN_PARTS = {
    ".streamlit/secrets.toml",
    "review_package/private",
    "data",
    "logs",
    "exports",
    "offline_merged",
    "__pycache__",
    ".pytest_cache",
}
FORBIDDEN_NAMES = {
    "expert_review_key_private.csv",
    "qc_assessment_all.csv",
    "processed_radon_data1.csv",
}


def main() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT).as_posix()
        if any(relative == part or relative.startswith(part + "/") for part in FORBIDDEN_PARTS):
            failures.append(f"forbidden path: {relative}")
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in {".sqlite", ".zip"}:
            failures.append(f"forbidden file: {relative}")
    try:
        assert_public_package_safe(ROOT / "review_package" / "public")
    except Exception as error:
        failures.append(f"public package: {error}")

    credential_pattern = re.compile(
        r"postgresql(?:\+psycopg)?://(?!USER:PASSWORD@)[^\"'\s]+", re.IGNORECASE
    )
    bcrypt_pattern = re.compile(r"\$2[aby]\$\d{2}\$[A-Za-z0-9./]{53}")
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if credential_pattern.search(text):
            failures.append(f"possible hard-coded database URL: {path.relative_to(ROOT)}")
        if bcrypt_pattern.search(text):
            failures.append(f"possible real bcrypt hash in code: {path.relative_to(ROOT)}")
    if failures:
        print("\n".join(f"FAIL: {item}" for item in failures))
        raise SystemExit(1)
    print("Deployment bundle security verification passed.")


if __name__ == "__main__":
    main()
