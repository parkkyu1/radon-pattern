from __future__ import annotations

from pathlib import Path

import pandas as pd

PUBLIC_COLUMNS = ("review_case_id", "image_filename")
FORBIDDEN_COLUMNS = (
    "pattern_id",
    "sn",
    "floor",
    "date",
    "time",
    "algorithm",
    "qc",
    "recon",
    "latent",
    "ach",
    "cluster",
    "emission",
)
FORBIDDEN_NAMES = ("private", "mapping", "secret", "sqlite", "manifest", "raw")


def assert_public_package_safe(public_dir: Path) -> None:
    csv_path = public_dir / "review_cases_public.csv"
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    frame = pd.read_csv(csv_path)
    if tuple(frame.columns) != PUBLIC_COLUMNS:
        raise ValueError(f"Public CSV columns must be exactly {PUBLIC_COLUMNS}.")
    for path in public_dir.rglob("*"):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if any(token in lower for token in FORBIDDEN_NAMES):
            raise RuntimeError(f"Forbidden file in public package: {path}")
    lowered_columns = [column.lower() for column in frame.columns]
    leaked = [
        column
        for column in lowered_columns
        if any(token in column for token in FORBIDDEN_COLUMNS)
    ]
    if leaked:
        raise RuntimeError(f"Forbidden public columns: {leaked}")
    expected = set(frame["image_filename"].astype(str))
    actual = {path.name for path in (public_dir / "images").glob("*.png")}
    if expected != actual:
        raise RuntimeError("Public CSV and PNG file set do not match.")

