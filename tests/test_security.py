from pathlib import Path

import pandas as pd
import pytest

from review_app.security import assert_public_package_safe


def test_real_public_package_is_safe() -> None:
    public = Path(__file__).resolve().parents[1] / "review_package" / "public"
    assert_public_package_safe(public)
    frame = pd.read_csv(public / "review_cases_public.csv")
    assert frame.columns.tolist() == ["review_case_id", "image_filename"]


def test_private_file_in_public_fails(tmp_path: Path) -> None:
    public = tmp_path / "public"
    images = public / "images"
    images.mkdir(parents=True)
    pd.DataFrame(
        {"review_case_id": ["R001"], "image_filename": ["R001.png"]}
    ).to_csv(public / "review_cases_public.csv", index=False)
    (images / "R001.png").write_bytes(b"png")
    (public / "private_mapping.csv").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError):
        assert_public_package_safe(public)

