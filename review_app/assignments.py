from __future__ import annotations

import hashlib
import random


def deterministic_case_order(
    reviewer_id: str, case_ids: list[str], order_seed: str
) -> list[str]:
    digest = hashlib.sha256(f"{order_seed}|{reviewer_id}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    ordered = list(dict.fromkeys(case_ids))
    rng.shuffle(ordered)
    return ordered

