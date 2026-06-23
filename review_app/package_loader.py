from __future__ import annotations

from pathlib import Path

import pandas as pd

from .security import assert_public_package_safe


def load_public_cases(public_dir: Path) -> pd.DataFrame:
    assert_public_package_safe(public_dir)
    frame = pd.read_csv(public_dir / "review_cases_public.csv")
    frame["review_case_id"] = frame["review_case_id"].astype(str)
    frame["image_filename"] = frame["image_filename"].astype(str)
    return frame

